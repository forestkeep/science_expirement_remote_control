from interface.set_power_supply_window import Ui_Set_power_supply
from PyQt5 import QtCore, QtWidgets
import copy
from Classes import ch_response_to_step, base_device, ch_response_to_step, base_ch
import time
from Classes import not_ready_style_border, not_ready_style_background, ready_style_border, ready_style_background, warning_style_border, warning_style_background
import random
import logging
logger = logging.getLogger(__name__)


class power_supply(base_device):
    def __init__(self, name, type_connection, installation_class) -> None:
        super().__init__(name, type_connection, installation_class)
        # print(f"класс источника питания  {name} создан")

    def get_number_channels(self) -> int:
        return len(self.channels)

    def check_connect(self) -> bool:  # менять для каждого прибора
        """проверяет подключение прибора, если прибор отвечает возвращает True, иначе False"""
        # TODO проверка соединения с прибором(запрос - ответ)
        # проверка соединения
        return True

    def show_setting_window(self, number_of_channel):
        self.switch_channel(number_of_channel)

        self.active_ports = []
        self.setting_window = Ui_Set_power_supply()
        self.setting_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setting_window.setupUi(self.setting_window)

        self.setting_window.type_work_enter.addItems(
            ["Стабилизация напряжения", "Стабилизация тока", "Стабилизация мощности"]
        )
        self.setting_window.triger_enter.addItems(["Таймер", "Внешний сигнал"])
        self.setting_window.triger_enter.setEnabled(True)

        self.setting_window.type_step_enter.addItems(["Заданный шаг"])

        self._scan_com_ports()

        self.setting_window.boudrate.addItems(
            [
                "50",
                "75",
                "110",
                "150",
                "300",
                "600",
                "1200",
                "2400",
                "4800",
                "9600",
                "19200",
                "38400",
                "57600",
                "115200",
            ]
        )

        self.setting_window.sourse_enter.setStyleSheet(
            ready_style_border
        )
        self.setting_window.type_step_enter.setStyleSheet(
            ready_style_border
        )
        self.setting_window.type_work_enter.setStyleSheet(
            ready_style_border
        )
        self.setting_window.triger_enter.setStyleSheet(
            ready_style_border
        )
        self.setting_window.boudrate.setStyleSheet(
            ready_style_border
        )
        self.setting_window.comportslist.setStyleSheet(
            ready_style_border
        )

        # =======================прием сигналов от окна==================
        self.setting_window.type_work_enter.currentIndexChanged.connect(
            lambda: self._change_units()
        )
        self.setting_window.type_work_enter.currentIndexChanged.connect(
            lambda: self._is_correct_parameters()
        )

        self.setting_window.type_step_enter.currentIndexChanged.connect(
            lambda: self._action_when_select_step()
        )
        self.setting_window.type_step_enter.currentIndexChanged.connect(
            lambda: self._is_correct_parameters()
        )
        self.setting_window.type_step_enter.currentIndexChanged.connect(
            lambda: self._action_when_select_trigger()
        )
        self.setting_window.type_step_enter.setToolTip(
            "Доступен фиксированный шаг. Адаптивный находится в разработке."
        )

        self.setting_window.triger_enter.currentIndexChanged.connect(
            lambda: self._action_when_select_trigger()
        )

        self.setting_window.step_enter.currentTextChanged.connect(
            lambda: self._is_correct_parameters()
        )
        self.setting_window.stop_enter.currentTextChanged.connect(
            lambda: self._is_correct_parameters()
        )
        self.setting_window.start_enter.currentTextChanged.connect(
            lambda: self._is_correct_parameters()
        )
        self.setting_window.second_limit_enter.currentTextChanged.connect(
            lambda: self._is_correct_parameters()
        )
        self.setting_window.sourse_enter.currentTextChanged.connect(
            lambda: self._is_correct_parameters()
        )

        self.setting_window.comportslist.highlighted.connect(
            lambda: self._scan_com_ports()
        )

        self.setting_window.buttonBox.button(
            QtWidgets.QDialogButtonBox.Ok
        ).clicked.connect(self.send_signal_ok)
        # ======================================================

        self.setting_window.show()

        # запрещаем исполнение функций во время инициализации
        self.key_to_signal_func = False
        # ============установка текущих параметров=======================
        self.setting_window.comportslist.setCurrentText(
            self.dict_buf_parameters["COM"])
        self.setting_window.boudrate.setCurrentText(
            self.dict_buf_parameters["baudrate"]
        )

        self.setting_window.type_work_enter.setCurrentText(
            self.active_channel.dict_buf_parameters["type_of_work"]
        )
        self.setting_window.type_step_enter.setCurrentText(
            self.active_channel.dict_buf_parameters["type_step"]
        )
        self.setting_window.start_enter.setCurrentText(
            self.active_channel.dict_buf_parameters["low_limit"]
        )
        self.setting_window.stop_enter.setCurrentText(
            self.active_channel.dict_buf_parameters["high_limit"]
        )
        self.setting_window.step_enter.setCurrentText(
            self.active_channel.dict_buf_parameters["step"]
        )
        self.setting_window.triger_enter.setCurrentText(
            self.active_channel.dict_buf_parameters["trigger"]
        )
        self.setting_window.second_limit_enter.setCurrentText(
            self.active_channel.dict_buf_parameters["second_value"]
        )
        self.setting_window.second_limit_enter.setEnabled(True)

        if self.active_channel.dict_buf_parameters["repeat_reverse"] == False:
            self.setting_window.radioButton.setChecked(False)
        else:
            self.setting_window.radioButton.setChecked(True)

        self.setting_window.radioButton.setToolTip(
            "При активации этого пункта источник питания пройдет по шагам от стартого значения до конечного и обратно."
        )

        if (
            self.active_channel.dict_buf_parameters["type_of_work"]
            == "Стабилизация напряжения"
        ):
            self.setting_window.second_value_limit_label.setText(
                "Ток не выше (А)")

        elif (
            self.active_channel.dict_buf_parameters["type_of_work"]
            == "Стабилизация тока"
        ):
            self.setting_window.second_value_limit_label.setText(
                "Напряжение не выше (V)"
            )
        else:
            self.setting_window.second_value_limit_label.setText("---")
            self.setting_window.second_limit_enter.setEnabled(False)

        self.key_to_signal_func = True  # разрешаем выполенение функций
        self._action_when_select_trigger()
        self._change_units()
        self._is_correct_parameters()

    def _is_correct_parameters(self):  # менять для каждого прибора
        if self.key_to_signal_func:
            # print("проверить параметры")
            if (
                self.setting_window.type_work_enter.currentText()
                == "Стабилизация напряжения"
            ):
                max = self.active_channel.max_voltage
                min = self.active_channel.min_step_V
                max_second_limit = self.active_channel.max_current
            if self.setting_window.type_work_enter.currentText() == "Стабилизация тока":
                max = self.active_channel.max_current
                min = self.active_channel.min_step_A
                max_second_limit = self.active_channel.max_voltage
            if (
                self.setting_window.type_work_enter.currentText()
                == "Стабилизация мощности"
            ):
                max = self.active_channel.max_power
                min = self.active_channel.min_step_W

            low_value = 0
            high_value = 0
            enter_step = 0
            second_limit = 0
            self.active_channel.is_stop_value_correct = True
            self.active_channel.is_start_value_correct = True
            self.active_channel.is_step_correct = True
            self.active_channel.is_second_value_correct = True
            self.active_channel.is_time_correct = True
            # проверка число или не число

            if self.setting_window.triger_enter.currentText() == "Таймер":
                try:
                    int(self.setting_window.sourse_enter.currentText())
                except:
                    self.active_channel.is_time_correct = False
            try:
                low_value = float(
                    self.setting_window.start_enter.currentText())
            except:
                self.active_channel.is_start_value_correct = False
            try:
                high_value = float(
                    self.setting_window.stop_enter.currentText())
            except:
                self.active_channel.is_stop_value_correct = False
            try:
                enter_step = float(
                    self.setting_window.step_enter.currentText())
            except:
                self.active_channel.is_step_correct = False
            try:
                second_limit = float(
                    self.setting_window.second_limit_enter.currentText()
                )
            except:
                self.active_channel.is_second_value_correct = False
            # ---------------------------
            # минимум и максимум не выходят за границы
            if self.active_channel.is_stop_value_correct:
                if high_value < min or high_value > max:
                    self.active_channel.is_stop_value_correct = False
            if self.active_channel.is_start_value_correct:
                if low_value < min or low_value > max:
                    self.active_channel.is_start_value_correct = False
            if self.active_channel.is_step_correct:
                if (
                    self.active_channel.is_start_value_correct
                    and self.active_channel.is_stop_value_correct
                ):
                    if enter_step > abs(high_value - low_value):
                        self.active_channel.is_step_correct = False
            if (
                self.active_channel.is_second_value_correct
                and self.setting_window.type_work_enter.currentText()
                != "Стабилизация мощности"
            ):
                if second_limit > max_second_limit or second_limit < 0.01:
                    self.active_channel.is_second_value_correct = False
            if self.active_channel.is_time_correct:
                self.setting_window.sourse_enter.setStyleSheet(
                    ready_style_border
                )
            else:
                self.setting_window.sourse_enter.setStyleSheet(
                    not_ready_style_border
                )

            if self.active_channel.is_stop_value_correct:
                self.setting_window.stop_enter.setStyleSheet(
                    ready_style_border
                )
            else:
                self.setting_window.stop_enter.setStyleSheet(
                    not_ready_style_border
                )
            if self.active_channel.is_start_value_correct:
                self.setting_window.start_enter.setStyleSheet(
                    ready_style_border
                )
            else:
                self.setting_window.start_enter.setStyleSheet(
                    not_ready_style_border
                )
            if self.active_channel.is_step_correct:
                if (
                    self.setting_window.type_step_enter.currentText()
                    == "Адаптивный шаг"
                ):
                    self.setting_window.step_enter.setStyleSheet(
                        "background-color: rgb(180, 180, 180)"
                    )
                else:
                    self.setting_window.step_enter.setStyleSheet(
                        ready_style_border
                    )
            else:
                if (
                    self.setting_window.type_step_enter.currentText()
                    == "Адаптивный шаг"
                ):
                    self.setting_window.step_enter.setStyleSheet(
                        "background-color: rgb(180, 180, 180)"
                    )
                else:
                    self.setting_window.step_enter.setStyleSheet(
                        not_ready_style_border
                    )
            if self.active_channel.is_second_value_correct:
                self.setting_window.second_limit_enter.setStyleSheet(
                    ready_style_border
                )
            else:
                if (
                    self.setting_window.type_work_enter.currentText()
                    != "Стабилизация мощности"
                ):
                    self.setting_window.second_limit_enter.setStyleSheet(
                        not_ready_style_border
                    )
                else:
                    self.setting_window.second_limit_enter.setStyleSheet(
                        ready_style_border
                    )

    def _change_units(self):
        if self.key_to_signal_func:
            # print("изменить параметры")
            self.setting_window.second_limit_enter.setEnabled(True)
            if (
                self.setting_window.type_work_enter.currentText()
                == "Стабилизация напряжения"
            ):
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
                    "Напряжение не выше (V)"
                )
            if (
                self.setting_window.type_work_enter.currentText()
                == "Стабилизация мощности"
            ):
                self.setting_window.label_7.setText("W")
                self.setting_window.label_8.setText("W")
                self.setting_window.label_9.setText("W")
                self.setting_window.second_value_limit_label.setText("---")
                self.setting_window.second_limit_enter.setStyleSheet(
                    "background-color: rgb(180, 180, 180)"
                )
                self.setting_window.second_limit_enter.setEnabled(False)

    def _action_when_select_step(self):
        if self.key_to_signal_func:
            # print("выбор шага")
            if self.setting_window.type_step_enter.currentText() == "Адаптивный шаг":
                self.setting_window.step_enter.setEnabled(False)
                self.setting_window.step_enter.setStyleSheet(
                    "background-color: rgb(180, 180, 180)"
                )
                self.setting_window.triger_enter.clear()
                self.setting_window.triger_enter.addItems(["Внешний сигнал"])
            else:
                self.setting_window.step_enter.setEnabled(True)
                # self.setting_window.triger_enter.clear()
                self.setting_window.triger_enter.addItems(["Таймер"])

    def add_parameters_from_window(self):  # менять для каждого прибора
        if self.key_to_signal_func:
            self.dict_buf_parameters["baudrate"] = (
                self.setting_window.boudrate.currentText()
            )
            self.dict_buf_parameters["COM"] = (
                self.setting_window.comportslist.currentText()
            )

            self.active_channel.dict_buf_parameters["type_of_work"] = (
                self.setting_window.type_work_enter.currentText()
            )
            self.active_channel.dict_buf_parameters["type_step"] = (
                self.setting_window.type_step_enter.currentText()
            )
            self.active_channel.dict_buf_parameters["trigger"] = (
                self.setting_window.triger_enter.currentText()
            )
            self.active_channel.dict_buf_parameters["high_limit"] = (
                self.setting_window.stop_enter.currentText()
            )
            self.active_channel.dict_buf_parameters["low_limit"] = (
                self.setting_window.start_enter.currentText()
            )
            self.active_channel.dict_buf_parameters["step"] = (
                self.setting_window.step_enter.currentText()
            )
            self.active_channel.dict_buf_parameters["sourse/time"] = (
                self.setting_window.sourse_enter.currentText()
            )

            self.active_channel.dict_buf_parameters["second_value"] = (
                self.setting_window.second_limit_enter.currentText()
            )
            try:
                self.active_channel.dict_buf_parameters["num steps"] = round(
                    (
                        float(
                            self.active_channel.dict_buf_parameters["high_limit"])
                        - float(self.active_channel.dict_buf_parameters["low_limit"])
                    )
                    / float(self.active_channel.dict_buf_parameters["step"])
                )
            except:
                pass

            if self.setting_window.radioButton.isChecked():
                self.active_channel.dict_buf_parameters["repeat_reverse"] = True
            else:
                self.active_channel.dict_buf_parameters["repeat_reverse"] = False

    def send_signal_ok(self,):
        "вызывается только после закрытия окна настроек"
        self.add_parameters_from_window()
        # те же самые настройки, ничего не делаем
        if (self.active_channel.dict_buf_parameters == self.active_channel.dict_settable_parameters and self.dict_buf_parameters == self.dict_settable_parameters):
            #return
            pass
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.active_channel.dict_settable_parameters = copy.deepcopy(
            self.active_channel.dict_buf_parameters)

        is_parameters_correct = True
        if not self.active_channel.is_stop_value_correct:
            is_parameters_correct = False
        if not self.active_channel.is_start_value_correct:
            is_parameters_correct = False
        if not self.active_channel.is_second_value_correct:
            is_parameters_correct = False
        if not self.active_channel.is_time_correct:
            is_parameters_correct = False
        if self.active_channel.dict_buf_parameters["type_step"] == "Заданный шаг":
            if not self.active_channel.is_step_correct:
                is_parameters_correct = False
        if self.dict_buf_parameters["COM"] == "Нет подключенных портов":
            is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

        try:
            float(self.setting_window.stop_enter.currentText())
            float(self.setting_window.start_enter.currentText())
            float(self.setting_window.step_enter.currentText())
            float(self.setting_window.boudrate.currentText())
            float(self.setting_window.second_limit_enter.currentText())
        except:
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

    def confirm_parameters(self):  # менять для каждого прибора
        """метод подтверждения корректности параметров от контроллера установки. установка проверяет ком порты, распределяет их между устройствами и отдает каждому из устройств"""

        # print(f" устройство {self.name} получило подтверждение настроек, рассчитываем шаги")

        # self.client.write_registers(address=int(
        # "0040", 16), count=2, slave=1, values=[0, 120])
        for ch in self.channels:
            if ch.is_ch_active():
                ch.step_index = -1
                self.switch_channel(ch.number)
            else:
                continue

            self.active_channel.steps_voltage.clear()
            self.active_channel.steps_current.clear()
            if (
                self.active_channel.dict_settable_parameters["type_of_work"]
                == "Стабилизация напряжения"
            ):

                if (
                    self.active_channel.dict_settable_parameters["type_step"]
                    == "Заданный шаг"
                ):
                    (
                        self.active_channel.steps_current,
                        self.active_channel.steps_voltage,
                    ) = self.__fill_arrays(
                        float(
                            self.active_channel.dict_settable_parameters["low_limit"]
                        ),
                        float(
                            self.active_channel.dict_settable_parameters["high_limit"]
                        ),
                        float(
                            self.active_channel.dict_settable_parameters["step"]),
                        float(
                            self.active_channel.dict_settable_parameters["second_value"]
                        ),
                    )

            elif (
                self.active_channel.dict_settable_parameters["type_of_work"]
                == "Стабилизация тока"
            ):
                if (
                    self.active_channel.dict_settable_parameters["type_step"]
                    == "Заданный шаг"
                ):
                    (
                        self.active_channel.steps_voltage,
                        self.active_channel.steps_current,
                    ) = self.__fill_arrays(
                        float(
                            self.active_channel.dict_settable_parameters["low_limit"]
                        ),
                        float(
                            self.active_channel.dict_settable_parameters["high_limit"]
                        ),
                        float(
                            self.active_channel.dict_settable_parameters["step"]),
                        float(
                            self.active_channel.dict_settable_parameters["second_value"]
                        ),
                    )

            elif (
                self.active_channel.dict_settable_parameters["type_of_work"]
                == "Стабилизация мощности"
            ):
                if (
                    self.active_channel.dict_settable_parameters["type_step"]
                    == "Заданный шаг"
                ):
                    pass

            if self.active_channel.dict_buf_parameters["repeat_reverse"] == True:
                buf_current = copy.deepcopy(self.active_channel.steps_current)
                buf_voltage = copy.deepcopy(self.active_channel.steps_voltage)
                buf_current = buf_current[::-1]  # разворот списка
                buf_voltage = buf_voltage[::-1]
                buf_current = buf_current[1: len(buf_current)]
                buf_voltage = buf_voltage[1: len(buf_voltage)]

                for cur, vol in zip(buf_current, buf_voltage):
                    self.active_channel.steps_current.append(cur)
                    self.active_channel.steps_voltage.append(vol)


            self.active_channel.dict_settable_parameters["num steps"] = len(
                self.active_channel.steps_voltage
            )

    # действия перед стартом эксперимента, включить, настроить, подготовить и т.д.
    def action_before_experiment(
        self, number_of_channel
    ) -> bool:
        """ставит минимально возможные значения тока и напряжения, включает выход прибора"""
        self.switch_channel(number_of_channel)
        # print(f"настройка канала {number_of_channel} прибора "+ str(self.name)+ " перед экспериментом..")

        is_correct = True
        if self._set_voltage(self.active_channel.number, self.active_channel.min_step_V) == False:
            is_correct = False
        if self._set_current(self.active_channel.number, self.active_channel.min_step_A) == False:
            is_correct = False

        if is_correct:
            self._output_switching_on(self.active_channel.number)
            return True
        else:
            return False

    def action_end_experiment(self, number_of_channel) -> bool:
        """плавное выключение прибора"""
        self.switch_channel(number_of_channel)
        # print("Плавное выключение источника питания")
        count = 3
        is_voltage_read = False

        while count > 0:
            voltage = self._get_setting_voltage(self.active_channel.number)
            if voltage == False:
                count -= 1
            else:
                is_voltage_read = True
                count = 0
        if is_voltage_read:
            step = 5
            while voltage > step:
                voltage -= step
                # print("напряжение = ", voltage)
                self._set_voltage(self.active_channel.number, voltage)
                time.sleep(5)

        self._output_switching_off(self.active_channel.number)
        return

    def on_next_step(
        self, number_of_channel, repeat=3
    ) -> bool:  # переопределена для источника питания
        """активирует следующие значение тока, напряжения прибора, если текущие значения максимальны, то возвращает ложь"""
        self.switch_channel(number_of_channel)
        #print(self.active_channel.steps_voltage)
        #print(self.active_channel.steps_current)

        if self.is_debug:
            pass
        #print("индекс массива ", self.active_channel.step_index)
        if self.active_channel.step_index < len(self.active_channel.steps_voltage) - 1:
            self.active_channel.step_index = self.active_channel.step_index + 1

            i = 0
            answer = ch_response_to_step.Step_fail
            while i-1 < repeat and answer == ch_response_to_step.Step_fail:
                time.sleep(0.5)
                i += 1
                if (self._set_voltage(self.active_channel.number,self.active_channel.steps_voltage[self.active_channel.step_index]) == True):
                    answer = ch_response_to_step.Step_done
                    #print(f"установлено успешно напряжение {self.active_channel.steps_voltage[self.active_channel.step_index]}")
                else:
                    answer = ch_response_to_step.Step_fail
                    if self.is_debug:
                        ##print(f"ошибка установки напряжения {self.name}, {self.active_channel.number}")
                        answer = ch_response_to_step.Step_done
                    continue


                if (self._set_current(self.active_channel.number,self.active_channel.steps_current[self.active_channel.step_index])== True):
                    answer = ch_response_to_step.Step_done
                else:
                    answer = ch_response_to_step.Step_fail
                    if self.is_debug:
                        ##print(f"ошибка установки напряжения {self.name}, {self.active_channel.number}")
                        answer = ch_response_to_step.Step_done
                    continue

        else:
            answer = ch_response_to_step.End_list_of_steps  # след шага нет

        if self.is_debug:
            if answer != ch_response_to_step.End_list_of_steps:
                answer = ch_response_to_step.Step_done

        return answer

    def do_meas(self, number_of_channel):
        self.switch_channel(number_of_channel)

        """прочитать текущие и настроенные значения"""
        start_time = time.time()
        parameters = [self.name + " ch-" + str(self.active_channel.number)]
        is_correct = True

        voltage = self._get_setting_voltage(self.active_channel.number)
        if voltage is not False:
            val = ["voltage_set=" + str(voltage)]
            parameters.append(val)
        else:
            is_correct = False

        if self.is_debug:
            if is_correct == False:
                pass
                # print(f"ошибка чтения выставленного значения напряжения {self.name}, {self.active_channel.number}")

        voltage = self._get_current_voltage(self.active_channel.number)
        if voltage is not False:
            val = ["voltage_rel=" + str(voltage)]
            parameters.append(val)
        else:
            is_correct = False

        if self.is_debug:
            if is_correct == False:
                pass
                # print(f"ошибка чтения текущего значения напряжения {self.name}, {self.active_channel.number}")

        current = self._get_setting_current(self.active_channel.number)
        if current is not False:
            val = ["current_set=" + str(current)]
            parameters.append(val)
        else:
            is_correct = False

        if self.is_debug:
            if is_correct == False:
                pass
                # print(f"ошибка чтения выставленного значения тока {self.name}, {self.active_channel.number}")

        current = self._get_current_current(self.active_channel.number)
        if current is not False:
            val = ["current_rel=" + str(current)]
            parameters.append(val)
        else:
            is_correct = False

        if self.is_debug:
            if is_correct == False:
                pass
                # print(f"ошибка чтения измеренного значения тока {self.name}, {self.active_channel.number}")

        # -----------------------------
        if self.is_debug:
            if is_correct == False:
                is_correct = True
                parameters.append(
                    ["voltage_set=" +
                        str(self.active_channel.steps_voltage[self.active_channel.step_index])]
                )
                parameters.append(["voltage_rel=" + str(random.random() * 30)])
                parameters.append(
                    ["current_set=" +
                        str(self.active_channel.steps_current[self.active_channel.step_index])]
                )
                if self.active_channel.step_index == 2:
                    parameters.append(
                        ["current_rel=fail"]
                    )
                else:
                    parameters.append(
                        ["current_rel=" + str(random.random() * 3)]
                    )
        # -----------------------------
        if not is_correct:
            pass
            # print("что-то не получилось при шаге")

        if is_correct:
            # print("сделан шаг", self.name + " ch " + str(self.active_channel.number))
            ans = ch_response_to_step.Step_done

        else:
            # print("Ошибка шага", self.name + " ch " + str(self.active_channel.number))
            val = ["voltage_set=" + "fail"]
            parameters.append(val)
            val = ["voltage_rel=" + "fail"]
            parameters.append(val)
            val = ["current_set=" + "fail"]
            parameters.append(val)
            val = ["current_rel=" + "fail"]
            parameters.append(val)

            # ans = ch_response_to_step.Step_fail
            ans = ch_response_to_step.Step_done
            # TODO: продумать момент, когда отправлять статус ошибка. По статусу ошибка эксперимент завершается. Вынести это в отдельное поле в настройках эксперимента или прекращать эксперимент когда один из приборов не отвечает, или продолжать эксперимент когда один из поиборов не отвечает.

        return ans, parameters, time.time() - start_time

    def __fill_arrays(self, start_value, stop_value, step, constant_value):
        steps_1 = []
        steps_2 = []
        if start_value > stop_value:
            step = step * (-1)

        current_value = start_value
        steps_1.append(constant_value)
        steps_2.append(current_value)
        while abs(step) < abs(stop_value - current_value):
            current_value = current_value + step
            current_value *= 100000
            current_value = round(current_value, 2)
            current_value /= 100000
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

    def set_test_mode(self):
        """переводит прибор в режим теста, выдаются сырые данные от функций передачи и приема"""
        self.is_test = True

    def reset_test_mode(self):
        self.is_test = False
