import eel
import numpy
import pandas as pd
from queue import Queue
from threading import Event, Lock
import random
import numpy as np
import logging
import os
from time import sleep
from datetime import datetime as dt

import serial
from pymeasure.instruments.keithley import Keithley2400
from Keithley196V2 import Keithley196 as K196
from Switch7001 import Switch
import csv
from simple_pid import PID

RT_data_q = Queue()

q_temp = Queue()
#Tq = Queue()
HeaterOutput_Q = Queue()
transport_parameter_q = Queue(maxsize=1)
Channel_list = []

halt_meas = Event()
stop_RT = Event()
stop_T = Event()
setpoint_changed = Event()
ramp_rate_changed = Event()
pid_changed = Event()

measurement_lock = Event()

error = Event()
error_name = 'No error'
cooling_timeout = 3600

setPoint = 280
ramp_setpoint = 0
ramp_rate = 0
Channel_list = [1,2,3,4]
Temperature = -999
Temp_rate = 0.01
eel.init('web')



@eel.expose
def change_channels(id,checked):
    if checked:
        Channel_list.append(id)
        Channel_list.sort()
    else:
        Channel_list.remove(id)
    print(Channel_list)


@eel.expose
def set_channels(channels):
    Channel_list = channels
    print(Channel_list)

@eel.expose
def update_transport(current,compliance,nplc):
    if transport_parameter_q.full():
        transport_parameter_q.get(block=False)
    transport_parameter_q.put((current,compliance,nplc),block=False) #we never want to block exectution
    print(current,compliance,nplc)

def update_keithley_parameters(sourcemeter):
    current,compliance,nplc = transport_parameter_q.get(block=False)
    sourcemeter.compliance_voltage = compliance
    sourcemeter.source_current = current/1000
    sourcemeter.voltage_nplc = nplc
    print("Updated")

def initialize_file(file_name,path=r"C:\Users\Amit\Documents\RT data"):
    logging.debug('path is {}'.format(path))
    print(path)
    file_path = os.path.join(path,"{}_RT.csv".format(file_name))
    i=1
    while os.path.exists(file_path):
        file_path = os.path.join(path,"{}_RT".format(file_name)+str(i)+".csv")
        i = i +1
    csv_file = open(file_path, 'w', newline='')
    fieldnames = ['Temperature','Resistance 1 [Ohm]','current 1 [mA]','Resistance 2 [Ohm]','current 2 [mA]','Resistance 3 [Ohm]','current 3 [mA]','Resistance 4 [Ohm]','current 4 [mA]','Time','Cernox_Resistance [Ohm]']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    return csv_file, writer

def initialize_IV_file(file_name,path=r"C:\Users\Amit\Documents\RT data"):
    logging.debug('path is {}'.format(path))
    print(path)
    file_path = os.path.join(path,"{}_IV.csv".format(file_name))
    i=1
    while os.path.exists(file_path):
        file_path = os.path.join(path,"{}_IV".format(file_name)+str(i)+".csv")
        i = i +1
    csv_file = open(file_path, 'w', newline='')
    fieldnames = ['Temperature','Voltage 1 [V]','current 1 [mA]', 'Voltage 2 [V]','current 2 [mA]','Voltage 3 [V]','current 3 [mA]','Voltage 4 [V]','current 4 [mA]','Time']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    return csv_file, writer


def initialize_keithley2400(I,V_comp,nplc,current_range=0.01,voltage_range = 0.1,address="GPIB1::16::INSTR"):
    #transport_parameter_q.get(block=False) #if there is some update for keithley for some reason- remove it.
    assert nplc > 0.01 and nplc <= 10
    V_comp = float(V_comp)
    nplc = float(nplc)
    I = float(I)
    sourcemeter = Keithley2400(address)
    sourcemeter.reset()
    #setting current params
    sourcemeter.use_front_terminals()
    eel.sleep(10/1000)
    sourcemeter.wires = 4  # set to 4 wires
    eel.sleep(10 / 1000)
    sourcemeter.apply_current(current_range=None, compliance_voltage=V_comp)
    eel.sleep(10 / 1000)
    sourcemeter.source_current = I
    eel.sleep(10 / 1000)

    #setting voltage read params
    sourcemeter.measure_voltage(nplc,voltage_range,auto_range=True)
    sleep(10 / 1000)
    sourcemeter.write(":SYST:BEEP:STAT OFF")

    #Checking for errors
    error_name = sourcemeter.error
    if not error_name[1] =='No error':
        error.set()
    return sourcemeter

def initialize_Switch(address="GPIB::16"):
    switch = Switch()
    switch.initialize()
    switch.Open_all_Channels()
    #TODO: FIX errors things

    # Checking for errors
    #error_name = sourcemeter.error #need to change to the right code
    #if not error_name[1] == 'No error':
    #    error.set()
    return switch



def measure_resistance(sourcemeter,AC=True):
    sourcemeter.enable_source() #should set current on
    eel.sleep(0.001)
    V_p = sourcemeter.voltage
    I = sourcemeter.source_current  # needs to measure not just say what is configure!!
    if not AC:
        sourcemeter.disable_source()
        if I == 0:
            return -999, 0
        else:
            return (V_p / I), I
    sourcemeter.source_current = - sourcemeter.source_current
    eel.sleep(0.001)
    V_m = sourcemeter.voltage
    I = -sourcemeter.source_current #needs to measure not just say what is configure!!
    sourcemeter.source_current = I
    #sourcemeter.shutdown() # turning the current off. not the device!
    sourcemeter.disable_source()

    # Checking for errors
    error_name = sourcemeter.error  # need to change to the right code
    if not error_name[1] == 'No error':
        error.set()

    if I == 0:
        return -999, 0
    else:
        return (V_p - V_m)/(2*I),I

def measure_voltage(sourcemeter,current):
    sourcemeter.source_current = current
    eel.sleep(0.001)
    V = sourcemeter.voltage
    sourcemeter.disable_source()
    return V




def Temp_loop():
    global Temperature
    global setPoint
    global PID_On
    global P,I,D
    setPoint=0
    P = 1
    I = 0
    D = 0
    PID_On = False
    HeaterOutput = 0
    pid = PID(P,I,D,setpoint=setPoint)
    pid.sample_time = Temp_rate
    pid.output_limits = (0,100)

    meter_196 = K196()

    while True:
        #We need to be able to change setpoint and PID_on inside the loop.
        #Use a queue? maybe a global variable?
        if setpoint_changed.is_set():
            pid.setpoint = setPoint
            eel.send_SP_data(setPoint)
            setpoint_changed.clear()
        if pid_changed.is_set():
            pid.Kp = P
            pid.Ki = I
            pid.Kd = D
            pid_changed.clear()
        Temperature = meter_196.getTemp()
        HeaterOutput = pid(Temperature)
        if PID_On:
            #print(HeaterOutput)
            HeaterOutput_Q.put(HeaterOutput)
        else:
            HeaterOutput_Q.put(0)


        #Tq.put(Temperature)
        eel.send_T_data(Temperature)
        eel.sleep(Temp_rate)


@eel.expose
def change_PID_setpoint(_set_point,_rate):
    # This maybe not a good idea. the setpoint should be set
    #within the python script as a part of rate
    #maybe add a setpoint option to the GUI?
    print("Set point changed to:")
    print(_set_point)
    print(_rate)
    global setPoint
    global ramp_setpoint
    global ramp_rate
    if float(_rate) ==0:
        setPoint = _set_point
        ramp_rate = 0
        setpoint_changed.set()
        ramp_rate_changed.set()
    else:
        ramp_rate = float(_rate)
        ramp_setpoint = float(_set_point)
        ramp_rate_changed.set()



@eel.expose
def change_PID_parameters(p,i,d):
    global P,I,D
    print("changed PID values:")
    print((p,i,d))
    if p:
        P = p
    if i:
        I = i
    if d:
        D = d
    pid_changed.set()

@eel.expose
def toggle_PID_ON(_state):
    global PID_On
    print("PID state: " + _state)
    PID_On = _state



def TempRateLoop():
    """ This get a rate from the gui, and changes setpoint with time"""
    global ramp_setpoint
    global ramp_rate
    global setPoint
    rate = ramp_rate
    while True:
        eel.sleep(0.1)
        if ramp_rate_changed.is_set():
            rate = ramp_rate
            sp = ramp_setpoint
            direction = (sp-setPoint)/abs((sp-setPoint)) #1 if we need to warmup
            ramp_rate_changed.clear()
        if rate == 0:
            continue
        else:
            while(direction*setPoint<sp*direction): #if heating - setPoint is smaller then desired, else setpoint is higher
                #rate is in kelvin per minute. every second change with rate per second
                setPoint += rate/60.0 * direction
                setpoint_changed.set()
                eel.sleep(1.0)
                if(direction*setPoint>sp*direction):
                    #this to make sure the loop is ending exatcly on the end temperature
                    setPoint = sp
                    setpoint_changed.set()
                    break
                if ramp_rate_changed.is_set():
                    #if the temperature is set with rate 0 while in this loop, we want to break from it.
                    rate = ramp_rate
                    if rate ==0:
                        break
            rate = 0







def Handle_Output():
    """This takes the output value from Temperature loop and handle it.
    First Outpsetpointut to Heater, then  send value to the GUI."""
    try:
        ser = serial.Serial('COM5',baudrate=11520,timeout=1)
    except:
        print("could not connect to heater.")
        return False
    print("connected to Heater")
    max_Output = 100
    min_Output = 0
    while True:
        if not HeaterOutput_Q.empty():
            OP = HeaterOutput_Q.get()
            if OP > max_Output:
                OP = max_Output
            elif OP < min_Output:
                OP = min_Output
            ser.write("{}\n".format(int(OP)).encode())
            #print("Output: "+ str(OP))
            eel.send_OP_data(OP)
            #OP_actual = ser.readline()


        eel.sleep(0.01)



def Get_stable_temp(k196,rate,meas_num,start_temp,Std_bound):
    logging.info('get stable temp')
    eel.set_meas_status('get stable temp')
    print('Stabilizing the temperature')
    logging.debug('Stabilizing the temperature')

    T = measure_Temp(k196)
    rate = float(rate)
    Temp_vec = []
    start_temp = float(start_temp)
    if start_temp < 6: #We should find the real low temperature limit
        error_name =(0,'The start temperature is too low')
        error.set()
        return -999, -999
    eel.spawn(send_tmep_data_to_page)  ## start messaging function to the page
    go_time=dt.now()
    end_time=dt.now()
    while not abs(start_temp - T)<1 and not halt_meas.is_set() and not (end_time-go_time)<cooling_timeout:
        eel.sleep(0.1)
        T = measure_Temp(k196)
        q.put(T)  # sending to gui
        go_time = dt.now()
        # We need to add a max time for cooling as another condition to stop the while not loop
        # need to add temp control
    if (end_time-go_time) > cooling_timeout:
        error_name = (0, 'cooling_timeout')
        error.set()
        stop_T.set()
        return -999, -999

    Is_stable = 0
    go_time=dt.now()
    end_time=dt.now()
    while not Is_stable == 1 and not halt_meas.is_set() and not (end_time-go_time)<600:
        for i in range(meas_num):
            Temp_vec[i] = measure_Temp(meter_196)
            q.put(Temp_vec[i])  # sending to gui
            eel.sleep(float(rate))
        end_time = dt.now()
        mean_Temp = numpy.mean(Temp_vec)
        if numpy.std(Temp_vec) < Std_bound:
            Is_stable = 1
            stop_T.set()
            return mean_Temp, numpy.std(Temp_vec)
        else:
            Is_stable = 0
    if (end_time-go_time) > 600:
        error_name = (0, 'stabelizins timeout')
        error.set()
        stop_T.set()
        return -999, -999
    stop_T.set()

def Switch_to(ch, Switch):
    Switch.Open_all_Channels()
    Switch.Close_Channel(ch)

    # Checking for errors
    error_name = Switch.read_error()  # need to change to the right code
    if not error_name[1] == 'No error':
        error.set()
    return ch

@eel.expose
def halt_measurement():
    logging.info('sending stop command.')
    halt_meas.set()


def start_IV_measure(low_current,high_current,number_of_points,voltage_comp,nplc_speed,sample_name,rate):
    if measurement_lock.is_set():
        return False
    measurement_lock.set()
    nplc_speed = float(nplc_speed)
    current = float(current) * 10**-3 #converting mA from frontend to Ampere for device
    voltage_comp = float(voltage_comp)
    rate = float(rate)


    currents = np.linspace(float(low_current),float(high_current),float(number_of_points))

    logging.info('start IV meas.')
    eel.set_meas_status(True)
    stop_RT.clear()
    stop_T.clear()
    halt_meas.clear()
    csv_file, writer = initialize_IV_file(sample_name)
    #fieldnames = ['Temperature','Voltage 1 [V]','current 1 [mA]', 'Voltage 2 [V]','current 2 [mA]','Voltage 3 [V]','current 3 [mA]','Voltage 4 [V]','current 4 [mA]','Time']
    switch = initialize_Switch()
    keithley = initialize_keithley2400(current,voltage_comp,nplc_speed) # return keith2400 object
    print('start measurement')
    logging.debug('start measurement')
    eel.spawn(send_measure_data_to_page) ## start messaging function to the page
    eel.sleep(0.5)
        while not halt_meas.is_set():
            # get new ch list
            data = {}
            rows = [] # save all values and write them at once
            #data["Cernox_Resistance [Ohm]"] = meter_196.get_voltage() * 10**5
            #print("temperature: {}".format(data["Temperature"]))

            _Channel_list = Channel_list # update local channel list from global only before and after for loop
            for channel in _Channel_list:
                Switch_to(channel, switch)
                for current in currents:
                    data["Time"] = dt.now()
                    data["Temperature"] = Temperature
                    V= measure_voltage(keithley,current)
                    RT_data_q.put((current,V,channel))
                    #fix this:
                    data["Voltage {0} [V]".format(channel)] = V
                    data["current {0} [mA]".format(channel)] = current
                    rows.append(data) #gather rows
                    #print("R{0}: {1}".format(channel,(data["Resistance {0} [Ohm]".format(channel)])))

            for row in rows: #write all rows
                writer.writerow(row) #this takes a dictionary and fill in the columns
            if not transport_parameter_q.empty(): #there is update waiting
                update_keithley_parameters(keithley) #update!

            eel.sleep(rate)
            halt_meas.set() #this is just to avoid thinking

        halt_meas.clear()
        #TODO: here remove the lock
        stop_RT.set()
        stop_T.set()
        measurement_lock.clear()
        eel.set_meas_status(False)
        eel.enable_start_button()
        csv_file.close()

@eel.expose
def start_cont_measure(current,voltage_comp,nplc_speed,sample_name,rate,AC=True):
    if measurement_lock.is_set():
        return False
    measurement_lock.set()
    #TODO: HERE set a flag to lock start mesurements
    #TODO: Make sure that this function canot be called before lock is unset. either by creating a new function that calls this one,
    # or disabling the START button in gui.
    nplc_speed = float(nplc_speed)
    current = float(current) * 10**-3 #converting mA from frontend to Ampere for device
    voltage_comp = float(voltage_comp)
    rate = float(rate)


    logging.info('start cont. meas.')
    eel.set_meas_status(True)
    stop_RT.clear()
    stop_T.clear()
    halt_meas.clear()
    csv_file, writer = initialize_file(sample_name)
    switch = initialize_Switch()
    keithley = initialize_keithley2400(current,voltage_comp,nplc_speed) # return keith2400 object
    print('start measurement')
    logging.debug('start measurement')
    eel.spawn(send_measure_data_to_page) ## start messaging function to the page
    eel.sleep(0.5)
    while not halt_meas.is_set():
        # get new ch list
        data = {}
        data["Temperature"] = Temperature
        #data["Cernox_Resistance [Ohm]"] = meter_196.get_voltage() * 10**5
        #print("temperature: {}".format(data["Temperature"]))
        data["Time"] = dt.now()
        _Channel_list = Channel_list # update local channel list from global only before and after for loop
        for channel in _Channel_list:
            Switch_to(channel, switch)
            R, I = measure_resistance(keithley,AC)
            RT_data_q.put((data["Temperature"],R,channel))
            data["Resistance {0} [Ohm]".format(channel)] = R
            data["current {0} [mA]".format(channel)] = I
            #print("R{0}: {1}".format(channel,(data["Resistance {0} [Ohm]".format(channel)])))

        writer.writerow(data) #this takes a dictionary and fill in the columns
        if not transport_parameter_q.empty(): #there is update waiting
            update_keithley_parameters(keithley) #update!

        eel.sleep(rate)

    halt_meas.clear()
    #TODO: here remove the lock
    stop_RT.set()
    stop_T.set()
    measurement_lock.clear()
    eel.set_meas_status(False)
    eel.enable_start_button()
    csv_file.close()

def send_measure_data_to_page():
    logging.debug('start sending')
    print('start sending.')
    while not stop_RT.is_set():
        if not RT_data_q.empty():
            value = RT_data_q.get()
            T, R, ch = value
            eel.update_channel(R, T, ch)
        else:
            eel.sleep(0.5)
    logging.debug('thread is exiting.')


eel.spawn(Temp_loop)
eel.spawn(Handle_Output)
eel.spawn(TempRateLoop)
eel.start('main.html')
