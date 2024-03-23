from enum import Enum
from pymodbus.client import ModbusSerialClient
from pymodbus.utilities import computeCRC
from interface.set_power_supply_window import Ui_Set_power_supply
from PyQt5 import QtCore, QtWidgets
import PyQt5.sip
import serial.tools.list_ports
from PyQt5.QtCore import QTimer, QDateTime
import copy
from pymodbus import exceptions
import time

is_debug = False


class device_response_to_step(Enum):
    End_list_of_steps = 0
    Step_done = 1
    Step_fail = 3


class control_in_experiment():
    def __init__(self) -> None:
        self.priority = 1
        self.am_i_should_do_step = False
        self.am_i_active_in_experiment = False
        self.previous_step_time = False
        self.pause_time = False
        self.number_meas = 0

    def set_priority(self, priority) -> bool:
        self.priority = priority
        return True

    def get_priority(self) -> int:
        return self.priority

    def increment_priority(self):
        if self.priority > 1:
            self.priority = self.priority - 1
        else:
            self.priority = 1

    def get_status_step(self):
        """возвращает ответ на вопрос, "должен ли я сделать шаг?" """
        return self.am_i_should_do_step

    def set_status_step(self, status):
        '''сообщаем прибору статус шага, должен проводить измерение или нет'''
        self.am_i_should_do_step = status
        return True


class installation_device(control_in_experiment):
    """"base class for devices which used in installation"""

    def __init__(self, name, type_connection, installation_class) -> None:
        super().__init__()
        self.is_test = False #флаг переводит прибор в режим теста, выдаются сырые данные от функций передачи и приема
        self.base_duration_step = 3  # базовое время, необходимое, чтобы сделать одно измерение прибором, может переопределяться в классе каждого прибора, участвует в расчете длительности эксперимента
        self.timer_for_scan_com_port = QTimer()
        self.timer_for_scan_com_port.timeout.connect(
            lambda: self._scan_com_ports())
        # показывает тип подключения устройства, нужно для анализа, какие устройства могут быть подключены к одному ком порту
        self.type_connection = type_connection
        # переменная хранит все возможные источники сигналов
        self.signal_list = []
        # класс установки, которая в данныйй момент управляет прибором
        self.installation_class = installation_class
        self.name = name
        self.setting_window = None

        # показывает количество шагов, сюда же сохраняется параметр из окна считывания настроек. В случае источников питания это поле просто не используется. Количество шагов вычисляется по массиву токов или напряжений
        self.number_steps = "3"

        self.client = None
        self.dict_buf_parameters = {"trigger": "Таймер",
                                    "sourse/time": str(10),  # секунды
                                    "num steps": 0,
                                    "baudrate": "9600",
                                    "COM": None
                                    }  # потенциальные параметры прибора, вводятся когда выбираются значения в настройках, применяются только после подтверждения пользователем и прохождении проверок
        self.dict_settable_parameters = {}  # текущие параметры прибора
        self.is_window_created = False
        # переменная хранит список доступных ком-портов
        self.active_ports = []
        # разрешает исполнение кода в функциях, срабатывающих по сигналам
        self.key_to_signal_func = False
        self.i_am_set = False

    def on_next_step(self):  # функция сообщает прибору, что нужно перейти на следующий шаг, например, выставить новые значения тока и напряжения в случае источника питания
        '''активирует следующий шаг прибора'''
        is_correct = True
        if self.number_steps == "Пока активны другие приборы":
            return is_correct
        if int(self.step_index) < int(self.number_steps)-1:
            self.step_index = self.step_index + 1
        else:
            is_correct = False  # след шага нет
        return is_correct

    def get_name(self) -> str:
        return str(self.name)

    def _scan_com_ports(self):
        '''проверяет наличие ком портов в системе'''
        #print("hop!")
        self.timer_for_scan_com_port.stop()
        ports = serial.tools.list_ports.comports()
        local_list_com_ports = []
        stop = False
        for port in ports:
            try:
                # Попытаемся открыть порт
                ser = serial.Serial(port.device)
                # Если порт успешно открыт, добавляем его в список активных портов
                local_list_com_ports.append(port.device)
                # Закрываем порт
                ser.close()
            except (OSError, serial.SerialException):
                pass
        if local_list_com_ports == []:
            local_list_com_ports.append("Нет подключенных портов")

        if local_list_com_ports == self.active_ports:
            pass
        else:
            try:
                self.setting_window.comportslist.clear()
                print("порты очищены")
                self.setting_window.comportslist.addItems(local_list_com_ports)
            except:
                stop = True
        self.active_ports = local_list_com_ports

        try:
            self.setting_window.isVisible()
        except:
            stop = True

        if not stop:
            self.timer_for_scan_com_port.start(1500)

    def get_type_connection(self) -> str:
        return self.type_connection

    def get_COM(self):
        try:
            answer = self.dict_settable_parameters["COM"]
        except:
            answer = False
        return answer

    def get_baud(self):
        try:
            answer = self.dict_settable_parameters["baudrate"]
        except:
            answer = False
        return answer

    def get_trigger_value(self):
        '''возвращает источник сигнала или время в секундах, если в качестве триггера выбран таймер, в случае ошибки возвращает False'''
        trigger = self.get_trigger()

        if trigger == "Таймер":
            try:
                answer = int(self.dict_settable_parameters["sourse/time"])
            except:
                answer = False
        elif trigger == "Внешний сигнал":
            answer = self.dict_settable_parameters["sourse/time"]
        else:
            answer = False
        return answer

    def get_trigger(self):
        '''возвращает тип триггера, таймер или внешний сигнал'''
        try:
            answer = self.dict_settable_parameters["trigger"]
        except:
            answer = False
        return answer

    def set_client(self, client):
        self.client = client

    def get_steps_number(self):
        '''возвращает число шагов прибора, если число не ограничено, то возвращает False'''
        try:
            answer = int(self.dict_settable_parameters["num steps"])
        except:
            answer = False
        return answer

    def get_settings(self):
        return self.dict_settable_parameters

    def _action_when_select_trigger(self):
        if self.key_to_signal_func:
            # print("выбор триггера")
            if self.setting_window.triger_enter.currentText() == "Таймер":
                buf = self.dict_buf_parameters["sourse/time"]
                # print(type(buf))
                self.setting_window.sourse_enter.clear()
                self.setting_window.sourse_enter.setEditable(True)
                self.setting_window.sourse_enter.addItems(
                    ["5", "10", "30", "60", "120", buf])
                self.setting_window.sourse_enter.setCurrentText(buf)
                self.setting_window.label_sourse.setText("Время(с)")
            else:
                # buf = self.setting_window.sourse_enter.currentText()
                buf = self.dict_buf_parameters["sourse/time"]
                self.setting_window.sourse_enter.clear()
                self.setting_window.sourse_enter.setEditable(False)
                # предоставьте список сигналов, я прибор под именем self.name
                self.signal_list = self.installation_class.get_signal_list(
                    self.name)
                self.setting_window.sourse_enter.addItems(self.signal_list)
                if buf in self.signal_list:
                    self.setting_window.sourse_enter.setCurrentText(buf)
                self.setting_window.label_sourse.setText("Источник сигнала")
            # self.add_parameters_from_window()
    def set_test_mode(self):
        self.is_test = True
    def reset_test_mode(self):
        self.is_test = False

    def set_parameters(self, parameters):
        """функция необходима для настройки параметров прибора в установке при добавлении прибора извне или при открытии сохраненной установки, передаваемый словарь гарантированно должен содержать параметры именно для данного прибора"""
        self.dict_buf_parameters = copy.deepcopy(parameters)
        self.dict_settable_parameters = copy.deepcopy(parameters)
        #print(fr"вошли в функцию передачи параметров установке. имя прибора{self.name}")
        #TODO:парсить параметры и записывать в соответсвующие переменные, предназначенные для сохранения параметров из окна
        self.installation_class.message_from_device_settings(
            self.name, True, self.dict_settable_parameters)
