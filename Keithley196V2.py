import pyvisa


class Keithley196():
    def __init__(self,address='GPIB0::7::INSTR'):
        self.inst = pyvisa.ResourceManager().open_resource(address)
        self.poly_fit = [0.0,1.0,2.0] #a,b,c,d of polynom
        # set range!!

    def poly(self, x):
        ans = 0
        for n, a in enumerate(self.poly_fit):
            ans += a * x ** n
        return ans

    def get_voltage(self):
        string = self.inst.query('*IDN?')
        return float(string.replace('\r\n','').replace('NDCV',''))


    def getTemp(self):
        #assuming 10 uA - as calibration
        return self.poly(self.get_voltage())

    def close(self):
        self.inst.close()