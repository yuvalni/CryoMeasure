from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QLineEdit, QCheckBox,
                               QGroupBox, QGridLayout, QFileDialog)
from pyqtgraph import PlotWidget
import pyqtgraph as pg




import numpy as np
import pandas as pd
from queue import Queue
from threading import Event, Lock
import logging
from PySide6.QtCore import Qt

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


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Measurement Control GUI")

        # Main layout
        main_layout = QVBoxLayout(self)

        # Sample name and file selection
        sample_layout = QHBoxLayout()
        self.sample_name_input = QLineEdit()
        self.sample_name_input.setPlaceholderText("Sample name")
        file_button = QPushButton("Choose File")
        file_button.clicked.connect(self.choose_file)
        sample_layout.addWidget(self.sample_name_input)
        sample_layout.addWidget(file_button)
        main_layout.addLayout(sample_layout)

        # Temperature Display
        temp_display = QLabel("Temperature:[K]")
        temp_display.setStyleSheet("background-color: lightblue; font-size: 20px; text-align: center;")
        temp_display.setFixedSize(150, 80)

        # Current Control Group
        current_group = QGroupBox("Current Control")
        current_layout = QGridLayout()
        current_group.setLayout(current_layout)
        
        current_layout.addWidget(QLabel("Current [mA]"), 0, 0)
        self.current_input = QLineEdit("0.1")
        current_layout.addWidget(self.current_input, 0, 1)

        current_layout.addWidget(QLabel("Voltage Compliance [V]"), 1, 0)
        self.voltage_compliance_input = QLineEdit("2")
        current_layout.addWidget(self.voltage_compliance_input, 1, 1)

        current_layout.addWidget(QLabel("NPLC"), 2, 0)
        self.nplc_input = QLineEdit("5")
        current_layout.addWidget(self.nplc_input, 2, 1)

        set_current_button = QPushButton("Set")
        current_layout.addWidget(set_current_button, 3, 0, 1, 2)

        # Channel Selection
        channel_selection_group = QGroupBox("Channels")
        channel_layout = QVBoxLayout()
        channel_selection_group.setLayout(channel_layout)

        self.channel_checkboxes = []
        for i in range(1, 5):
            checkbox = QCheckBox(f"{i}")
            checkbox.setChecked(True)    
            self.channel_checkboxes.append(checkbox)
            channel_layout.addWidget(checkbox)

        for i in range(4):
            self.channel_checkboxes[i].stateChanged.connect(lambda state,index=i+1: self.change_channels(index, state ))

        #set_channel_button = QPushButton("Set")
        #channel_layout.addWidget(set_channel_button)

        # Temperature Control
        temperature_group = QGroupBox("Temperature")
        temperature_layout = QGridLayout()
        temperature_group.setLayout(temperature_layout)
        
        temperature_layout.addWidget(QLabel("Set Point [K]"), 0, 0)
        self.set_point_input = QLineEdit()
        temperature_layout.addWidget(self.set_point_input, 0, 1)

        temperature_layout.addWidget(QLabel("Rate [K/min]"), 1, 0)
        self.rate_input = QLineEdit()
        temperature_layout.addWidget(self.rate_input, 1, 1)

        set_temp_button = QPushButton("Set")
        temperature_layout.addWidget(set_temp_button, 2, 0, 1, 2)

        # PID Control
        pid_group = QGroupBox("PID")
        pid_layout = QGridLayout()
        pid_group.setLayout(pid_layout)
        
        pid_layout.addWidget(QLabel("P"), 0, 0)
        self.p_input = QLineEdit("1")
        pid_layout.addWidget(self.p_input, 0, 1)

        pid_layout.addWidget(QLabel("I"), 1, 0)
        self.i_input = QLineEdit("0")
        pid_layout.addWidget(self.i_input, 1, 1)

        pid_layout.addWidget(QLabel("D"), 2, 0)
        self.d_input = QLineEdit("0")
        pid_layout.addWidget(self.d_input, 2, 1)

        self.pid_checkbox = QCheckBox("PID on")
        pid_layout.addWidget(self.pid_checkbox, 3, 0, 1, 2)

        set_pid_button = QPushButton("Set PID")
        pid_layout.addWidget(set_pid_button, 4, 0, 1, 2)

        # PID Output Indicator
        pid_output_label = QLabel("Output [%]:")
        self.pid_output_display = QLabel("0.0")
        self.pid_output_display.setStyleSheet("background-color: lightgray; padding: 5px;")
        pid_layout.addWidget(pid_output_label, 5, 0)
        pid_layout.addWidget(self.pid_output_display, 5, 1)

        # Graph Plot
        self.graph = PlotWidget()
        self.graph.addLegend()
        self.graph.setLabel("left", "Temperature", units="K")
        self.graph.setLabel("bottom", "Time", units="s")

        # Start/Stop Buttons
        button_layout = QHBoxLayout()
        start_button = QPushButton("Start")
        stop_button = QPushButton("Stop")
        button_layout.addWidget(start_button)
        button_layout.addWidget(stop_button)

        # Arrange all widgets into the main layout
        control_layout = QHBoxLayout()
        control_layout.addWidget(current_group)
        control_layout.addWidget(channel_selection_group)
        control_layout.addWidget(temp_display)
        control_layout.addWidget(temperature_group)
        control_layout.addWidget(pid_group)

        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.graph)
        main_layout.addLayout(button_layout)

    def choose_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Data File", "", "All Files (*)")
        if file_name:
            self.sample_name_input.setText(file_name)



    def change_channels(self,id,state):
        #print(state)
        checked = state== Qt.CheckState.Checked.value
        #print(Qt.CheckState.Unchecked.value)
        #print(Qt.CheckState.Checked.value)
        if checked:
            Channel_list.append(id)
            Channel_list.sort()
        else:
            Channel_list.remove(id)
        print(Channel_list)


    def update_keithley_parameters(self,sourcemeter):
        #current,compliance,nplc = transport_parameter_q.get(block=False)
        #take this from gui
        sourcemeter.compliance_voltage = compliance
        sourcemeter.source_current = current/1000
        sourcemeter.voltage_nplc = nplc

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
    
    def Temp_loop():
        #need to handle gui right
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
if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
