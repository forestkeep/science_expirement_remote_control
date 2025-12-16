import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pymodbus.client import ModbusSerialClient

from Devices.pid_temp_controller import pidController
from Devices.base_pid_temp_controller import chActPidController, chMeasPidController
from Devices.tcn06_local import REGISTERS as TCN06_REGISTERS
from pymodbus.exceptions import ModbusException

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

    def _set_temperature(self, ch_num, temperature) -> bool:
        return self._write_reg(address=TCN06_REGISTERS['Заданная температура (SV)']['address'], slave=self.dict_settable_parameters["slave_id"], values=int(temperature))

    def _write_reg(self, address, slave, values) -> bool:
        if isinstance(values, int) or isinstance(values, float):
            values = [values]
        if self.is_test == True:
            return self.client.write_registers(address=address, slave=slave, values=values)
        else:
            try:
                ans = self.client.write_registers(address=address, slave=slave, values=values)
                if ans.isError():
                    logger.warning(f"ошибка в ответе записи регистров {address=} {slave=} {values=} {ans=}")
                    return False
                else:
                    pass
            except Exception as e:
                logger.warning(f"ошибка записи регистров, исключение {str(e)}")
                return False
            return True

    def _get_current_temperature(self, ch_num):
        ans = self._read_reg(address=TCN06_REGISTERS['Измеренная температура (PV)']['address'], slave=self.dict_settable_parameters["slave_id"])
        return ans

    def _get_current_power_percent(self, ch_num):
        return self._read_reg(address=TCN06_REGISTERS['Процент выхода (OUT)']['address'], slave=self.dict_settable_parameters["slave_id"])

    def _get_setting_temperature(self, ch_num):
        return self._read_reg(address=TCN06_REGISTERS['Заданная температура (SV)']['address'], slave=self.dict_settable_parameters["slave_id"])
      
    def _read_reg(self, address, slave):
        try:
            result = self.client.read_holding_registers(address=address, count=1, slave=slave)
            if not result.isError():
                value = result.registers[0]
                return value

            else:
                logger.warning(f"Ошибка чтения регистра {address}  {slave=}: {result}")
                return False
        except ModbusException as e:
            logger.warning(f"Modbus ошибка чтения регистра {address} : {e}")
            return False

if __name__ == "__main__":
    import pickle
    client = ModbusSerialClient(
        port="COM5", baudrate=9600, stopbits=1, bytesize=8, parity="E"
    )

    pickle.dumps(client)
    client.close()