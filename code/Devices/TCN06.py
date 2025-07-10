import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pymodbus.client import ModbusSerialClient

from Devices.pid_temp_controller import pidController
from Devices.base_pid_temp_controller import chActPidController, chMeasPidController
logger = logging.getLogger(__name__)

class pidControllerTCN06(pidController):
    def __init__(self, name, installation_class) -> None:

        super().__init__(name, "modbus", installation_class)

        #определяем наши каналы и задаем им параметры
        self.ch1_act = chActPidController(
            1,
            self.name,
            message_broker=self.message_broker,
            max_temp=1000,
            min_temp=0,
        )
        self.ch1_meas = chMeasPidController(1, self.name, self.message_broker)
        self.channels = self.create_channel_array()

    #ниже прописываем свои функции, которые понадобятся для управления контроллером

    def _set_temperature(
        self, ch_num, voltage
    ) -> bool:  # в сотых долях вольта 20000 - 200В
        voltage *= 100
        response = self._write_reg(
            address=int("0040", 16), count=2, slave=1, values=[0, int(voltage)]
        )
        return response

    def _write_reg(self, address, count, slave, values) -> bool:
        if self.is_test == True:
            return self.client.write_registers(
                address=address, slave=slave, values=values
            )
        else:
            try:
                ans = self.client.write_registers(
                    address=address, slave=slave, values=values
                )
                if ans.isError():
                    return False
                else:
                    pass
            except Exception as e:
                logger.warning(f"ошибка записи регистров {str(e)}")
                return False
            return True

    def _read_current_parameters(self, address, count, slave):
        if self.is_test == True:
            return self.client.read_input_registers(
                address=address, count=count, slave=slave
            )
        else:
            try:
                ans = self.client.read_input_registers(
                    address=address, count=count, slave=slave
                )

                if ans.isError():
                    return False
                else:
                    return ans.registers
            except Exception as e:
                logger.warning(f"ошибка чтения регистров {str(e)}")
                return False

    def _get_current_temperature(self, ch_num):
        response = self._read_current_parameters(
            address=int("0000", 16), count=1, slave=1
        )
        if self.is_test == True:
            return response

        if response != False:
            response = response[0] / 100
        return response

    def _get_current_power_percent(self, ch_num):
        response = self._read_current_parameters(
            address=int("0001", 16), count=1, slave=1
        )
        if self.is_test == True:
            return response

        if response != False:
            pass
            response = response[0] / 100
        return response

    def _read_setting_parameters(self, address, count, slave):
        if self.is_test == True:
            return self.client.read_holding_registers(
                address=address, count=count, slave=slave
            )
        try:
            ans = self.client.read_holding_registers(
                address=address, count=count, slave=slave
            )

            if ans.isError():
                return False
            else:
                return ans.registers
        except Exception as e:
            logger.warning(f"ошибка чтения регистров {str(e)}")
            return False

    def _get_setting_temperature(self, ch_num):
        response = self._read_setting_parameters(
            address=int("0040", 16), count=2, slave=1
        )
        if self.is_test == True:
            return response

        if response != False:
            response = response[1] / 100
        return response

if __name__ == "__main__":
    import pickle
    client = ModbusSerialClient(
        port="COM5", baudrate=9600, stopbits=1, bytesize=8, parity="E"
    )

    pickle.dumps(client)
    client.close()