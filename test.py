from Keithley196V2 import Keithley196
k196 = Keithley196()
from CryoMeasure import *
start_cont_measure(10**-5,2,5,'second_cooling_measurement_roughing_pump',0.05,k196,AC=False)