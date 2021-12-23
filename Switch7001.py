import math

from device import Device


class Switch(Device):
    def __init__(self,host, connection_type="usb" ):
        super(Switch, self).__init__(connection_type=connection_type, host=host)

    def initialize(self, sMode):
        self.write(':syst: pres')
        self.write('*CLS')

    def Open_all_Channels(self):
        self.write(':OPEN ALL')

    def Open_Channel(self, ch):
        self.write(':OPEN {0}'.format(ch))

    def Close_Channel(self, ch):
        self.write(':CLOSe {0}'.format(ch))

    def Channel_State(self):
        return self.ask(':CLOSe:STATe?')
    '''This query command is used to request the channels that are currently closed. For example if
    channels 1!2!3 and 2!36 are closed, the following message will be sent to the computer after
    sending this command and addressing the Model 7001 to talk:
    (@1!2!3, 2!36)'''

    def read_error(self):
        return self.ask(':syst:err?')