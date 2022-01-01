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
from pymeasure.instruments.keithley import Keithley2400
from Keithley196V2 import Keithley196 as K196
from Switch7001 import Switch
import csv

q = Queue()
q_temp = Queue()
Channel_list = []
cmd_q = Queue()
data_q = Queue(maxsize = 1)
halt_meas = Event()
stop_RT = Event()
stop_T = Event()
error = Event()
error_name = 'No error'
cooling_timeout = 3600
Channel_list = []

eel.init('web')

#Main Script
  # initializing
    #file_path = initialize_file(file_name,path='defulet_path'):
    #Switch = initialize_Switch(Start_Channel,address="GPIB::16"):
#    k196 = initialize_Keithley196(voltage_range = 0.001,address="GPIB::16"):
 # geting rady to measure
    #mean_Temp, std_temp = Get_stable_temp(meter_196,rate,meas_num,start_temp,Std_bound)
 # measuring

def initialize_file(file_name,path=r"C:\Users\Amit\Documents\RT data"):
    logging.debug('path is {}'.format(path))
    print(path)
    file_path = os.path.join(path,"{}_RT.csv".format(file_name))
    i=1
    while os.path.exists(file_path):
        file_path = os.path.join(path,"{}_RT".format(file_name)+str(i)+".csv")
        i = i +1
    csv_file = open(file_path, 'w', newline='')
    fieldnames = ['Temperature','Resistance 1 [Ohm]','current 1 [mA]','Resistance 2 [Ohm]','current 2 [mA]','Resistance 3 [Ohm]','current 3 [mA]','Resistance 4 [Ohm]','current 4 [mA]','Time']
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    return csv_file, writer


def initialize_keithley2400(I,V_comp,nplc,current_range=0.01,voltage_range = 0.001,address="GPIB0::16::INSTR"):
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
    sourcemeter.apply_current(current_range,V_comp)
    eel.sleep(10 / 1000)
    sourcemeter.source_current = I
    eel.sleep(10 / 1000)

    #setting voltage read params
    sourcemeter.measure_voltage(nplc,voltage_range,False)
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


def measure_resistance(sourcemeter):
    sourcemeter.enable_source() #should set current on
    eel.sleep(0.001)
    V_p = sourcemeter.voltage
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


def halt_measurement():
    logging.info('sending stop command.')
    halt_meas.set()

@eel.expose
def start_cont_measure(current,voltage_comp,nplc_speed,sample_name,rate,meter_196):
    rate = float(rate)
    logging.info('start cont. meas.')
    #eel.set_meas_status('start cont. meas.')
    stop_RT.clear()
    halt_meas.clear()
    csv_file, writer = initialize_file(sample_name)
    switch = initialize_Switch()
    keithley = initialize_keithley2400(current,voltage_comp,nplc_speed) # return keith2400 object
    print('start measurement')
    logging.debug('start measurement')
    #eel.spawn(send_measure_data_to_page) ## start messaging function to the page


    Channel_list = [1,2,3,4] #this is temporary
    while not halt_meas.is_set():
        # get new ch list
        data = {}
        data["Temperature"] = meter_196.getTemp()
        data["Time"] = dt.now()
        _Channel_list = Channel_list # update local channel list from global only before and after for loop
        for channel in _Channel_list:
            Switch_to(channel, switch)
            R, I = measure_resistance(keithley)
            data["Resistance {0} [Ohm]".format(channel)] = R
            data["current {0} [mA]".format(channel)] = I

        #eel.send_data(data) #we need to write this function
        writer.writerow(data) #this takes a dictionary and fill in the columns
        eel.sleep(rate)

    halt_meas.clear()
    stop_RT.set()
    eel.set_meas_status('idle.')
    csv_file.close()

    def send_measure_data_to_page():
        logging.debug('start sending')
        print('start sending.')
        while not stop_RT.is_set():
            if not q.empty():
                value = q.get()
                T, R = value
                print(T, R)
                eel.get_RT_data(T, R)
            else:
                eel.sleep(0.5)
        logging.debug('thread is exiting.')


    def send_temp_data_to_page():
        logging.debug('start sending')
        print('start sending.')
        while not stop_T.is_set():
            if not q.empty():
                value = q.get()
                Temp= value
                print(Temp)
                eel.send_T_data(Temp)
            else:
                eel.sleep(0.5)
        logging.debug('thread is exiting.')


def end_measurement(s):
    halt_meas.clear()
    eel.toggle_start_measure()
    stop_RT.set() #kill eel messagin thread
    s.send(b'disconnect')
    s.close()
    logging.debug('Closed connection to Dyna')
    eel.change_connection_ind(False)


#def Switch_from_to(a, b, Switch):
    # open_Channel(a)
    # close_Channel(b)

    # Checking for errors
#   error_name = sourcemeter.error  # need to change to the right code
#  if not error_name[1] == '':
#        error.set()
# return b
