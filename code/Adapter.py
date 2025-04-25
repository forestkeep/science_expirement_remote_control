# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

import enum
import logging
import time

import pyvisa
import serial
from serial import Serial
from serial.tools import list_ports
from profilehooks import profile

logger = logging.getLogger(__name__)

class resourse(enum.Enum):
    serial = 1
    pyvisa = 2

class Adapter:

    def __init__(self, sourse, baud=9600, timeout: float = 2000) -> None:

        logger.info(f"создаем адаптер {sourse=}")
        self.client = None
        self.baudrate = baud
        self.which_resourse = None
        self.is_open = False
        self.timeout = timeout
        self.name = sourse

        if "COM" in sourse:
            self.client = Serial(port = sourse, baudrate = self.baudrate, timeout=self.timeout / 1000)
            logger.info(f"client создан {self.client=}")
            self.which_resourse = resourse.serial
            self.is_open = self.client.is_open
        else:
            rm = pyvisa.ResourceManager()
            self.client = rm.open_resource(sourse)
            self.client.timeout = self.timeout
            self.which_resourse = resourse.pyvisa

    def __del__(self):
        try:
            self.close()
        except:
            pass

    def set_timeout(self, timeout: float):
        if isinstance(timeout, (float, int)) and timeout > 0:
            if self.which_resourse == resourse.serial:
                self.client.timeout = timeout / 1000
            elif self.which_resourse == resourse.pyvisa:
                self.client.timeout = timeout
            else:
                raise AdapterException("unknown resource")
        else:
            raise ValueError("Таймаут должен быть положительным числом.")

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

            if not isinstance(data, (list, tuple, str)):
                command = str(data)
            if self.client.write_termination in data:
                logger.debug(f"удаляем {self.client.write_termination=} из {data=}")
                data = data.replace(self.client.write_termination, "")
            ans = self.client.write(data)
            return ans
        else:
            raise AdapterException("unknown resource")

    def open(self):
        if self.which_resourse == resourse.serial:
            try:
                self.client.open()
            except serial.SerialException as e:
                pass
            self.is_open = self.client.is_open
        elif self.which_resourse == resourse.pyvisa:
            self.client.open()
        else:
            raise AdapterException("unknown resource")

    def read(self, num_bytes=10):
        if self.which_resourse == resourse.serial:
            return self.client.read(size=num_bytes)
        elif self.which_resourse == resourse.pyvisa:
            self.client.read()
        else:
            raise AdapterException("unknown resource")

    def readline(self):
        if self.which_resourse == resourse.serial:
            return self.client.readline()
        elif self.which_resourse == resourse.pyvisa:
            return self.client.read_raw()
        else:
            raise AdapterException("unknown resource")
    @profile(stdout=False, filename='baseline.prof')
    def query(self, command, timeout=False, end_symbol=False):
        '''timeout - ms'''
        if end_symbol:
            command = command + end_symbol
        if self.which_resourse == resourse.serial:
            if timeout:
                self.client.timeout = timeout/1000
            self.client.reset_input_buffer()
            try:
                self.client.write(command)
            except:
                self.client.write(command.encode())
            ans = self.client.readline()
            return ans
        elif self.which_resourse == resourse.pyvisa:
            if timeout:
                self.client.timeout = timeout

            if not isinstance(command, (list, tuple, str)):
                command = str(command)

            if self.client.write_termination in command:
                logger.debug(f"удаляем {self.client.write_termination=} из {command=}")
                command = command.replace(self.client.write_termination, "")
            return self.client.query(command)
        else:
            raise AdapterException("unknown resource")

    def query_ascii_values(self, command):
        if self.which_resourse == resourse.serial:
            return False
        elif self.which_resourse == resourse.pyvisa:
            return self.client.query_ascii_values(command)
        else:
            raise AdapterException("unknown resource")

    def read_raw(self):
        if self.which_resourse == resourse.serial:
            return self.client.readline()
        elif self.which_resourse == resourse.pyvisa:
            return self.client.read_raw()
        else:
            raise AdapterException("unknown resource")

class instrument:

    @staticmethod
    def get_com_ports() -> list:
        tr = 9
        ports = []
        for port in list_ports.comports():
            ports.append(port.device)
        tr += 10
        return ports, tr

    @staticmethod
    def get_available_com_ports() -> list:
        ports = []
        for port in list_ports.comports():
            try:
                ser = serial.Serial(port.device)
                ports.append(port.device)
                ser.close()
                del ser
            except Exception as e:
                pass
        return ports

    @staticmethod
    def get_visa_resourses() -> list:
        res = pyvisa.ResourceManager().list_resources()
        return res

    @staticmethod
    def get_resourses() -> list:
        """return all available resourses"""
        resourses = instrument.get_available_com_ports()
        res_vis = instrument.get_visa_resourses()
        for res in res_vis:
            if "ASRL" in res:
                pass
            else:
                resourses.append(res)
                
        return resourses

class AdapterException(Exception):
    def __init__(self, message):
        super().__init__(message)

if __name__ == "__main__":
    '''
    for i in range(4):
        res = instrument.get_visa_resourses()
        print(res)
        my = Adapter(res[0])
        my.write("*IDN?")
        time.sleep(1)
    '''
    import pickle
    client = Adapter("COM7", baud = 9600)
    client.close()
    print(pickle.dumps(client))
    command = ""
    while True:
        start = time.perf_counter()
        timeout = 100
        print(client.query("", timeout=timeout))
        print(time.perf_counter() - start)
    print(instrument.get_available_com_ports())
