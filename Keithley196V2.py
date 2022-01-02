import pyvisa
from datetime import datetime as dt

class Keithley196():
    def __init__(self,address='GPIB0::7::INSTR'):
        self.inst = pyvisa.ResourceManager().open_resource(address)
        self.poly_fit_HighTemp = [2.266093970179639e+03,-74.679741502403559,1.306792649962983,-0.014094956469091,9.945749933401484e-05,-4.688871397124473e-07,1.466123461743109e-09,-2.920818817154983e-12,3.357507675208470e-15,-1.695097455234765e-18] #a,b,c,d of polynom
        self.poly_fit_MedTemp = []
        self.poly_fit_LowTemp = []  # a,b,c,d of polynom

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
        if voltage<(2.909943652343750e+2)*(10**-5): #if temperature is higher then ~60K use high temp polynom
            return self.poly(voltage*(10**5), self.poly_fit_HighTemp)
        if self.flag==0:
            print('Low Temp Poly',dt.now())
            self.flag = 1
        return self.poly(voltage * (10 ** 5), self.poly_fit_LowTemp)


    def close(self):
        self.inst.close()