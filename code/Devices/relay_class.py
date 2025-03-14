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

import copy
import enum
import logging
import struct
import time

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
from pymodbus.pdu import ExceptionResponse
from PyQt5.QtWidgets import QApplication

from Devices.Classes import (base_ch, base_device, ch_response_to_step,
                             which_part_in_ch)
from Devices.interfase.relay_set_window import Ui_Set_relay

logger = logging.getLogger(__name__)

# sourse_enter -> sourse_act_enter || sourse_meas_enter
# triger_enter -> triger_act_enter || triger_meas_enter

class out_state(enum.Enum):
    on = 1
    off = 2

class current_polarity(enum.Enum):
    pol_1 = 1
    pol_2 = 2

class relayPr1Class(base_device):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "modbus", installation_class)
        # print("класс реле создан")

        self.device = None  # класс прибора будет создан при подтверждении параметров,
        self.counter = 0

        self.part_ch = (
            which_part_in_ch.bouth
        )  # указываем, из каких частей состоиит канал в данном приборе
        self.ch1_act = chActPR(1, self)
        self.ch1_meas = chMeasPR(1, self)
        self.channels = self.create_channel_array()
        self.polarity = current_polarity.pol_1
        self.state_output = out_state.off

        self.command = None
        self.setting_window = Ui_Set_relay()
        self.setting_window.setGeometry(300, 300, 650, 400)
        self.base_settings_window()

    @base_device.base_show_window
    def show_setting_window(self, number_of_channel):
        self.switch_channel(number_of_channel)

        print("func")

        self.key_to_signal_func = False
        # ============установка текущих параметров=======================

        if (
            self.active_channel_act.dict_settable_parameters["mode"]
            != QApplication.translate("Device","Включение - Выключение")
        ):
            self.setting_window.change_pol_button.setChecked(True)
            self.setting_window.radioButton.setEnabled(True)
        else:
            self.setting_window.radioButton.setChecked(True)
            self.setting_window.change_pol_button.setEnabled(True)

        self.setting_window.hall1_meas.setChecked(
            self.active_channel_meas.dict_settable_parameters["hall1"] == True
        )
        self.setting_window.hall2_meas.setChecked(
            self.active_channel_meas.dict_settable_parameters["hall2"] == True
        )
        self.setting_window.hall3_meas.setChecked(
            self.active_channel_meas.dict_settable_parameters["hall3"] == True
        )
        self.setting_window.hall4_meas.setChecked(
            self.active_channel_meas.dict_settable_parameters["hall4"] == True
        )
        self.setting_window.temp_meas.setChecked(
            self.active_channel_meas.dict_settable_parameters["temp"] == True
        )

        self.key_to_signal_func = True

        self._action_when_select_trigger()
        self._is_correct_parameters()

        self.setting_window.show()

    @base_device.base_is_correct_parameters
    def _is_correct_parameters(self) -> bool:  # менять для каждого прибора
        return True

    @base_device.base_add_parameters_from_window
    def add_parameters_from_window(self):
        if self.key_to_signal_func:
            if self.setting_window.radioButton.isChecked():
                self.active_channel_act.dict_buf_parameters["mode"] = (
                    QApplication.translate("Device","Включение - Выключение")
                )
            else:
                self.active_channel_act.dict_buf_parameters["mode"] = QApplication.translate("Device","Смена полярности")

            self.active_channel_meas.dict_buf_parameters["hall1"] = (
                self.setting_window.hall1_meas.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["hall2"] = (
                self.setting_window.hall2_meas.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["hall3"] = (
                self.setting_window.hall3_meas.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["hall4"] = (
                self.setting_window.hall4_meas.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["temp"] = (
                self.setting_window.temp_meas.isChecked()
            )

    def send_signal_ok(
        self,
    ):  # действие при подтверждении настроек, передать парамтры классу инсталляции, проверить и окрасить в цвет окошко, вписать паарметры
        "вызывается только после закрытия окна настроек"
        self.add_parameters_from_window()
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.active_channel_act.dict_settable_parameters = copy.deepcopy(
            self.active_channel_act.dict_buf_parameters
        )
        self.active_channel_meas.dict_settable_parameters = copy.deepcopy(
            self.active_channel_meas.dict_buf_parameters
        )
        is_parameters_correct = True
        if self.dict_buf_parameters["COM"] == QApplication.translate("Device","Нет подключенных портов"):
            is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

        if is_parameters_correct:
            if not self._is_correct_parameters():
                is_parameters_correct = False

        #print("actrelay",self.active_channel_act, self.active_channel_act.dict_buf_parameters)
        #print("measrelay",self.active_channel_act, self.active_channel_meas.dict_buf_parameters)

        self.installation_class.message_from_device_settings(
            name_device=self.name,
            num_channel=self.active_channel_meas.number,
            status_parameters=is_parameters_correct,
            list_parameters_device=self.dict_settable_parameters,
            list_parameters_act=self.active_channel_act.dict_settable_parameters,
            list_parameters_meas=self.active_channel_meas.dict_settable_parameters,
        )

    # фцункция подтверждения корректности параметров от контроллера установкию. установка проверяет ком порты, распределяет их между устройствами и отдает каждому из устройств
    def confirm_parameters(self):
        #print(str(self.name) +" получил подтверждение настроек, рассчитываем шаги")

        for ch in self.channels:
            if ch.is_ch_active():
                ch.step_index = -1

        #print("actrelay",self.active_channel_act, self.active_channel_act.dict_buf_parameters)
        #print("measrelay",self.active_channel_meas, self.active_channel_meas.dict_buf_parameters)

    # настройка прибора перед началом эксперимента, переопределяется при каждлом старте эксперимента

    def action_before_experiment(
        self, number_of_channel
    ) -> bool:  # менять для каждого прибора
        self.switch_channel(number_of_channel)
        # print(f"настройка канала {number_of_channel} прибора "+ str(self.name)+ " перед экспериментом..")
        status = True
        if not self._set_polarity_1(self.active_channel_act.number):
            return False
        else:
            self.active_channel_act.polarity = current_polarity.pol_1
        if not self._output_switching_on(self.active_channel_act.number):
            return False
        else:
            self.active_channel_act.state_output = out_state.on
            
        if not self.calibration():
            return False

        return status

    def action_end_experiment(self, ch) -> bool:
        """выключение прибора"""
        self.switch_channel(ch_name=ch.get_name())
        # print("Плавное выключение источника питания")
        status = True
        if ch.get_type() == "act":
            if not self._set_polarity_1(self.active_channel_act.number):
                status = False
            else:
                self.polarity = current_polarity.pol_1
            if not self._output_switching_off(self.active_channel_act.number):
                status = False
            else:
                self.state_output = out_state.off

        return status

    def do_action(self, ch, repeat=3) -> bool:  # переопределена
        """Производит действие приборра"""
        parameters = [self.name + " " + str(ch.get_name())]
        start_time = time.perf_counter()
        if ch.get_type() == "act":
            self.switch_channel(number=ch.get_number())
            do_next = True
            if do_next:
                i = 0
                answer = ch_response_to_step.Step_fail
                while i - 1 < repeat and answer == ch_response_to_step.Step_fail:
                    time.sleep(0.1)
                    i += 1
                    if (
                        self.active_channel_act.dict_settable_parameters["mode"]
                        == QApplication.translate("Device","Смена полярности")
                    ):
                        if self.active_channel_act.polarity == current_polarity.pol_1:
                            if not self._set_polarity_2(self.active_channel_act.number):
                                is_correct = False
                            else:
                                self.active_channel_act.polarity = (
                                    current_polarity.pol_2
                                )
                                answer = ch_response_to_step.Step_done
                        else:
                            if not self._set_polarity_1(self.active_channel_act.number):
                                is_correct = False
                            else:
                                self.active_channel_act.polarity = (
                                    current_polarity.pol_1
                                )
                                answer = ch_response_to_step.Step_done
                    else:
                        if self.active_channel_act.state_output == out_state.on:
                            if not self._output_switching_off(
                                self.active_channel_act.number
                            ):
                                is_correct = False
                            else:
                                self.active_channel_act.state_output = out_state.off
                                answer = ch_response_to_step.Step_done
                        else:
                            if not self._output_switching_on(
                                self.active_channel_act.number
                            ):
                                is_correct = False
                            else:
                                self.active_channel_act.state_output = out_state.on
                                answer = ch_response_to_step.Step_done

            if self.is_debug:
                if answer != ch_response_to_step.End_list_of_steps:
                    answer = ch_response_to_step.Step_done

            return answer, parameters, time.perf_counter() - start_time
        return ch_response_to_step.Incorrect_ch, parameters, time.perf_counter() - start_time

    def do_meas(self, ch):
        self.switch_channel(number=ch.get_number())
        start_time = time.perf_counter()
        parameters = [self.name + " " + str(ch.get_name())]
        if ch.get_type() == "meas":
            is_correct = True

            if (
                self.active_channel_act.dict_settable_parameters["mode"]
                == QApplication.translate("Device","Смена полярности")
            ):
                if self.active_channel_act.polarity == current_polarity.pol_1:
                    val = [QApplication.translate("Device","Полярность") + "=" + str(1)]
                else:
                    val = [QApplication.translate("Device","Полярность") + "=" + str(2)]
            else:
                if self.active_channel_act.state_output == out_state.on:
                    val = [QApplication.translate("Device","Выход") + "=" + str(2)]
                else:
                    val = [QApplication.translate("Device","Выход") + "=" + str(2)]
            parameters.append(val)

            if self.active_channel_meas.dict_settable_parameters["temp"] == True:
                temp_values = self.read_temp_sensor()
                if temp_values:
                    val = ["temperature=" + str(temp_values)]
                else:
                    val = ["temperature=" + "fail"]
                    is_correct = False
                parameters.append(val)



            hall_values = self.read_hall_sensors()
            #print(f"{hall_values=}")
            decoded_numbers = False
            if hall_values != False:
                raw_data = struct.pack('> ' + 'H' * len(hall_values.registers), *hall_values.registers)
                #print(f"данные: {raw_data.hex()}")
                decoded_numbers = self.decode_raw_data(raw_data)
                #print(f"{decoded_numbers=}")
                
            if self.active_channel_meas.dict_settable_parameters["hall1"] == True:
                if decoded_numbers:
                    val = ["hall1=" + str(decoded_numbers[0])]
                else:
                    val = ["hall1=" + "fail"]
                    is_correct = False
                parameters.append(val)
                    
            if self.active_channel_meas.dict_settable_parameters["hall2"] == True:
                if decoded_numbers:
                    val = ["hall2=" + str(decoded_numbers[1])]
                else:
                    val = ["hall2=" + "fail"]
                    is_correct = False
                parameters.append(val)
            if self.active_channel_meas.dict_settable_parameters["hall3"] == True:
                if decoded_numbers:
                    val = ["hall3=" + str(decoded_numbers[2])]
                else:
                    val = ["hall3=" + "fail"]
                    is_correct = False
                parameters.append(val)
            if self.active_channel_meas.dict_settable_parameters["hall4"] == True:
                if decoded_numbers:
                    val = ["hall4=" + str(decoded_numbers[3])]
                else:
                    val = ["hall4=" + "fail"]
                    is_correct = False
                parameters.append(val)
                
            if is_correct:
                #print("сделан шаг", self.name + " ch " + str(self.active_channel.number))
                ans = ch_response_to_step.Step_done
            else:
                #print("ошибка шага", self.name + " ch " + str(self.active_channel.number))
                ans = ch_response_to_step.Step_fail
                
            if self.is_debug:
                if ans != ch_response_to_step.End_list_of_steps:
                    ans = ch_response_to_step.Step_done

            return ans, parameters, time.perf_counter() - start_time
        return ch_response_to_step.Incorrect_ch, parameters, time.perf_counter() - start_time

    def read_hall_sensors(self):
        response = self._read_reg(adr=0x03F1, slave=0x0A, num_registers=0x0014)

        return response
    
    def read_temp_sensor(self):
        response = self._read_reg(adr=0x0405, slave=0x0A, num_registers=0x0007)
        print(f"{response=}")
        if response:
            response = struct.pack('> ' + 'H' * len(response.registers), *response.registers)
            print(f"{len(response)=}")
            if len(response) >= 7:
                    # Извлекаем 7 байтов
                    segment = response[0:7]
                    sign = segment[0]
                    hundr = segment[1]
                    tent = segment[2]
                    integer_part = segment[3]
                    tenths = segment[4]
                    hundredths = segment[5]
                    thousandths = segment[6]
                    # Собираем число
                    response = (1 if sign == 1 else -1) * (hundr*100 + tent*10+ integer_part + tenths / 10 + hundredths / 100 + thousandths / 1000)
            else:
                response = False
        print(f"{response=}")
        return response


    def _set_polarity_1(self, number_of_channel) -> bool:
        self.switch_channel(number_of_channel)
        response = self._write_reg(address=0x03E8, value=0x0008, slave=0x0A)

        return response

    def _set_polarity_2(self, number_of_channel) -> bool:
        self.switch_channel(number_of_channel)
        response = self._write_reg(address=0x03E8, value=0x0108, slave=0x0A)
        return response

    def _output_switching_on(self, number_of_channel) -> bool:
        self.switch_channel(number_of_channel)
        response = self._write_reg(address=0x03E7, value=0x0108, slave=0x0A)
        return response
    
    def calibration(self):
        address = 0x03E9
        slave = 0x0A
        value = 0x0108
        #калимбровка
        ans = self._write_reg(address=address, slave=slave, value=value)
        return ans
    
    def decode_raw_data(self, raw_data):
        decoded_values = []
        for i in range(0, len(raw_data), 5):
            if i + 5 <= len(raw_data):
                # Извлекаем 5 байтов
                segment = raw_data[i:i + 5]
                sign = segment[0]
                integer_part = segment[1]
                tenths = segment[2]
                hundredths = segment[3]
                thousandths = segment[4]
                # Собираем число
                decoded_number = (1 if sign == 1 else -1) * (integer_part + tenths / 10 + hundredths / 100 + thousandths / 1000)
                decoded_values.append(decoded_number)
    
        return decoded_values

    def _output_switching_off(self, number_of_channel) -> bool:
        self.switch_channel(number_of_channel)
        response = self._write_reg(address=0x03E7, value=0x0008, slave=0x0A)
        return response

    def _change_polarity(self, number_of_channel) -> bool:
        self.switch_channel(number_of_channel)
        response = self._write_reg(address=0x03E8, value=0x0308, slave=0x0A)
        return response

    def get_parameters(self, number_of_channel) -> list:
        self.switch_channel(number_of_channel)

    def _write_reg(self, address, slave, value) -> bool:
        try:
            ans = self.client.write_register(address=address, slave=slave, value=value)

            if isinstance(ans, ExceptionResponse):
                # print("ошибка записи в регистр реле", ans)
                return False

            if isinstance(ans, ModbusIOException):
                # print("ошибка записи в регистр реле", ans)
                return False

        except:
            # print("Ошибка модбас модуля или клиента")
            return False
        return True

    def _read_reg(self, adr, slave, num_registers) -> bool:
        try:
            ans = self.client.read_holding_registers(
                address=adr, count=num_registers, slave=slave
            )

            if isinstance(ans, ExceptionResponse):
                # print("ошибка записи в регистр реле", ans)
                return False

            if isinstance(ans, ModbusIOException):
                # print("ошибка записи в регистр реле", ans)
                return False

            return ans
        except:
            # print("Ошибка модбас модуля или клиента")
            return False

class chActPR(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number, ch_type="act", device_class=device_class)
        self.base_duration_step = 0.1  # у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.dict_buf_parameters["mode"] = ( QApplication.translate("Device", "Смена полярности") )
        self.dict_buf_parameters["num steps"] = "1"

        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)

        self.polarity = current_polarity.pol_1
        self.state_output = out_state.off


class chMeasPR(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number, ch_type="meas", device_class=device_class)
        self.base_duration_step = 0.1  # у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.dict_buf_parameters["num steps"] = "1"
        self.dict_buf_parameters["hall1"] = False
        self.dict_buf_parameters["hall2"] = False
        self.dict_buf_parameters["hall3"] = False
        self.dict_buf_parameters["hall4"] = False
        self.dict_buf_parameters["temp"] = False

        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)

def decode_raw_data(raw_data):
    decoded_values = []
    for i in range(0, len(raw_data), 5):
        if i + 5 <= len(raw_data):
            # Извлекаем 5 байтов
            segment = raw_data[i:i + 5]
            sign = segment[0]
            integer_part = segment[1]
            tenths = segment[2]
            hundredths = segment[3]
            thousandths = segment[4]
            # Собираем число
            decoded_number = (1 if sign == 1 else -1) * (integer_part + tenths / 10 + hundredths / 100 + thousandths / 1000)
            decoded_values.append(decoded_number)

    return decoded_values


"""
//0A 06 03 E9 01 08 - команда модбас для калибровки значений датчиков холла, датчики опрашиваются 50 раз, значение усредняется и затем это значение принимается за ноль
//0A 03 03 F1 00 14 - команда запроса значений с 4 датчиков холла
//значения данных с датчиков холла лежат в регистрах, начиная с адреса 1010, на каждый датчик по 5 регистров [знак(1 - положительное)][целое число вольт][десятые][сотые][тысячные]

//0A 06 03 E8 01 08 - команда модбас для включения состояния выходных реле в положение 1
//0A 06 03 E8 00 08 - команда модбас для включения состояния выходных реле в положение 0

//0A 06 03 E8 03 08 - команда модбас для переключения состояния выходных реле
//0A 06 03 E7 01 08 - команда модбас для включения реле
//0A 06 03 E7 00 08 - команда модбас для выключения реле
"""

if __name__ == "__main__":
    from pymodbus.client import ModbusSerialClient
    from pymodbus.exceptions import (MessageRegisterException, ModbusException,
                                     ModbusIOException, NoSuchSlaveException,
                                     NotImplementedException,
                                     ParameterException)
    from pymodbus.pdu import ExceptionResponse, ModbusRequest, ModbusResponse

    port = "COM4"
    client = ModbusSerialClient(
        port=port, baudrate=9600, bytesize=8, parity="N", stopbits=1
    )
    address = 0x03E9
    slave = 0x0A
    value = 0x0108
    #калимбровка
    ans = client.write_register(address=address, slave=slave, value=value)
    adr = 0x03F1
    num_registers = 0x000B
    slave = 0x0A
    while True:
        
        ans = client.read_holding_registers(address=adr, count=num_registers, slave=slave)

        if isinstance(ans, ExceptionResponse):
            print("ошибка ExceptionResponse", ans)

        if isinstance(ans, ModbusIOException):
            print("ошибка ModbusIOException", ans)
        #ans = client.convert_from_registers(ans.registers, int)
        raw_data = struct.pack('> ' + 'H' * len(ans.registers), *ans.registers)
        print(f"данные: {raw_data.hex()}")  # Вывод в шестнадцатеричном формате для удобства
        decoded_numbers = decode_raw_data(raw_data)
        print(decoded_numbers)
        time.sleep(10)

"""Error code 04 = Slave Device Failure

'An unrecoverable error occured while the server was attempting to perform the requested action'
"""
