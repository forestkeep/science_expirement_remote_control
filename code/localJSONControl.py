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

import sys
import re
from PyQt5 import QtWidgets

class localDeviceControl(QtWidgets.QWidget):
    def __init__(self, dev_file):
        super().__init__()
        self.device_data = dev_file
        self.setWindowTitle(self.get_device_name())
        self.init_ui()

    def get_device_name(self):
        device_type = self.device_data.json_data["device_type"]
        device_name = self.device_data.json_data["device_name"]
        return f"{device_type} - {device_name}"

    def init_ui(self):
        number_channels = self.device_data.json_data["number_channels"]
        self.tabs = QtWidgets.QTabWidget(self)
        for i in range(1):
            channel_tab = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(channel_tab)
            commands = self.device_data.json_data["commands"]
            command_keys = list(commands.keys())

            command_group_with_params = []
            command_group_without_params = []

            for index, key in enumerate(command_keys):
                command_group = QtWidgets.QGroupBox(key.replace("_", " ") )
                command_layout = QtWidgets.QVBoxLayout(command_group)
                
                command_info = commands[key]
                has_param = self.extract_parameters(command_info['command'])
                
                if has_param:
                    for param_name in has_param:
                        spin_box = QtWidgets.QSpinBox()
                        spin_box.setPrefix(f"{param_name}: ")
                        command_layout.addWidget(spin_box)
                    command_group_with_params.append(command_group)
                else:
                    command_group_without_params.append(command_group)

                button = QtWidgets.QPushButton('Execute')
                button.clicked.connect(lambda ch, cmd=key, spin=spin_box if has_param else None: self.execute_command(cmd, spin))
                command_layout.addWidget(button)

                result_label = QtWidgets.QLabel("Result:")
                command_layout.addWidget(result_label)


            current_vert_lay = QtWidgets.QVBoxLayout()
            command_group_without_params.extend(command_group_with_params)
            for index, command_group in enumerate(command_group_without_params):
                current_vert_lay.addWidget(command_group)
                if (index+1) % 4 == 0 and index != 0:
                    layout.addLayout(current_vert_lay)
                    current_vert_lay = QtWidgets.QVBoxLayout()

            self.tabs.addTab(channel_tab, f"Channel {i}")

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def extract_parameters(self, input_string):
        return re.findall(r'\{(.*?)\}', input_string)

    def execute_command(self, command_key, spin_box=None):
        command = self.device_data.json_data["commands"][command_key]
        command_str = command["command"]
        if spin_box:
            parameter_value = spin_box.value()
            parameters = {}
            has_param = self.extract_parameters(command_str)
            for param in has_param:
                parameters[param] = parameter_value
            command_str = command_str.format(**parameters)
        
        print(f"Executing command: {command_str}")

if __name__ == "__main__":
        app = QtWidgets.QApplication(sys.argv)
        window = localDeviceControl('device_config_test.json')
        window.resize(800, 600)
        window.show()
        sys.exit(app.exec_())