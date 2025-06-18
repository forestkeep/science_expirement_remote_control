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

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QApplication

from Devices.Classes import (base_device, ch_response_to_step,
                             not_ready_style_border, ready_style_border,
                             warning_style_border, which_part_in_ch)
from Devices.interfase.Set_oscilloscope_window import setWinOscilloscope
from Devices.osc_rigol_commands import oscRigolCommands

logger = logging.getLogger(__name__)

class oscilloscopeClass(base_device):
    def __init__(self, name, type_connection, installation_class) -> None:
        super().__init__(name, type_connection, installation_class)
        # ===Создать каналы и массив из каналов===
        self.part_ch = (
            which_part_in_ch.only_meas
        )  # указываем, из каких частей состоиит канал в данном приборе
        self.device_type = "oscilloscope"

        # ==========end==========

        # ===Прочие поля, необходимые для прибора

        # ==========end==========

        # ===Создать экземпляр класса окна настроек===
        self.setting_window = setWinOscilloscope()
        # ==========end==========

        # ===установка параметров и настройка редактирования===

        # ==========end==========

    @base_device.base_show_window
    def show_setting_window(self, number_of_channel):

        self.switch_channel(number_of_channel)

        self.key_to_signal_func = False

        # ===Заполнить поля значениями из буфера===
        self.setting_window.check_VMAX.setChecked(
            self.active_channel_meas.dict_buf_parameters["VMAX"]
        )
        self.setting_window.check_VMIN.setChecked(
            self.active_channel_meas.dict_buf_parameters["VMIN"]
        )
        self.setting_window.check_VPP.setChecked(
            self.active_channel_meas.dict_buf_parameters["VPP"]
        )
        self.setting_window.check_VTOP.setChecked(
            self.active_channel_meas.dict_buf_parameters["VTOP"]
        )
        self.setting_window.check_VBASE.setChecked(
            self.active_channel_meas.dict_buf_parameters["VBASE"]
        )
        self.setting_window.check_VAMP.setChecked(
            self.active_channel_meas.dict_buf_parameters["VAMP"]
        )
        self.setting_window.check_VAVG.setChecked(
            self.active_channel_meas.dict_buf_parameters["VAVG"]
        )
        self.setting_window.check_VRMS.setChecked(
            self.active_channel_meas.dict_buf_parameters["VRMS"]
        )
        self.setting_window.check_OVERshoot.setChecked(
            self.active_channel_meas.dict_buf_parameters["OVERshoot"]
        )
        self.setting_window.check_MAREA.setChecked(
            self.active_channel_meas.dict_buf_parameters["MAREA"]
        )
        self.setting_window.check_MPAREA.setChecked(
            self.active_channel_meas.dict_buf_parameters["MPAREA"]
        )
        self.setting_window.check_PREShoot.setChecked(
            self.active_channel_meas.dict_buf_parameters["PREShoot"]
        )
        self.setting_window.check_PERIOD.setChecked(
            self.active_channel_meas.dict_buf_parameters["PERIOD"]
        )
        self.setting_window.check_FREQUENCY.setChecked(
            self.active_channel_meas.dict_buf_parameters["FREQUENCY"]
        )
        self.setting_window.check_RTIME.setChecked(
            self.active_channel_meas.dict_buf_parameters["RTIME"]
        )
        self.setting_window.check_FTIME.setChecked(
            self.active_channel_meas.dict_buf_parameters["FTIME"]
        )
        self.setting_window.check_PWIDth.setChecked(
            self.active_channel_meas.dict_buf_parameters["PWIDth"]
        )
        self.setting_window.check_NWIDth.setChecked(
            self.active_channel_meas.dict_buf_parameters["NWIDth"]
        )
        self.setting_window.check_PDUTy.setChecked(
            self.active_channel_meas.dict_buf_parameters["PDUTy"]
        )
        self.setting_window.check_NDUTy.setChecked(
            self.active_channel_meas.dict_buf_parameters["NDUTy"]
        )
        self.setting_window.check_TVMAX.setChecked(
            self.active_channel_meas.dict_buf_parameters["TVMAX"]
        )
        self.setting_window.check_TVMIN.setChecked(
            self.active_channel_meas.dict_buf_parameters["TVMIN"]
        )
        self.setting_window.check_PSLEWrate.setChecked(
            self.active_channel_meas.dict_buf_parameters["PSLEWrate"]
        )
        self.setting_window.check_NSLEWrate.setChecked(
            self.active_channel_meas.dict_buf_parameters["NSLEWrate"]
        )
        self.setting_window.check_VUPPER.setChecked(
            self.active_channel_meas.dict_buf_parameters["VUPPER"]
        )
        self.setting_window.check_VMID.setChecked(
            self.active_channel_meas.dict_buf_parameters["VMID"]
        )
        self.setting_window.check_VLOWER.setChecked(
            self.active_channel_meas.dict_buf_parameters["VLOWER"]
        )
        self.setting_window.check_VARIance.setChecked(
            self.active_channel_meas.dict_buf_parameters["VARIance"]
        )
        self.setting_window.check_PVRMS.setChecked(
            self.active_channel_meas.dict_buf_parameters["PVRMS"]
        )
        self.setting_window.check_PPULses.setChecked(
            self.active_channel_meas.dict_buf_parameters["PPULses"]
        )
        self.setting_window.check_NPULses.setChecked(
            self.active_channel_meas.dict_buf_parameters["NPULses"]
        )
        self.setting_window.check_PEDGes.setChecked(
            self.active_channel_meas.dict_buf_parameters["PEDGes"]
        )
        self.setting_window.check_NEDGes.setChecked(
            self.active_channel_meas.dict_buf_parameters["NEDGes"]
        )

        for num_ch in range(1, self.total_number_of_channels + 1):
            self.setting_window.checkboxes_ch[num_ch - 1].setChecked(
                self.active_channel_meas.dict_buf_parameters[f"actch{num_ch}"]
            )
            # загрузить осциллограммы для канала или нет
            self.setting_window.check_save_csv[num_ch - 1].setChecked(
                self.active_channel_meas.dict_buf_parameters[f"savech{num_ch}"]
            )

            self.setting_window.com_boxes[num_ch - 1]["Coupling"].setCurrentText(
                self.active_channel_meas.dict_buf_parameters[f"Couplingch{num_ch}"]
            )
            self.setting_window.com_boxes[num_ch - 1]["BW_Limit"].setCurrentText(
                self.active_channel_meas.dict_buf_parameters[f"BW_Limitch{num_ch}"]
            )
            self.setting_window.com_boxes[num_ch - 1]["Probe"].setCurrentText(
                str(self.active_channel_meas.dict_buf_parameters[f"Probech{num_ch}"])
            )
            self.setting_window.com_boxes[num_ch - 1]["Invert"].setCurrentText(
                self.active_channel_meas.dict_buf_parameters[f"Invertch{num_ch}"]
            )

            number, factor = self.get_parts_vscale(
                self.active_channel_meas.dict_buf_parameters[f"vscalech{num_ch}"]
            )
            self.setting_window.vert_scale_boxes[num_ch - 1][0].setCurrentText(number)
            self.setting_window.vert_scale_boxes[num_ch - 1][1].setCurrentText(factor)

        self.setting_window.trig_box["Sourse"].setCurrentText(
            self.active_channel_meas.dict_buf_parameters["Sourse"]
        )
        self.setting_window.trig_box["Type"].setCurrentText(
            self.active_channel_meas.dict_buf_parameters["Type"]
        )
        self.setting_window.trig_box["Slope"].setCurrentText(
            self.active_channel_meas.dict_buf_parameters["Slope"]
        )
        self.setting_window.trig_box["Sweep"].setCurrentText(
            self.active_channel_meas.dict_buf_parameters["Sweep"]
        )

        number, factor = self.get_parts_vscale(
            self.active_channel_meas.dict_buf_parameters["Level"]
        )
        self.setting_window.trig_box["Level"].setCurrentText(number)
        self.setting_window.trig_box["Level_factor"].setCurrentText(factor)

        number, factor = self.get_parts_scale(
            self.active_channel_meas.dict_buf_parameters["scale"]
        )
        self.setting_window.enter_scale_number.setCurrentText(number)
        self.setting_window.enter_scale_factor.setCurrentText(factor)
        # ==========end==========

        self.key_to_signal_func = True
        self._action_when_select_trigger()
        self._is_correct_parameters()
        self.setting_window.show()

    @pyqtSlot()
    @base_device.base_is_correct_parameters
    def _is_correct_parameters(self) -> bool:
        if self.key_to_signal_func:
            def_style = "border: 1px solid rgb(50, 50, 50); border-radius: 5px; QToolTip { color: #ffffff; background-color: rgb(50, 50, 50); border: 1px solid white;}"

            # ===Проверить корректность полей===
            is_trig_correct = self.is_trig_level_correct()
            is_ch_scale_corrects = []
            for i in range(1, self.total_number_of_channels + 1):
                is_ch_scale_corrects.append(self.is_ch_vscale_correct(ch_number=i))

            is_ch_enabled = self.is_ch_enabled()

            is_time_scale_correct = self.is_correct_time_scale()
            # ==========end==========

            # ===Установить цвета полей на основании проверки===

            self.setting_window.trig_box["Level"].setStyleSheet(ready_style_border)
            self.setting_window.trig_box["Level_factor"].setStyleSheet(
                ready_style_border
            )
            self.setting_window.enter_scale_factor.setStyleSheet(ready_style_border)
            self.setting_window.enter_scale_number.setStyleSheet(ready_style_border)

            for i in range(1, self.total_number_of_channels + 1):
                self.setting_window.com_boxes[i - 1]["BW_Limit"].setStyleSheet(
                    ready_style_border
                )
                self.setting_window.com_boxes[i - 1]["Coupling"].setStyleSheet(
                    ready_style_border
                )
                self.setting_window.com_boxes[i - 1]["Probe"].setStyleSheet(
                    ready_style_border
                )
                self.setting_window.com_boxes[i - 1]["Invert"].setStyleSheet(
                    ready_style_border
                )
                self.setting_window.checkboxes_ch[i - 1].setStyleSheet(
                    ready_style_border
                )
                self.setting_window.vert_scale_boxes[i - 1][0].setStyleSheet(
                    ready_style_border
                )
                self.setting_window.vert_scale_boxes[i - 1][1].setStyleSheet(
                    ready_style_border
                )

            for i in range(1, self.total_number_of_channels + 1):
                is_ch_scale_corrects.append(self.is_ch_vscale_correct(ch_number=i))

                if not is_ch_scale_corrects[i - 1]:
                    self.setting_window.vert_scale_boxes[i - 1][0].setStyleSheet(
                        not_ready_style_border
                    )
                    self.setting_window.vert_scale_boxes[i - 1][1].setStyleSheet(
                        not_ready_style_border
                    )

            if not is_trig_correct:
                if not self.is_trig_and_sourse_correct():
                    self.setting_window.trig_box["Level"].setStyleSheet(
                        warning_style_border
                    )
                    self.setting_window.trig_box["Level_factor"].setStyleSheet(
                        warning_style_border
                    )

                    if (
                        self.setting_window.trig_box["Sourse"].currentText()
                        != "Hand control"
                    ):
                        index = (
                            int(self.setting_window.trig_box["Sourse"].currentText()[-1])
                            - 1
                        )
                        self.setting_window.vert_scale_boxes[index][0].setStyleSheet(
                            warning_style_border
                        )
                        self.setting_window.vert_scale_boxes[index][1].setStyleSheet(
                            warning_style_border
                        )

                else:
                    self.setting_window.trig_box["Level"].setStyleSheet(
                        not_ready_style_border
                    )
                    self.setting_window.trig_box["Level_factor"].setStyleSheet(
                        not_ready_style_border
                    )

            for i in range(1, self.total_number_of_channels + 1):
                if self.setting_window.checkboxes_ch[i - 1].isChecked() == False:
                    self.setting_window.vert_scale_boxes[i - 1][0].setStyleSheet(
                        def_style
                    )
                    self.setting_window.vert_scale_boxes[i - 1][1].setStyleSheet(
                        def_style
                    )
                    self.setting_window.com_boxes[i - 1]["BW_Limit"].setStyleSheet(
                        def_style
                    )
                    self.setting_window.com_boxes[i - 1]["Coupling"].setStyleSheet(
                        def_style
                    )
                    self.setting_window.com_boxes[i - 1]["Probe"].setStyleSheet(
                        def_style
                    )
                    self.setting_window.com_boxes[i - 1]["Invert"].setStyleSheet(
                        def_style
                    )

            if not is_ch_enabled:
                for i in range(1, self.total_number_of_channels + 1):
                    self.setting_window.checkboxes_ch[i - 1].setStyleSheet(
                        not_ready_style_border
                    )
            else:
                for i in range(1, self.total_number_of_channels + 1):
                    if self.setting_window.checkboxes_ch[i - 1].isChecked() == False:
                        self.setting_window.checkboxes_ch[i - 1].setStyleSheet(
                            def_style
                        )

            if not is_time_scale_correct:
                self.setting_window.enter_scale_factor.setStyleSheet(
                    not_ready_style_border
                )
                self.setting_window.enter_scale_number.setStyleSheet(
                    not_ready_style_border
                )
            # ==========end==========

            # ===Вернуть ответ на основе проверки параметров
            is_ch_scale_correct = True
            for cor in is_ch_scale_corrects:
                is_ch_scale_correct = is_ch_scale_correct and cor

            return (
                is_trig_correct
                and is_ch_scale_correct
                and is_time_scale_correct
                and is_ch_enabled
            )

            # ==========end==========

        return False

    # ===Методы расчета различных значений===
    def calculate_scale(self, number, factor) -> float:
        if number == "Hand control" or factor == "Hand control":
            return False
        enter_factor = {"s": 1, "ms": 0.001, "us": 0.000001, "ns": 0.000000001}
        scale = round(float(number) * enter_factor[factor] * 1000000000) / 1000000000
        return scale

    def get_parts_scale(self, value) -> str:
        if value == False or value == "Hand control":
            return "Hand control", "Hand control"

        enter_factor = {1: "s", 0.001: "ms", 0.000001: "us", 0.000000001: "ns"}
        numbers = [1, 2, 5, 10, 20, 50, 100, 200, 500]
        dec_factors = [1 / 1000000000, 1 / 1000000, 1 / 1000, 1, 1000]

        number = 1
        dec_factor = 1
        for i in range(len(numbers)):
            for k in range(len(dec_factors)):
                if (
                    float(value)
                    == round(numbers[i] * dec_factors[k] * 1000000000) / 1000000000
                ):
                    number = numbers[i]
                    dec_factor = dec_factors[k]
                    break
        return str(number), enter_factor[dec_factor]

    def calculate_vscale(self, number, factor) -> float:
        if number == "Hand control" or factor == "Hand control":
            return False
        enter_factor = {"kv": 1000, "v": 1, "mv": 0.001}
        return round(float(number) * enter_factor[factor] * 1000) / 1000

    def get_parts_vscale(self, value) -> str:
        if value == False or value == "Hand control":
            return "Hand control", "Hand control"

        enter_factor = {1000: "kv", 1: "v", 0.001: "mv"}
        numbers = [1, 2, 5, 10, 20, 50, 100, 200, 500]
        dec_factors = [1 / 1000, 1, 1000]

        number = 1
        dec_factor = 1
        for i in range(len(numbers)):
            for k in range(len(dec_factors)):
                if value == round(numbers[i] * dec_factors[k] * 1000) / 1000:
                    number = numbers[i]
                    dec_factor = dec_factors[k]
                    break
        return str(number), enter_factor[dec_factor]

    def is_number(self, string):
        try:
            float(string)
            return True
        except ValueError:
            return False

    def is_trig_level_correct(self) -> bool:

        if (
            self.setting_window.trig_box["Sourse"].currentText() != "Hand control"
            and self.setting_window.trig_box["Sourse"].currentText() != ""
        ):
            index = int(self.setting_window.trig_box["Sourse"].currentText()[-1]) - 1
            sourse_scale_num = self.setting_window.vert_scale_boxes[index][
                0
            ].currentText()
            sourse_scale_factor = self.setting_window.vert_scale_boxes[index][
                1
            ].currentText()

        else:
            trig_level_num = self.setting_window.trig_box["Level"].currentText()
            trig_level_factor = self.setting_window.trig_box[
                "Level_factor"
            ].currentText()
            if (
                self.is_number(string=trig_level_num) == False
                and trig_level_num != "Hand control"
            ):
                return False
            if (
                trig_level_num == "Hand control" and trig_level_factor != "Hand control"
            ) or (
                trig_level_num != "Hand control" and trig_level_factor == "Hand control"
            ):
                return False
            return True

        trig_level_num = self.setting_window.trig_box["Level"].currentText()
        trig_level_factor = self.setting_window.trig_box["Level_factor"].currentText()

        if (
            self.is_number(string=trig_level_num) == False
            and trig_level_num != "Hand control"
        ):
            return False

        if (
            trig_level_num == "Hand control" and trig_level_factor != "Hand control"
        ) or (trig_level_num != "Hand control" and trig_level_factor == "Hand control"):
            return False

        sourse_scale = self.calculate_vscale(
            number=sourse_scale_num, factor=sourse_scale_factor
        )
        trig_level = self.calculate_vscale(
            number=trig_level_num, factor=trig_level_factor
        )

        if sourse_scale != False and trig_level != False:
            if trig_level <= sourse_scale * 5 and trig_level >= sourse_scale * (-5):
                return True
            else:
                return False

        elif sourse_scale == False and trig_level == False:
            return True

    def is_trig_and_sourse_correct(self) -> bool:
        """функция для связки корректности показаний триггера и его источника.
        Если она возвращает False, то это означает, что триггер и параметры имсточника нужно подсветить желтым
        """

        if self.setting_window.trig_box["Sourse"].currentText() != "Hand control":
            index = int(self.setting_window.trig_box["Sourse"].currentText()[-1]) - 1
            sourse_scale_num = self.setting_window.vert_scale_boxes[index][
                0
            ].currentText()
            sourse_scale_factor = self.setting_window.vert_scale_boxes[index][
                1
            ].currentText()

        trig_level_num = self.setting_window.trig_box["Level"].currentText()
        trig_level_factor = self.setting_window.trig_box["Level_factor"].currentText()

        if (
            self.is_number(string=trig_level_num) == False
            and trig_level_num != "Hand control"
        ):
            return True

        if (
            trig_level_num == "Hand control" and trig_level_factor != "Hand control"
        ) or (trig_level_num != "Hand control" and trig_level_factor == "Hand control"):
            return True

        sourse_scale = self.calculate_vscale(
            number=sourse_scale_num, factor=sourse_scale_factor
        )
        trig_level = self.calculate_vscale(
            number=trig_level_num, factor=trig_level_factor
        )
        if sourse_scale == False and trig_level != False:
            return False

        elif sourse_scale != False and trig_level == False:
            return False

        elif sourse_scale != False and trig_level != False:
            if trig_level <= sourse_scale * 5 and trig_level >= sourse_scale * (-5):
                return True
            else:
                return False

        else:
            return True

    def is_ch_vscale_correct(self, ch_number) -> bool:
        if self.setting_window.checkboxes_ch[ch_number - 1].isChecked() == True:
            sourse_scale_num = self.setting_window.vert_scale_boxes[ch_number - 1][
                0
            ].currentText()
            sourse_scale_factor = self.setting_window.vert_scale_boxes[ch_number - 1][
                1
            ].currentText()
            vscale = self.calculate_vscale(
                number=sourse_scale_num, factor=sourse_scale_factor
            )
            if vscale == False and (
                sourse_scale_factor != "Hand control"
                or sourse_scale_num != "Hand control"
            ):
                return False
            else:
                probe = self.setting_window.com_boxes[ch_number - 1][
                    "Probe"
                ].currentText()
                if probe != "Hand control" and vscale / 10 > float(probe):
                    return False
        return True

    def is_ch_enabled(self) -> bool:
        for i in range(1, self.total_number_of_channels + 1):
            if self.setting_window.checkboxes_ch[i - 1].isChecked():
                return True
        return False

    def is_correct_time_scale(self) -> bool:
        if (
            self.setting_window.enter_scale_number.currentText() == "Hand control"
            and self.setting_window.enter_scale_factor.currentText() != "Hand control"
            or self.setting_window.enter_scale_number.currentText() != "Hand control"
            and self.setting_window.enter_scale_factor.currentText() == "Hand control"
        ):
            return False
        return True

    # ==========end==========

    @base_device.base_add_parameters_from_window
    def add_parameters_from_window(self):

        if self.key_to_signal_func:
            # ===Записать в буфер значения из полей===
            self.active_channel_meas.dict_buf_parameters["VMAX"] = (
                self.setting_window.check_VMAX.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["VMIN"] = (
                self.setting_window.check_VMIN.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["VPP"] = (
                self.setting_window.check_VPP.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["VTOP"] = (
                self.setting_window.check_VTOP.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["VBASE"] = (
                self.setting_window.check_VBASE.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["VAMP"] = (
                self.setting_window.check_VAMP.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["VAVG"] = (
                self.setting_window.check_VAVG.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["VRMS"] = (
                self.setting_window.check_VRMS.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["OVERshoot"] = (
                self.setting_window.check_OVERshoot.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["MAREA"] = (
                self.setting_window.check_MAREA.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["MPAREA"] = (
                self.setting_window.check_MPAREA.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["PREShoot"] = (
                self.setting_window.check_PREShoot.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["PERIOD"] = (
                self.setting_window.check_PERIOD.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["FREQUENCY"] = (
                self.setting_window.check_FREQUENCY.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["RTIME"] = (
                self.setting_window.check_RTIME.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["FTIME"] = (
                self.setting_window.check_FTIME.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["PWIDth"] = (
                self.setting_window.check_PWIDth.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["NWIDth"] = (
                self.setting_window.check_NWIDth.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["PDUTy"] = (
                self.setting_window.check_PDUTy.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["NDUTy"] = (
                self.setting_window.check_NDUTy.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["TVMAX"] = (
                self.setting_window.check_TVMAX.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["TVMIN"] = (
                self.setting_window.check_TVMIN.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["PSLEWrate"] = (
                self.setting_window.check_PSLEWrate.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["NSLEWrate"] = (
                self.setting_window.check_NSLEWrate.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["VUPPER"] = (
                self.setting_window.check_VUPPER.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["VMID"] = (
                self.setting_window.check_VMID.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["VLOWER"] = (
                self.setting_window.check_VLOWER.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["VARIance"] = (
                self.setting_window.check_VARIance.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["PVRMS"] = (
                self.setting_window.check_PVRMS.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["PPULses"] = (
                self.setting_window.check_PPULses.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["NPULses"] = (
                self.setting_window.check_NPULses.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["PEDGes"] = (
                self.setting_window.check_PEDGes.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["NEDGes"] = (
                self.setting_window.check_NEDGes.isChecked()
            )

            for num in range(1, self.total_number_of_channels + 1):
                self.active_channel_meas.dict_buf_parameters[f"actch{num}"] = (
                    self.setting_window.checkboxes_ch[num - 1].isChecked()
                )
                self.active_channel_meas.dict_buf_parameters[f"savech{num}"] = (
                    self.setting_window.check_save_csv[num - 1].isChecked()
                )
                self.active_channel_meas.dict_buf_parameters[f"Couplingch{num}"] = (
                    self.setting_window.com_boxes[num - 1]["Coupling"].currentText()
                )
                self.active_channel_meas.dict_buf_parameters[f"BW_Limitch{num}"] = (
                    self.setting_window.com_boxes[num - 1]["BW_Limit"].currentText()
                )
                self.active_channel_meas.dict_buf_parameters[f"Probech{num}"] = (
                    self.setting_window.com_boxes[num - 1]["Probe"].currentText()
                )
                self.active_channel_meas.dict_buf_parameters[f"Invertch{num}"] = (
                    self.setting_window.com_boxes[num - 1]["Invert"].currentText()
                )
                self.active_channel_meas.dict_buf_parameters[f"vscalech{num}"] = (
                    self.calculate_vscale(
                        number=self.setting_window.vert_scale_boxes[num - 1][
                            0
                        ].currentText(),
                        factor=self.setting_window.vert_scale_boxes[num - 1][
                            1
                        ].currentText(),
                    )
                )

            self.active_channel_meas.dict_buf_parameters["scale"] = (
                self.calculate_scale(
                    number=self.setting_window.enter_scale_number.currentText(),
                    factor=self.setting_window.enter_scale_factor.currentText(),
                )
            )

            self.active_channel_meas.dict_buf_parameters["Sourse"] = (
                self.setting_window.trig_box["Sourse"].currentText()
            )
            self.active_channel_meas.dict_buf_parameters["Type"] = (
                self.setting_window.trig_box["Type"].currentText()
            )
            self.active_channel_meas.dict_buf_parameters["Slope"] = (
                self.setting_window.trig_box["Slope"].currentText()
            )
            self.active_channel_meas.dict_buf_parameters["Sweep"] = (
                self.setting_window.trig_box["Sweep"].currentText()
            )

            trig_level_num = self.setting_window.trig_box["Level"].currentText()
            trig_level_factor = self.setting_window.trig_box[
                "Level_factor"
            ].currentText()
            self.active_channel_meas.dict_buf_parameters["Level"] = (
                self.calculate_vscale(number=trig_level_num, factor=trig_level_factor)
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
            pass
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.active_channel_meas.dict_settable_parameters = copy.deepcopy(
            self.active_channel_meas.dict_buf_parameters
        )

        is_parameters_correct = True
        if self.dict_buf_parameters["COM"] == QApplication.translate("Device","Нет подключенных портов"):
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
            self.command = oscRigolCommands(device=self)

            # ==========end==========
        else:
            pass

    def set_ch_settings(self, num_ch) -> bool:
        """включает или выключает канал. Если канал включен, передает настройки прибору. Возвращает статус, успешно или не успешно"""
        status = True

        if not self.command.on_off_channel(
            number_ch=num_ch,
            is_enable=self.active_channel_meas.dict_buf_parameters[f"actch{num_ch}"],
        ):
            status = False

        if self.active_channel_meas.dict_buf_parameters[f"actch{num_ch}"] == True:

            if (
                self.active_channel_meas.dict_buf_parameters[f"Couplingch{num_ch}"]
                != "Hand control"
            ):
                if not self.command.set_coupling(
                    number_ch=num_ch,
                    coupling=self.active_channel_meas.dict_buf_parameters[
                        f"Couplingch{num_ch}"
                    ],
                ):
                    status = False

            if (
                self.active_channel_meas.dict_buf_parameters[f"BW_Limitch{num_ch}"]
                != "Hand control"
            ):
                if not self.command.set_BW_limit(
                    ch_number=num_ch,
                    bw_limit=self.active_channel_meas.dict_buf_parameters[
                        f"BW_Limitch{num_ch}"
                    ],
                ):
                    status = False

            if (
                self.active_channel_meas.dict_buf_parameters[f"Probech{num_ch}"]
                != "Hand control"
            ):
                if not self.command.set_probe(
                    ch_number=num_ch,
                    probe=self.active_channel_meas.dict_buf_parameters[
                        f"Probech{num_ch}"
                    ],
                ):
                    status = False

            if (
                self.active_channel_meas.dict_buf_parameters[f"Invertch{num_ch}"]
                != "Hand control"
            ):
                if not self.command.set_invert(
                    ch_number=num_ch,
                    invert=self.active_channel_meas.dict_buf_parameters[
                        f"Invertch{num_ch}"
                    ],
                ):
                    status = False

            if (
                self.active_channel_meas.dict_buf_parameters[f"vscalech{num_ch}"]
                != False
            ):
                if not self.command.set_ch_scale(
                    ch_number=num_ch,
                    scale=self.active_channel_meas.dict_buf_parameters[
                        f"vscalech{num_ch}"
                    ],
                ):
                    status = False

        return status
    
    def action_before_experiment(self, number_of_channel) -> bool:
        self.switch_channel(number_of_channel)
        if not hasattr(self, "command") or not self.command:
            self.command = oscRigolCommands(device=self)

        # ===Действия перед экспериментом, запись настроек в прибор===
        pause = 0.1
        status = True

        for i in range(1, 5):
            if self.set_ch_settings(num_ch=i) == False:
                status = False

        if self.active_channel_meas.dict_buf_parameters["scale"] != False:
            if not self.command.set_scale(
                scale=self.active_channel_meas.dict_buf_parameters["scale"]
            ):
                status = False

        if self.active_channel_meas.dict_buf_parameters["Sourse"] != "Hand control":
            if not self.command.set_trigger_sourse(
                number_ch=self.active_channel_meas.dict_buf_parameters["Sourse"][3]
            ):  # string = Ch-1
                status = False

        if self.active_channel_meas.dict_buf_parameters["Type"] != "Hand control":
            if not self.command.set_trigger_mode(
                mode=self.active_channel_meas.dict_buf_parameters["Type"]
            ):
                status = False

        if self.active_channel_meas.dict_buf_parameters["Slope"] != "Hand control":
            if not self.command.set_trigger_edge_slope(
                slope=self.active_channel_meas.dict_buf_parameters["Slope"]
            ):
                status = False

        if self.active_channel_meas.dict_buf_parameters["Sweep"] != "Hand control":
            if not self.command.set_trigger_sweep(
                sweep=self.active_channel_meas.dict_buf_parameters["Sweep"]
            ):
                status = False

        if self.active_channel_meas.dict_buf_parameters["Level"] != False:
            if not self.command.set_trigger_edge_level(
                level=self.active_channel_meas.dict_buf_parameters["Level"]
            ):
                status = False
        # ==========end==========

        return status

    def meas_parameters(self, parameters):
        """функция поизводит измерения необходимых пааметров в отмеченных каналах и добавляет их в переданный массив"""
        act_channels = []
        for i in range(1, 5):
            if self.active_channel_meas.dict_buf_parameters[f"actch{i}"] == True:
                act_channels.append(i)

        items = [
            "VMAX",
            "VMIN",
            "VPP",
            "VTOP",
            "VBASE",
            "VAMP",
            "VAVG",
            "VRMS",
            "OVERshoot",
            "MAREA",
            "MPAREA",
            "PREShoot",
            "PERIOD",
            "FREQUENCY",
            "RTIME",
            "FTIME",
            "PWIDth",
            "NWIDth",
            "PDUTy",
            "NDUTy",
            "TVMAX",
            "TVMIN",
            "PSLEWrate",
            "NSLEWrate",
            "VUPPER",
            "VMID",
            "VLOWER",
            "VARIance",
            "PVRMS",
            "PPULses",
            "NPULses",
            "PEDGes",
            "NEDGes",
        ]

        for item in items:
            if self.active_channel_meas.dict_buf_parameters[item] == True:
                buf_mas = self.command.get_meas_parameter(
                    parameter=item, channels=act_channels, is_debug=self.is_debug
                )
                for i in range(len(act_channels)):

                    val = [f"{item}{act_channels[i]}=" + str(buf_mas[i])]
                    parameters.append(val)

        return parameters

    def get_wave_form(self, parameters):
        """Считывает осциллограммы в отмеченных каналах"""
        act_channels = []
        for i in range(1, self.total_number_of_channels + 1):
            if (
                self.active_channel_meas.dict_buf_parameters[f"actch{i}"] == True
                and self.active_channel_meas.dict_buf_parameters[f"savech{i}"] == True
            ):
                act_channels.append(i)

        if len(act_channels) > 0:
            if not self.is_debug:
                scale = self.command.get_scale()
                step = self.command.calculate_step_time()
            else:
                scale = 0.0002
                steps = [0.000000002, 0.000000005, 0.00000001, 0.00000002, 0.00000005]
                step = random.choice(steps)
            val = ["scale=" + str(scale)]
            parameters.append(val)
            val = ["step=" + str(step)]
            parameters.append(val)

        status, result = self.command.get_raw_wave_data(
            channels_number=act_channels, is_debug=self.is_debug
        )

        if status == True:
            for num_ch in act_channels:
                val = [f"wavech{num_ch}=" + "|".join(map(str, result[num_ch]))]
                parameters.append(val)
        else:
            for num_ch in act_channels:
                val = [f"wavech{num_ch}=" + "fail"]
                parameters.append(val)
        return parameters, status

    def do_meas(self, ch):
        """прочитать текущие и настроенные значения"""
        self.switch_channel(ch_name=ch.get_name())
        start_time = time.perf_counter()
        parameters = [self.name + " " + str(ch.get_name())]
        message = False
        if ch.get_type() == "meas":
            is_correct = True

            # ===проведение измерений и действия с прибором===
            if not self.is_debug:
                timeout = 10
                #TODO: вынести таймаут в интерфейс пользователя
                self.command.single()
                time_stamp = time.perf_counter()
                while self.command.get_status() != "STOP\n":
                    if time.perf_counter() - time_stamp > timeout:
                        message = QApplication.translate("Device","Остановки по триггеру не произошло, останавливаем принудительно")
                        self.command.stop()
            else:
                pass

            parameters = self.meas_parameters(parameters=parameters)
            parameters, is_correct = self.get_wave_form(parameters=parameters)

            self.command.run()

            # ==========end==========

            if is_correct:
                ans = ch_response_to_step.Step_done
            else:
                # ===Добавить значения fail===
                # ==========end==========

                ans = ch_response_to_step.Step_fail

            return ans, parameters, time.perf_counter() - start_time, message
        return ch_response_to_step.Incorrect_ch, parameters, time.perf_counter() - start_time

    def distribute_parameters(self, input_array):
        """функция делит входной массив с параметрами на массивы с параметрами соответствующих каналов, возвращает словарь, ключи - номера каналов. общие параметры добавляются к каждому массиву"""
        channels = {}
        device, ch = input_array[0].split()
        general_param = []

        for item in input_array[1:]:

            param_str = item[0]
            param_name, param_value = param_str.split("=")

            try:
                channel_number = int(param_name[-1])

                if channel_number not in channels.keys():
                    channels[channel_number] = [f"{device} ch-{channel_number}_meas"]

                channels[channel_number].append([f"{param_name[0:-1]}={param_value}"])
            except:
                general_param.append([item[0]])
        for chann in channels.values():
            chann.extend(general_param)
        return channels
