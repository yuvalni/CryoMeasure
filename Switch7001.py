import pyvisa


class Switch():
    def __init__(self, address='GPIB0::6::INSTR'):
        self.inst = pyvisa.ResourceManager().open_resource(address)

    def initialize(self):
        #TODO: What is this for?
        #self.inst.write(':syst: pres')
        self.inst.write('*CLS')

    def Open_all_Channels(self):
        self.inst.write(':OPEN ALL')

    def Open_Channel(self, ch):
        self.inst.write(':OPEN (@2!{0})'.format(ch))

    def Close_Channel(self, ch):
        self.inst.write(':CLOSe (@2!{0})'.format(ch))

    def Channel_State(self):
        return self.inst.quary(':CLOSe:STATe?')
    '''This query command is used to request the channels that are currently closed. For example if
    channels 1!2!3 and 2!36 are closed, the following message will be sent to the computer after
    sending this command and addressing the Model 7001 to talk:
    '(@2!2:2!3,2!5)\n'
    '''

    def read_error(self):
        return self.inst.query(':syst:err?')