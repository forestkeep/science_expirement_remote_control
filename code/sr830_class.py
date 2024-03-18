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


class sr830_class(installation_device):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "serial", installation_class)
        print("класс синхронного детектора создан")
        self.device = None  # класс прибора будет создан при подтверждении параметров,
        # переменная хранит все возможные источники сигналов , сделать функцию, формирующую этот список в зависимости от структуры установки
        self.counter = 0
        self.dict_buf_parameters["time_const"] = "1000",  # секунды
        self.dict_buf_parameters["filter_slope"] = "6",  # dB
        self.dict_buf_parameters["SYNK_200_Hz"] = "off",
        self.dict_buf_parameters["sensitivity"] = "1",  # вольты
        self.dict_buf_parameters["reserve"] = "high reserve"
        self.dict_buf_parameters["input_channel"] = "A"
        self.dict_buf_parameters["input_type"] = "AC"
        self.dict_buf_parameters["input_connect"] = "ground"
        self.dict_buf_parameters["filters"] = "line"
        self.dict_buf_parameters["frequency"] = "400"
        self.dict_buf_parameters["amplitude"] = "1"
        self.dict_buf_parameters["num steps"] = "1"

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
        self.sensitivity_enter_number = "1"
        self.sensitivity_enter_factor = "X1"
        self.sensitivity_enter_decimal_factor = "V"
        self.input_channels_enter = "A"
        self.input_type_enter = "AC"
        self.connect_ch_enter = "float"
        self.reserve_enter = "high reserve"
        self.filters_enter = "line"
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
            self.setting_window = Ui_Set_sr830()
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
            self.setting_window.amplitude_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.frequency_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")

            self.setting_window.SYNK_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.filters_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.reserve_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.connect_ch_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.Filt_slope_enter_level.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.input_type_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.sensitivity_enter_decimal_factor.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.sensitivity_enter_factor.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.sensitivity_enter_number.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.time_const_enter_decimal_factor.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.time_const_enter_number.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.time_const_enter_factor.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.input_channels_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.comportslist.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.boudrate.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.num_meas_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")

            self.setting_window.frequency_enter.setEditable(True)
            self.setting_window.frequency_enter.addItems(
                ["400"])
            self.setting_window.amplitude_enter.setEditable(True)
            self.setting_window.amplitude_enter.addItems(
                ["1"])

            self.setting_window.num_meas_enter.setEditable(True)
            self.setting_window.num_meas_enter.addItems(
                ["3"])

            # =======================прием сигналов от окна==================
            self.setting_window.sensitivity_enter_number.currentIndexChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.sensitivity_enter_factor.currentIndexChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.sensitivity_enter_decimal_factor.currentIndexChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.amplitude_enter.currentIndexChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.frequency_enter.currentIndexChanged.connect(
                lambda: self._is_correct_parameters())

            self.setting_window.triger_enter.currentIndexChanged.connect(
                lambda: self._action_when_select_trigger())

            self.setting_window.amplitude_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.frequency_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())

            self.setting_window.num_meas_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.sourse_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())

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
            '''
            if self.comportslist is not None:
                self.setting_window.comportslist.setCurrentText(
                    self.comportslist)
            '''
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
            num_meas_list = ["5","10","20","50"]
            if self.installation_class.get_signal_list(self.name) != []:#если в списке сигналов пусто, то и других активных приборов нет, текущий прибор в установке один
                num_meas_list.append("Пока активны другие приборы")
            self.setting_window.num_meas_enter.addItems(num_meas_list)
            self.setting_window.num_meas_enter.setCurrentText(
                str(self.number_steps))

            self.setting_window.sourse_enter.setCurrentText(
                self.dict_buf_parameters["sourse/time"])

            '''

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
                self.signal_list = self.installation_class.get_signal_list(
                    self.name)
                self.setting_window.sourse_enter.addItems(self.signal_list)
                self.setting_window.sourse_enter.addItems(["1", "2", "3", "4"])
                self.setting_window.sourse_enter.setCurrentText(
                    self.sourse_enter)
                self.setting_window.label_sourse.setText("Источник сигнала")
            '''
            self.key_to_signal_func = True  # разрешаем выполенение функций
            self._action_when_select_trigger()

    def _is_correct_parameters(self) -> bool:  # менять для каждого прибора
        if self.key_to_signal_func:
            # print("проверить параметры")
            is_number_correct = True
            is_fact_correct = True
            is_dec_fact_correct = True

            is_ampl_correct = True
            is_freq_correct = True
            is_num_steps_correct = True
            is_time_correct = True
            if self.setting_window.sensitivity_enter_decimal_factor.currentText() == "V/uA":

                if self.setting_window.sensitivity_enter_factor.currentText() != "X1":
                    is_fact_correct = False
                if self.setting_window.sensitivity_enter_number.currentText() != "1":
                    is_number_correct = False
            elif self.setting_window.sensitivity_enter_decimal_factor.currentText() == "nV/fA":
                if self.setting_window.sensitivity_enter_number.currentText() == "1":
                    is_number_correct = False
# число илии нет
            try:
                float(self.setting_window.amplitude_enter.currentText())
            except:
                is_ampl_correct = False
            try:
                float(self.setting_window.frequency_enter.currentText())
            except:
                is_freq_correct = False

            if is_ampl_correct:
                if float(self.setting_window.amplitude_enter.currentText()) > 10 or float(self.setting_window.amplitude_enter.currentText()) < 0.01:
                    is_ampl_correct = False
            if is_freq_correct:
                if float(self.setting_window.frequency_enter.currentText()) > 102000 or float(self.setting_window.frequency_enter.currentText()) < 0.01:
                    is_freq_correct = False
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

            self.setting_window.sensitivity_enter_number.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.sensitivity_enter_factor.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.sensitivity_enter_decimal_factor.setStyleSheet(
                "background-color: rgb(255, 255, 255);")

            self.setting_window.amplitude_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.frequency_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.num_meas_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.sourse_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")

            if not is_number_correct:
                self.setting_window.sensitivity_enter_number.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")
            if not is_fact_correct:
                self.setting_window.sensitivity_enter_factor.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")
            if not is_dec_fact_correct:
                self.setting_window.sensitivity_enter_decimal_factor.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")

            if not is_freq_correct:
                self.setting_window.frequency_enter.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")
            if not is_ampl_correct:
                self.setting_window.amplitude_enter.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")

            if not is_num_steps_correct:
                self.setting_window.num_meas_enter.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")

            if not is_time_correct:
                self.setting_window.sourse_enter.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")

            if is_number_correct and is_fact_correct and is_dec_fact_correct and is_ampl_correct and is_freq_correct and is_num_steps_correct and is_time_correct:
                return True
            else:
                return False

    def change_units(self):
        pass

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
            "V/uA": 1, "mV/nA": 0.001, "uV/pA": 0.000001, "nV/fA": 0.000000001}  # в вольтах подсчет
        factor = sensitivity_enter_factor[self.setting_window.sensitivity_enter_factor.currentText(
        )]
        decimal_factor = sensitivity_enter_decimal_factor[self.setting_window.sensitivity_enter_decimal_factor.currentText(
        )]

        return round((float(self.setting_window.sensitivity_enter_number.currentText()) * factor * decimal_factor)*1000000000)/1000000000

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

        try:
            self.number_steps = int(
                self.setting_window.num_meas_enter.currentText())
        except:
            if self.setting_window.num_meas_enter.currentText() == "":
                self.number_steps = self.setting_window.num_meas_enter.currentText()
            else:
                self.number_steps = "Пока активны другие приборы"

        time_const = self.calculate_time_const()
        sensitivity = self.calculate_sensitivity()
        dict_filter_slope = {"6 dB": 6, "12 dB": 12, "18 dB": 18, "24 dB": 24}
        filter_slope = dict_filter_slope[self.setting_window.Filt_slope_enter_level.currentText(
        )]

        SYNK_200_Hz = self.setting_window.SYNK_enter.currentText()
        reserve = self.setting_window.reserve_enter.currentText()
        frequency = self.setting_window.frequency_enter.currentText()
        amplitude = self.setting_window.amplitude_enter.currentText()

        if self.key_to_signal_func:
            self.dict_buf_parameters["time_const"] = time_const
            self.dict_buf_parameters["filter_slope"] = filter_slope
            self.dict_buf_parameters["SYNK_200_Hz"] = SYNK_200_Hz
            self.dict_buf_parameters["sensitivity"] = sensitivity
            self.dict_buf_parameters["reserve"] = reserve
            self.dict_buf_parameters["frequency"] = float(frequency)
            self.dict_buf_parameters["amplitude"] = float(amplitude)
            self.dict_buf_parameters["num steps"] = self.number_steps

            self.dict_buf_parameters["input_channel"] = self.setting_window.input_channels_enter.currentText(
            )
            self.dict_buf_parameters["input_type"] = self.setting_window.input_type_enter.currentText(
            )
            self.dict_buf_parameters["input_connect"] = self.setting_window.connect_ch_enter.currentText(
            )

            self.dict_buf_parameters["filters"] = self.setting_window.filters_enter.currentText(
            )
            self.dict_buf_parameters["trigger"] = self.setting_window.triger_enter.currentText(
            )
            self.dict_buf_parameters["sourse/time"] = self.setting_window.sourse_enter.currentText()
            self.dict_buf_parameters["baudrate"] = self.setting_window.boudrate.currentText(
            )
            self.dict_buf_parameters["COM"] = self.setting_window.comportslist.currentText(
            )

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

    # фцункция подтверждения корректности параметров от контроллера установкию. установка проверяет ком порты, распределяет их между устройствами и отдает каждому из устройств
    def confirm_parameters(self):
        print(str(self.name) +
              " получил подтверждение настроек, рассчитываем шаги")
        if True:

            self.step_index = -1
            self.i_am_set = True
            self.command = commandsSR830(self.client)
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
    # настройка прибора перед началом эксперимента, переопределяется при каждлом старте эксперимента

    def action_before_experiment(self) -> bool:  # менять для каждого прибора

        print("настройка прибора " + str(self.name) + " перед экспериментом..")
        pause = 0.1
        status = True
        if not self.command._set_filter_slope(
                slope=self.dict_settable_parameters["filter_slope"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_input_conf(
                conf=self.dict_settable_parameters["input_channel"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_input_type_conf(
                type_conf=self.dict_settable_parameters["input_type"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_input_type_connect(
                input_ground=self.dict_settable_parameters["input_connect"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_line_filters(
                type=self.dict_settable_parameters["filters"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_reserve(
                reserve=self.dict_settable_parameters["reserve"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_time_const(
                time_constant=self.dict_settable_parameters["time_const"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_sens(
                sens=self.dict_settable_parameters["sensitivity"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_frequency(
                freq=self.dict_settable_parameters["frequency"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_amplitude(
                ampl=self.dict_settable_parameters["amplitude"]):
            status = False
        print((status))
        return status

    def action_end_experiment(self) -> bool:
        '''плавное выключение прибора'''
        return True

    def do_meas(self):
        '''прочитать текущие и настроенные значения'''
        print("делаем измерение", self.name)

        start_time = time.time()
        parameters = [self.name]
        is_correct = True

        is_stop_analyze = False
        count = 0
        result_analyze = False
        while not is_stop_analyze:
            self.command.push_autophase()
            buf_display_value = []
            for i in range(10):
                disp2 = self.command.get_parameter(self.command.COMM_DISPLAY, timeout=1, param=2)
                print(disp2)
                if not disp2:
                    continue
                else:
                    buf_display_value.append(float(disp2))
                    #val = ["disp2=" + str(disp2)]
                    #parameters.append(val)
                #time.sleep(0.05)
            if len(buf_display_value) > 3:
                if max(buf_display_value) < 2 and min(buf_display_value) > -2:#выход за границы
                    if len(buf_display_value) >= 5:
                        for i in range(len(buf_display_value)-2):#анализ монотонности
                            if buf_display_value[i] >= buf_display_value[i+1] and buf_display_value[i+1] <= buf_display_value[i+2]:
                                is_stop_analyze = True
                                result_analyze = True
                                break
                            if buf_display_value[i] <= buf_display_value[i+1] and buf_display_value[i+1] >= buf_display_value[i+2]:
                                is_stop_analyze = True
                                result_analyze = True
                                break

            count+=1
            print("счетчик повторов нажатий кнопки автофаза",count)
            if count >= 10:
                is_stop_analyze = True


        if result_analyze == True:
            print("удалось устаканить фазу, измеряем...")
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
        else:
            print("Не получилось обнулить фазу, ставим прочерки", self.name)
            val = ["disp1=" + "fail"]
            parameters.append(val)
            val = ["disp2=" + "fail"]
            parameters.append(val)
            val = ["phase=" + "fail"]
            parameters.append(val)

        # -----------------------------
        if is_debug:
            if is_correct == False:
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
        line = self.command.get_parameter(self.command.COMM_ID, timeout=1)
        if line is not False:
            print(line)
            return True
        return False


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
