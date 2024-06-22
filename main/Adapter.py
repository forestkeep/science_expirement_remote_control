import pyvisa
import serial
from serial import Serial
import enum
import logging

logger = logging.getLogger(__name__)

class resourse(enum.Enum):
    serial = 1
    pyvisa = 2

class Adapter():
    def __init__(self, sourse, baud = 9600, timeout: float = 1) -> None:
        self.client = None
        self.baudrate = baud
        self.which_resourse = None
        self.is_open = False
        self.timeout = timeout

        if "COM" in sourse:
            self.client = Serial(sourse, self.baudrate, timeout=self.timeout)
            self.which_resourse = resourse.serial
            self.is_open = self.client.is_open
        else:
            rm = pyvisa.ResourceManager()
            self.client = rm.open_resource(sourse)
            self.which_resourse = resourse.pyvisa

    def __del__(self):
        try:
            self.close()
        except:
            pass

    def close(self):
        if self.which_resourse == resourse.serial:
            self.client.close()
            self.is_open = self.client.is_open
        elif self.which_resourse == resourse.pyvisa:
            self.client.close()
        else:
            raise AdapterException("unknown resource")

    def write(self, data):
        if self.which_resourse == resourse.serial:
            try:
                ans = self.client.write(data)
            except:
                ans = self.client.write(data.encode())
            return ans
        elif self.which_resourse == resourse.pyvisa:
            ans = self.client.write(data)
            return ans
        else:
            raise AdapterException("unknown resource")

    def open(self):
        if self.which_resourse == resourse.serial:
            self.client.open()
            self.is_open = self.client.is_open
        elif self.which_resourse == resourse.pyvisa:
            self.client.open()
        else:
            raise AdapterException("unknown resource")

    def read(self, num_bytes):
        if self.which_resourse == resourse.serial:
            return self.client.read(size=num_bytes)
        elif self.which_resourse == resourse.pyvisa:
            self.client.read(count=num_bytes)
        else:
            raise AdapterException("unknown resource")

    def readline(self):
        if self.which_resourse == resourse.serial:
            return self.client.readline()
        elif self.which_resourse == resourse.pyvisa:
            return self.client.read_raw()
        else:
            raise AdapterException("unknown resource")
        

class instrument():

    @staticmethod
    def get_com_ports() -> list:
        tr = 9
        ports = []
        for port in serial.tools.list_ports.comports():
                ports.append(port.device)
        tr+=10
        return ports, tr
    
    @staticmethod
    def get_available_com_ports() -> list:
        ports = []
        for port in serial.tools.list_ports.comports():
            try:
                ser = serial.Serial(port.device)
                ports.append(port.device)
                ser.close()
            except (OSError, serial.SerialException):
                pass
        return ports
    
    @staticmethod
    def get_visa_resourses() -> list:
        res = pyvisa.ResourceManager().list_resources()
        return res
    
    @staticmethod
    def get_resourses() -> list:
        '''return all available resourses'''
        ports = instrument.get_available_com_ports()
        res_vis = instrument.get_visa_resourses()
        for res in res_vis:
            if "ASRL" in res:
                pass
            else:
                ports.append(res)
        return ports
    
class AdapterException(Exception):
    def __init__(self, message):
        super().__init__(message)


if __name__ == "__main__":
    adapter = Adapter("COM7", 9600)
    adapter.write()
    print()
    print(instrument.get_resourses())
    pass