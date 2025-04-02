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

import logging
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Devices.power_supply_class import power_supply
from Devices.base_power_supply import chActPowerSupply, chMeasPowerSupply

logger = logging.getLogger(__name__)

class matrixWps300s(power_supply):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "serial", installation_class)
        self.ch1_act = chActPowerSupply(
            1,
            self,
            max_current=10,
            max_voltage=80,
            max_power=300,
            min_step_A=0.001,
            min_step_V=0.001,
            min_step_W=1,
        )
        self.ch1_meas = chMeasPowerSupply(1, self)
        self.channels = self.create_channel_array()

    def _set_voltage(self, ch_num, voltage) -> bool:
        """установить значение напряжения канала"""
        logger.debug(f"устанавливаем напряжение {voltage} канала {ch_num}")
        self.open_port()
        self.select_channel(ch_num)
        self.client.write(f"VOLT {voltage}\r\n")
        time.sleep(0.2)
        self.client.write(f"VOLT?\r\n")
        time.sleep(0.2)
        response = None
        try:
            response = self.client.readline().decode().strip()
            response = float(response)
        except:
            logger.warning(f"настройка напряжения ответ-{response}")
            response = False
        self.client.close()
        logger.debug(f"статус {response == voltage}")
        return response == voltage

    def _set_current(self, ch_num, current) -> bool:
        """установить значение тока канала"""
        logger.debug(f"устанавливаем ток {current} канала {ch_num}")
        self.open_port()
        self.select_channel(ch_num)
        self.client.write(f"CURR {current}\r\n")
        time.sleep(0.2)
        self.client.write(f"CURR?\r\n")
        time.sleep(0.2)
        response = None
        try:
            response = self.client.readline().decode().strip()
            response = float(response)
        except:
            logger.warning(f"установка тока ответ-{response}")
            response = False
        self.client.close()
        logger.debug(f"статус {response == current}")
        return response == current

    def _output_switching_on(self, ch_num) -> bool:
        """включить канал"""
        self.open_port()
        self.client.write(f"OUTP ON\r\n")
        self.client.close()

    def _output_switching_off(self, ch_num) -> bool:
        """выключить канал"""
        self.open_port()
        self.client.write(f"OUTP OFF\r\n")
        self.client.close()

    def _get_current_voltage(self, ch_num) -> float:
        """возвращает значение установленного напряжения канала"""
        self.open_port()
        self.select_channel(ch_num)
        self.client.write(f"MEAS:VOLT?\r\n")
        time.sleep(0.2)
        response = None
        try:
            response = self.client.readline().decode().strip()
            response = float(response)
        except:
            response = False
        self.client.close()
        return response

    def _get_current_current(self, ch_num) -> float:
        """возвращает значение измеренного тока канала"""
        self.open_port()
        self.select_channel(ch_num)
        self.client.write(f"MEAS:CURR?\r\n")
        time.sleep(0.2)
        response = None
        try:
            response = self.client.readline().decode().strip()
            response = float(response)
        except:
            response = False
        self.client.close()
        return response

    def _get_setting_voltage(self, ch_num) -> float:
        """возвращает значение установленного напряжения канала"""
        self.open_port()
        self.select_channel(ch_num)
        self.client.write(f"VOLT?\r\n")
        time.sleep(0.2)
        response = None
        try:
            response = self.client.readline().decode().strip()
            response = float(response)
        except:
            response = False
        self.client.close()
        return response

    def _get_setting_current(self, ch_num) -> float:
        """возвращает значение установленного тока канала"""
        self.open_port()            
        self.select_channel(ch_num)
        self.client.write(f"CURR?\r\n")
        time.sleep(0.2)
        response = None
        try:
            response = self.client.readline().decode().strip()
            response = float(response)
        except:
            response = False
        self.client.close()
        return response

    def _get_setting_state(self, ch_num) -> bool:
        """возвращает состояние канала вкл(true) или выкл(false)"""
        pass

    def select_channel(self, channel):
        self.open_port()
        self.client.write(f"INST CH{channel}\r\n")
