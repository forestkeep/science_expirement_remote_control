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
import json

from PyQt5.QtWidgets import QApplication

try:
    from Devices.base_power_supply import basePowerSupply, chActPowerSupply, chMeasPowerSupply
except:
    from base_power_supply import basePowerSupply, chActPowerSupply, chMeasPowerSupply
    
logger = logging.getLogger(__name__)

class power_supply(basePowerSupply):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "type_connection", installation_class)
        
    def load_json(self, json_data: dict):
        try:
                self.JSON_temp = json_data
                data = json_data
                self.channels_number = int(data["number_channels"])
                #self.device_name = data["device_name"]
                channels_parameters = data["channels parameters"]
                self.create_channels(channels_parameters=channels_parameters)

                self.commands = data['commands']

                self.set_volt_cmd = "VOLT {voltage}\n"
                self.ask_volt_cmd = "VOLT?\n"
                self.meas_volt_cmd = "MEAS:VOLT?\n"
                self.meas_cur_cmd = "MEAS:CURR?\n"
                self.set_cur_cmd = "CURR {current}\n"
                self.ask_cur_cmd = "CURR?\n"
                self.ON_CH_cmd = "OUTP CH{ch_num},ON\n"
                self.OFF_CH_cmd = "OUTP CH{ch_num},OFF\n"
                self.select_CH_cmd = "INST CH{ch_num}\n"

                self.set_volt_cmd = self.commands["_set_voltage"]["command"]
                self.ask_volt_cmd = self.commands["_get_setting_voltage"]["command"]
                self.meas_volt_cmd = self.commands["_get_current_voltage"]["command"]
                self.meas_cur_cmd = self.commands["_get_current_current"]["command"]
                self.set_cur_cmd =self.commands["_set_current"]["command"]
                self.ask_cur_cmd = self.commands["_get_setting_current"]["command"]
                self.ON_CH_cmd = self.commands["_output_switching_on"]["command"]
                self.OFF_CH_cmd = self.commands["_output_switching_off"]["command"]
                self.select_CH_cmd = self.commands["select_channel"]["command"]

        except Exception as e:
            logger.error(f"Не удалось загрузить команды из {json_data}: {e}")

    def create_channels(self, channels_parameters: dict):
        for ch in range(self.channels_number):
            setattr(self, f'ch{ch+1}_act', chActPowerSupply(ch+1,
                                                            self.name,
                                                            message_broker=self.message_broker,
                                                            max_current=float(channels_parameters["max_channels_current"][ch+1]),
                                                            max_voltage=float(channels_parameters["max_channels_voltage"][ch+1]),
                                                            max_power=float(channels_parameters["max_channels_power"][ch+1]),
                                                            min_step_A=float(channels_parameters["current_resolution"][ch+1]),
                                                            min_step_V=float(channels_parameters["voltage_resolution"][ch+1]),
                                                            min_step_W=float(channels_parameters["power_resolution"][ch+1])
                                                            ))
            setattr(self, f'ch{ch+1}_meas', chMeasPowerSupply(ch+1, self.name, self.message_broker))
        self.channels = self.create_channel_array()

class install_fake():
    def __init__(self, broker):
        self.message_broker = broker

class messageBrokerFake:
    def __init__(self) -> None:
        self.subscribe_list = []

    def get_subscribe_list(self, object) -> list:
        send_list = []
        return send_list
    
    def get_subscribe_description(self, subscribe_name) -> list:
        return ""

    def subscribe(self, object, name_subscribe):
        return False

    def remove_my_subscribe(self, object, name_subscribe=False):
        pass

    def clear_all_subscribers(self):
        pass

    def clear_all(self):
        """очистить все подписки"""
        self.subscribe_list = []

    def clear_my_topicks(self, publisher):
        pass
        
                    
    def create_subscribe(self, name_subscribe, publisher, description=""):
        pass

    def push_publish(self, name_subscribe, publisher):
        return False

    def get_subscribers(self, publisher, name_subscribe):
        return False

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    msg = messageBrokerFake()
    data = json.load(open("Devices/JSONDevices/device_config_test.json", "r"))
    fake_inst = install_fake(msg)
    test_block = power_supply(fake_inst)
    test_block.load_json(data)

    for cmd in test_block.commands:
        print(cmd)
        print(getattr(test_block, cmd))
