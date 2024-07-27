from interface.set_sr830_window import Ui_Set_sr830
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTimer, QDateTime
import copy, time
from commandsSR830 import commandsSR830
from Classes import base_ch, base_device, ch_response_to_step, which_part_in_ch
from interface.relay_set_window import Ui_Set_relay
from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException, NoSuchSlaveException, NotImplementedException, ParameterException, ModbusException, MessageRegisterException
from pymodbus.pdu import ExceptionResponse, ModbusRequest, ModbusResponse
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
# importing libraries
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import sys
import enum
import logging
logger = logging.getLogger(__name__)

#sourse_enter -> sourse_act_enter || sourse_meas_enter
#triger_enter -> triger_act_enter || triger_meas_enter

class out_state(enum.Enum):
    on = 1
    off = 2

class current_polarity(enum.Enum):
    pol_1 = 1
    pol_2 = 2

class relayPr1Class(base_device):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "modbus", installation_class)
        #print("класс реле создан")

        self.device = None  # класс прибора будет создан при подтверждении параметров,
        self.counter = 0

        self.part_ch = which_part_in_ch.bouth#указываем, из каких частей состоиит канал в данном приборе 
        self.ch1_a = chActPR(1, self)
        self.ch1_m = chMeasPR(1, self)
        self.channels=[self.ch1_a, self.ch1_m]
        self.ch1_a.is_active = True#по умолчанию для каждого прибора включен первый канал
        self.ch1_m.is_active = True#по умолчанию для каждого прибора включен первый канал
        self.active_channel_act = self.ch1_a
        self.active_channel_meas = self.ch1_m
        self.polarity = current_polarity.pol_1
        self.state_output = out_state.off

        self.command = None
        self.setting_window = Ui_Set_relay()
        self.base_settings_window()

    @base_device.base_show_window
    def show_setting_window(self, number_of_channel):
            self.switch_channel(number_of_channel)

            self.key_to_signal_func = False
            # ============установка текущих параметров=======================

            if self.active_channel_act.dict_settable_parameters["mode"] != "Включение - Выключение":
                self.setting_window.change_pol_button.setChecked(True)
                self.setting_window.radioButton.setEnabled(True)
            else:
                self.setting_window.radioButton.setChecked(True)
                self.setting_window.change_pol_button.setEnabled(True)

            self.setting_window.hall1_meas.setChecked(self.active_channel_meas.dict_settable_parameters["hall1"] == True)
            self.setting_window.hall2_meas.setChecked(self.active_channel_meas.dict_settable_parameters["hall2"] == True)
            self.setting_window.hall3_meas.setChecked(self.active_channel_meas.dict_settable_parameters["hall3"] == True)
            self.setting_window.hall4_meas.setChecked(self.active_channel_meas.dict_settable_parameters["hall4"] == True)

            self.key_to_signal_func = True  # разрешаем выполнение функций

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
                self.active_channel_act.dict_buf_parameters["mode"] = "Включение - Выключение"
            else:
                self.active_channel_act.dict_buf_parameters["mode"] = "Смена полярности"

            self.active_channel_meas.dict_buf_parameters["hall1"] = self.setting_window.hall1_meas.isChecked()
            self.active_channel_meas.dict_buf_parameters["hall2"] = self.setting_window.hall2_meas.isChecked()
            self.active_channel_meas.dict_buf_parameters["hall3"] = self.setting_window.hall3_meas.isChecked()
            self.active_channel_meas.dict_buf_parameters["hall4"] = self.setting_window.hall4_meas.isChecked()

    def send_signal_ok(self):  # действие при подтверждении настроек, передать парамтры классу инсталляции, проверить и окрасить в цвет окошко, вписать паарметры
        "вызывается только после закрытия окна настроек"
        self.add_parameters_from_window()
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.active_channel_act.dict_settable_parameters = copy.deepcopy(self.active_channel_act.dict_buf_parameters)
        self.active_channel_meas.dict_settable_parameters = copy.deepcopy(self.active_channel_meas.dict_buf_parameters)
        is_parameters_correct = True
        if self.dict_buf_parameters["COM"] == 'Нет подключенных портов':
            is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

        if is_parameters_correct:
            if not self._is_correct_parameters():
                is_parameters_correct = False

        self.installation_class.message_from_device_settings(
            name_device = self.name,
            num_channel = self.active_channel_meas.number,
            status_parameters = is_parameters_correct,
            list_parameters_device = self.dict_settable_parameters,
            list_parameters_act = self.active_channel_act.dict_settable_parameters,
            list_parameters_meas = self.active_channel_meas.dict_settable_parameters
        )


    # фцункция подтверждения корректности параметров от контроллера установкию. установка проверяет ком порты, распределяет их между устройствами и отдает каждому из устройств
    def confirm_parameters(self):
        #print(str(self.name) +" получил подтверждение настроек, рассчитываем шаги")
        if True:
            for ch in self.channels:
                if ch.is_ch_active():
                    ch.step_index = -1
        else:
            pass
    # настройка прибора перед началом эксперимента, переопределяется при каждлом старте эксперимента

    def action_before_experiment(self, number_of_channel) -> bool:  # менять для каждого прибора
        self.switch_channel(number_of_channel)
        #print(f"настройка канала {number_of_channel} прибора "+ str(self.name)+ " перед экспериментом..")
        status = True
        if not self._set_polarity_1(self.active_channel_act.number):
            return False
        else:
            self.active_channel_act.polarity = current_polarity.pol_1
        if not self._output_switching_on(self.active_channel_act.number):
            return False
        else:
            self.active_channel_act.state_output = out_state.on

        return status

    def action_end_experiment(self, ch) -> bool:
        '''выключение прибора'''
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
        '''Производит действие приборра'''
        parameters = [self.name + " " + str(ch.get_name())]
        start_time = time.time()
        if ch.get_type() == "act":
            self.switch_channel(number=ch.get_number())
            do_next = True
            if do_next:
                i = 0
                answer = ch_response_to_step.Step_fail
                while i-1 < repeat and answer == ch_response_to_step.Step_fail:
                    time.sleep(0.1)
                    i += 1
                    if self.active_channel_act.dict_settable_parameters["mode"] == "Смена полярности":
                        if self.active_channel_act.polarity == current_polarity.pol_1:
                            if not self._set_polarity_2(self.active_channel_act.number):
                                is_correct = False
                            else:
                                self.active_channel_act.polarity = current_polarity.pol_2
                                answer = ch_response_to_step.Step_done
                        else:
                            if not self._set_polarity_1(self.active_channel_act.number):
                                is_correct = False
                            else:
                                self.active_channel_act.polarity = current_polarity.pol_1
                                answer = ch_response_to_step.Step_done
                    else:
                        if self.active_channel_act.state_output == out_state.on:
                            if not self._output_switching_off(self.active_channel_act.number):
                                is_correct = False
                            else:
                                self.active_channel_act.state_output = out_state.off
                                answer = ch_response_to_step.Step_done
                        else:
                            if not self._output_switching_on(self.active_channel_act.number):
                                is_correct = False
                            else:
                                self.active_channel_act.state_output = out_state.on
                                answer = ch_response_to_step.Step_done


            if self.is_debug:
                if answer != ch_response_to_step.End_list_of_steps:
                    answer = ch_response_to_step.Step_done

            return answer, parameters, time.time() - start_time
        return ch_response_to_step.Incorrect_ch, parameters, time.time() - start_time
    
    def do_meas(self, ch):
        self.switch_channel(number=ch.get_number())
        start_time = time.time()
        parameters = [self.name + " " + str(ch.get_name())]
        if ch.get_type() == "meas":
            is_correct = True

            if self.active_channel_act.dict_settable_parameters["mode"] == "Смена полярности":
                if self.active_channel_act.polarity == current_polarity.pol_1:
                    val = ["Полярность=" + str(1)]
                else:
                    val = ["Полярность=" + str(2)]
            else:
                if self.active_channel_act.state_output == out_state.on:
                    val = ["Выход=" + str(1)]
                else:
                    val = ["Выход=" + str(0)]
            parameters.append(val)


            hall_values = self.read_hall_sensors()
            if self.active_channel_meas.dict_settable_parameters["hall1"] == True:
                pass
            if self.active_channel_meas.dict_settable_parameters["hall2"] == True:
                pass
            if self.active_channel_meas.dict_settable_parameters["hall3"] == True:
                pass
            if self.active_channel_meas.dict_settable_parameters["hall4"] == True:
                pass

            # -----------------------------
            if self.is_debug:
                is_correct = True
            # -----------------------------

            if is_correct:
            # print("сделан шаг", self.name + " ch " + str(self.active_channel.number))
                ans = ch_response_to_step.Step_done
            else:
                #print("ошибка шага", self.name + " ch " + str(self.active_channel.number))
                ans = ch_response_to_step.Step_fail

            return ans, parameters, time.time() - start_time
        return ch_response_to_step.Incorrect_ch, parameters, time.time() - start_time
    
    def check_connect(self) -> bool:
        return True
    
    def read_hall_sensors(self):
        response = self._read_reg(adr = 0x03F1, slave = 0x0A, num_registers = 0x0014 )
        hall_value = [4]
        if response is not False:
            hall_value[0], hall_value[1], hall_value[2], hall_value[3] = self.decode_hall_registers(data = response)
            return hall_value
    
    def decode_hall_registers(self, data):
        logger.info(f"response read hall sensors: {data}")
        return 1,1,1,1

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
            ans = self.client.write_register(
                address=address, slave=slave, value=value)
            
            if isinstance(ans, ExceptionResponse):
                #print("ошибка записи в регистр реле", ans)
                return False
            
            if isinstance(ans, ModbusIOException):
                #print("ошибка записи в регистр реле", ans)
                return False
            
        except:
            #print("Ошибка модбас модуля или клиента")
            return False
        return True
    
    def _read_reg(self, adr, slave, num_registers) -> bool:
        try:
            ans = self.client.read_holding_registers(address = adr, count = num_registers, slave = slave)

            if isinstance(ans, ExceptionResponse):
                #print("ошибка записи в регистр реле", ans)
                return False
            
            if isinstance(ans, ModbusIOException):
                #print("ошибка записи в регистр реле", ans)
                return False
            
            ans = self.client.convert_from_registers(ans.registers(), int)

            return ans
        except:
            #print("Ошибка модбас модуля или клиента")
            return False
        return True


class chActPR(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number, ch_type = "act", device_class=device_class)
        self.base_duration_step = 0.1#у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.dict_buf_parameters["mode"] = "Смена полярности",
        self.dict_buf_parameters["num steps"] = "1"

        self.dict_settable_parameters = self.dict_buf_parameters

        self.polarity = current_polarity.pol_1
        self.state_output = out_state.off

class chMeasPR(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number, ch_type = "meas", device_class = device_class)
        self.base_duration_step = 0.1#у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.dict_buf_parameters["num steps"] = "1"
        self.dict_buf_parameters["hall1"] = False
        self.dict_buf_parameters["hall2"] = False
        self.dict_buf_parameters["hall3"] = False
        self.dict_buf_parameters["hall4"] = False

        self.dict_settable_parameters = self.dict_buf_parameters

'''
//0A 06 03 E9 01 08 - команда модбас для калибровки значений датчиков холла, датчики опрашиваются 50 раз, значение усредняется и затем это значение принимается за ноль
//0A 03 03 F1 00 14 - команда запроса значений с 4 датчиков холла
//значения данных с датчиков холла лежат в регистрах, начиная с адреса 1010, на каждый датчик по 5 регистров [знак(1 - положительное)][целое число вольт][десятые][сотые][тысячные]

//0A 06 03 E8 01 08 - команда модбас для включения состояния выходных реле в положение 1
//0A 06 03 E8 00 08 - команда модбас для включения состояния выходных реле в положение 0

//0A 06 03 E8 03 08 - команда модбас для переключения состояния выходных реле
//0A 06 03 E7 01 08 - команда модбас для включения реле
//0A 06 03 E7 00 08 - команда модбас для выключения реле
'''
#pyinstaller --onefile relay_class.py
if __name__ == '__main__':
    from pymodbus.client import ModbusSerialClient
    from pymodbus.exceptions import ModbusIOException, NoSuchSlaveException, NotImplementedException, ParameterException, ModbusException, MessageRegisterException
    from pymodbus.pdu import ExceptionResponse, ModbusRequest, ModbusResponse
    start = input()
    port = "COM4"
    client = ModbusSerialClient(port=port, baudrate=9600, bytesize=8, parity="N", stopbits=1)
    adr = 0x03F1 
    num_registers = 0x0014
    slave = 0x0A 
    ans = client.read_holding_registers(address = adr, count = num_registers, slave = slave)

    if isinstance(ans, ExceptionResponse):
        print("ошибка ExceptionResponse", ans)
      
    if isinstance(ans, ModbusIOException):
        print("ошибка ModbusIOException", ans)
    print(f"{ans=}")
    ans = client.convert_from_registers(ans.registers(), int)
    print(f"{ans=}")

    input()



    '''

    while True:
        values = client.read_input_registers(address=40060, count=1, unit=unit)
        # or client.read_holding_registers(...)
        if isinstance(values, ModbusIOException):
            print(values)
        else:
            # here if values is not an ModbusIOException
            print("Values:", values)
            if values[0] == 0xFFFF:
                print("Error detected")
            elif values[0] == 2002:
                print("Data ready")
                result = client.read_input_registers(
                    address=40051, count=9, unit=unit)
                if isinstance(result, ModbusIOException):
                    print("Could not read result")
                    print("Maybe client.read_holding_registers?")
                else:
                    print("Got a result:", result)
    '''

'''Error code 04 = Slave Device Failure

'An unrecoverable error occured while the server was attempting to perform the requested action'
'''
