from interface.set_sr830_window import Ui_Set_sr830
from PyQt5 import QtCore, QtWidgets
import PyQt5.sip
import serial.tools.list_ports
from PyQt5.QtCore import QTimer, QDateTime
import serial
from pymeasure.instruments.srs import SR830
from pymeasure.adapters import SerialAdapter
import copy
from Classes import device_response_to_step


class sr830_class():
    def __init__(self, signal_list, installation_class, name) -> None:
        print("класс синхронного детектора создан")
        self.device = None  # класс прибора будет создан при подтверждении параметров,
        # показывает тип подключения устройства, нужно для анализа, какие устройства могут быть подключены к одному ком порту
        self.type_connection = "serial"
        # переменная хранит все возможные источники сигналов , сделать функцию, формирующую этот список в зависимости от структуры установки
        self.sourses = signal_list
        self.installation_class = installation_class
        # переменная хранит список доступных ком-портов
        self.active_ports = []
        self.counter = 0
        self.name = name

        self.client = 0
        self.dict_buf_parameters = {"trigger": "Таймер",
                                    "sourse/time": str(10),  # секунды
                                    "time_const": "1000",  # секунды
                                    "filter_slope": "6",  # dB
                                    "SYNK_200_Hz": "off",
                                    "sensitivity": "500",  # вольты
                                    "reserve": "high reserve",
                                    "input_channel": "A" + "/" + "AC" + "/" + "ground",
                                    "filters": "line",
                                    "frequency": "10000",  # Гц
                                    "amplitude": "1",  # Вольты
                                    "baudrate": "9600",
                                    "COM": None,
                                    }  # потенциальные параметры прибора, вводятся когда выбираются значения в настройках, применяются только после подтверждения пользователем и прохождении проверок
        self.dict_settable_parameters = {}  # текущие паарметры прибора
        self.is_window_created = False
        # разрешает исполнение кода в функциях, срабатывающих по сигналам
        self.key_to_signal_func = False

        # переменные для сохранения параметров окна-----------------------------
        self.frequency_enter = "400"
        self.amplitude_enter = "1"
        self.sourse_enter = "5"
        self.boudrate = "9600"
        self.comportslist = None
        self.time_const_enter_number = "1"
        self.time_const_enter_factor = "X1"
        self.time_const_enter_decimal_factor = "ks"
        self.Filt_slope_enter_level = "6 dB"
        self.SYNK_enter = "On"
        self.sensitivity_enter_number = "5"
        self.sensitivity_enter_factor = "X100"
        self.sensitivity_enter_decimal_factor = "V"
        self.input_channels_enter = "A"
        self.input_type_enter = "AC"
        self.connect_ch_enter = "float"
        self.reserve_enter = "high reserve"
        self.filters_enter = "line"
        self.triger_enter = "Таймер"

        self.i_am_set = False

    def get_type_connection(self) -> str:
        return self.type_connection

    def get_COM(self):
        return self.dict_buf_parameters["COM"]

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
            self.setting_window = Ui_Set_sr830()
            self.setting_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            self.setting_window.setupUi(self.setting_window)

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
            self.setting_window.triger_enter.addItems(
                ["Внешний сигнал"])
            self.setting_window.triger_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.sourse_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.amplitude_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.frequency_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")

            self.setting_window.frequency_enter.setEditable(True)
            self.setting_window.frequency_enter.addItems(
                ["400"])
            self.setting_window.amplitude_enter.setEditable(True)
            self.setting_window.amplitude_enter.addItems(
                ["1"])

            # =======================прием сигналов от окна==================

            self.setting_window.triger_enter.currentIndexChanged.connect(
                lambda: self.action_when_select_trigger())
            '''
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
            self.setting_window.sensitivity_enter_number.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.sensitivity_enter_factor.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.sensitivity_enter_decimal_factor.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())

            self.setting_window.time_const_enter_number.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.time_const_enter_decimal_factor.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.time_const_enter_factor.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            
            self.setting_window.Filt_slope_enter_level.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.SYNK_enter.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.reserve_enter.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.filters_enter.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            
            self.setting_window.input_channels_enter.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.input_type_enter.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.connect_ch_enter.currentIndexChanged.connect(
                lambda: self.add_parameters_from_window())

            self.setting_window.amplitude_enter.currentTextChanged.connect(
                lambda: self.add_parameters_from_window())
            self.setting_window.frequency_enter.currentTextChanged.connect(
                lambda: self.add_parameters_from_window())
            '''
            self.setting_window.amplitude_enter.currentTextChanged.connect(
                lambda: self.is_correct_parameters())
            self.setting_window.frequency_enter.currentTextChanged.connect(
                lambda: self.is_correct_parameters())

            self.setting_window.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(
                self.send_signal_ok)
            # ======================================================
            self.setting_window.show()
            self.key_to_signal_func = False
            # ============установка текущих параметров=======================

            self.setting_window.frequency_enter.setCurrentText(
                self.frequency_enter)
            self.setting_window.amplitude_enter.setCurrentText(
                self.amplitude_enter)
            self.setting_window.sourse_enter.setCurrentText(self.sourse_enter)
            self.setting_window.boudrate.setCurrentText(self.boudrate)
            self.setting_window.comportslist.setCurrentText(self.comportslist)
            self.setting_window.time_const_enter_number.setCurrentText(
                self.time_const_enter_number)
            self.setting_window.time_const_enter_factor.setCurrentText(
                self.time_const_enter_factor)
            self.setting_window.time_const_enter_decimal_factor.setCurrentText(
                self.time_const_enter_decimal_factor)
            self.setting_window.Filt_slope_enter_level.setCurrentText(
                self.Filt_slope_enter_level)
            self.setting_window.SYNK_enter.setCurrentText(self.SYNK_enter)
            self.setting_window.sensitivity_enter_number.setCurrentText(
                self.sensitivity_enter_number)
            self.setting_window.sensitivity_enter_factor.setCurrentText(
                self.sensitivity_enter_factor)
            self.setting_window.sensitivity_enter_decimal_factor.setCurrentText(
                self.sensitivity_enter_decimal_factor)
            self.setting_window.input_channels_enter.setCurrentText(
                self.input_channels_enter)
            self.setting_window.input_type_enter.setCurrentText(
                self.input_type_enter)
            self.setting_window.connect_ch_enter.setCurrentText(
                self.connect_ch_enter)
            self.setting_window.reserve_enter.setCurrentText(
                self.reserve_enter)
            self.setting_window.filters_enter.setCurrentText(
                self.filters_enter)
            self.setting_window.triger_enter.setCurrentText(self.triger_enter)

            if self.setting_window.triger_enter.currentText() == "Таймер":
                self.setting_window.sourse_enter.clear()
                self.setting_window.sourse_enter.setEditable(True)
                self.setting_window.sourse_enter.addItems(
                    ["5", "10", "30", "60", "120"])
                self.setting_window.sourse_enter.setCurrentText(
                    self.sourse_enter)
                self.setting_window.label_sourse.setText("Время(с)")
            else:
                self.setting_window.sourse_enter.clear()
                self.setting_window.sourse_enter.setEditable(False)
                self.setting_window.sourse_enter.addItems(["1", "2", "3", "4"])
                self.setting_window.sourse_enter.setCurrentText(
                    self.sourse_enter)
                self.setting_window.label_sourse.setText("Источник сигнала")
            self.key_to_signal_func = True  # разрешаем выполенение функций

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
        # TODO: проверка параметров
        pass

    def change_units(self):
        pass

    def action_when_select_trigger(self):
        if self.key_to_signal_func:
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
                self.setting_window.sourse_enter.addItems(self.sourses)

                if buf in self.sourses:
                    self.setting_window.sourse_enter.setCurrentText(buf)
                self.setting_window.label_sourse.setText("Источник сигнала")
            # self.add_parameters_from_window()

    def calculate_time_const(self) -> str:
        time_const_enter_factor = {"X1": 1, "X10": 10, "X100": 100}
        time_const_enter_decimal_factor = {
            "ks": 1000, "s": 1, "ms": 0.001, "us": 0.000001}
        factor = time_const_enter_factor[self.setting_window.time_const_enter_factor.currentText(
        )]
        decimal_factor = time_const_enter_decimal_factor[self.setting_window.time_const_enter_decimal_factor.currentText(
        )]
        return float(self.setting_window.time_const_enter_number.currentText()) * factor * decimal_factor

    def calculate_sensitivity(self) -> str:
        sensitivity_enter_factor = {"X1": 1, "X10": 10, "X100": 100}
        sensitivity_enter_decimal_factor = {
            "V": 1, "mV": 0.001, "uV": 0.000001, "nV": 0.000000001}
        factor = sensitivity_enter_factor[self.setting_window.sensitivity_enter_factor.currentText(
        )]
        decimal_factor = sensitivity_enter_decimal_factor[self.setting_window.sensitivity_enter_decimal_factor.currentText(
        )]
        return float(self.setting_window.sensitivity_enter_number.currentText()) * factor * decimal_factor

    def add_parameters_from_window(self):
        self.frequency_enter = self.setting_window.frequency_enter.currentText()
        self.amplitude_enter = self.setting_window.amplitude_enter.currentText()
        self.time_const_enter_number = self.setting_window.time_const_enter_number.currentText()
        self.time_const_enter_factor = self.setting_window.time_const_enter_factor.currentText()
        self.time_const_enter_decimal_factor = self.setting_window.time_const_enter_decimal_factor.currentText()
        self.Filt_slope_enter_level = self.setting_window.Filt_slope_enter_level.currentText()
        self.SYNK_enter = self.setting_window.SYNK_enter.currentText()
        self.sensitivity_enter_number = self.setting_window.sensitivity_enter_number.currentText()
        self.sensitivity_enter_factor = self.setting_window.sensitivity_enter_factor.currentText()
        self.sensitivity_enter_decimal_factor = self.setting_window.sensitivity_enter_decimal_factor.currentText()
        self.input_channels_enter = self.setting_window.input_channels_enter.currentText()
        self.input_type_enter = self.setting_window.input_type_enter.currentText()
        self.connect_ch_enter = self.setting_window.connect_ch_enter.currentText()
        self.reserve_enter = self.setting_window.reserve_enter.currentText()
        self.filters_enter = self.setting_window.filters_enter.currentText()
        self.triger_enter = self.setting_window.triger_enter.currentText()
        self.sourse_enter = self.setting_window.sourse_enter.currentText()
        self.boudrate = self.setting_window.boudrate.currentText()
        self.comportslist = self.setting_window.comportslist.currentText()

        time_const = self.calculate_time_const()
        sensitivity = self.calculate_sensitivity()
        dict_filter_slope = {"6 dB": 6, "12 dB": 12, "18 dB": 18, "24 dB": 24}
        filter_slope = dict_filter_slope[self.setting_window.Filt_slope_enter_level.currentText(
        )]

        SYNK_200_Hz = self.setting_window.SYNK_enter.currentText()
        reserve = self.setting_window.reserve_enter.currentText()
        frequency = self.setting_window.frequency_enter.currentText()
        amplitude = self.setting_window.amplitude_enter.currentText()

        input_channel = self.setting_window.input_channels_enter.currentText(
        ) + "/" + self.setting_window.input_type_enter.currentText() + "/" + self.setting_window.connect_ch_enter.currentText()

        if self.key_to_signal_func:
            self.dict_buf_parameters["time_const"] = time_const
            self.dict_buf_parameters["filter_slope"] = filter_slope
            self.dict_buf_parameters["SYNK_200_Hz"] = SYNK_200_Hz
            self.dict_buf_parameters["sensitivity"] = sensitivity
            self.dict_buf_parameters["reserve"] = reserve
            self.dict_buf_parameters["frequency"] = frequency
            self.dict_buf_parameters["amplitude"] = amplitude
            self.dict_buf_parameters["input_channel"] = input_channel
            self.dict_buf_parameters["filters"] = self.setting_window.filters_enter.currentText(
            )
            self.dict_buf_parameters["trigger"] = self.setting_window.triger_enter.currentText(
            )
            self.dict_buf_parameters["sourse/time"] = self.setting_window.sourse_enter.currentText()
            self.dict_buf_parameters["baudrate"] = self.setting_window.boudrate.currentText(
            )
            self.dict_buf_parameters["COM"] = self.setting_window.comportslist.currentText(
            )

    def set_client(self, client):
        self.client = client

    def do_step(self):
        parameters = []

        print("сделан шаг", self.name)
        return device_response_to_step.Step_done, parameters

    def get_trigger_value(self):
        return self.dict_settable_parameters["sourse/time"]

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

        if self.is_parameters_correct:
            pass
        else:
            pass
        self.installation_class.message_from_device_settings(
            self.name, self.is_parameters_correct, self.dict_settable_parameters)

    # фцункция подтверждения корректности параметров от контроллера установкию. установка проверяет ком порты, распределяет их между устройствами и отдает каждому из устройств
    def confirm_parameters(self):
        print(str(self.name) +
              " получил подтверждение настроек, рассчитываем шаги")
        if True:

            self.step_index = 0
            self.i_am_set = True
            self.device = SR830(SerialAdapter(self.client))
            '''

            if self.check_connect():
                self.installation_class.message_from_device_status_connect(
                    True, self.name)
            else:
                self.installation_class.message_from_device_status_connect(
                    False, self.name)
            pass
            '''

        else:
            pass

    def check_connect(self) -> bool:
        # TODO проверка соединения с прибором(запрос - ответ)
        # проверка соединения
        return True

    # настройка прибора перед началом эксперимента, переопределяется при каждлом старте эксперимента
    def setup_before_experiment(self) -> bool:
        pass

    def get_settings(self):
        return self.dict_settable_parameters


if __name__ == "__main__":
    pass
    # Создание клиента Modbus RTU
    # client = ModbusSerialClient(
    # method='rtu', port='COM3', baudrate=9600, stopbits=1, bytesize=8, parity='E')

    # power_supply = maisheng_power_class()
    # power_supply.set_client(client)

    # set_voltage(client,20000)

    '''
    for i in range(0,20000,1000):
        set_voltage(client,i)
        time.sleep(5)
    '''

    # power_supply.output_switching_off()
    # power_supply.set_current(1500)
    # i = power_supply.get_setting_voltage()
    # print(i.registers)

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
    # client.close()

'''

        self.frequency_enter
        self.amplitude_enter
        self.time_const_enter_number
        self.time_const_enter_factor
        self.time_const_enter_decimal_factor
        self.Filt_slope_enter_level
        self.SYNK_enter
        self.sensitivity_enter_number
        self.sensitivity_enter_factor
        self.sensitivity_enter_decimal_factor
        self.input_channels_enter
        self.input_type_enter
        self.connect_ch_enter
        self.reserve_enter
        self.filters_enter
        self.triger_enter
        self.sourse_enter
        self.boudrate
        self.comportslist
    










        self.time_const_enter_number = "1"
        self.time_const_enter_factor = "X1"
        self.time_const_enter_decimal_factor = "ks"
        self.Filt_slope_enter_level = "6 dB"
        self.SYNK_enter = "On"
        self.sensitivity_enter_number"5"
        self.sensitivity_enter_factor"X100"
        self.sensitivity_enter_decimal_factor"V"
        self.input_channels_enter"A"
        self.input_type_enter = "AC"
        self.connect_ch_enter = "float"
        self.reserve_enter = "high reserve"
        self.filters_enter = "line"
        self.triger_enter = "Таймер"


'''
