import serial
import time

RESET = "*RST"
STATUS_BYTE = "*STB"
DEV_ID = "*IDN"


Voltage_meas = "MEAS:VOLT?"  # MEASURE:VOLTAGE:DC?
Current_meas = "MEAS:CURR?"  # MEASURE:CURRENT:DC?


class commmsnds():
    def open_port(self):
        if self.client.is_open == False:
            self.client.open()

    def select_channel(self, channel):
        self.open_port()
        self.client.write(f'INST CH{channel}\n'.encode())



    def __init__(self) -> None:
        self.client = serial.Serial("COM11", 9600, timeout=1)

    def _set_voltage(self, channel, voltage):
        self.open_port()
        self.select_channel(channel)
        self.client.write(f'VOLT {voltage}\n'.encode())
        self.client.write(f'VOLT?\n'.encode())
        response = self.client.readline().decode().strip()
        try:
            response = float(response)
        except:
            response = False
        self.client.close()
        return  response == voltage

    def _set_current(self, channel, current):
        self.open_port()
        self.select_channel(channel)
        self.client.write(f'CURR {current}\n'.encode())
        self.client.write(f'CURR?\n'.encode())
        response = self.client.readline().decode().strip()
        try:
            response = float(response)
        except:
            response = False
        self.client.close()
        return  response == current

    def _output_switching_on(self, channel):
        self.open_port()
        self.client.write(f'OUTP CH{channel},ON\n'.encode())
        self.client.close()

    def _output_switching_off(self, channel):
        self.open_port()
        self.client.write(f'OUTP CH{channel},OFF\n'.encode())
        self.client.close()

    def _get_current_voltage(self, channel):
        self.open_port()
        self.select_channel(channel)
        self.client.write(f'MEAS:VOLT?\n'.encode())
        response = self.client.readline().decode().strip()
        try:
            response = float(response)
        except:
            response = False
        self.client.close()
        return  response

    def _get_current_current(self, channel):
        self.open_port()
        self.select_channel(channel)
        self.client.write(f'MEAS:CURR?\n'.encode())
        response = self.client.readline().decode().strip()
        try:
            response = float(response)
        except:
            response = False
        self.client.close()
        return  response

    def _get_setting_voltage(self, channel):
        self.open_port()
        self.select_channel(channel)
        self.client.write(f'VOLT?\n'.encode())
        response = self.client.readline().decode().strip()
        try:
            response = float(response)
        except:
            response = False
        self.client.close()
        return  response

    def _get_setting_current(self, channel):
        self.open_port()
        self.select_channel(channel)
        self.client.write(f'CURR?\n'.encode())
        response = self.client.readline().decode().strip()
        try:
            response = float(response)
        except:
            response = False
        self.client.close()
        return   response
    
    def read_port(self):
        self.open_port()
        return self.client.readline().decode().strip()


if __name__ == "__main__":
        
        client = serial.Serial("COM16", 9600, timeout=1)
        #client.write(10)
        ans = 0b01111111
        ans+=0b00000001
        rr = 0x0

        print(ans)
        tmpBuffer = 128
        print(chr(rr))
        client.write(1)
        '''


        dev = commmsnds()


        dev._set_voltage(2, 12.366)
        dev._output_switching_on(2)
        while True:
            print("V=",dev._get_current_voltage(2))
            i = 0
            while i< 10:
                print(dev.read_port())
                time.sleep(0.1)
                i+=1
            print("A=", dev._get_current_current(2))
            i = 0
            while i< 10:
                print(dev.read_port())
                time.sleep(0.1)
                i+=1
           
        '''
        '''
        for i in range(3):
            dev._output_switching_on(i+1)
            time.sleep(1)
            dev._output_switching_off(i+1)
        '''
        '''
        dev.read_current(1)
        dev.read_voltage(1)

        dev.read_set_current(1)

        dev.read_set_voltage(1)

        dev.set_current(1, 5.23)

        dev.set_voltage(1, 21.52)
        '''

'''
SCPI Command

Description

MEASure Subsystem

MEASure:VOLTage? Measures and returns the average voltage at the sense location

MEASure:CURRent? Measures and returns the average current at the sense location

OUTPut Subsystem

OUTPut? Provides the output state of the product

OUTPut:ARM Enables or disables ARM functionality for auto-sequencing

OUTPut:START Enables the power processing circuitry in the product to begin producing output

OUTPut:STOP Disables the power processing circuitry in the product to stop producing output

OUTPut:PROTection:CLEar Reset soft faults

SOURce Subsystem

VOLTage and VOLTage:TRIGgered Sets the voltage set-point

VOLTage:PROTection Sets the over voltage trip (OVT) set-point

CURRent and CURRent:TRIGgered Sets the current set-point

CURRent:PROTection Sets the over current trip (OCT) set-point

PERiod Sets the time period for present auto-sequencing memory step

RECall:MEMory Selects a memory location for auto-sequencing

CONFigure Subsystem

CONTrol:INTernal Configures the ability start, stop, arm, and clear via the front panel

CONTrol:EXTernal Configures the ability start, stop, arm, and clear via digital inputs and computer command

REMote:SENSe Configures the sense location and automated compensation values

INTErlock Configures the product’s interlock functionality

CONFigure:SETPT Configures from which interface the product receives its set points

SYSTtem Subsystem

SYSTem:VERSion? Returns hardware revision and firmware version

SYSTem:ERRor? Returns error type and message

SYSTem:COMMunicate:NETwork:MAC? Returns MAC address

SYSTem:COMMunicate:NETwork:SER Returns Ethernet module serial number

SYSTem:COMMunicate:NETwork:ADDRess Set the static IP address

SYSTem:COMMunicate:NETwork:GATE Set the Gateway IP address

SYSTem:COMMunicate:NETwork:SUBNet Set the subnet IP Mask address

SYSTem:COMMunicate:NETwork:PORT Set the socket number

SYSTem:COMMunicate:NETwork:HOSTname Return hostname

SYSTem:COMMunicate:NETwork:DHCP Set DHCP operation mode

SYSTem:COMMunicate:GPIB:VERSion Returns firmware version of GPIB module

SYSTem:COMMunicate:GPIB:ADDRess Returns address of GPIB module

STATus Subsystem

*CLS Clear all status registers

*ESE? Configure Event Status Enable Register

*ESR? Read Event Status Register

*ESR? Bit values for the running state

*IDN? Product identification

*OPC Operation Complete Bit

STATus:OPERation:CONDition? Returns the value of the Operation Status register

STATus:QUEStionable:CONDition? Returns the value of the Questionable Status register

*RST Reset to factory default states

*SRE Service Request Enable Register

*STB Status Byte
'''
