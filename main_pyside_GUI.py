from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QLineEdit, QCheckBox,
                               QGroupBox, QGridLayout, QFileDialog)
from pyqtgraph import PlotWidget
import pyqtgraph as pg
from PySide6 import Qt
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
        temp_display = QLabel("Temperature:\n[K]")
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

        set_channel_button = QPushButton("Set")
        channel_layout.addWidget(set_channel_button)

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






if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
