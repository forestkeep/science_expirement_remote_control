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

from PyQt5.QtWidgets import QApplication
from Devices.Classes import base_ch, base_device, ch_response_to_step, which_part_in_ch
from Devices.interfase.set_voltmeter_window import Ui_Set_voltmeter

logger = logging.getLogger(__name__)

"""

Команда	                               Описание
[:SENSe]:VOLTage:AC:CH1	               Установить канал CH1 напряжения AC
[:SENSe]:VOLTage:AC:CH2	               Установить канал CH2 напряжения AC
[:SENSe]:VOLTage:AC:RANGe[:UPPer] 	   Выбрать диапазон (верхняя граница)
[:SENSe]:VOLTage:AC:RANGe[:UPPer]?	   Запросить текущий диапазон
[:SENSe]:VOLTage:AC:FILTer 	           Выбрать режим отображения 3½ или 4½
[:SENSe]:VOLTage:AC:FILTer?	           Запросить статус фильтра
[:SENSe]:VOLTage:AC:GND 	           Включить/выключить заземление
[:SENSe]:VOLTage:AC:GND?	           Проверить статус заземления
[:SENSe]:VOLTage:AC:RANGe:AUTO 	       Включить/выключить авторазбор диапазона
[:SENSe]:VOLTage:AC:RANGe:AUTO?	       Проверить статус авторазбора диапазона
:CALCulate:FUNCtion ""	               Выполнить математическую функцию
:CALCulate:FUNCtion?	               Запросить текущую математическую функцию
:SYSTem:VERSion?	                   Получить версию системы
IDN?	                               Получить строку идентификации прибора
*RST	                               Сбросить конфигурацию до включения
:TRG	                               Однократное запуск измерения
:TRIGger:SOURce { BUS	IMMediate}     Установить триггер начала измерения.  BUS - по команде с шины данных
:READ?	                               Получить измеренные данные
"""


class akip2404Class(base_device):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "serial", installation_class)
        self.ch1_meas = ch_meas_akip_class(1, self)
        self.ch2_meas = ch_meas_akip_class(2, self)
        self.channels = self.create_channel_array()
        self.device = None  # класс прибора будет создан при подтверждении параметров,
        # переменная хранит все возможные источники сигналов , сделать функцию, формирующую этот список в зависимости от структуры установки
        self.counter = 0
        # сюда при подтверждении параметров будет записан класс команд с клиентом
        self.command = None

        self.part_ch = (
            which_part_in_ch.only_meas
        )  # указываем, из каких частей состоиит канал в данном приборе
        self.setting_window = Ui_Set_voltmeter()
        self.base_settings_window()
        self.setting_window.range_enter.addItems(
            ["Auto", "3mV", "30mV", "300mV", "3V", "30V", "300V"]
        )
        self.setting_window.type_work_enter.addItems([QApplication.translate("Voltmeter","Напряжение")])

    @base_device.base_show_window
    def show_setting_window(self, number_of_channel):

        self.switch_channel(number_of_channel)
        # запрещаем исполнение функций во время инициализации
        self.key_to_signal_func = False
        # ============установка текущих параметров=======================
        self.setting_window.type_work_enter.setCurrentText(
            self.active_channel_meas.dict_buf_parameters["type_meas"]
        )
        self.setting_window.range_enter.setCurrentText(
            self.active_channel_meas.dict_buf_parameters["range"]
        )
        self.key_to_signal_func = True  # разрешаем выполенение функций

        self._action_when_select_trigger()
        self._is_correct_parameters()
        self.setting_window.show()

    @base_device.base_is_correct_parameters
    def _is_correct_parameters(self) -> bool:
        return True

    @base_device.base_add_parameters_from_window
    def add_parameters_from_window(self):
        if self.key_to_signal_func:
            self.active_channel_meas.dict_buf_parameters["type_meas"] = (
                self.setting_window.type_work_enter.currentText()
            )
            self.active_channel_meas.dict_buf_parameters["range"] = (
                self.setting_window.range_enter.currentText()
            )

    def send_signal_ok(
        self,
    ):  # действие при подтверждении настроек, передать парамтры классу инсталляции, проверить и окрасить в цвет окошко, вписать паарметры
        self.add_parameters_from_window()
        self.timer_for_scan_com_port.stop()

        if (
            self.active_channel_meas.dict_buf_parameters
            == self.active_channel_meas.dict_settable_parameters
            and self.dict_buf_parameters == self.dict_settable_parameters
        ):
            pass
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.active_channel_meas.dict_settable_parameters = copy.deepcopy(
            self.active_channel_meas.dict_buf_parameters
        )

        is_parameters_correct = True
        if self.dict_buf_parameters["COM"] == QApplication.translate("Connection","Нет подключенных портов"):
            is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

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

            for ch in self.channels:
                if ch.is_ch_active():
                    ch.step_index = -1


    def action_before_experiment(
        self, number_of_channel
    ) -> bool:  # менять для каждого прибора
        self.switch_channel(number_of_channel)
        self.select_channel(channel=self.active_channel_meas.number)
        print(
            f"настройка канала {number_of_channel} прибора "
            + str(self.name)
            + " перед экспериментом.."
        )

        status = True
        if self.active_channel_meas.dict_settable_parameters["range"] != "Auto":
            try:
                strip = self.active_channel_meas.dict_buf_parameters["range"][-2:]
                if strip == "mV":
                    val = (
                        float(
                            self.active_channel_meas.dict_buf_parameters["range"][0:-2:]
                        )
                        / 1000
                    )
                else:
                    val = float(
                        self.active_channel_meas.dict_buf_parameters["range"][0:-1:]
                    )
                ans = self.set_parameter(
                    command=":SENSe:VOLTage:AC:RANGe:UPPer", timeout=1, param=val
                )
                if ans == False:
                    status = False
            except ValueError as e:
                logger.warning(f"ошибка: {str(e)}")
        else:
            pass
            # TODO: проверить, включен ли режим авто, если нет, то включить
            # [:SENSe]:VOLTage:AC:RANGe:AUTO 	Включить/выключить авторазбор диапазона
            # [:SENSe]:VOLTage:AC:RANGe:AUTO?

        return status

    def do_meas(self, ch):
        """прочитать текущие и настроенные значения"""
        self.switch_channel(ch_name=ch.get_name())
        start_time = time.time()
        parameters = [self.name + " " + str(ch.get_name())]
        if ch.get_type() == "meas":
            print("делаем измерение", self.name, str(ch.get_name()))

            is_correct = True
            voltage = self._get_current_voltage(ch_num = self.active_channel.number)
            if voltage is not False:
                val = ["voltage=" + str(voltage)]
                parameters.append(val)
            else:
                is_correct = False

            # -----------------------------
            if self.is_debug:
                if is_correct == False:
                    is_correct = True
                    parameters.append(["voltage=" + str(254)])
            # -----------------------------

            if is_correct:
                print("сделан шаг", self.name)
                ans = ch_response_to_step.Step_done
            else:
                print("Ошибка шага", self.name)
                val = ["voltage=" + "fail"]
                parameters.append(val)

                ans = ch_response_to_step.Step_fail

            return ans, parameters, time.time() - start_time
        return ch_response_to_step.Incorrect_ch, parameters, time.time() - start_time

    def _get_current_voltage(self, ch_num) -> float:
        """возвращает значение установленного напряжения канала"""
        self.open_port()
        self.select_channel(channel = ch_num)
        time.sleep(0.3)
        response = self.get_parameter("READ", 3)
        if response is not False:
            num, ed = response[:6], (
                response[6:].strip() if response != False else (None, None)
            )
            try:
                response = float(num) / 1000 if ed == "mV" else float(num)
            except Exception as e:
                logger.warning(f"ошибка: {str(e)} ответ прибора - {response}")
                response = False
        self.client.close()
        return response

    def set_parameter(self, command, timeout, param):
        self.open_port()
        param = str(param)
        self.client.write(
            bytes(command, "ascii") + b" " + bytes(param, "ascii") + b"\r\n"
        )

        start_time = time.time()
        while time.time() - start_time < timeout:
            line = self.client.readline().decode().strip()
            if line:
                return line
        return False

    def get_parameter(self, command, timeout, param=False):
        self.open_port()
        if param == False:
            self.client.write(bytes(command, "ascii") + b"?\r\n")
        else:
            param = str(param)
            self.client.write(
                bytes(command, "ascii") + b"? " + bytes(param, "ascii") + b"\r\n"
            )
        if param != False:
            print(
                "чтение параметров",
                bytes(command, "ascii") + b"? " + bytes(param, "ascii") + b"\r\n",
            )
        else:
            print(bytes(command, "ascii") + b"?\r\n")

        start_time = time.time()
        while time.time() - start_time < timeout:
            line = self.client.readline().decode().strip()
            if line:
                print("Received:", line)
                return line
        logger.warning("No answer from device AKIP2404 timeout")
        return False

    def check_connect(self) -> bool:
        line = self.get_parameter("*IDN", timeout=1)
        ver = self.get_parameter(":SYSTem:VERSion", timeout=1)
        if line is not False and ver is not False:
            return line + "  " + ver
        return False

    def select_channel(self, channel):
        self.open_port()
        command = bytes(f":VOLTage:AC:CH{channel}\n", "ascii")
        self.client.write( command )


class ch_meas_akip_class(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number, ch_type="meas", device_class=device_class)
        self.base_duration_step = 0.1  # у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.dict_buf_parameters["type_meas"] = QApplication.translate("Voltmeter","Напряжение")  # секунды
        self.dict_buf_parameters["range"] = "Auto"  # dB
        self.dict_buf_parameters["num steps"] = "1"

        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)


if __name__ == "__main__":



    pass
