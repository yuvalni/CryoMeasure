import pyvisa
from datetime import datetime as dt

class Keithley196():
    def __init__(self,address='GPIB0::7::INSTR'):
        self.inst = pyvisa.ResourceManager().open_resource(address)
        self.poly_fit_HighTemp = [2.266093970179639e+03,-74.679741502403559,1.306792649962983,-0.014094956469091,9.945749933401484e-05,-4.688871397124473e-07,1.466123461743109e-09,-2.920818817154983e-12,3.357507675208470e-15,-1.695097455234765e-18] #a,b,c,d of polynom
        self.poly_fit_MedTemp = [3.847885862700156e+02,-2.857599908816134,0.011208582325180,-2.682987830440934e-05,4.071137070332167e-08,-3.857907847124153e-11,2.087523622701420e-14,-4.426803462142916e-18,-9.650337680202309e-22,4.910997020133234e-25]
        self.poly_fit_LowTemp = [1.474961505714320e+02,-0.514009200082837,9.478152337631471e-04,-1.095475294340138e-06,8.431608728251271e-10,-4.398065114076154e-13,1.538071005155538e-16,-3.455037124618886e-20,4.505799905786075e-24,-2.592838468122653e-28]  # a,b,c,d of polynom

        self.poly_high_limits = (0,326.48) #Ohms
        self.poly_med_limits = (307.17, 1044.19)  # Ohms
        self.poly_low_limits = (835.894, 3000)  # Ohms

        # set range!!
        self.flag = 0

    def poly(self, x,poly):
        ans = 0
        for n, a in enumerate(poly):
            ans += a * x ** n
        return ans

    def get_voltage(self):
        string = self.inst.query('*IDN?')
        return float(string.replace('\r\n','').replace('NDCV',''))


    def getTemp(self):
        #assuming 10 uA - as calibration
        voltage = self.get_voltage()
        if voltage > self.poly_low_limits[0] * 10**-5:
            return self.poly(voltage*(10**5), self.poly_fit_LowTemp)
        elif voltage > self.poly_med_limits[0] * 10**-5:
            return self.poly(voltage * (10 ** 5), self.poly_fit_MedTemp)
        else:
            return self.poly(voltage * (10 ** 5), self.poly_fit_HighTemp)


    def close(self):
        self.inst.close()
