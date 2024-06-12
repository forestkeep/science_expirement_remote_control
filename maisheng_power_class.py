from pymodbus.client import ModbusSerialClient
from interface.set_power_supply_window import Ui_Set_power_supply
from PyQt5.QtCore import QTimer, QDateTime
from Classes import ch_response_to_step, base_device, ch_response_to_step, base_ch
import time
from power_supply_class import power_supply
import logging
logger = logging.getLogger(__name__)
# 3Регулируемый блок питания MAISHENG WSD-20H15 (200В, 15А)
# Создание клиента Modbus RTU

# Отправлено главным компьютером: 01 10 00 40 00 02 04 00 00 (4E 20) (C3 E7) (При
#                                01 10 00 40 00 02 04 00 00  4E 20   C3 E7

# напряжении 200V, единица измерения 0,01 V)
# Ответ конечного устройства: 01 10 00 40 00 02 40 1C

# удаленная настройка выходного напряжения 0,01 В
class ch_power_supply_class(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number)
        self.base_duration_step = 2#у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.steps_current = []
        self.steps_voltage = []
        self.max_current = 15
        self.max_voltage = 200
        self.max_power = 2000
        self.min_step_V = 0.01
        self.min_step_A = 0.01
        self.min_step_W = 1
        self.dict_buf_parameters["type_of_work"] = "Стабилизация напряжения"
        self.dict_buf_parameters["type_step"] = "Заданный шаг"
        self.dict_buf_parameters["high_limit"] = str(10)
        self.dict_buf_parameters["low_limit"] = str(self.min_step_V)
        self.dict_buf_parameters["step"] = "2"
        self.dict_buf_parameters["second_value"] = str(self.max_current)
        self.dict_buf_parameters["repeat_reverse"] = False

class maishengPowerClass(power_supply):
    def __init__(self, name, installation_class) -> None:

        super().__init__(name, "modbus", installation_class)
        self.ch1 = ch_power_supply_class(1, self)
        self.channels = [self.ch1]
        self.ch1.is_active = (
            True  # по умолчанию для каждого прибора включен первый канал
        )
        self.active_channel = (
            self.ch1
        )  # поле необходимо для записи параметров при настройке в нужный канал


    def _set_voltage(self,ch_num, voltage) -> bool:  # в сотых долях вольта 20000 - 200В
        voltage*=100
        response = self._write_reg(
            address=int("0040", 16), count=2, slave=1, values=[0, int(voltage)]
        )
        return response

    def _set_current(self,ch_num, current) -> bool:  # в сотых долях ампера
        current*=100
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

    def _set_frequency(self,ch_num, frequency) -> bool:
        """удаленная настройка выходной частоты в Гц"""
        high = 0
        if frequency > 65535:
            high = 1
        frequency = frequency - 65535 - 1
        response = self._write_reg(
            address=int("0043", 16), count=2, slave=1, values=[high, frequency]
        )
        return response

    def _set_duty_cycle(self,ch_num, duty_cycle) -> bool:
        if duty_cycle > 100 or duty_cycle < 1:
            return False
        response = self._write_reg(
            address=int("0044", 16), count=2, slave=1, values=[0, duty_cycle]
        )
        return response

    def _write_reg(self, address, count, slave, values) -> bool:
        if self.is_test == True:
            return self.client.write_registers(
                address=address, count=count, slave=slave, values=values
            )
        else:
            try:
                ans = self.client.write_registers(
                    address=address, count=count, slave=slave, values=values
                )
                if ans.isError():
                    #print("ошибка ответа устройства при установке значения", ans)
                    return False
                else:
                    pass
                    # print(ans.registers)
            except:
                #print("Ошибка модбас модуля или клиента")
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
                    #print("ошибка ответа устройства при чтении текущего", ans)
                    return False
                else:
                    # print(ans.registers)
                    return ans.registers
            except:
                #print("Ошибка модбас модуля или клиента")
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
                #print("ошибка ответа устройства при чтении установленного", ans)
                return False
            else:
                # print(ans.registers)
                return ans.registers
        except:
            #print("Ошибка модбас модуля или клиента")
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

    def _get_setting_frequency(self,ch_num):
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
    # Создание клиента Modbus RTU
    client = ModbusSerialClient(
        method="rtu", port="COM3", baudrate=9600, stopbits=1, bytesize=8, parity="E"
    )

    power_supply = maishengPowerClass("wsd", "rere")
    power_supply.set_client(client)
    power_supply.set_test_mode()
    while True:
        #print("введи значение напряжения, разделитель точка")
        voltage = input()
        flag = True
        try:
            voltage = float(voltage)
        except:
            #print("ошибка, нужно ввести число")
            flag = False

        if flag:
            ans = power_supply._set_voltage(voltage * 100)
            #print("ответ модуля:", ans)
            time.sleep(2)
            #print("читаем установленное значение напряжения...")
            ans = power_supply._get_setting_voltage()
            #print("ответ модуля на чтение установленного напряжения:", ans)
            time.sleep(2)
            #print("читаем текущее значение напряжения...")
            ans = power_supply._get_current_voltage()
            #print("ответ модуля на чтение текущего напряжения(с дисплея):", ans)

            client.close()

  
