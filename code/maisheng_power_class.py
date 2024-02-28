from pymodbus.client import ModbusSerialClient
from pymodbus.utilities import computeCRC
from interface.set_power_supply_window import Ui_Set_power_supply
from PyQt5 import QtCore, QtWidgets
import PyQt5.sip
import serial.tools.list_ports
from PyQt5.QtCore import QTimer, QDateTime
import copy
from Classes import device_response_to_step, installation_device
from pymodbus import exceptions
import time
from Classes import is_debug
# 3Регулируемый блок питания MAISHENG WSD-20H15 (200В, 15А)
# Создание клиента Modbus RTU

# Отправлено главным компьютером: 01 10 00 40 00 02 04 00 00 (4E 20) (C3 E7) (При
#                                01 10 00 40 00 02 04 00 00  4E 20   C3 E7

# напряжении 200V, единица измерения 0,01 V)
# Ответ конечного устройства: 01 10 00 40 00 02 40 1C

# удаленная настройка выходного напряжения 0,01 В


class maisheng_power_class(installation_device):
    def __init__(self, name, installation_class) -> None:

        super().__init__(name, "modbus", installation_class)

        print("класс источника питания создан")

        # заполняется в случае корректных параметров(подтверждения от контроллера установки)
        self.steps_current = []
        # заполняется в случае корректных параметров(подтверждения от контроллера установки)
        self.steps_voltage = []

        self.max_current = 15
        self.max_voltage = 200
        self.max_power = 2000
        self.min_step_V = 0.01
        self.min_step_A = 0.1
        self.min_step_W = 1
        self.dict_buf_parameters["type_of_work"] = "Стабилизация напряжения"
        self.dict_buf_parameters["type_step"] = "Заданный шаг"
        self.dict_buf_parameters["high_limit"] = str(10)
        self.dict_buf_parameters["low_limit"] = str(self.min_step_V)
        self.dict_buf_parameters["step"] = "2"
        self.dict_buf_parameters["second_value"] = str(self.max_current)

    def show_setting_window(self):  # менять для каждого прибора

        if self.is_window_created:
            pass
        else:
            # при новом запуске окна настроек необходимо обнулять активный порт для продолжения сканирования
            self.active_ports = []
            self.setting_window = Ui_Set_power_supply()
            self.setting_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            self.setting_window.setupUi(self.setting_window)

            self.setting_window.type_work_enter.addItems(
                ["Стабилизация напряжения", "Стабилизация тока", "Стабилизация мощности"])
            self.setting_window.triger_enter.addItems(
                ["Таймер", "Внешний сигнал"])
            self.setting_window.triger_enter.setEnabled(True)

            self.setting_window.type_step_enter.addItems(
                ["Заданный шаг"])  # "Адаптивный шаг"
            # +++++++++++++++++выбор ком порта+++++++++++++
            self._scan_com_ports()
            # ++++++++++++++++++++++++++++++++++++++++++

            self.setting_window.boudrate.addItems(
                ["50", "75", "110", "150", "300", "600", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
            self.setting_window.sourse_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.type_step_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.type_work_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.triger_enter.setStyleSheet(
                "background-color: rgb(255, 255, 255);")
            self.setting_window.boudrate.setStyleSheet(
                "background-color: rgb(255, 255, 255)")
            self.setting_window.comportslist.setStyleSheet(
                "background-color: rgb(255, 255, 255)")
            # =======================прием сигналов от окна==================
            self.setting_window.type_work_enter.currentIndexChanged.connect(
                lambda: self._change_units())
            self.setting_window.type_work_enter.currentIndexChanged.connect(
                lambda: self._is_correct_parameters())

            self.setting_window.type_step_enter.currentIndexChanged.connect(
                lambda: self._action_when_select_step())
            self.setting_window.type_step_enter.currentIndexChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.type_step_enter.currentIndexChanged.connect(
                lambda: self._action_when_select_trigger())

            self.setting_window.triger_enter.currentIndexChanged.connect(
                lambda: self._action_when_select_trigger())

            self.setting_window.step_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.stop_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.start_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.second_limit_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.sourse_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())

            self.setting_window.comportslist.highlighted.connect(
                lambda: self._scan_com_ports())

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
            self.setting_window.start_enter.setCurrentText(
                self.dict_buf_parameters["low_limit"])
            self.setting_window.stop_enter.setCurrentText(
                self.dict_buf_parameters["high_limit"])
            self.setting_window.step_enter.setCurrentText(
                self.dict_buf_parameters["step"])
            self.setting_window.triger_enter.setCurrentText(
                self.dict_buf_parameters["trigger"])
            self.setting_window.comportslist.setCurrentText(
                self.dict_buf_parameters["COM"])
            self.setting_window.boudrate.setCurrentText(
                self.dict_buf_parameters["baudrate"])
            self.setting_window.second_limit_enter.setCurrentText(
                self.dict_buf_parameters["second_value"])
            self.setting_window.second_limit_enter.setEnabled(True)

            if self.dict_buf_parameters["type_of_work"] == "Стабилизация напряжения":
                self.setting_window.second_value_limit_label.setText(
                    "Ток не выше (А)")

            elif self.dict_buf_parameters["type_of_work"] == "Стабилизация тока":
                self.setting_window.second_value_limit_label.setText(
                    "Напряжение не выше (V)")
            else:
                self.setting_window.second_value_limit_label.setText(
                    "---")
                self.setting_window.second_limit_enter.setEnabled(False)

            self.key_to_signal_func = True  # разрешаем выполенение функций
            self._action_when_select_trigger()
            self._change_units()
            self._is_correct_parameters()

    def _is_correct_parameters(self):  # менять для каждого прибора
        if self.key_to_signal_func:
            print("проверить параметры")
            if self.setting_window.type_work_enter.currentText() == "Стабилизация напряжения":
                max = self.max_voltage
                min = self.min_step_V
                max_second_limit = self.max_current
            if self.setting_window.type_work_enter.currentText() == "Стабилизация тока":
                max = self.max_current
                min = self.min_step_A
                max_second_limit = self.max_voltage
            if self.setting_window.type_work_enter.currentText() == "Стабилизация мощности":
                max = self.max_power
                min = self.min_step_W

            low_value = 0
            high_value = 0
            enter_step = 0
            second_limit = 0
            self.is_stop_value_correct = True
            self.is_start_value_correct = True
            self.is_step_correct = True
            self.is_second_value_correct = True
            self.is_time_correct = True
    # проверка число или не число

            if self.setting_window.triger_enter.currentText() == "Таймер":
                try:
                    int(self.setting_window.sourse_enter.currentText())
                except:
                    self.is_time_correct = False

            try:
                low_value = float(
                    self.setting_window.start_enter.currentText())
            except:
                self.is_start_value_correct = False
            try:
                high_value = float(
                    self.setting_window.stop_enter.currentText())
            except:
                self.is_stop_value_correct = False
            try:
                enter_step = float(
                    self.setting_window.step_enter.currentText())
            except:
                self.is_step_correct = False
            try:
                second_limit = float(
                    self.setting_window.second_limit_enter.currentText())
            except:
                self.is_second_value_correct = False
    # ---------------------------
    # минимум и максимум не выходят за границы
            if self.is_stop_value_correct:
                if high_value < min or high_value > max:
                    self.is_stop_value_correct = False
            if self.is_start_value_correct:
                if low_value < min or low_value > max:
                    self.is_start_value_correct = False
            if self.is_step_correct:
                if self.is_start_value_correct and self.is_stop_value_correct:
                    if enter_step > abs(high_value - low_value):
                        self.is_step_correct = False
            if self.is_second_value_correct and self.setting_window.type_work_enter.currentText() != "Стабилизация мощности":
                if second_limit > max_second_limit or second_limit < 0.01:
                    self.is_second_value_correct = False

            if self.is_time_correct:
                self.setting_window.sourse_enter.setStyleSheet(
                    "background-color: rgb(255, 255, 255);")
            else:
                self.setting_window.sourse_enter.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")

            if self.is_stop_value_correct:
                self.setting_window.stop_enter.setStyleSheet(
                    "background-color: rgb(255, 255, 255);")
            else:
                self.setting_window.stop_enter.setStyleSheet(
                    "background-color: rgb(255, 180, 180);")
            if self.is_start_value_correct:
                self.setting_window.start_enter.setStyleSheet(
                    "background-color: rgb(255, 255, 255);")
            else:
                self.setting_window.start_enter.setStyleSheet(
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
            if self.is_second_value_correct:
                self.setting_window.second_limit_enter.setStyleSheet(
                    "background-color: rgb(255, 255, 255);")
            else:
                if self.setting_window.type_work_enter.currentText() != "Стабилизация мощности":
                    self.setting_window.second_limit_enter.setStyleSheet(
                        "background-color: rgb(255, 180, 180);")
                else:
                    self.setting_window.second_limit_enter.setStyleSheet(
                        "background-color: rgb(255, 255, 255);")

    def _change_units(self):
        if self.key_to_signal_func:
            print("изменить параметры")
            self.setting_window.second_limit_enter.setEnabled(True)
            if self.setting_window.type_work_enter.currentText() == "Стабилизация напряжения":
                self.setting_window.label_7.setText("V")
                self.setting_window.label_8.setText("V")
                self.setting_window.label_9.setText("V")
                self.setting_window.second_value_limit_label.setText(
                    "Ток не выше (А)")
            if self.setting_window.type_work_enter.currentText() == "Стабилизация тока":
                self.setting_window.label_7.setText("A")
                self.setting_window.label_8.setText("A")
                self.setting_window.label_9.setText("A")
                self.setting_window.second_value_limit_label.setText(
                    "Напряжение не выше (V)")
            if self.setting_window.type_work_enter.currentText() == "Стабилизация мощности":
                self.setting_window.label_7.setText("W")
                self.setting_window.label_8.setText("W")
                self.setting_window.label_9.setText("W")
                self.setting_window.second_value_limit_label.setText(
                    "---")
                self.setting_window.second_limit_enter.setStyleSheet(
                    "background-color: rgb(180, 180, 180)")
                self.setting_window.second_limit_enter.setEnabled(False)

    def _action_when_select_step(self):
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

    def add_parameters_from_window(self):  # менять для каждого прибора

        if self.key_to_signal_func:
            self.dict_buf_parameters["type_of_work"] = self.setting_window.type_work_enter.currentText(
            )
            self.dict_buf_parameters["type_step"] = self.setting_window.type_step_enter.currentText(
            )
            self.dict_buf_parameters["trigger"] = self.setting_window.triger_enter.currentText(
            )
            self.dict_buf_parameters["high_limit"] = self.setting_window.stop_enter.currentText(
            )
            self.dict_buf_parameters["low_limit"] = self.setting_window.start_enter.currentText(
            )
            self.dict_buf_parameters["step"] = self.setting_window.step_enter.currentText(
            )
            self.dict_buf_parameters["sourse/time"] = self.setting_window.sourse_enter.currentText()
            self.dict_buf_parameters["baudrate"] = self.setting_window.boudrate.currentText(
            )
            self.dict_buf_parameters["COM"] = self.setting_window.comportslist.currentText(
            )
            self.dict_buf_parameters["second_value"] = self.setting_window.second_limit_enter.currentText(
            )

    def send_signal_ok(self):  # действие при подтверждении настроек, передать парамтры классу инсталляции, проверить и окрасить в цвет окошко, вписать паарметры

        self.add_parameters_from_window()
        # те же самые настройки, ничего не делаем
        if self.dict_buf_parameters == self.dict_settable_parameters and not self.i_am_set:
            return
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.i_am_set = False

        self.is_parameters_correct = True
        if not self.is_stop_value_correct:
            self.is_parameters_correct = False
        if not self.is_start_value_correct:
            self.is_parameters_correct = False
        if not self.is_second_value_correct:
            self.is_parameters_correct = False
        if not self.is_time_correct:
            self.is_parameters_correct = False
        if self.dict_buf_parameters["type_step"] == "Заданный шаг":
            if not self.is_step_correct:
                self.is_parameters_correct = False
        if self.dict_buf_parameters["COM"] == 'Нет подключенных портов':
            self.is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

        try:
            float(self.setting_window.stop_enter.currentText())
            float(self.setting_window.start_enter.currentText())
            float(self.setting_window.step_enter.currentText())
            float(self.setting_window.boudrate.currentText())
            float(self.setting_window.second_limit_enter.currentText())
        except:
            self.is_parameters_correct = False

        if self.is_parameters_correct:
            pass
        else:
            pass

        self.installation_class.message_from_device_settings(
            self.name, self.is_parameters_correct, self.dict_settable_parameters)

    # фцункция подтверждения корректности параметров от контроллера установкию. установка проверяет ком порты, распределяет их между устройствами и отдает каждому из устройств
    def confirm_parameters(self):  # менять для каждого прибора
        print(str(self.name) + " получил подтверждение настроек, рассчитываем шаги")
        if True:
            self.step_index = -1
            self.i_am_set = True

            # self.client.write_registers(address=int(
            # "0040", 16), count=2, slave=1, values=[0, 120])

            self.steps_voltage.clear()
            self.steps_current.clear()
            if self.dict_settable_parameters["type_of_work"] == "Стабилизация напряжения":
                if self.dict_settable_parameters["type_step"] == "Заданный шаг":
                    self.steps_current, self.steps_voltage = self._fill_arrays(float(self.dict_settable_parameters['low_limit']), float(
                        self.dict_settable_parameters['high_limit']), float(self.dict_settable_parameters['step']), float(self.dict_settable_parameters["second_value"]))

            elif self.dict_settable_parameters["type_of_work"] == "Стабилизация тока":
                if self.dict_settable_parameters["type_step"] == "Заданный шаг":
                    self.steps_voltage, self.steps_current = self._fill_arrays(float(self.dict_settable_parameters['low_limit']), float(
                        self.dict_settable_parameters['high_limit']), float(self.dict_settable_parameters['step']), float(self.dict_settable_parameters["second_value"]))

            elif self.dict_settable_parameters["type_of_work"] == "Стабилизация мощности":
                if self.dict_settable_parameters["type_step"] == "Заданный шаг":
                    pass
        else:
            pass

        self.dict_settable_parameters["num steps"] = len(self.steps_voltage)
        # print(str(self.name) + " рассчитал шаги")
        # print("напряжение", self.steps_voltage)
        # print("ток", self.steps_current)

    def check_connect(self) -> bool:  # менять для каждого прибора
        '''проверяет подключение прибора, если прибор отвечает возвращает True, иначе False'''
        # TODO проверка соединения с прибором(запрос - ответ)
        # проверка соединения
        return True

    # действия перед стартом эксперимента, включить, настроить, подготовить и т.д.
    def action_before_experiment(self) -> bool:  # менять для каждого прибора
        '''ставит минимально возможные значения тока и напряжения, включает выход прибора'''
        print("настройка прибора " + str(self.name) + " перед экспериментом..")
        is_correct = True
        if self._set_voltage(self.min_step_V*100) == False:
            is_correct = False
        if self._set_current(self.min_step_A*100) == False:
            is_correct = False
        if is_correct:
            self._output_switching_on()
            return True
        else:
            return False

    def action_end_experiment(self) -> bool:
        '''плавное выключение прибора'''
        # TODO: плавное выключение
        self._output_switching_off()
        return

    def on_next_step(self) -> bool:  # переопределена для источника питания
        '''активирует следующие значение тока, напряжения прибора, если текущие значения максимальны, то возвращает ложь'''
        is_correct = True

        if self.step_index < len(self.steps_voltage)-1:
            self.step_index = self.step_index + 1

            if self._set_voltage(self.steps_voltage[self.step_index]*100) == False:
                is_correct = False
            if self._set_current(self.steps_current[self.step_index]*100) == False:
                is_correct = False
            return True
        else:
            is_correct = False  # след шага нет

        return is_correct

    def do_meas(self):
        '''прочитать текущие и настроенные значения'''

        start_time = time.time()
        parameters = [self.name]
        is_correct = True

        voltage = self._get_setting_voltage()
        if voltage is not False:
            val = ["voltage_set=" + str(voltage)]
            parameters.append(val)
        else:
            is_correct = False

        voltage = self._get_current_voltage()
        if voltage is not False:
            val = ["voltage_rel=" + str(voltage)]
            parameters.append(val)
        else:
            is_correct = False

        current = self._get_setting_current()
        if current is not False:
            val = ["current_set=" + str(current)]
            parameters.append(val)
        else:
            is_correct = False

        current = self._get_current_current()
        if current is not False:
            val = ["current_rel=" + str(current)]
            parameters.append(val)
        else:
            is_correct = False

        # -----------------------------
        if is_debug:
            is_correct = True
            parameters.append(
                ["voltage_set=" + str(self.steps_voltage[self.step_index])])
            parameters.append(["voltage_rel=" + str(847)])
            parameters.append(
                ["current_set=" + str(self.steps_current[self.step_index])])
        # -----------------------------

        if is_correct:
            print("сделан шаг", self.name)
            ans = device_response_to_step.Step_done
        else:
            print("Ошибка шага", self.name)
            val = ["voltage_set=" + "fail"]
            parameters.append(val)
            val = ["voltage_rel=" + "fail"]
            parameters.append(val)
            val = ["current_set=" + "fail"]
            parameters.append(val)
            val = ["current_rel=" + "fail"]
            parameters.append(val)

            ans = device_response_to_step.Step_fail

        return ans, parameters, time.time() - start_time

    def _fill_arrays(self, start_value, stop_value, step, constant_value):
        steps_1 = []
        steps_2 = []
        if start_value > stop_value:
            step = step*(-1)

        current_value = start_value
        steps_1.append(constant_value)
        steps_2.append(current_value)
        while abs(step) < abs(stop_value-current_value):
            current_value = current_value + step
            steps_1.append(constant_value)
            steps_2.append(current_value)
            # print(current_value)
            if current_value == stop_value:
                steps_1.append(constant_value)
                steps_2.append(current_value)
                break
        else:
            steps_1.append(constant_value)
            steps_2.append(stop_value)
        return steps_1, steps_2

    def _set_voltage(self, voltage) -> bool:  # в сотых долях вольта 20000 - 200В
        response = self._write_reg(address=int(
            "0040", 16), count=2, slave=1, values=[0, int(voltage)])
        return response

    def _set_current(self, current) -> bool:  # в сотых долях ампера
        response = self._write_reg(address=int(
            "0041", 16), count=2, slave=1, values=[0, int(current)])
        return response

    def _output_switching_on(self) -> bool:
        response = self._write_reg(address=int(
            "0042", 16), count=2, slave=1, values=[0, 1])
        return response

    def _output_switching_off(self) -> bool:
        response = self._write_reg(address=int(
            "0042", 16), count=2, slave=1, values=[0, 0])
        return response

    # удаленная настройка выходной частоты в Гц
    def _set_frequency(self, frequency) -> bool:
        high = 0
        if frequency > 65535:
            high = 1
        frequency = frequency - 65535 - 1
        response = self._write_reg(address=int(
            "0043", 16), count=2, slave=1, values=[high, frequency])
        return response

    def _set_duty_cycle(self, duty_cycle) -> bool:
        if duty_cycle > 100 or duty_cycle < 1:
            return False
        response = self._write_reg(address=int(
            "0044", 16), count=2, slave=1, values=[0, duty_cycle])
        return response

    def _write_reg(self, address, count, slave, values) -> bool:
        try:
            ans = self.client.write_registers(
                address=address, count=count, slave=slave, values=values)
            if ans.isError():
                print("ошибка ответа устройства при установке значения", ans)
                return False
            else:
                print(ans.registers)
        except:
            print("Ошибка модбас модуля или клиента")
            return False
        return True
# ----------------------------------------------------------------

    def _read_current_parameters(self, address, count, slave):
        try:
            ans = self.client.read_input_registers(
                address=address, count=count, slave=slave)
            if ans.isError():
                print("ошибка ответа устройства при чтении текущего", ans)
                return False
            else:
                print(ans.registers)
                return ans.registers
        except:
            print("Ошибка модбас модуля или клиента")
            return False

    def _get_current_voltage(self):
        response = self._read_current_parameters(
            address=int("0000", 16), count=1, slave=1)
        if response != False:
            pass
            response = response[0]/100

            # TODO читаем параметры и кладем их в респонсе
        return response

    def _get_current_current(self):
        response = self._read_current_parameters(
            address=int("0001", 16), count=1, slave=1)
        if response != False:
            pass
            response = response[0]/100
            # TODO читаем параметры и кладем их в респонсе
        return response

    def _get_current_frequency(self):
        pass

    def _get_current_duty_cycle(self):
        pass
# ----------------------------------------------------------------

    def _read_setting_parameters(self, address, count, slave):
        try:
            ans = self.client.read_holding_registers(
                address=address, count=count, slave=slave)
            if ans.isError():
                print("ошибка ответа устройства при чтении установленного", ans)
                return False
            else:
                print(ans.registers)
                return ans.registers
        except:
            print("Ошибка модбас модуля или клиента")
            return False

    def _get_setting_voltage(self):
        response = self._read_setting_parameters(
            address=int("0040", 16), count=2, slave=1)
        if response != False:
            response = response[1]/100
            # TODO читаем параметры и кладем их в респонсе
        return response

    def _get_setting_current(self):
        response = self._read_setting_parameters(
            address=int("0041", 16), count=2, slave=1)
        if response != False:
            response = response[1]/100
            # TODO читаем параметры и кладем их в респонсе
        return response

    def _get_setting_frequency(self):
        response = self._read_setting_parameters(
            address=int("0043", 16), count=2, slave=1)
        if response != False:
            pass
            # TODO читаем параметры и кладем их в респонсе
        return response

    def _get_setting_state(self):
        response = self._read_setting_parameters(
            address=int("0042", 16), count=2, slave=1)
        if response != False:
            pass
            # TODO читаем параметры и кладем их в респонсе
        return response

    def _get_setting_duty_cycle(self):
        response = self._read_setting_parameters(
            address=int("0044", 16), count=2, slave=1)
        if response != False:
            pass
            # TODO читаем параметры и кладем их в респонсе
        return response


if __name__ == "__main__":
    # Создание клиента Modbus RTU
    client = ModbusSerialClient(
        method='rtu', port='COM13', baudrate=9600, stopbits=1, bytesize=8, parity='E')

    power_supply = maisheng_power_class([], "tr", "rere")
    power_supply.set_client(client)

    power_supply._set_voltage(200)
    '''
    for i in range(0,20000,1000):
        set_voltage(client,i)
        time.sleep(5)
    '''
    power_supply._output_switching_off()
    power_supply._set_current(1500)
    i = power_supply._get_setting_voltage()

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
