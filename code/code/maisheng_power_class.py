from pymodbus.client import ModbusSerialClient
from pymodbus.utilities import computeCRC
from interface.set_power_supply_window import Ui_Set_power_supply
from PyQt5 import QtCore, QtWidgets
import PyQt5.sip
import serial.tools.list_ports
from PyQt5.QtCore import QTimer, QDateTime
import copy
# Создание клиента Modbus RTU

# Отправлено главным компьютером: 01 10 00 40 00 02 04 00 00 (4E 20) (C3 E7) (При
#                                01 10 00 40 00 02 04 00 00  4E 20   C3 E7

# напряжении 200V, единица измерения 0,01 V)
# Ответ конечного устройства: 01 10 00 40 00 02 40 1C


# удаленная настройка выходного напряжения 0,01 В
class maisheng_power_class():
    def __init__(self, signal_list, installation_class, name) -> None:
        print("класс источника питания создан")
        # показывает тип подключения устройства, нужно для анализа, какие устройства могут быть подключены к одному ком порту
        self.type_connection = "modbus"
        # переменная хранит все возможные источники сигналов , сделать функцию, формирующую этот список в зависимости от структуры установки
        self.sourses = signal_list
        self.installation_class = installation_class
        # переменная хранит список доступных ком-портов
        self.active_ports = []
        self.counter = 0
        self.name = name
        # заполняется в случае корректных параметров(подтверждения от контроллера установки)
        self.steps_current = []
        # заполняется в случае корректных параметров(подтверждения от контроллера установки)
        self.steps_voltage = []

        self.client = 0
        self.max_current = 12
        self.max_voltage = 200
        self.max_power = 2000
        self.min_step_V = 0.01
        self.min_step_A = 0.1
        self.min_step_W = 1
        self.dict_buf_parameters = {"trigger": "Таймер",
                                    "sourse/time": str(10),  # секунды
                                    "type_of_work": "Стабилизация напряжения",
                                    "type_step": "Заданный шаг",
                                    "high_limit": str(self.max_voltage),
                                    "low_limit": "0",
                                    "step": "5",
                                    "baudrate": "9600",
                                    "COM": None
                                    }  # потенциальные параметры прибора, вводятся когда выбираются значения в настройках, применяются только после подтверждения пользователем и прохождении проверок
        self.dict_settable_parameters = {}  # текущие паарметры прибора
        # client.connect()
        self.is_window_created = False
        # разрешает исполнение кода в функциях, срабатывающих по сигналам
        self.key_to_signal_func = False

        self.i_am_set = False

    def get_type_connection(self) -> str:
        return self.type_connection

    def get_COM(self):
        return self.dict_settable_parameters["COM"]

    def get_baud(self):
        return self.dict_settable_parameters["baudrate"]

    def show_setting_window(self):

        if self.is_window_created:
            self.setting_window.show()
        else:
            self.timer_for_scan_com_port = QTimer()
            self.timer_for_scan_com_port.timeout.connect(
                lambda: self.scan_com_ports())
            # при новом запуске окна настроек необходимо обнулять активный порт для продолжения сканирования
            self.active_ports = []
            # self.is_window_created - True
            self.setting_window = Ui_Set_power_supply()
            self.setting_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            self.setting_window.setupUi(self.setting_window)

            self.setting_window.type_work_enter.addItems(
                ["Стабилизация напряжения", "Стабилизация тока", "Стабилизация мощности"])
            self.setting_window.triger_enter.addItems(
                ["Таймер", "Внешний сигнал"])
            self.setting_window.triger_enter.setEnabled(True)

            self.setting_window.type_step_enter.addItems(
                ["Заданный шаг", "Адаптивный шаг"])
            # +++++++++++++++++выбор ком порта+++++++++++++
            self.scan_com_ports()
            # ++++++++++++++++++++++++++++++++++++++++++

            self.setting_window.boudrate.addItems(
                ["50", "75", "110", "150", "300", "600", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
            self.setting_window.sourse_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            # self.setting_window.sourse_enter.setEditable(True)
            # self.setting_window.sourse_enter.addItems(
            # ["5", "10", "30", "60", "120"])
            self.setting_window.type_step_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.type_work_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.triger_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            # =======================прием сигналов от окна==================
            self.setting_window.type_work_enter.currentIndexChanged.connect(
                lambda: self.change_units())
            self.setting_window.type_work_enter.currentIndexChanged.connect(
                lambda: self.is_correct_parameters())

            self.setting_window.type_step_enter.currentIndexChanged.connect(
                lambda: self.action_when_select_step())
            self.setting_window.type_step_enter.currentIndexChanged.connect(
                lambda: self.is_correct_parameters())
            self.setting_window.type_step_enter.currentIndexChanged.connect(
                lambda: self.action_when_select_trigger())

            self.setting_window.triger_enter.currentIndexChanged.connect(
                lambda: self.action_when_select_trigger())

            self.setting_window.step_enter.currentTextChanged.connect(
                lambda: self.is_correct_parameters())
            self.setting_window.max_enter.currentTextChanged.connect(
                lambda: self.is_correct_parameters())
            self.setting_window.min_enter.currentTextChanged.connect(
                lambda: self.is_correct_parameters())

            self.setting_window.comportslist.highlighted.connect(
                lambda: self.scan_com_ports())
            '''
            self.setting_window.type_work_enter.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.type_step_enter.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.min_enter.currentTextChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.max_enter.currentTextChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.step_enter.currentTextChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.comportslist.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.comportslist.currentTextChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.boudrate.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.sourse_enter.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.sourse_enter.currentTextChanged.connect(
                lambda: self.add_parameters_from_window())
            '''
            self.setting_window.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(
                self.send_signal_ok)
            # ======================================================
            self.setting_window.show()
            # запрещаем исполнение функций во время инициализации
            self.key_to_signal_func = False
            # ============установка текущих параметров=======================
            self.setting_window.type_work_enter.setCurrentText(
                self.dict_buf_parameters["type_of_work"])
            self.setting_window.type_step_enter.setCurrentText(
                self.dict_buf_parameters["type_step"])
            self.setting_window.min_enter.setCurrentText(
                self.dict_buf_parameters["low_limit"])
            self.setting_window.max_enter.setCurrentText(
                self.dict_buf_parameters["high_limit"])
            self.setting_window.step_enter.setCurrentText(
                self.dict_buf_parameters["step"])
            self.setting_window.triger_enter.setCurrentText(
                self.dict_buf_parameters["trigger"])
            self.setting_window.comportslist.setCurrentText(
                self.dict_buf_parameters["COM"])
            self.setting_window.boudrate.setCurrentText(
                self.dict_buf_parameters["baudrate"])
            if self.setting_window.triger_enter.currentText() == "Таймер":
                self.setting_window.sourse_enter.clear()
                self.setting_window.sourse_enter.setEditable(True)
                self.setting_window.sourse_enter.addItems(
                    ["5", "10", "30", "60", "120"])
                self.setting_window.sourse_enter.setCurrentText(
                    self.dict_buf_parameters["sourse/time"])
                self.setting_window.label_sourse.setText("Время(с)")
            else:
                self.setting_window.sourse_enter.clear()
                self.setting_window.sourse_enter.setEditable(False)
                self.setting_window.sourse_enter.addItems(["1", "2", "3", "4"])
                self.setting_window.sourse_enter.setCurrentText(
                    self.dict_buf_parameters["sourse/time"])
                self.setting_window.label_sourse.setText("Источник сигнала")
            self.key_to_signal_func = True  # разрешаем выполенение функций
            self.change_units()
            self.is_correct_parameters()
            # self.add_parameters_from_window()
            self.lock_double_open = False

            # self.action_when_select_step()
            # ==============================================================
    def scan_com_ports(self):
        self.counter += 1
        self.timer_for_scan_com_port.stop()
        ports = serial.tools.list_ports.comports()
        local_list_com_ports = []
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
            self.setting_window.comportslist.clear()
            self.setting_window.comportslist.addItems(local_list_com_ports)
        self.active_ports = local_list_com_ports
        self.timer_for_scan_com_port.start(1500)

    def is_correct_parameters(self):
        if self.key_to_signal_func:
            print("проверить параметры")
            if self.setting_window.type_work_enter.currentText() == "Стабилизация напряжения":
                max = self.max_voltage
                min = 0
            if self.setting_window.type_work_enter.currentText() == "Стабилизация тока":
                max = self.max_current
                min = 0
            if self.setting_window.type_work_enter.currentText() == "Стабилизация мощности":
                max = self.max_power
                min = 0

            enter_minimum = 0
            enter_maximum = 0
            enter_step = 0
            self.is_max_correct = True
            self.is_min_correct = True
            self.is_step_correct = True
    # проверка число или не число
            try:
                enter_minimum = float(
                    self.setting_window.min_enter.currentText())
            except:
                self.is_min_correct = False
            try:
                enter_maximum = float(
                    self.setting_window.max_enter.currentText())
            except:
                self.is_max_correct = False
            try:
                enter_step = float(
                    self.setting_window.step_enter.currentText())
            except:
                self.is_step_correct = False
    # ---------------------------
    # минимум и максимум больше нуля
            if self.is_max_correct:
                if enter_maximum < 0 or enter_maximum > max or enter_maximum < enter_minimum:
                    self.is_max_correct = False
            if self.is_min_correct:
                if enter_minimum < 0 or enter_minimum < min or enter_maximum < enter_minimum:
                    self.is_min_correct = False
            if self.is_step_correct:
                if self.is_min_correct and self.is_max_correct:
                    if enter_step > enter_maximum - enter_minimum:
                        self.is_step_correct = False

            if self.is_max_correct:
                self.setting_window.max_enter.setStyleSheet(
                    "background-color: rgb(255, 255, 255);")
            else:
                self.setting_window.max_enter.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")
            if self.is_min_correct:
                self.setting_window.min_enter.setStyleSheet(
                    "background-color: rgb(255, 255, 255);")
            else:
                self.setting_window.min_enter.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")
            if self.is_step_correct:
                if self.setting_window.type_step_enter.currentText() == "Адаптивный шаг":
                    self.setting_window.step_enter.setStyleSheet(
                        "background-color: rgb(180, 180, 180)")
                else:
                    self.setting_window.step_enter.setStyleSheet(
                        "background-color: rgb(255, 255, 255);")
            else:
                if self.setting_window.type_step_enter.currentText() == "Адаптивный шаг":
                    self.setting_window.step_enter.setStyleSheet(
                        "background-color: rgb(180, 180, 180)")
                else:
                    self.setting_window.step_enter.setStyleSheet(
                        "background-color: rgb(255, 180, 180);")

    def change_units(self):
        if self.key_to_signal_func:
            print("изменить параметры")
            if self.setting_window.type_work_enter.currentText() == "Стабилизация напряжения":
                self.setting_window.label_7.setText("V")
                self.setting_window.label_8.setText("V")
                self.setting_window.label_9.setText("V")
            if self.setting_window.type_work_enter.currentText() == "Стабилизация тока":
                self.setting_window.label_7.setText("A")
                self.setting_window.label_8.setText("A")
                self.setting_window.label_9.setText("A")
            if self.setting_window.type_work_enter.currentText() == "Стабилизация мощности":
                self.setting_window.label_7.setText("W")
                self.setting_window.label_8.setText("W")
                self.setting_window.label_9.setText("W")

    def action_when_select_step(self):
        if self.key_to_signal_func:
            print("выбор шага")
            if self.setting_window.type_step_enter.currentText() == "Адаптивный шаг":
                self.setting_window.step_enter.setEnabled(False)
                self.setting_window.step_enter.setStyleSheet(
                    "background-color: rgb(180, 180, 180)")
                self.setting_window.triger_enter.clear()
                self.setting_window.triger_enter.addItems(["Внешний сигнал"])
            else:
                self.setting_window.step_enter.setEnabled(True)
                # self.setting_window.triger_enter.clear()
                self.setting_window.triger_enter.addItems(
                    ["Таймер"])
    # если выбран таймер, то необходимо запретить выбирать источник сигнала

    def action_when_select_trigger(self):
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
                print(self.sourses)
                self.setting_window.sourse_enter.addItems(self.sourses)
                if buf in self.sourses:
                    self.setting_window.sourse_enter.setCurrentText(buf)
                self.setting_window.label_sourse.setText("Источник сигнала")
            # self.add_parameters_from_window()

    # вызывается при закрытии окна настроек
    def add_parameters_from_window(self):

        if self.key_to_signal_func:
            self.dict_buf_parameters["type_of_work"] = self.setting_window.type_work_enter.currentText(
            )
            self.dict_buf_parameters["type_step"] = self.setting_window.type_step_enter.currentText(
            )
            self.dict_buf_parameters["trigger"] = self.setting_window.triger_enter.currentText(
            )
            self.dict_buf_parameters["high_limit"] = self.setting_window.max_enter.currentText(
            )
            self.dict_buf_parameters["low_limit"] = self.setting_window.min_enter.currentText(
            )
            self.dict_buf_parameters["step"] = self.setting_window.step_enter.currentText(
            )
            self.dict_buf_parameters["sourse/time"] = self.setting_window.sourse_enter.currentText()
            self.dict_buf_parameters["baudrate"] = self.setting_window.boudrate.currentText(
            )
            self.dict_buf_parameters["COM"] = self.setting_window.comportslist.currentText(
            )

    def send_signal_ok(self):  # действие при подтверждении настроек, передать парамтры классу инсталляции, проверить и окрасить в цвет окошко, вписать паарметры

        self.add_parameters_from_window()
        # те же самые настройки, ничего не делаем
        if self.dict_buf_parameters == self.dict_settable_parameters and not self.i_am_set:
            return
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.i_am_set = False

        self.is_parameters_correct = True
        if not self.is_max_correct:
            self.is_parameters_correct = False
        if not self.is_min_correct:
            self.is_parameters_correct = False
        if self.dict_buf_parameters["type_step"] == "Заданный шаг":
            if not self.is_step_correct:
                self.is_parameters_correct = False
        if self.dict_buf_parameters["COM"] == 'Нет подключенных портов':
            self.is_parameters_correct = False
        self.timer_for_scan_com_port.stop()
        try:
            float(self.setting_window.max_enter.currentText())
            float(self.setting_window.min_enter.currentText())
            float(self.setting_window.step_enter.currentText())
            float(self.setting_window.boudrate.currentText())
        except:
            self.is_parameters_correct = False

        if self.is_parameters_correct:
            pass
        else:
            pass

        self.installation_class.message_from_device_settings(
            self.name, self.is_parameters_correct, self.dict_settable_parameters)

    # фцункция подтверждения корректности параметров от контроллера установкию. установка проверяет ком порты, распределяет их между устройствами и отдает каждому из устройств

    def confirm_parameters(self, answer, client):
        print(str(self.name) + " получил подтверждение настроек, рассчитываем шаги")
        if answer == True:

            self.i_am_set = True
            self.set_client(client)
            self.client.write_registers(address=int(
                "0040", 16), count=2, slave=1, values=[0, 120])

            self.steps_voltage.clear()
            self.steps_current.clear()
            if self.dict_buf_parameters["type_of_work"] == "Стабилизация напряжения":
                if self.dict_buf_parameters["type_step"] == "Заданный шаг":
                    self.steps_current, self.steps_voltage = self.fill_arrays(float(self.dict_buf_parameters['low_limit']), float(
                        self.dict_buf_parameters['high_limit']), float(self.dict_buf_parameters['step']), float(self.max_current))

            elif self.dict_buf_parameters["type_of_work"] == "Стабилизация тока":
                if self.dict_buf_parameters["type_step"] == "Заданный шаг":
                    self.steps_voltage, self.steps_current = self.fill_arrays(float(self.dict_buf_parameters['low_limit']), float(
                        self.dict_buf_parameters['high_limit']), float(self.dict_buf_parameters['step']), float(self.max_voltage))

            elif self.dict_buf_parameters["type_of_work"] == "Стабилизация мощности":
                if self.dict_buf_parameters["type_step"] == "Заданный шаг":
                    pass

        else:
            pass

    def check_connect(self) -> bool:
        # TODO проверка соединения с прибором(запрос - ответ)
        # проверка соединения
        self.installation_class.add_text_to_log(
            self.name + " - соединение установлено")
        return True

    def fill_arrays(self, start_value, stop_value, step, constant_value):
        steps_1 = []
        steps_2 = []
        current_value = start_value
        while current_value < stop_value:
            steps_1.append(constant_value)
            steps_2.append(current_value)
            current_value = current_value + step
            if current_value == stop_value:
                steps_1.append(constant_value)
                steps_2.append(current_value)
                break
        else:
            steps_1.append(constant_value)
            steps_2.append(stop_value)
        return steps_1, steps_2

    def set_client(self, client):
        self.client = client

    def set_voltage(self, voltage):
        return self.client.write_registers(address=int("0040", 16), count=2, slave=1, values=[0, voltage])
# удаленная настройка выходного тока 0,01А

    def set_current(self, current):
        return self.client.write_registers(address=int("0041", 16), count=2, slave=1, values=[0, current])

    def output_switching_on(self):
        return self.client.write_registers(address=int("0042", 16), count=2, slave=1, values=[0, 1])

    def output_switching_off(self):
        return self.client.write_registers(address=int("0042", 16), count=2, slave=1, values=[0, 0])

    # удаленная настройка выходной частоты в Гц
    def set_frequency(self, frequency):
        high = 0
        if frequency > 65535:
            high = 1
        frequency = frequency - 65535 - 1
        return self.client.write_registers(address=int("0043", 16), count=2, slave=1, values=[high, frequency])

    def set_duty_cycle(self, duty_cycle):
        if duty_cycle > 100 or duty_cycle < 1:
            return False
        return self.client.write_registers(address=int("0044", 16), count=2, slave=1, values=[0, duty_cycle])

    def get_current_voltage(self):
        return self.client.read_input_registers(address=int("0000", 16), count=1, slave=1)

    def get_current_current(self):
        return self.client.read_input_registers(address=int("0001", 16), count=1, slave=1)

    def get_current_frequency(self):
        pass

    def get_current_duty_cycle(self):
        pass

    def get_setting_voltage(self):
        return self.client.read_holding_registers(address=int("0040", 16), count=2, slave=1)

    def get_setting_current(self):
        return self.lient.read_holding_registers(address=int("0041", 16), count=2, slave=1)

    def get_setting_frequency(self):
        return self.client.read_holding_registers(address=int("0043", 16), count=2, slave=1)

    def get_setting_state(self):
        return self.client.read_holding_registers(address=int("0042", 16), count=2, slave=1)

    def get_setting_duty_cycle(self):
        return self.client.read_holding_registers(address=int("0044", 16), count=2, slave=1)


if __name__ == "__main__":
    # Создание клиента Modbus RTU
    client = ModbusSerialClient(
        method='rtu', port='COM3', baudrate=9600, stopbits=1, bytesize=8, parity='E')

    power_supply = maisheng_power_class()
    power_supply.set_client(client)

    # set_voltage(client,20000)
    '''
    for i in range(0,20000,1000):
        set_voltage(client,i)
        time.sleep(5)
    '''
    power_supply.output_switching_off()
    power_supply.set_current(1500)
    i = power_supply.get_setting_voltage()

    print(i.registers)

    '''
    print("установка напряжения ответ", set_voltage(client,10000))
    time.sleep(1)
    print("напряжение текущее ",get_setting_voltage(client))
    time.sleep(1)
    print("установка тока ответ",set_current(client,100))
    time.sleep(1)
    print("включениие ответ",output_switching_on(client))
    time.sleep(1)
    print("напряжение текущее после включения",get_current_voltage(client))
    '''
    # client.read_discrete_inputs(address=40, count=2, slave=2)
    # client.read_exception_status()
    # client.readwrite_registers()
    # Чтение данных из регистров хранения (holding registers)
    # client.read_coils(address=40, count=2, slave=2)
    # result = client.read_holding_registers(address=2, count=5, unit=1)
    # if result.isError():
    # print("Ошибка чтения данных:", result)
    # else:
    # print("Прочитанные данные:", result.registers)

    # Запись данных в регистры хранения
    '''
    data = [10, 20, 30, 40, 50]
    result = client.write_registers(address=0, values=data, unit=1)
    if result.isError():
        print("Ошибка записи данных:", result)
    else:
        print("Данные успешно записаны")
    '''
    # Закрытие соединения
    client.close()
