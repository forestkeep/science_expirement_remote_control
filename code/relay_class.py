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
from Classes import device_response_to_step, installation_device
from Classes import is_debug
from relay_set_window import Ui_Set_relay
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
import sys


class relay_pr1_class(installation_device):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "modbus", installation_class)
        print("класс реле создан")
        self.device = None  # класс прибора будет создан при подтверждении параметров,
        # переменная хранит все возможные источники сигналов , сделать функцию, формирующую этот список в зависимости от структуры установки
        self.counter = 0
        self.dict_buf_parameters["mode"] = "Смена полярности",
        self.dict_buf_parameters["num steps"] = "1"

        # переменные для сохранения параметров окна-----------------------------
        self.mode = "Смена полярности"
        self.sourse_enter = "5"
        self.boudrate = "9600"
        self.comportslist = None
        self.triger_enter = "Таймер"

        # сюда при подтверждении параметров будет записан класс команд с клиентом
        self.command = None

    def show_setting_window(self):
        if self.is_window_created:
            self.setting_window.show()
        else:
            self.timer_for_scan_com_port = QTimer()
            self.timer_for_scan_com_port.timeout.connect(
                lambda: self._scan_com_ports())
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
                "background-color: rgb(255, 255, 255);")

            # self.setting_window.sourse_enter.setEditable(True)
            # self.setting_window.sourse_enter.addItems(
            # ["5", "10", "30", "60", "120"])
            self.setting_window.triger_enter.addItems(
                ["Внешний сигнал"])
            self.setting_window.triger_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.sourse_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")

            self.setting_window.comportslist.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.boudrate.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.num_meas_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")

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

            self.setting_window.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(
                self.send_signal_ok)
            # self.setting_window.setMouseTracking(True)
            # ======================================================
            self.setting_window.show()
            self.key_to_signal_func = False
            # ============установка текущих параметров=======================

            self.setting_window.sourse_enter.setCurrentText(self.sourse_enter)
            self.setting_window.boudrate.setCurrentText(self.boudrate)
            if self.comportslist is not None:
                self.setting_window.comportslist.setCurrentText(
                    self.comportslist)

            self.setting_window.triger_enter.setCurrentText(self.triger_enter)

            num_meas_list = ["5", "10", "20", "50"]
            # если в списке сигналов пусто, то и других активных приборов нет, текущий прибор в установке один
            if self.installation_class.get_signal_list(self.name) != []:
                num_meas_list.append("Пока активны другие приборы")
            self.setting_window.num_meas_enter.addItems(num_meas_list)

            self.setting_window.num_meas_enter.setCurrentText(
                str(self.number_steps))

            self.setting_window.sourse_enter.setCurrentText(
                self.dict_buf_parameters["sourse/time"])

            if self.mode != "Включение - Выключение":
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
                if self.setting_window.num_meas_enter.currentText() == "Пока активны другие приборы" and self.installation_class.get_signal_list(self.name) != []:
                    pass
                else:
                    is_num_steps_correct = False

            if self.setting_window.triger_enter.currentText() == "Таймер":
                try:
                    int(self.setting_window.sourse_enter.currentText())
                except:
                    is_time_correct = False

            self.setting_window.num_meas_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.sourse_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")

            if not is_num_steps_correct:
                self.setting_window.num_meas_enter.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")

            if not is_time_correct:
                self.setting_window.sourse_enter.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")

            if is_num_steps_correct and is_time_correct:
                return True
            else:
                return False

    def change_units(self):
        pass

    def add_parameters_from_window(self):

        if self.setting_window.radioButton.isChecked():
            self.mode = "Включение - Выключение"
        else:
            self.mode = "Смена полярности"
        self.triger_enter = self.setting_window.triger_enter.currentText()
        self.sourse_enter = self.setting_window.sourse_enter.currentText()
        self.boudrate = self.setting_window.boudrate.currentText()
        self.comportslist = self.setting_window.comportslist.currentText()

        try:
            self.number_steps = int(
                self.setting_window.num_meas_enter.currentText())
        except:
            if self.setting_window.num_meas_enter.currentText() == "":
                self.number_steps = self.setting_window.num_meas_enter.currentText()
            else:
                self.number_steps = "Пока активны другие приборы"

        if self.key_to_signal_func:
            self.dict_buf_parameters["num steps"] = self.number_steps
            self.dict_buf_parameters["trigger"] = self.setting_window.triger_enter.currentText(
            )
            self.dict_buf_parameters["sourse/time"] = self.setting_window.sourse_enter.currentText()
            self.dict_buf_parameters["baudrate"] = self.setting_window.boudrate.currentText(
            )
            self.dict_buf_parameters["COM"] = self.setting_window.comportslist.currentText(
            )
            self.dict_buf_parameters["mode"] = self.mode

    def send_signal_ok(self):  # действие при подтверждении настроек, передать парамтры классу инсталляции, проверить и окрасить в цвет окошко, вписать паарметры
        self.add_parameters_from_window()
        # те же самые настройки и я не настроен, ничего не делаем
        if self.dict_buf_parameters == self.dict_settable_parameters and not self.i_am_set:
            return
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.i_am_set = False

        self.is_parameters_correct = True
        if self.dict_buf_parameters["COM"] == 'Нет подключенных портов':
            self.is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

        if not self._is_correct_parameters():
            self.is_parameters_correct = False

        if self.is_parameters_correct:
            pass
        else:
            pass
        self.installation_class.message_from_device_settings(
            self.name, self.is_parameters_correct, self.dict_settable_parameters)


# drgtregtdfgdssdfsersrcsersacrersrsarsecrserctscarscrsecrrersdarsadfdscfdsfcsdfcsdfsdfdfasfsdfsdfsffsdfsdfsfsdfsfsfsdfsdfsdfsdfsdfsdfsdfsfsdfsdfsdfsdfsdfsfsfdfsdfsdfsdfsdfsdfsdfsdfsdfsdfdfsdfsdfsdfsdfsdfsdfdsfsdfsdfsdffdfsd

    # фцункция подтверждения корректности параметров от контроллера установкию. установка проверяет ком порты, распределяет их между устройствами и отдает каждому из устройств

    def confirm_parameters(self):
        print(str(self.name) +
              " получил подтверждение настроек, рассчитываем шаги")
        if True:

            self.step_index = -1
            self.i_am_set = True
        else:
            pass
    # настройка прибора перед началом эксперимента, переопределяется при каждлом старте эксперимента

    def action_before_experiment(self) -> bool:  # менять для каждого прибора

        print("настройка прибора " + str(self.name) + " перед экспериментом..")
        status = True
        if not self.command._set_filter_slope(
                slope=self.dict_settable_parameters["filter_slope"]):
            status = False

        return status

    def action_end_experiment(self) -> bool:
        '''выключение прибора'''
        return True

    def do_meas(self):
        '''прочитать текущие и настроенные значения'''
        print("делаем измерение", self.name)

        start_time = time.time()
        parameters = [self.name]
        is_correct = True

        disp1 = self.command.get_parameter(
            command=self.command.COMM_DISPLAY, timeout=1, param=1)
        if not disp1:
            is_correct = False
        else:
            val = ["disp1=" + str(disp1)]
            parameters.append(val)

        disp2 = self.command.get_parameter(
            self.command.COMM_DISPLAY, timeout=1, param=2)
        if not disp2:
            is_correct = False
        else:
            val = ["disp2=" + str(disp2)]
            parameters.append(val)

        phase = self.command.get_parameter(
            self.command.PHASE, timeout=1)
        if not phase:
            is_correct = False
        else:
            val = ["phase=" + str(phase)]
            parameters.append(val)

        # -----------------------------
        if is_debug:
            is_correct = True
            parameters.append(["disp1=" + str(254)])
            parameters.append(["disp2=" + str(847)])
            parameters.append(["phase=" + str(777)])
        # -----------------------------

        if is_correct:
            print("сделан шаг", self.name)
            ans = device_response_to_step.Step_done
        else:
            print("Ошибка шага", self.name)
            val = ["disp1=" + "fail"]
            parameters.append(val)
            val = ["disp2=" + "fail"]
            parameters.append(val)
            val = ["phase=" + "fail"]
            parameters.append(val)

            ans = device_response_to_step.Step_fail

        return ans, parameters, time.time() - start_time

    def check_connect(self) -> bool:
        return True

    def _set_polarity_1(self, voltage) -> bool:
        response = self._write_reg(address=0x03E8, value=0x0008, slave=0x0A)
        return response

    def _set_polarity_2(self, current) -> bool:
        response = self._write_reg(address=0x03E8, value=0x0108, slave=0x0A)
        return response

    def _output_switching_on(self) -> bool:
        response = self._write_reg(address=0x03E7, value=0x0108, slave=0x0A)
        return response

    def _output_switching_off(self) -> bool:
        response = self._write_reg(address=0x03E7, value=0x0008, slave=0x0A)
        return response

    def _change_polarity(self) -> bool:
        response = self._write_reg(address=0x03E8, value=0x0308, slave=0x0A)
        return response

    def _write_reg(self, address, slave, values) -> bool:
        try:
            ans = self.client.write_register(
                address=address, slave=slave, values=values)
            if isinstance(ans, ExceptionResponse):
                print("ошибка записи в регистр реле", ans)
                return False
        except:
            print("Ошибка модбас модуля или клиента")
            return False
        return True


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
    clas = relay_pr1_class("rerere", 1)
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
