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
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Devices.Classes import base_ch
from Devices.oscilloscope import oscilloscopeClass


class chMeasOscilloscope(base_ch):
    def __init__(self, number, device_class, total_number_of_channels) -> None:
        super().__init__(number, ch_type="meas", device_class=device_class)

        self.base_duration_step = 2  # у каждого канала каждого прибора есть свое время. необходимое для выполнения шага

        self.dict_buf_parameters["VMAX"] = False
        self.dict_buf_parameters["VMIN"] = False
        self.dict_buf_parameters["VPP"] = False
        self.dict_buf_parameters["VTOP"] = False
        self.dict_buf_parameters["VBASE"] = False
        self.dict_buf_parameters["VAMP"] = False
        self.dict_buf_parameters["VAVG"] = False
        self.dict_buf_parameters["VRMS"] = False
        self.dict_buf_parameters["OVERshoot"] = False
        self.dict_buf_parameters["MAREA"] = False
        self.dict_buf_parameters["MPAREA"] = False
        self.dict_buf_parameters["PREShoot"] = False
        self.dict_buf_parameters["PERIOD"] = False
        self.dict_buf_parameters["FREQUENCY"] = False
        self.dict_buf_parameters["RTIME"] = False
        self.dict_buf_parameters["FTIME"] = False
        self.dict_buf_parameters["PWIDth"] = False
        self.dict_buf_parameters["NWIDth"] = False
        self.dict_buf_parameters["PDUTy"] = False
        self.dict_buf_parameters["NDUTy"] = False
        self.dict_buf_parameters["TVMAX"] = False
        self.dict_buf_parameters["TVMIN"] = False
        self.dict_buf_parameters["PSLEWrate"] = False
        self.dict_buf_parameters["NSLEWrate"] = False
        self.dict_buf_parameters["VUPPER"] = False
        self.dict_buf_parameters["VMID"] = False
        self.dict_buf_parameters["VLOWER"] = False
        self.dict_buf_parameters["VARIance"] = False
        self.dict_buf_parameters["PVRMS"] = False
        self.dict_buf_parameters["PPULses"] = False
        self.dict_buf_parameters["NPULses"] = False
        self.dict_buf_parameters["PEDGes"] = False
        self.dict_buf_parameters["NEDGes"] = False
        self.dict_buf_parameters["scale"] = "Hand control"
        self.dict_buf_parameters["Sourse"] = "Hand control"
        self.dict_buf_parameters["Type"] = "Hand control"
        self.dict_buf_parameters["Slope"] = "Hand control"
        self.dict_buf_parameters["Sweep"] = "Hand control"
        self.dict_buf_parameters["Level"] = "Hand control"

        # активен канал или нет
        for num_ch in range(1, total_number_of_channels + 1):
            self.dict_buf_parameters[f"actch{num_ch}"] = False
            # загрузить осциллограммы для канала или нет
            self.dict_buf_parameters[f"savech{num_ch}"] = False
            # загрузить осциллограммы для канала или нет
            self.dict_buf_parameters[f"savech{num_ch}"] = False
            self.dict_buf_parameters[f"Couplingch{num_ch}"] = "Hand control"
            self.dict_buf_parameters[f"BW_Limitch{num_ch}"] = "Hand control"
            self.dict_buf_parameters[f"Probech{num_ch}"] = "Hand control"
            self.dict_buf_parameters[f"Invertch{num_ch}"] = "Hand control"
            self.dict_buf_parameters[f"vscalech{num_ch}"] = "Hand control"

        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)


class DS1104Z(oscilloscopeClass):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "serial", installation_class)
        # ===Создать каналы и массив из каналов===
        self.total_number_of_channels = 4  # указать число каналов в приборе
        self.ch1_meas = chMeasOscilloscope(1, self, self.total_number_of_channels)
        self.channels = self.create_channel_array()

        # ==========end==========

        # ===Прочие поля, необходимые для прибора

        # ==========end==========

        # ===Создать экземпляр класса окна настроек===
        # ==========end==========
        self.base_settings_window()

        # ===установка параметров и настройка редактирования===

        # ==========end==========
