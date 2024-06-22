from interface.set_sr830_window import Ui_Set_sr830
from PyQt5 import QtCore, QtWidgets
import PyQt5.sip
import serial.tools.list_ports
from PyQt5.QtCore import QTimer, QDateTime
import serial
from pymeasure.instruments.srs import SR830
from pymeasure.adapters import SerialAdapter
import copy
from commandsSR830 import commandsSR830
import time
from Classes import base_ch, base_device, ch_response_to_step
from interface.relay_set_window import Ui_Set_relay
from pymodbus.client import ModbusSerialClient
from pymodbus.utilities import computeCRC
from pymodbus.exceptions import ModbusIOException, NoSuchSlaveException, NotImplementedException, ParameterException, ModbusException, MessageRegisterException
from pymodbus.pdu import ExceptionResponse, ModbusRequest, ModbusResponse
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
# importing libraries
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from Classes import not_ready_style_border, not_ready_style_background, ready_style_border, ready_style_background, warning_style_border, warning_style_background
import sys
import enum
import logging
logger = logging.getLogger(__name__)




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
        # переменная хранит все возможные источники сигналов , сделать функцию, формирующую этот список в зависимости от структуры установки
        self.counter = 0

        self.ch1 = ch_PR_class(1, self)
        self.channels=[self.ch1]
        self.ch1.is_active = True#по умолчанию для каждого прибора включен первый канал
        self.active_channel = self.ch1 #поле необходимо для записи параметров при настройке в нужный канал

        self.polarity = current_polarity.pol_1
        self.state_output = out_state.off

        self.command = None

    def get_number_channels(self) -> int:
        return len(self.channels)
    
    def show_setting_window(self,number_of_channel):
            self.switch_channel(number_of_channel)
            # при новом запуске окна настроек необходимо обнулять активный порт для продолжения сканирования
            self.active_ports = []

            # self.is_window_created - True
            self.setting_window = Ui_Set_relay()
            self.setting_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            self.setting_window.setupUi(self.setting_window)

            # +++++++++++++++++выбор ком порта+++++++++++++
            self._scan_com_ports()
            # ++++++++++++++++++++++++++++++++++++++++++

            self.setting_window.boudrate.addItems(
                ["50", "75", "110", "150", "300", "600", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])

            self.setting_window.sourse_enter.setStyleSheet(
                ready_style_border)

            # self.setting_window.sourse_enter.setEditable(True)
            # self.setting_window.sourse_enter.addItems(
            # ["5", "10", "30", "60", "120"])
            self.setting_window.triger_enter.addItems(["Таймер", "Внешний сигнал"])
        
            self.setting_window.triger_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.sourse_enter.setStyleSheet(
                ready_style_border)

            self.setting_window.comportslist.setStyleSheet(
                ready_style_border)
            self.setting_window.boudrate.setStyleSheet(
                ready_style_border)
            self.setting_window.num_meas_enter.setStyleSheet(
                ready_style_border)
            

            self.setting_window.num_meas_enter.setEditable(True)
            self.setting_window.num_meas_enter.addItems(
                ["3"])

            # =======================прием сигналов от окна==================

            self.setting_window.triger_enter.currentIndexChanged.connect(
                lambda: self._action_when_select_trigger())

            self.setting_window.num_meas_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.sourse_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            
            #self.setting_window.comportslist.highlighted.connect(lambda: self._scan_com_ports())

            self.setting_window.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(
                self.send_signal_ok)
            # self.setting_window.setMouseTracking(True)
            # ======================================================
            self.setting_window.show()
            self.key_to_signal_func = False
            # ============установка текущих параметров=======================

            self.setting_window.sourse_enter.setCurrentText(self.active_channel.dict_buf_parameters["sourse/time"])
            self.setting_window.boudrate.setCurrentText(self.dict_buf_parameters["baudrate"])

            self.setting_window.comportslist.setCurrentText(self.dict_buf_parameters["COM"])
            self.setting_window.triger_enter.setCurrentText(self.active_channel.dict_buf_parameters["trigger"])

            num_meas_list = ["5", "10", "20", "50"]
            # если в списке сигналов пусто, то и других активных приборов нет, текущий прибор в установке один
            if self.installation_class.get_signal_list(self.name, self.active_channel.number) != []:
                num_meas_list.append("Пока активны другие приборы")
            self.setting_window.num_meas_enter.addItems(num_meas_list)

            self.setting_window.num_meas_enter.setCurrentText(
                str(self.active_channel.dict_buf_parameters["num steps"]))

            self.setting_window.sourse_enter.setCurrentText(
                self.active_channel.dict_buf_parameters["sourse/time"])

            if self.active_channel.dict_buf_parameters["mode"] != "Включение - Выключение":
                self.setting_window.change_pol_button.setChecked(True)
                self.setting_window.radioButton.setEnabled(True)
            else:
                self.setting_window.radioButton.setChecked(True)
                self.setting_window.change_pol_button.setEnabled(True)

            self.key_to_signal_func = True  # разрешаем выполенение функций
            self._action_when_select_trigger()

    def _is_correct_parameters(self) -> bool:  # менять для каждого прибора
        if self.key_to_signal_func:
            # print("проверить параметры")

            is_num_steps_correct = True
            is_time_correct = True

# число илии нет
            # ----------------------------------------
            try:
                int(self.setting_window.num_meas_enter.currentText())
            except:
                if self.setting_window.num_meas_enter.currentText() == "Пока активны другие приборы" and self.installation_class.get_signal_list(self.name, self.active_channel.number) != []:
                    pass
                else:
                    is_num_steps_correct = False

            if self.setting_window.triger_enter.currentText() == "Таймер":
                try:
                    int(self.setting_window.sourse_enter.currentText())
                except:
                    is_time_correct = False
            
            self.setting_window.num_meas_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.sourse_enter.setStyleSheet(
                ready_style_border)
            
            if not is_num_steps_correct:
                self.setting_window.num_meas_enter.setStyleSheet(
                    not_ready_style_border)

            if not is_time_correct:
                self.setting_window.sourse_enter.setStyleSheet(
                    not_ready_style_border)

            if is_num_steps_correct and is_time_correct:
                return True
            else:
                return False

    def add_parameters_from_window(self):

        if self.setting_window.radioButton.isChecked():
            self.active_channel.dict_buf_parameters["mode"] = "Включение - Выключение"
        else:
            self.active_channel.dict_buf_parameters["mode"] = "Смена полярности"

        try:
            self.active_channel.dict_buf_parameters["num steps"] = int(
                self.setting_window.num_meas_enter.currentText())
        except:
            if self.setting_window.num_meas_enter.currentText() == "":
                self.active_channel.dict_buf_parameters["num steps"] = int(self.setting_window.num_meas_enter.currentText())
            else:
                self.active_channel.dict_buf_parameters["num steps"] = "Пока активны другие приборы"

        if self.key_to_signal_func:
            #self.dict_buf_parameters["num steps"] = self.number_steps
            self.active_channel.dict_buf_parameters["trigger"] = self.setting_window.triger_enter.currentText(
            )
            self.active_channel.dict_buf_parameters["sourse/time"] = self.setting_window.sourse_enter.currentText()
            self.dict_buf_parameters["baudrate"] = self.setting_window.boudrate.currentText(
            )
            self.dict_buf_parameters["COM"] = self.setting_window.comportslist.currentText(
            )
            #self.dict_buf_parameters["mode"] = self.mode

    def send_signal_ok(self):  # действие при подтверждении настроек, передать парамтры классу инсталляции, проверить и окрасить в цвет окошко, вписать паарметры
        "вызывается только после закрытия окна настроек"
        self.add_parameters_from_window()
        # те же самые настройки, ничего не делаем
        if (self.active_channel.dict_buf_parameters == self.active_channel.dict_settable_parameters and self.dict_buf_parameters == self.dict_settable_parameters):
            #return
            pass
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.active_channel.dict_settable_parameters = copy.deepcopy(self.active_channel.dict_buf_parameters)

        is_parameters_correct = True
        if self.dict_buf_parameters["COM"] == 'Нет подключенных портов':
            is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

        if not self._is_correct_parameters():
            is_parameters_correct = False

        self.installation_class.message_from_device_settings(
            self.name,
            self.active_channel.number,
            is_parameters_correct,
            {
                **self.dict_settable_parameters,
                **self.active_channel.dict_settable_parameters,
            },
        )


# drgtregtdfgdssdfsersrcsersacrersrsarsecrserctscarscrsecrrersdarsadfdscfdsfcsdfcsdfsdfdfasfsdfsdfsffsdfsdfsfsdfsfsfsdfsdfsdfsdfsdfsdfsdfsfsdfsdfsdfsdfsdfsfsfdfsdfsdfsdfsdfsdfsdfsdfsdfsdfdfsdfsdfsdfsdfsdfsdfdsfsdfsdfsdffdfsd

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
        if not self._set_polarity_1(self.active_channel.number):
            return False
        else:
            self.active_channel.polarity = current_polarity.pol_1
        if not self._output_switching_on(self.active_channel.number):
            return False
        else:
            self.active_channel.state_output = out_state.on


        return status

    def action_end_experiment(self, number_of_channel) -> bool:
        '''выключение прибора'''
        self.switch_channel(number_of_channel)
        status = True
        if not self._set_polarity_1(self.active_channel.number):
            return False
        else:
            self.polarity = current_polarity.pol_1
        if not self._output_switching_off(self.active_channel.number):
            return False
        else:
            self.state_output = out_state.off

        return status
    
    def on_next_step(self, number_of_channel, repeat=3) -> bool:  # переопределена

        '''активирует следующий шаг канала прибора'''
        self.switch_channel(number_of_channel)

        if self.is_debug:
            pass
        #print("индекс массива ", self.active_channel.step_index)
        if int(self.active_channel.step_index) < int(self.active_channel.dict_buf_parameters["num steps"])-1 or\
               self.active_channel.dict_buf_parameters["num steps"] == "Пока активны другие приборы":
            self.active_channel.step_index = self.active_channel.step_index + 1

            i = 0
            answer = ch_response_to_step.Step_fail
            while i-1 < repeat and answer == ch_response_to_step.Step_fail:
                time.sleep(0.5)
                i += 1
                if self.active_channel.dict_settable_parameters["mode"] == "Смена полярности":
                    if self.active_channel.polarity == current_polarity.pol_1:
                        if not self._set_polarity_2(self.active_channel.number):
                            is_correct = False
                        else:
                            self.active_channel.polarity = current_polarity.pol_2
                            answer = ch_response_to_step.Step_done
                    else:
                        if not self._set_polarity_1(self.active_channel.number):
                            is_correct = False
                        else:
                            self.active_channel.polarity = current_polarity.pol_1
                            answer = ch_response_to_step.Step_done
                else:
                    if self.active_channel.state_output == out_state.on:
                        if not self._output_switching_off(self.active_channel.number):
                            is_correct = False
                        else:
                            self.active_channel.state_output = out_state.off
                            answer = ch_response_to_step.Step_done
                    else:
                        if not self._output_switching_on(self.active_channel.number):
                            is_correct = False
                        else:
                            self.active_channel.state_output = out_state.on
                            answer = ch_response_to_step.Step_done
        else:
            answer = ch_response_to_step.End_list_of_steps  # след шага нет

        if self.is_debug:
            if answer != ch_response_to_step.End_list_of_steps:
                answer = ch_response_to_step.Step_done

        return answer
    
    def do_meas(self, number_of_channel):
        #print("делаем действие", self.name)
        self.switch_channel(number_of_channel)
        start_time = time.time()
        parameters = [self.name + " ch-" + str(self.active_channel.number)]
        is_correct = True

        if self.active_channel.dict_settable_parameters["mode"] == "Смена полярности":
            if self.active_channel.polarity == current_polarity.pol_1:
                val = ["Полярность=" + str(1)]
            else:
                val = ["Полярность=" + str(2)]
                    
        else:
            if self.active_channel.state_output == out_state.on:
                val = ["Выход=" + str(1)]
            else:
                val = ["Выход=" + str(0)]
        parameters.append(val)


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

    def check_connect(self) -> bool:
        return True

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
        except:
            #print("Ошибка модбас модуля или клиента")
            return False
        return True
    
    def _read_reg(self, adr, slave, num_registers) -> bool:
        try:
            ans = self.client.read_holding_registers(address = adr, count = num_registers, slave = slave)
            ans = self.client.convert_from_registers(ans.registers(), int)

            if isinstance(ans, ExceptionResponse):
                #print("ошибка записи в регистр реле", ans)
                return False
            return ans
        except:
            #print("Ошибка модбас модуля или клиента")
            return False
        return True


class ch_PR_class(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number)
        #print(f"канал {number} создан")
        #print(self.am_i_should_do_step, "ацаыввыаваываываывыаывываываываываываывавыаывыыв")
        self.base_duration_step = 0.1#у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.dict_buf_parameters["mode"] = "Смена полярности",
        self.dict_buf_parameters["num steps"] = "1"
        self.polarity = current_polarity.pol_1
        self.state_output = out_state.off
        


'''
//0A 06 03 E8 01 08 - команда модбас для включения состояния выходных реле в положение 1
//0A 06 03 E8 00 08 - команда модбас для включения состояния выходных реле в положение 0
//0A 06 03 E8 03 08 - команда модбас для переключения состояния выходных реле
//0A 06 03 E7 01 08 - команда модбас для включения реле
//0A 06 03 E7 00 08 - команда модбас для выключения реле
'''


if __name__ == '__main__':
    '''
    App = QApplication(sys.argv)

# create the instance of our Window
    window = Window()

# start the app
    sys.exit(App.exec())
    '''

    app = QtWidgets.QApplication(sys.argv)
    '''
    port = "COM13"
    client = ModbusSerialClient(
        port=port, baudrate=9600, bytesize=8, parity="N", stopbits=1)
    reply = client.write_register(address=0x03E8, value=0x0308, slave=0x0A)
    if isinstance(reply, ExceptionResponse):
        print("ошибка записи в регистр реле", reply)
    '''
    clas = relayPr1Class("rerere", 1)
    clas.show_setting_window()
    sys.exit(app.exec_())

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
