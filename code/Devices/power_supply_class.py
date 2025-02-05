# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

import copy
import logging
import random
import time

from PyQt5.QtWidgets import QApplication

from Devices.Classes import (base_ch, base_device, ch_response_to_step,
                             not_ready_style_border, ready_style_border,
                             which_part_in_ch)
from Devices.interfase.set_power_supply_window import Ui_Set_power_supply

logger = logging.getLogger(__name__)


class chActPowerSupply(base_ch):
    def __init__(
        self,
        number,
        device_class,
        max_current,
        max_voltage,
        max_power,
        min_step_A=0.001,
        min_step_V=0.001,
        min_step_W=1,
    ) -> None:
        super().__init__(number, ch_type="act", device_class=device_class)
        self.base_duration_step = 10  # у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.steps_current = []
        self.steps_voltage = []
        self.max_current = max_current
        self.max_voltage = max_voltage
        self.max_power = max_power
        self.min_step_V = min_step_V
        self.min_step_A = min_step_A
        self.min_step_W = min_step_W
        self.dict_buf_parameters["type_of_work"] = "Стабилизация напряжения"
        self.dict_buf_parameters["type_step"] = "Заданный шаг"
        self.dict_buf_parameters["high_limit"] = str(5)
        self.dict_buf_parameters["low_limit"] = str(self.min_step_V)
        self.dict_buf_parameters["step"] = "1"
        self.dict_buf_parameters["second_value"] = str(self.max_current)
        self.dict_buf_parameters["repeat_reverse"] = False
        self.dict_buf_parameters["soft_start"] = False
        self.dict_buf_parameters["soft_off"] = False

        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)


class chMeasPowerSupply(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number, ch_type="meas", device_class=device_class)
        self.base_duration_step = 10  # у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.dict_buf_parameters["meas_cur"] = False
        self.dict_buf_parameters["meas_vol"] = False
        self.dict_buf_parameters["meas_set_cur"] = False
        self.dict_buf_parameters["meas_set_vol"] = False

        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)


class power_supply(base_device):

    def __init__(self, name, type_connection, installation_class) -> None:
        super().__init__(name, type_connection, installation_class)
        self.part_ch = (
            which_part_in_ch.bouth
        )  # указываем, из каких частей состоиит канал в данном приборе
        self.setting_window = Ui_Set_power_supply()
        self.base_settings_window()

        self.setting_window.type_work_enter.addItems(
            [ QApplication.translate("Device","Стабилизация напряжения"), QApplication.translate("Device","Стабилизация тока") ]
        )
        self.setting_window.type_step_enter.addItems([ QApplication.translate("Device","Заданный шаг") ])

        # =======================прием сигналов от окна==================
        self.setting_window.type_work_enter.currentIndexChanged.connect(
            lambda: self._change_units()
        )
        self.setting_window.type_step_enter.currentIndexChanged.connect(
            lambda: self._action_when_select_step()
        )
        self.setting_window.type_step_enter.currentIndexChanged.connect(
            lambda: self._action_when_select_trigger()
        )
        self.setting_window.type_step_enter.setToolTip(
            QApplication.translate("Device","Доступен фиксированный шаг. Адаптивный находится в разработке.")
        )
        self.setting_window.radioButton.setToolTip(
            QApplication.translate("Device","При активации этого пункта источник питания пройдет по шагам от стартого значения до конечного и обратно.")
        )
        self.setting_window.num_act_label.setParent(None)
        self.setting_window.num_act_enter.setParent(None)


    def time_decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            print(f"Метод {func.__name__} - {end_time - start_time} с")
            return result

        return wrapper

    @base_device.base_show_window
    def show_setting_window(self, number_of_channel):
        #print(f"показываем окно настройки для канала {number_of_channel}")
        self.switch_channel(number=number_of_channel)
        # запрещаем исполнение функций во время инициализации
        self.key_to_signal_func = False
        # self.base_show_window()

        # ============установка текущих параметров=======================
        self.setting_window.type_work_enter.setCurrentText(
            self.active_channel_act.dict_buf_parameters["type_of_work"]
        )
        self.setting_window.type_step_enter.setCurrentText(
            self.active_channel_act.dict_buf_parameters["type_step"]
        )
        self.setting_window.start_enter.setCurrentText(
            str(self.active_channel_act.dict_buf_parameters["low_limit"])
        )
        self.setting_window.stop_enter.setCurrentText(
            str(self.active_channel_act.dict_buf_parameters["high_limit"])
        )
        self.setting_window.step_enter.setCurrentText(
            str(self.active_channel_act.dict_buf_parameters["step"])
        )
        self.setting_window.second_limit_enter.setCurrentText(
            str(self.active_channel_act.dict_buf_parameters["second_value"])
        )
        self.setting_window.second_limit_enter.setEnabled(True)

        self.setting_window.radioButton.setChecked(
            self.active_channel_act.dict_buf_parameters["repeat_reverse"] == True
        )

        if (
            self.active_channel_act.dict_buf_parameters["type_of_work"]
            == QApplication.translate("Device","Стабилизация напряжения")
        ):
            self.setting_window.second_value_limit_label.setText( QApplication.translate("Device","Ток не выше (А)") )

        elif (
            self.active_channel_act.dict_buf_parameters["type_of_work"]
            == QApplication.translate("Device","Стабилизация тока")
        ):
            self.setting_window.second_value_limit_label.setText(
                QApplication.translate("Device","Напряжение не выше (V)")
            )
        else:
            self.setting_window.second_value_limit_label.setText("---")
            self.setting_window.second_limit_enter.setEnabled(False)
            
        self.setting_window.radioButton.setChecked(self.active_channel_act.dict_buf_parameters["repeat_reverse"] == True) 
            
        self.setting_window.is_soft_start.setChecked( self.active_channel_act.dict_buf_parameters["soft_start"]  == True)

        self.setting_window.is_soft_stop.setChecked( self.active_channel_act.dict_buf_parameters["soft_off"] == True)

        self.setting_window.voltage_meas.setChecked(
            self.active_channel_meas.dict_buf_parameters["meas_vol"] == True
        )
        self.setting_window.current_meas.setChecked(
            self.active_channel_meas.dict_buf_parameters["meas_cur"] == True
        )
        self.setting_window.set_voltage_meas.setChecked(
            self.active_channel_meas.dict_buf_parameters["meas_set_vol"] == True
        )
        self.setting_window.set_current_meas.setChecked(
            self.active_channel_meas.dict_buf_parameters["meas_set_cur"] == True
        )
        self.key_to_signal_func = True

        self._action_when_select_trigger()
        self._change_units()
        self._is_correct_parameters()
        self.setting_window.show()

    @base_device.base_is_correct_parameters
    def _is_correct_parameters(self):  # менять для каждого прибора
        if self.key_to_signal_func:
            if (
                self.setting_window.type_work_enter.currentText()
                == QApplication.translate("Device","Стабилизация напряжения")
            ):
                max = self.active_channel_act.max_voltage
                min = self.active_channel_act.min_step_V
                max_second_limit = self.active_channel_act.max_current
            if self.setting_window.type_work_enter.currentText() == QApplication.translate("Device","Стабилизация тока"):
                max = self.active_channel_act.max_current
                min = self.active_channel_act.min_step_A
                max_second_limit = self.active_channel_act.max_voltage
            if (
                self.setting_window.type_work_enter.currentText()
                == QApplication.translate("Device","Стабилизация мощности")
            ):
                max = self.active_channel_act.max_power
                min = self.active_channel_act.min_step_W

            low_value = 0
            high_value = 0
            enter_step = 0
            second_limit = 0
            self.active_channel_act.is_stop_value_correct = True
            self.active_channel_act.is_start_value_correct = True
            self.active_channel_act.is_step_correct = True
            self.active_channel_act.is_second_value_correct = True
            # проверка число или не число

            try:
                low_value = float(self.setting_window.start_enter.currentText())
            except:
                self.active_channel_act.is_start_value_correct = False
            try:
                high_value = float(self.setting_window.stop_enter.currentText())
            except:
                self.active_channel_act.is_stop_value_correct = False
            try:
                enter_step = float(self.setting_window.step_enter.currentText())
            except:
                self.active_channel_act.is_step_correct = False
            try:
                second_limit = float(
                    self.setting_window.second_limit_enter.currentText()
                )
            except:
                self.active_channel_act.is_second_value_correct = False
            # ---------------------------
            # минимум и максимум не выходят за границы
            if self.active_channel_act.is_stop_value_correct:
                if high_value < min or high_value > max:
                    self.active_channel_act.is_stop_value_correct = False

            if self.active_channel_act.is_start_value_correct:
                if low_value < min or low_value > max:
                    self.active_channel_act.is_start_value_correct = False

            if self.active_channel_act.is_step_correct:
                if (
                    self.active_channel_act.is_start_value_correct
                    and self.active_channel_act.is_stop_value_correct
                ):
                    if self.active_channel_act.is_step_correct:
                        if enter_step > abs(high_value - low_value) or enter_step < min:
                            self.active_channel_act.is_step_correct = False

            if (
                self.active_channel_act.is_second_value_correct
                and self.setting_window.type_work_enter.currentText()
                != "Стабилизация мощности"
            ):
                if second_limit > max_second_limit or second_limit < 0.01:
                    self.active_channel_act.is_second_value_correct = False

            if self.active_channel_act.is_stop_value_correct:
                self.setting_window.stop_enter.setStyleSheet(ready_style_border)
            else:
                self.setting_window.stop_enter.setStyleSheet(not_ready_style_border)

            if self.active_channel_act.is_start_value_correct:
                self.setting_window.start_enter.setStyleSheet(ready_style_border)
            else:
                self.setting_window.start_enter.setStyleSheet(not_ready_style_border)

            if self.active_channel_act.is_step_correct:
                if (
                    self.setting_window.type_step_enter.currentText()
                    == QApplication.translate("Device","Адаптивный шаг")
                ):
                    self.setting_window.step_enter.setStyleSheet(
                        "background-color: rgb(180, 180, 180)"
                    )
                else:
                    self.setting_window.step_enter.setStyleSheet(ready_style_border)
            else:
                if (
                    self.setting_window.type_step_enter.currentText()
                    == QApplication.translate("Device","Адаптивный шаг")
                ):
                    self.setting_window.step_enter.setStyleSheet(
                        "background-color: rgb(180, 180, 180)"
                    )
                else:
                    self.setting_window.step_enter.setStyleSheet(not_ready_style_border)

            if self.active_channel_act.is_second_value_correct:
                self.setting_window.second_limit_enter.setStyleSheet(ready_style_border)
            else:
                if (
                    self.setting_window.type_work_enter.currentText()
                    != QApplication.translate("Device","Стабилизация мощности")
                ):
                    self.setting_window.second_limit_enter.setStyleSheet(
                        not_ready_style_border
                    )
                else:
                    self.setting_window.second_limit_enter.setStyleSheet(
                        ready_style_border
                    )

            return (
                self.active_channel_act.is_stop_value_correct
                and self.active_channel_act.is_start_value_correct
                and self.active_channel_act.is_step_correct
                and self.active_channel_act.is_second_value_correct
            )

        return False

    def _change_units(self):
        if self.key_to_signal_func:
            # print("изменить параметры")
            self.setting_window.second_limit_enter.setEnabled(True)
            if (
                self.setting_window.type_work_enter.currentText()
                == QApplication.translate("Device","Стабилизация напряжения")
            ):
                self.setting_window.label_7.setText("V")
                self.setting_window.label_8.setText("V")
                self.setting_window.label_9.setText("V")
                self.setting_window.second_value_limit_label.setText( QApplication.translate("Device","Ток не выше (А)") )
            if self.setting_window.type_work_enter.currentText() == QApplication.translate("Device","Стабилизация тока"):
                self.setting_window.label_7.setText("A")
                self.setting_window.label_8.setText("A")
                self.setting_window.label_9.setText("A")
                self.setting_window.second_value_limit_label.setText(
                    QApplication.translate("Device","Напряжение не выше (V)")
                )
            if (
                self.setting_window.type_work_enter.currentText()
                == QApplication.translate("Device","Стабилизация мощности")
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
            if self.setting_window.type_step_enter.currentText() == QApplication.translate("Device","Адаптивный шаг"):
                self.setting_window.step_enter.setEnabled(False)
                self.setting_window.step_enter.setStyleSheet(
                    "background-color: rgb(180, 180, 180)"
                )
                self.setting_window.triger_meas_enter.clear()
                self.setting_window.triger_meas_enter.addItems([ QApplication.translate("Device","Внешний сигнал") ])
            else:
                self.setting_window.step_enter.setEnabled(True)
                self.setting_window.triger_meas_enter.addItems([ QApplication.translate("Device","Таймер") ])

    @base_device.base_add_parameters_from_window
    def add_parameters_from_window(self):  # менять для каждого прибора

        if self.key_to_signal_func:
            self.active_channel_act.dict_buf_parameters["type_of_work"] = (
                self.setting_window.type_work_enter.currentText()
            )
            self.active_channel_act.dict_buf_parameters["type_step"] = (
                self.setting_window.type_step_enter.currentText()
            )
            self.active_channel_act.dict_buf_parameters["high_limit"] = (
                self.setting_window.stop_enter.currentText()
            )
            self.active_channel_act.dict_buf_parameters["low_limit"] = (
                self.setting_window.start_enter.currentText()
            )
            self.active_channel_act.dict_buf_parameters["step"] = (
                self.setting_window.step_enter.currentText()
            )

            self.active_channel_act.dict_buf_parameters["second_value"] = (
                self.setting_window.second_limit_enter.currentText()
            )

            self.active_channel_act.dict_buf_parameters["repeat_reverse"] = (
                self.setting_window.radioButton.isChecked()
            )
            self.active_channel_act.dict_buf_parameters["soft_start"] = (
                self.setting_window.is_soft_start.isChecked()
            )
            self.active_channel_act.dict_buf_parameters["soft_off"] = (
                self.setting_window.is_soft_stop.isChecked()
            )

            self.active_channel_meas.dict_buf_parameters["meas_cur"] = (
                self.setting_window.current_meas.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["meas_vol"] = (
                self.setting_window.voltage_meas.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["meas_set_cur"] = (
                self.setting_window.set_current_meas.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["meas_set_vol"] = (
                self.setting_window.set_voltage_meas.isChecked()
            )

    def send_signal_ok(
        self,
    ):
        "вызывается только после закрытия окна настроек"
        self.add_parameters_from_window()
        # те же самые настройки, ничего не делаем
        
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.active_channel_act.dict_settable_parameters = copy.deepcopy(self.active_channel_act.dict_buf_parameters)
        self.active_channel_meas.dict_settable_parameters = copy.deepcopy(self.active_channel_meas.dict_buf_parameters)
        is_parameters_correct = True

        if self.dict_buf_parameters["COM"] == QApplication.translate("Device","Нет подключенных портов") :
            is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

        if is_parameters_correct:
            is_parameters_correct = self._is_correct_parameters()

        try:
            float(self.setting_window.stop_enter.currentText())
            float(self.setting_window.start_enter.currentText())
            float(self.setting_window.step_enter.currentText())
            float(self.setting_window.boudrate.currentText())
            float(self.setting_window.second_limit_enter.currentText())
        except:
            is_parameters_correct = False

        #print(f"{self.active_channel_act.dict_settable_parameters=} {self.active_channel_act}")
        #print(f"{self.active_channel_meas.dict_settable_parameters=} {self.active_channel_meas}")

        self.installation_class.message_from_device_settings(
            name_device=self.name,
            num_channel=self.active_channel_meas.number,
            status_parameters=is_parameters_correct,
            list_parameters_device=self.dict_settable_parameters,
            list_parameters_act=self.active_channel_act.dict_settable_parameters,
            list_parameters_meas=self.active_channel_meas.dict_settable_parameters,
        )

    def confirm_parameters(self):  # менять для каждого прибора
        """метод подтверждения корректности параметров от контроллера установки. установка проверяет ком порты, распределяет их между устройствами и отдает каждому из устройств"""

        for ch in self.channels:
            if ch.is_ch_active():
                ch.step_index = -1
                self.switch_channel(ch.number)
            else:
                continue

            self.active_channel_act.steps_voltage.clear()
            self.active_channel_act.steps_current.clear()
            if (
                self.active_channel_act.dict_settable_parameters["type_of_work"]
                == QApplication.translate("Device","Стабилизация напряжения")
            ):

                if (
                    self.active_channel_act.dict_settable_parameters["type_step"]
                    == QApplication.translate("Device","Заданный шаг")
                ):
                    (
                        self.active_channel_act.steps_current,
                        self.active_channel_act.steps_voltage,
                    ) = self.__fill_arrays(
                        float(
                            self.active_channel_act.dict_settable_parameters[
                                "low_limit"
                            ]
                        ),
                        float(
                            self.active_channel_act.dict_settable_parameters[
                                "high_limit"
                            ]
                        ),
                        float(self.active_channel_act.dict_settable_parameters["step"]),
                        float(
                            self.active_channel_act.dict_settable_parameters[
                                "second_value"
                            ]
                        ),
                    )

            elif (
                self.active_channel_act.dict_settable_parameters["type_of_work"]
                == QApplication.translate("Device","Стабилизация тока")
            ):
                if (
                    self.active_channel_act.dict_settable_parameters["type_step"]
                    == QApplication.translate("Device","Заданный шаг")
                ):
                    (
                        self.active_channel_act.steps_voltage,
                        self.active_channel_act.steps_current,
                    ) = self.__fill_arrays(
                        float(
                            self.active_channel_act.dict_settable_parameters[
                                "low_limit"
                            ]
                        ),
                        float(
                            self.active_channel_act.dict_settable_parameters[
                                "high_limit"
                            ]
                        ),
                        float(self.active_channel_act.dict_settable_parameters["step"]),
                        float(
                            self.active_channel_act.dict_settable_parameters[
                                "second_value"
                            ]
                        ),
                    )

            elif (
                self.active_channel_act.dict_settable_parameters["type_of_work"]
                == QApplication.translate("Device","Стабилизация мощности")
            ):
                if (
                    self.active_channel_act.dict_settable_parameters["type_step"]
                    == QApplication.translate("Device","Заданный шаг")
                ):
                    pass

            if self.active_channel_act.dict_buf_parameters["repeat_reverse"] == True:
                buf_current = copy.deepcopy(self.active_channel_act.steps_current)
                buf_voltage = copy.deepcopy(self.active_channel_act.steps_voltage)
                buf_current = buf_current[::-1]  # разворот списка
                buf_voltage = buf_voltage[::-1]
                buf_current = buf_current[1 : len(buf_current)]
                buf_voltage = buf_voltage[1 : len(buf_voltage)]

                for cur, vol in zip(buf_current, buf_voltage):
                    self.active_channel_act.steps_current.append(cur)
                    self.active_channel_act.steps_voltage.append(vol)

            self.active_channel_act.dict_settable_parameters["num steps"] = int(
                len(self.active_channel_act.steps_voltage)
            )

    # действия перед стартом эксперимента, включить, настроить, подготовить и т.д.
    def action_before_experiment(self, number_of_channel) -> bool:
        """устанавливает значения тока и напряжения, включает выход прибора"""

        self.switch_channel(number_of_channel)
        # print(f"настройка канала {number_of_channel} прибора "+ str(self.name)+ " перед экспериментом..")
        is_correct = True
        if ( self._set_voltage( self.active_channel_act.number, self.active_channel_act.min_step_V ) == False ):
            is_correct = False
        if ( self._set_current( self.active_channel_act.number, self.active_channel_act.min_step_A ) == False ):
            is_correct = False

        if is_correct:
            self._output_switching_on( self.active_channel_act.number )
            return True
        else:
            return False

    def action_end_experiment( self, ch ) -> bool:
        """выключение прибора"""
        self.switch_channel(ch_name=ch.get_name())
        # print("Плавное выключение источника питания")
        status = True
        if ch.get_type() == "act":
            if self.active_channel_act.dict_buf_parameters["soft_start"] == True:
                count = 3
                is_voltage_read = False

                while count > 0:
                    voltage = self._get_setting_voltage(self.active_channel_act.number)
                    if voltage == False:
                        count -= 1
                    else:
                        is_voltage_read = True
                        count = 0
                if is_voltage_read:
                    step = int(voltage / 10)
                    while voltage > step:
                        voltage -= step
                        # print("напряжение = ", voltage)
                        self._set_voltage(self.active_channel_act.number, voltage)
                        time.sleep(3)
                else:
                    status = False

            self._output_switching_off(self.active_channel_act.number)
        return status

    def soft_start( self, number_of_channel, repeat=3 ):
        """плавное включение прибора"""
        self.switch_channel(number_of_channel)
        # print("Плавное выключение источника питания")

        if (
            self.active_channel_act.dict_buf_parameters["type_of_work"]
            == QApplication.translate("Device","Стабилизация напряжения")
        ):
            focus_funk = self._set_voltage
            step = int(self.active_channel_act.steps_voltage[0] / 5)
        elif (
            self.active_channel_act.dict_buf_parameters["type_of_work"]
            == QApplication.translate("Device","Стабилизация тока")
        ):
            focus_funk = self._set_current
            step = int(self.active_channel_act.steps_current[0] / 5)
            
        else:
            return False
        param = 0
        while param < step * 5:
            param += step
            count = repeat
            time.sleep(1)
            status = False
            while count > 0:
                buf_par = focus_funk(self.active_channel_act.number, param)
                if buf_par == False:
                    count -= 1
                    time.sleep(0.2)
                else:
                    count = 0
                    status = True
            if status == False:
                return False
        return True

    def do_action( self, ch, repeat=3 ) -> bool:
        """активирует следующие значение тока, напряжения прибора, если текущие значения максимальны, то возвращает ложь"""
        parameters = [self.name + " " + str(ch.get_name())]
        start_time = time.time()
        if ch.get_type() == "act":
            if ch.step_index < len(ch.steps_voltage) - 1:
                if (
                    ch.step_index == 0
                    and ch.dict_settable_parameters["soft_start"] == True
                ):
                    if (
                        self.soft_start(number_of_channel=ch.get_number(), repeat=3)
                        == False
                    ):
                        """ошибка плавного старта"""
                        return (
                            ch_response_to_step.Step_fail,
                            parameters,
                            time.time() - start_time,
                        )

                i = 0
                answer = ch_response_to_step.Step_fail
                while i - 1 < repeat and answer == ch_response_to_step.Step_fail:
                    time.sleep(0.2)
                    i += 1
                    if (
                        self._set_voltage(
                            ch.get_number(), ch.steps_voltage[ch.step_index]
                        )
                        == True
                    ):
                        answer = ch_response_to_step.Step_done
                        # print(f"установлено успешно напряжение {self.active_channel.steps_voltage[self.active_channel.step_index]}")
                    else:
                        answer = ch_response_to_step.Step_fail
                        if self.is_debug:
                            answer = ch_response_to_step.Step_done
                        continue

                    if (
                        self._set_current(
                            ch.get_number(), ch.steps_current[ch.step_index]
                        )
                        == True
                    ):
                        answer = ch_response_to_step.Step_done
                    else:
                        answer = ch_response_to_step.Step_fail
                        if self.is_debug:
                            answer = ch_response_to_step.Step_done
                        continue

            else:
                answer = ch_response_to_step.End_list_of_steps  # след шага нет

            if self.is_debug:
                if answer != ch_response_to_step.End_list_of_steps:
                    answer = ch_response_to_step.Step_done

            return answer, parameters, time.time() - start_time
        return ch_response_to_step.Incorrect_ch, parameters, time.time() - start_time

    def do_meas( self, ch ):
        """прочитать текущие и настроенные значения"""
        start_time = time.time()
        parameters = [self.name + " " + str(ch.get_name())]
        if ch.get_type() == "meas":

            is_correct = True
            current_actual = None
            voltage_actual = None

            if ch.dict_settable_parameters["meas_set_vol"] == True:
                voltage = self._get_setting_voltage(ch.get_number())
                if voltage is not False:
                    val = ["voltage_set=" + str(voltage)]
                    parameters.append(val)
                else:
                    is_correct = False
                    if self.is_debug:
                        is_correct = True
                        parameters.append(["voltage_set=" + str(random.random())])
                    else:
                        val = ["voltage_set=" + "fail"]
                        parameters.append(val)

            if ch.dict_settable_parameters["meas_vol"] == True:
                voltage = self._get_current_voltage(ch.number)
                if voltage is not False:
                    val = ["voltage_rel=" + str(voltage)]
                    voltage_actual = voltage
                    parameters.append(val)
                else:
                    is_correct = False
                    if self.is_debug:
                        is_correct = True
                        parameters.append(["voltage_rel=" + str(random.random() * 30)])
                    else:
                        val = ["voltage_rel=" + "fail"]
                        parameters.append(val)

            if ch.dict_settable_parameters["meas_set_cur"] == True:
                current = self._get_setting_current(ch.get_number())
                if current is not False:
                    val = ["current_set=" + str(current)]
                    parameters.append(val)
                else:
                    is_correct = False
                    if self.is_debug:
                        is_correct = True
                        parameters.append(["current_set=" + str(random.random())])
                    else:
                        val = ["current_set=" + "fail"]
                        parameters.append(val)

            if ch.dict_settable_parameters["meas_cur"] == True:
                current = self._get_current_current(ch.get_number())
                if current is not False:
                    val = ["current_rel=" + str(current)]
                    current_actual = current
                    parameters.append(val)
                else:
                    is_correct = False
                    if self.is_debug:
                        is_correct = True
                        parameters.append(["current_rel=" + str(random.random() * 30)])
                    else:
                        val = ["current_rel=" + "fail"]
                        parameters.append(val)

            if voltage_actual != None and current_actual != None and current_actual > 0:
                val = ["R_rel=" + str(voltage_actual / current_actual)]
                parameters.append(val)
                val = ["W_rel=" + str(voltage_actual * current_actual)]
                parameters.append(val)

            if is_correct:
                ans = ch_response_to_step.Step_done
            else:
                ans = ch_response_to_step.Step_fail

            return ans, parameters, time.time() - start_time

        return ch_response_to_step.Incorrect_ch, parameters, time.time() - start_time

    def __fill_arrays( self, start_value, stop_value, step, constant_value ):
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
            if current_value == stop_value:
                steps_1.append(constant_value)
                steps_2.append(current_value)
                break
        else:
            steps_1.append(constant_value)
            steps_2.append(stop_value)
        return steps_1, steps_2

    def set_test_mode( self ):
        """переводит прибор в режим теста, выдаются сырые данные от функций передачи и приема"""
        self.is_test = True

    def reset_test_mode( self ):
        self.is_test = False
