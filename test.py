from Keithley196V2 import Keithley196
k196 = Keithley196()
from CryoMeasure import *
start_cont_measure(0.001,2,0.5,'yuval_test',0.01,k196)