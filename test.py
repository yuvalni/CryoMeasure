from Keithley196V2 import Keithley196
k196 = Keithley196()
from CryoMeasure import *
start_cont_measure(10**-4,2,5,'BIN046',0.05,k196,AC=True)