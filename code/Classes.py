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

# сюда добавляются классы всех устройств в системе вместе с ключами
'''
dict_device_class = {"Maisheng": maisheng_power_class,
                     "Lock in": sr830_class, "ms": maisheng_power_class}
'''


class device_response_to_step(Enum):
    End_list_of_steps = 0
    Step_done = 1
    Step_fail = 3


class device:
    """device parameters"""

    def __init__(self, model, type_of_connection, protocol) -> None:
        self.model = model
        self.type_of_connection = type_of_connection
        self.protocol = protocol

    def get_model(self) -> str:
        return self.model


class powersupply(device):
    def __init__(self, model, type_of_connection, protocol, number_of_channel):
        super().__init__(model, type_of_connection, protocol)
        self.number_of_channel = number_of_channel


class installation_device:
    """"base class for devices which used in installation"""

    def __init__(self, name, type_connection, installation_class) -> None:
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

        self.client = None
        self.dict_buf_parameters = {"trigger": "Таймер",
                                    "sourse/time": str(10),  # секунды
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

    def set_signal_list(self, lst):
        self.signal_list = lst

    def get_name(self) -> str:
        return str(self.name)

    def _scan_com_ports(self):  # универсальная функция каждого прибора
        print("hop!")
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

    def get_type_connection(self) -> str:  # универсальная
        return self.type_connection

    def get_COM(self):  # универсальная
        return self.dict_settable_parameters["COM"]

    def get_baud(self):  # универсальная
        return self.dict_settable_parameters["baudrate"]

    def get_trigger_value(self):  # унивесалььно
        return self.dict_settable_parameters["sourse/time"]

    def set_client(self, client):  # универсальная
        self.client = client

    def get_steps_number(self) -> float:  # унииверсаль
        if self.dict_settable_parameters["trigger"] == "Таймер":
            try:
                # 5 секунд время на то, чтобы сделать шаг
                return len(self.steps_voltage) * (float(self.dict_settable_parameters["sourse/time"]) + 5)
            except:
                return 0
        else:
            return 0

    def get_settings(self):  # универсальная
        return self.dict_settable_parameters

    # универальная функция для каждого прибора
    def _action_when_select_trigger(self):
        if self.key_to_signal_func:
            print("выбор триггера")
            if self.setting_window.triger_enter.currentText() == "Таймер":
                self.setting_window.sourse_enter.clear()
                self.setting_window.sourse_enter.setEditable(True)
                self.setting_window.sourse_enter.addItems(
                    ["5", "10", "30", "60", "120"])
                self.setting_window.label_sourse.setText("Время(с)")
            else:
                buf = self.setting_window.sourse_enter.currentText()
                self.setting_window.sourse_enter.clear()
                self.setting_window.sourse_enter.setEditable(False)
                print(self.signal_list)
                self.setting_window.sourse_enter.addItems(self.signal_list)
                if buf in self.signal_list:
                    self.setting_window.sourse_enter.setCurrentText(buf)
                self.setting_window.label_sourse.setText("Источник сигнала")
            # self.add_parameters_from_window()


if __name__ == "__main__":
    lst = powersupply("maisheng", "COM", "modbus", 1)

    print(lst.get_model())
