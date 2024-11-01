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
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtCore import pyqtSlot

from Devices.Classes import (
    base_ch,
    base_device,
    ch_response_to_step,
    not_ready_style_border,
    ready_style_border,
    which_part_in_ch,
)
from Devices.commandsSR830 import commandsSR830
from Devices.interfase.set_sr830_window import Ui_Set_sr830

logger = logging.getLogger(__name__)


class sr830Class(base_device):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "serial", installation_class)
        # ===Создать каналы и вызвать функция конфигурация и построения массива каналов===
        self.part_ch = (
            which_part_in_ch.only_meas
        )  # указываем, из каких частей состоиит канал в данном приборе
        self.ch1_meas = ch_meas_sr830_class(1, self)
        self.channels = self.create_channel_array()
        # ==========end==========

        # ===Прочие поля, необходимые для прибора
        self.counter = 0
        self.command = None
        # ==========end==========

        # ===Создать экземпляр класса окна настроек===
        self.setting_window = Ui_Set_sr830()
        # ==========end==========
        self.base_settings_window()

        # ===установка параметров и настройка редактирования===
        self.setting_window.frequency_enter.setEditable(True)
        self.setting_window.frequency_enter.addItems(["400"])
        self.setting_window.amplitude_enter.setEditable(True)
        self.setting_window.amplitude_enter.addItems(["1"])
        # ==========end==========

        # ===Установка слотов для сигналов===

        # ==========end==========

    @base_device.base_show_window
    def show_setting_window(self, number_of_channel):

        self.switch_channel(number_of_channel)

        self.key_to_signal_func = False
        # self.base_show_window()

        # ===Заполнить поля значениями из буфера===
        self.setting_window.frequency_enter.setCurrentText(
            str(self.active_channel_meas.dict_buf_parameters["frequency"])
        )
        self.setting_window.amplitude_enter.setCurrentText(
            str(self.active_channel_meas.dict_buf_parameters["amplitude"])
        )
        self.setting_window.sourse_meas_enter.setCurrentText(
            self.active_channel_meas.dict_buf_parameters["sourse/time"]
        )
        self.setting_window.boudrate.setCurrentText(
            self.dict_buf_parameters["baudrate"]
        )
        self.setting_window.comportslist.setCurrentText(self.dict_buf_parameters["COM"])

        number, factor, dec_factor = self.get_parts_time_const(
            float(self.active_channel_meas.dict_buf_parameters["time_const"])
        )
        self.setting_window.time_const_enter_number.setCurrentText(number)
        self.setting_window.time_const_enter_factor.setCurrentText(factor)
        self.setting_window.time_const_enter_decimal_factor.setCurrentText(dec_factor)

        self.setting_window.Filt_slope_enter_level.setCurrentText(
            str(self.active_channel_meas.dict_buf_parameters["filter_slope"])
        )
        self.setting_window.SYNK_enter.setCurrentText(
            str(self.active_channel_meas.dict_buf_parameters["SYNK_200_Hz"])
        )

        number, factor, dec_factor = self.get_parts_sen(
            float(self.active_channel_meas.dict_buf_parameters["sensitivity"])
        )
        self.setting_window.sensitivity_enter_number.setCurrentText(number)
        self.setting_window.sensitivity_enter_factor.setCurrentText(factor)
        self.setting_window.sensitivity_enter_decimal_factor.setCurrentText(dec_factor)

        self.setting_window.input_channels_enter.setCurrentText(
            self.active_channel_meas.dict_buf_parameters["input_channel"]
        )
        self.setting_window.input_type_enter.setCurrentText(
            self.active_channel_meas.dict_buf_parameters["input_type"]
        )
        self.setting_window.connect_ch_enter.setCurrentText(
            self.active_channel_meas.dict_buf_parameters["input_connect"]
        )
        self.setting_window.reserve_enter.setCurrentText(
            self.active_channel_meas.dict_buf_parameters["reserve"]
        )
        self.setting_window.filters_enter.setCurrentText(
            self.active_channel_meas.dict_buf_parameters["filters"]
        )
        # ==========end==========

        self.key_to_signal_func = True
        self._action_when_select_trigger()
        self._is_correct_parameters()
        self.setting_window.show()

    @pyqtSlot()
    @base_device.base_is_correct_parameters
    def _is_correct_parameters(self) -> bool:
        if self.key_to_signal_func:

            # ===Проверить корректность полей===
            is_number_correct = True
            is_fact_correct = True
            is_dec_fact_correct = True

            is_ampl_correct = True
            is_freq_correct = True

            if (
                self.setting_window.sensitivity_enter_decimal_factor.currentText()
                == "V/uA"
            ):

                if self.setting_window.sensitivity_enter_factor.currentText() != "X1":
                    is_fact_correct = False
                if self.setting_window.sensitivity_enter_number.currentText() != "1":
                    is_number_correct = False
            elif (
                self.setting_window.sensitivity_enter_decimal_factor.currentText()
                == "nV/fA"
            ):
                if self.setting_window.sensitivity_enter_number.currentText() == "1":
                    is_number_correct = False

            try:
                float(self.setting_window.amplitude_enter.currentText())
            except:
                is_ampl_correct = False
            try:
                float(self.setting_window.frequency_enter.currentText())
            except:
                is_freq_correct = False

            if is_ampl_correct:
                if (
                    float(self.setting_window.amplitude_enter.currentText()) > 10
                    or float(self.setting_window.amplitude_enter.currentText()) < 0.01
                ):
                    is_ampl_correct = False
            if is_freq_correct:
                if (
                    float(self.setting_window.frequency_enter.currentText()) > 102000
                    or float(self.setting_window.frequency_enter.currentText()) < 0.01
                ):
                    is_freq_correct = False
            # ==========end==========

            # ===Установить цвета полей на основании проверки===
            self.setting_window.sensitivity_enter_number.setStyleSheet(
                ready_style_border
            )
            self.setting_window.sensitivity_enter_factor.setStyleSheet(
                ready_style_border
            )
            self.setting_window.sensitivity_enter_decimal_factor.setStyleSheet(
                ready_style_border
            )

            self.setting_window.amplitude_enter.setStyleSheet(ready_style_border)
            self.setting_window.frequency_enter.setStyleSheet(ready_style_border)
            self.setting_window.num_meas_enter.setStyleSheet(ready_style_border)
            self.setting_window.sourse_meas_enter.setStyleSheet(ready_style_border)

            if not is_number_correct:
                self.setting_window.sensitivity_enter_number.setStyleSheet(
                    not_ready_style_border
                )
            if not is_fact_correct:
                self.setting_window.sensitivity_enter_factor.setStyleSheet(
                    not_ready_style_border
                )
            if not is_dec_fact_correct:
                self.setting_window.sensitivity_enter_decimal_factor.setStyleSheet(
                    not_ready_style_border
                )

            if not is_freq_correct:
                self.setting_window.frequency_enter.setStyleSheet(
                    not_ready_style_border
                )
            if not is_ampl_correct:
                self.setting_window.amplitude_enter.setStyleSheet(
                    not_ready_style_border
                )
            # ==========end==========

            # ===Вернуть ответ на основе проверки параметров
            return (
                is_number_correct
                and is_fact_correct
                and is_dec_fact_correct
                and is_ampl_correct
                and is_freq_correct
            )
            # ==========end==========

        return False

    # ===Методы расчета различных значений===
    def calculate_time_const(self) -> str:
        time_const_enter_factor = {"X1": 1, "X10": 10, "X100": 100}
        time_const_enter_decimal_factor = {
            "ks": 1000,
            "s": 1,
            "ms": 0.001,
            "us": 0.000001,
        }
        factor = time_const_enter_factor[
            self.setting_window.time_const_enter_factor.currentText()
        ]
        decimal_factor = time_const_enter_decimal_factor[
            self.setting_window.time_const_enter_decimal_factor.currentText()
        ]
        return (
            round(
                float(self.setting_window.time_const_enter_number.currentText())
                * factor
                * decimal_factor
                * 1000000000
            )
            / 1000000000
        )

    def calculate_sensitivity(self) -> str:
        sensitivity_enter_factor = {"X1": 1, "X10": 10, "X100": 100}
        sensitivity_enter_decimal_factor = {
            "V/uA": 1,
            "mV/nA": 0.001,
            "uV/pA": 0.000001,
            "nV/fA": 0.000000001,
        }  # в вольтах подсчет
        factor = sensitivity_enter_factor[
            self.setting_window.sensitivity_enter_factor.currentText()
        ]
        decimal_factor = sensitivity_enter_decimal_factor[
            self.setting_window.sensitivity_enter_decimal_factor.currentText()
        ]

        return (
            round(
                (
                    float(self.setting_window.sensitivity_enter_number.currentText())
                    * factor
                    * decimal_factor
                )
                * 1000000000
            )
            / 1000000000
        )

    def get_parts_sen(self, value):
        sensitivity_enter_decimal_factor = {
            1: "V/uA",
            0.001: "mV/nA",
            0.000001: "uV/pA",
            0.000000001: "nV/fA",
        }
        numbers = [1, 3, 5]
        factors = [1, 10, 100]
        dec_factors = [1 / 1000000000, 1 / 1000000, 1 / 1000, 1]

        number = 1
        factor = 1
        dec_factor = 1
        for i in range(len(numbers)):
            for j in range(len(factors)):
                for k in range(len(dec_factors)):
                    if (
                        value
                        == round(numbers[i] * factors[j] * dec_factors[k] * 1000000000)
                        / 1000000000
                    ):
                        number = numbers[i]
                        factor = factors[j]
                        dec_factor = dec_factors[k]
                        break
        return (
            str(number),
            "X" + str(factor),
            sensitivity_enter_decimal_factor[dec_factor],
        )

    def get_parts_time_const(self, value):
        time_const_enter_decimal_factor = {
            1000: "ks",
            1: "s",
            0.001: "ms",
            0.000001: "us",
        }
        numbers = [1, 3]
        factors = [1, 10, 100]
        dec_factors = [1 / 1000000, 1 / 1000, 1, 1000]

        number = 1
        factor = 1
        dec_factor = 1
        for i in range(len(numbers)):
            for j in range(len(factors)):
                for k in range(len(dec_factors)):
                    if (
                        value
                        == round(numbers[i] * factors[j] * dec_factors[k] * 1000000000)
                        / 1000000000
                    ):
                        number = numbers[i]
                        factor = factors[j]
                        dec_factor = dec_factors[k]
                        break
        return (
            str(number),
            "X" + str(factor),
            time_const_enter_decimal_factor[dec_factor],
        )

    # ==========end==========

    @base_device.base_add_parameters_from_window
    def add_parameters_from_window(self):

        if self.key_to_signal_func:
            # self.base_add_parameters_from_window()
            # ===Записать в буфер значения из полей===
            self.active_channel_meas.dict_buf_parameters["time_const"] = (
                self.calculate_time_const()
            )
            self.active_channel_meas.dict_buf_parameters["filter_slope"] = float(
                self.setting_window.Filt_slope_enter_level.currentText()
            )
            self.active_channel_meas.dict_buf_parameters["SYNK_200_Hz"] = (
                self.setting_window.SYNK_enter.currentText()
            )
            self.active_channel_meas.dict_buf_parameters["sensitivity"] = (
                self.calculate_sensitivity()
            )
            self.active_channel_meas.dict_buf_parameters["reserve"] = (
                self.setting_window.reserve_enter.currentText()
            )
            self.active_channel_meas.dict_buf_parameters["frequency"] = float(
                self.setting_window.frequency_enter.currentText()
            )
            self.active_channel_meas.dict_buf_parameters["amplitude"] = float(
                self.setting_window.amplitude_enter.currentText()
            )

            self.active_channel_meas.dict_buf_parameters["input_channel"] = (
                self.setting_window.input_channels_enter.currentText()
            )
            self.active_channel_meas.dict_buf_parameters["input_type"] = (
                self.setting_window.input_type_enter.currentText()
            )
            self.active_channel_meas.dict_buf_parameters["input_connect"] = (
                self.setting_window.connect_ch_enter.currentText()
            )

            self.active_channel_meas.dict_buf_parameters["filters"] = (
                self.setting_window.filters_enter.currentText()
            )
            self.active_channel_meas.dict_buf_parameters["trigger"] = (
                self.setting_window.triger_meas_enter.currentText()
            )
            self.active_channel_meas.dict_buf_parameters["sourse/time"] = (
                self.setting_window.sourse_meas_enter.currentText()
            )
            # ==========end==========

    def send_signal_ok(
        self,
    ):  # действие при подтверждении настроек, передать парамтры классу инсталляции, проверить и окрасить в цвет окошко, вписать паарметры
        self.add_parameters_from_window()
        # те же самые настройки, ничего не делаем
        if (
            self.active_channel_meas.dict_buf_parameters
            == self.active_channel_meas.dict_settable_parameters
            and self.dict_buf_parameters == self.dict_settable_parameters
        ):
            # return
            pass
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.active_channel_meas.dict_settable_parameters = copy.deepcopy(
            self.active_channel_meas.dict_buf_parameters
        )

        is_parameters_correct = True
        if self.dict_buf_parameters["COM"] == "Нет подключенных портов":
            is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

        # ===Дополнительные проверки перед отправкой параметров прибора в класс установки===

        # ==========end==========

        if not self._is_correct_parameters():
            is_parameters_correct = False

        self.installation_class.message_from_device_settings(
            name_device=self.name,
            num_channel=self.active_channel_meas.number,
            status_parameters=is_parameters_correct,
            list_parameters_device=self.dict_settable_parameters,
            list_parameters_meas=self.active_channel_meas.dict_settable_parameters,
        )

    def confirm_parameters(self):
        if True:
            for ch in self.channels:
                if ch.is_ch_active():
                    ch.step_index = -1

            # ===Действия при подтверждении параметров от класса установки, приготовления к старту===
            self.command = commandsSR830(self)

            self.get_sin = self.sin_wave(
                freq=1, amplitude=1, phase_shift=0, sample_rate=100
            )  # Частота 1 Гц, амплитуда 1, фазовый сдвиг 0, частота дискретизации 100 Гц
            self.get_ln = self.natural_log_generator()
            self.get_exp = self.exponential_function_generator()
            self.get_mult = self.multiple_function_generator(3)
            # ==========end==========
        else:
            pass

    def action_before_experiment(self, number_of_channel) -> bool:
        self.switch_channel(number_of_channel)

        # ===Действия перед экспериментом, запись настроек в прибор===
        pause = 0.1
        status = True
        if not self.command._set_filter_slope(
            slope=self.active_channel_meas.dict_settable_parameters["filter_slope"]
        ):
            status = False

        time.sleep(pause)
        if not self.command._set_input_conf(
            conf=self.active_channel_meas.dict_settable_parameters["input_channel"]
        ):
            status = False

        time.sleep(pause)
        if not self.command._set_input_type_conf(
            type_conf=self.active_channel_meas.dict_settable_parameters["input_type"]
        ):
            status = False

        time.sleep(pause)
        if not self.command._set_input_type_connect(
            input_ground=self.active_channel_meas.dict_settable_parameters[
                "input_connect"
            ]
        ):
            status = False

        time.sleep(pause)
        if not self.command._set_line_filters(
            type=self.active_channel_meas.dict_settable_parameters["filters"]
        ):
            status = False

        time.sleep(pause)
        if not self.command._set_reserve(
            reserve=self.active_channel_meas.dict_settable_parameters["reserve"]
        ):
            status = False

        time.sleep(pause)
        if not self.command._set_time_const(
            time_constant=self.active_channel_meas.dict_settable_parameters[
                "time_const"
            ]
        ):
            status = False

        time.sleep(pause)
        if not self.command._set_sens(
            sens=self.active_channel_meas.dict_settable_parameters["sensitivity"]
        ):
            status = False

        time.sleep(pause)
        if not self.command._set_frequency(
            freq=self.active_channel_meas.dict_settable_parameters["frequency"]
        ):
            status = False

        time.sleep(pause)
        if not self.command._set_amplitude(
            ampl=self.active_channel_meas.dict_settable_parameters["amplitude"]
        ):
            status = False

        # ==========end==========

        return status

    def do_meas(self, ch):
        """прочитать текущие и настроенные значения"""
        self.switch_channel(ch_name=ch.get_name())
        start_time = time.time()
        parameters = [self.name + " " + str(ch.get_name())]
        if ch.get_type() == "meas":
            is_correct = True

            # ===проведение измерений и действия с прибором===
            is_stop_analyze = False
            count = 0
            result_analyze = False
            if not self.is_debug:
                while not is_stop_analyze:
                    self.command.push_autophase()
                    buf_display_value = []
                    for i in range(6):
                        disp2 = self.command.get_parameter(
                            self.command.COMM_DISPLAY, timeout=0.5, param=2
                        )

                        if not disp2:
                            continue
                        else:
                            buf_display_value.append(float(disp2))
                            # val = ["disp2=" + str(disp2)]

                    if len(buf_display_value) > 3:
                        if (
                            max(buf_display_value) < 2 and min(buf_display_value) > -2
                        ):  # выход за границы
                            if len(buf_display_value) >= 5:
                                for i in range(
                                    len(buf_display_value) - 2
                                ):  # анализ монотонности
                                    if (
                                        buf_display_value[i] >= buf_display_value[i + 1]
                                        and buf_display_value[i + 1]
                                        <= buf_display_value[i + 2]
                                    ):
                                        is_stop_analyze = True
                                        result_analyze = True
                                        break
                                    if (
                                        buf_display_value[i] <= buf_display_value[i + 1]
                                        and buf_display_value[i + 1]
                                        >= buf_display_value[i + 2]
                                    ):
                                        is_stop_analyze = True
                                        result_analyze = True
                                        break

                    count += 1
                    if count >= 3:
                        is_stop_analyze = True

            if result_analyze == True:
                disp1 = self.command.get_parameter(
                    command=self.command.COMM_DISPLAY, timeout=1, param=1
                )
                if not disp1:
                    is_correct = False
                else:
                    val = ["disp1=" + str(disp1)]
                    parameters.append(val)

                disp2 = self.command.get_parameter(
                    self.command.COMM_DISPLAY, timeout=1, param=2
                )
                if not disp2:
                    is_correct = False
                else:
                    val = ["disp2=" + str(disp2)]
                    parameters.append(val)

                phase = self.command.get_parameter(self.command.PHASE, timeout=1)
                if not phase:
                    is_correct = False
                else:
                    val = ["phase=" + str(phase)]
                    parameters.append(val)
            else:
                if self.is_debug:
                    is_correct = True
                    parameters.append(["SIN=" + next(self.get_sin)])
                    parameters.append(["Ln=" + next(self.get_ln)])
                    parameters.append(["EXP=" + next(self.get_exp)])
                    parameters.append(["MULT=" + next(self.get_mult)])
                    parameters.append(["disp1=" + str(254)])
                    parameters.append(["disp2=" + str(847)])
                    parameters.append(["phase=" + str(777)])
                else:
                    val = ["disp1=" + "fail"]
                    parameters.append(val)
                    val = ["disp2=" + "fail"]
                    parameters.append(val)
                    val = ["phase=" + "fail"]
                    parameters.append(val)
            # ==========end==========

            if is_correct:
                ans = ch_response_to_step.Step_done
            else:
                # ===Добавить значения fail===
                val = ["disp1=" + "fail"]
                parameters.append(val)
                val = ["disp2=" + "fail"]
                parameters.append(val)
                val = ["phase=" + "fail"]
                parameters.append(val)
                # ==========end==========

                ans = ch_response_to_step.Step_fail

            return ans, parameters, time.time() - start_time
        return ch_response_to_step.Incorrect_ch, parameters, time.time() - start_time


class ch_meas_sr830_class(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number, ch_type="meas", device_class=device_class)
        # print(f"канал {number} создан")
        # print(self.am_i_should_do_step, "ацаыввыаваываываывыаывываываываываываывавыаывыыв")
        self.base_duration_step = 2  # у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.dict_buf_parameters["time_const"] = "1000"  # секунды
        self.dict_buf_parameters["filter_slope"] = "6"  # dB
        self.dict_buf_parameters["SYNK_200_Hz"] = "off"
        self.dict_buf_parameters["sensitivity"] = "1"  # вольты
        self.dict_buf_parameters["reserve"] = "high reserve"
        self.dict_buf_parameters["input_channel"] = "A"
        self.dict_buf_parameters["input_type"] = "AC"
        self.dict_buf_parameters["input_connect"] = "ground"
        self.dict_buf_parameters["filters"] = "line"
        self.dict_buf_parameters["frequency"] = "400"
        self.dict_buf_parameters["amplitude"] = "1"
        self.dict_buf_parameters["num steps"] = "1"
        self.dict_settable_parameters = self.dict_buf_parameters


if __name__ == "__main__":

    pass
    # Создание клиента Modbus RTU
    # client = ModbusSerialClient(
    # method='rtu', port='COM3', baudrate=9600, stopbits=1, bytesize=8, parity='E')

    # power_supply = maisheng_power_class()
    # power_supply.set_client(client)

    # set_voltage(client,20000)

    """
    for i in range(0,20000,1000):
        set_voltage(client,i)
        time.sleep(5)
    """

    # power_supply.output_switching_off()
    # power_supply.set_current(1500)
    # i = power_supply.get_setting_voltage()
    # print(i.registers)

    """
    print("установка напряжения ответ", set_voltage(client,10000))
    time.sleep(1)
    print("напряжение текущее ",get_setting_voltage(client))
    time.sleep(1)
    print("установка тока ответ",set_current(client,100))
    time.sleep(1)
    print("включениие ответ",output_switching_on(client))
    time.sleep(1)
    print("напряжение текущее после включения",get_current_voltage(client))
    """

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

    """
    data = [10, 20, 30, 40, 50]
    result = client.write_registers(address=0, values=data, unit=1)
    if result.isError():
        print("Ошибка записи данных:", result)
    else:
        print("Данные успешно записаны")
    """

    # Закрытие соединения
    # client.close()

"""

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


"""
