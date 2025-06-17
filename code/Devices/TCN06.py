import logging
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pymodbus.client import ModbusSerialClient

from Devices.power_supply_class import power_supply
from Devices.base_power_supply import chActPowerSupply, chMeasPowerSupply
logger = logging.getLogger(__name__)


class maishengPowerClass(power_supply):
    def __init__(self, name, installation_class) -> None:

        super().__init__(name, "modbus", installation_class)

        #определяем наши каналы и задаем им параметры
        self.ch1_act = chActPowerSupply(
            1,
            self.name,
            message_broker=self.message_broker,
            max_current=15,
            max_voltage=200,
            max_power=600,
            min_step_A=0.01,
            min_step_V=0.01,
            min_step_W=1,
        )
        self.ch1_meas = chMeasPowerSupply(1, self.name, self.message_broker)
        self.channels = self.create_channel_array()

    #ниже прописываем свои функции, которые понадобятся для управления контроллером

    def _set_voltage(
        self, ch_num, voltage
    ) -> bool:  # в сотых долях вольта 20000 - 200В
        voltage *= 100
        response = self._write_reg(
            address=int("0040", 16), count=2, slave=1, values=[0, int(voltage)]
        )
        return response

    def _set_current(self, ch_num, current) -> bool:  # в сотых долях ампера
        current *= 100
        response = self._write_reg(
            address=int("0041", 16), count=2, slave=1, values=[0, int(current)]
        )
        return response

    def _output_switching_on(self, ch_num) -> bool:
        response = self._write_reg(
            address=int("0042", 16), count=2, slave=1, values=[0, 1]
        )
        return response

    def _output_switching_off(self, ch_num) -> bool:
        response = self._write_reg(
            address=int("0042", 16), count=2, slave=1, values=[0, 0]
        )
        return response

    def _set_frequency(self, ch_num, frequency) -> bool:
        """удаленная настройка выходной частоты в Гц"""
        high = 0
        if frequency > 65535:
            high = 1
        frequency = frequency - 65535 - 1
        response = self._write_reg(
            address=int("0043", 16), count=2, slave=1, values=[high, frequency]
        )
        return response

    def _set_duty_cycle(self, ch_num, duty_cycle) -> bool:
        if duty_cycle > 100 or duty_cycle < 1:
            return False
        response = self._write_reg(
            address=int("0044", 16), count=2, slave=1, values=[0, duty_cycle]
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

    def _get_current_voltage(self, ch_num):
        response = self._read_current_parameters(
            address=int("0000", 16), count=1, slave=1
        )
        if self.is_test == True:
            return response

        if response != False:
            response = response[0] / 100
        return response

    def _get_current_current(self, ch_num):
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

    def _get_setting_voltage(self, ch_num):
        response = self._read_setting_parameters(
            address=int("0040", 16), count=2, slave=1
        )
        if self.is_test == True:
            return response

        if response != False:
            response = response[1] / 100
        return response

    def _get_setting_current(self, ch_num):
        response = self._read_setting_parameters(
            address=int("0041", 16), count=2, slave=1
        )
        if response != False:
            response = response[1] / 100
        return response

    def _get_setting_frequency(self, ch_num):
        response = self._read_setting_parameters(
            address=int("0043", 16), count=2, slave=1
        )
        if response != False:
            pass
            # TODO читаем параметры и кладем их в респонсе
        return response

    def _get_setting_state(self, ch_num):
        response = self._read_setting_parameters(
            address=int("0042", 16), count=2, slave=1
        )
        if response != False:
            pass
            # TODO читаем параметры и кладем их в респонсе
        return response

    def _get_setting_duty_cycle(self, ch_num):
        response = self._read_setting_parameters(
            address=int("0044", 16), count=2, slave=1
        )
        if response != False:
            pass
            # TODO читаем параметры и кладем их в респонсе
        return response


if __name__ == "__main__":
    import pickle
    client = ModbusSerialClient(
        port="COM5", baudrate=9600, stopbits=1, bytesize=8, parity="E"
    )

    pickle.dumps(client)
    client.close()