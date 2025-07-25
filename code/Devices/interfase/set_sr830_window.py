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

from PyQt5 import QtCore, QtGui, QtWidgets

from Devices.interfase.base_set_window import base_settings_window
logger = logging.getLogger(__name__)

class Ui_Set_sr830(base_settings_window):
    def __init__(self) -> None:
        super().__init__()

    def setupUi(self):
        self.remove_act()

        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_12 = QtWidgets.QLabel()
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_12.setFont(font)
        self.label_12.setObjectName("label_12")
        self.verticalLayout_2.addWidget(self.label_12)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_5 = QtWidgets.QLabel()
        self.label_5.setObjectName("label_5")
        self.horizontalLayout_3.addWidget(self.label_5)
        self.frequency_enter = QtWidgets.QComboBox()
        self.frequency_enter.setCurrentText("")
        self.frequency_enter.setObjectName("frequency_enter")
        self.horizontalLayout_3.addWidget(self.frequency_enter)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_4 = QtWidgets.QLabel()
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_2.addWidget(self.label_4)

        self.amplitude_enter = QtWidgets.QComboBox()
        self.amplitude_enter.setCurrentText("")
        self.amplitude_enter.setObjectName("amplitude_enter")
        self.horizontalLayout_2.addWidget(self.amplitude_enter)

        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.label = QtWidgets.QLabel()

        self.label.setFont(font)
        self.label.setObjectName("label")
        self.verticalLayout_3.addWidget(self.label)
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")

        self.time_const_enter_number = QtWidgets.QComboBox()
        self.time_const_enter_number.setEditable(False)
        self.time_const_enter_number.setObjectName("time_const_enter_number")
        self.time_const_enter_number.addItem("")
        self.horizontalLayout_7.addWidget(self.time_const_enter_number)

        self.time_const_enter_factor = QtWidgets.QComboBox()
        self.time_const_enter_factor.setEditable(False)
        self.time_const_enter_factor.setObjectName("time_const_enter_factor")
        self.time_const_enter_factor.addItem("")
        self.horizontalLayout_7.addWidget(self.time_const_enter_factor)

        self.time_const_enter_decimal_factor = QtWidgets.QComboBox()
        self.time_const_enter_decimal_factor.setStyleSheet("")
        self.time_const_enter_decimal_factor.setEditable(False)
        self.time_const_enter_decimal_factor.setObjectName(
            "time_const_enter_decimal_factor"
        )
        self.time_const_enter_decimal_factor.addItem("")
        self.horizontalLayout_7.addWidget(self.time_const_enter_decimal_factor)

        self.verticalLayout_3.addLayout(self.horizontalLayout_7)
        self.horizontalLayout_10 = QtWidgets.QVBoxLayout()
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.verticalLayout_7 = QtWidgets.QHBoxLayout()
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.label_16 = QtWidgets.QLabel()
        self.label_16.setFont(font)
        self.label_16.setObjectName("label_16")
        self.verticalLayout_7.addWidget(self.label_16)

        self.Filt_slope_enter_level = QtWidgets.QComboBox()
        self.Filt_slope_enter_level.setEditable(False)
        self.Filt_slope_enter_level.setObjectName("Filt_slope_enter_level")
        self.Filt_slope_enter_level.addItem("")
        self.verticalLayout_7.addWidget(self.Filt_slope_enter_level)

        self.horizontalLayout_10.addLayout(self.verticalLayout_7)

        self.verticalLayout_8 = QtWidgets.QHBoxLayout()
        self.verticalLayout_8.setObjectName("verticalLayout_8")

        self.label_17 = QtWidgets.QLabel()
        self.label_17.setFont(font)
        self.label_17.setObjectName("label_17")
        self.verticalLayout_8.addWidget(self.label_17)

        self.SYNK_enter = QtWidgets.QComboBox()
        self.SYNK_enter.setEditable(False)
        self.SYNK_enter.setObjectName("min_enter_7")
        self.SYNK_enter.addItem("")
        self.verticalLayout_8.addWidget(self.SYNK_enter)

        self.horizontalLayout_10.addLayout(self.verticalLayout_8)
        self.verticalLayout_3.addLayout(self.horizontalLayout_10)

        self.verticalLayout_4 = QtWidgets.QVBoxLayout()
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.label_13 = QtWidgets.QLabel()

        self.label_13.setFont(font)
        self.label_13.setObjectName("label_13")
        self.verticalLayout_4.addWidget(self.label_13)
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")

        self.sensitivity_enter_number = QtWidgets.QComboBox()
        self.sensitivity_enter_number.setEditable(False)
        self.sensitivity_enter_number.setObjectName("sensitivity_enter_number")
        self.sensitivity_enter_number.addItem("")
        self.horizontalLayout_8.addWidget(self.sensitivity_enter_number)

        self.sensitivity_enter_factor = QtWidgets.QComboBox()
        self.sensitivity_enter_factor.setEditable(False)
        self.sensitivity_enter_factor.setObjectName("sensitivity_enter_factor")
        self.sensitivity_enter_factor.addItem("")
        self.horizontalLayout_8.addWidget(self.sensitivity_enter_factor)

        self.sensitivity_enter_decimal_factor = QtWidgets.QComboBox()
        self.sensitivity_enter_decimal_factor.setStyleSheet("")
        self.sensitivity_enter_decimal_factor.setEditable(False)
        self.sensitivity_enter_decimal_factor.setObjectName(
            "sensitivity_enter_decimal_factor"
        )
        self.sensitivity_enter_decimal_factor.addItem("")
        self.horizontalLayout_8.addWidget(self.sensitivity_enter_decimal_factor)

        self.verticalLayout_4.addLayout(self.horizontalLayout_8)

        self.verticalLayout_5 = QtWidgets.QVBoxLayout()
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.label_14 = QtWidgets.QLabel()

        self.label_14.setFont(font)
        self.label_14.setObjectName("label_14")
        self.verticalLayout_5.addWidget(self.label_14)
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setSizeConstraint(
            QtWidgets.QLayout.SetDefaultConstraint
        )
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.input_channels_enter = QtWidgets.QComboBox()
        self.input_channels_enter.setEditable(False)
        self.input_channels_enter.setObjectName("input_channels_enter")
        self.input_channels_enter.addItem("")

        self.horizontalLayout_9.addWidget(self.input_channels_enter)
        self.input_type_enter = QtWidgets.QComboBox()
        self.input_type_enter.setEditable(False)
        self.input_type_enter.setObjectName("input_type_enter")
        self.input_type_enter.addItem("")

        self.horizontalLayout_9.addWidget(self.input_type_enter)
        self.connect_ch_enter = QtWidgets.QComboBox()
        self.connect_ch_enter.setStyleSheet("")
        self.connect_ch_enter.setEditable(False)
        self.connect_ch_enter.setObjectName("step_enter_3")
        self.connect_ch_enter.addItem("")
        self.horizontalLayout_9.addWidget(self.connect_ch_enter)
        self.verticalLayout_5.addLayout(self.horizontalLayout_9)

        self.verticalLayout_6 = QtWidgets.QHBoxLayout()
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.label_18 = QtWidgets.QLabel()
        self.label_18.setFont(font)
        self.label_18.setObjectName("label_18")
        self.verticalLayout_6.addWidget(self.label_18)

        self.reserve_enter = QtWidgets.QComboBox()
        self.reserve_enter.setEditable(False)
        self.reserve_enter.setObjectName("reserve_enter")
        self.reserve_enter.addItem("")

        self.verticalLayout_6.addWidget(self.reserve_enter)

        self.verticalLayout_9 = QtWidgets.QHBoxLayout()
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        self.label_19 = QtWidgets.QLabel()
        self.label_19.setFont(font)
        self.label_19.setObjectName("label_19")
        self.verticalLayout_9.addWidget(self.label_19)

        self.filters_enter = QtWidgets.QComboBox()
        self.filters_enter.setEditable(False)
        self.filters_enter.setObjectName("min_enter_5")
        self.filters_enter.addItem("")

        self.verticalLayout_9.addWidget(self.filters_enter)

        self.Layout_set_dev_meas.addLayout(self.verticalLayout_2, 1, 0, 1, 1)
        self.Layout_set_dev_meas.addLayout(self.verticalLayout_4, 2, 0, 1, 1)
        self.Layout_set_dev_meas.addLayout(self.verticalLayout_5, 3, 0, 1, 1)
        self.Layout_set_dev_meas.addLayout(self.verticalLayout_3, 4, 0, 1, 1)
        self.Layout_set_dev_meas.addLayout(self.verticalLayout_6, 5, 0, 1, 1)
        self.Layout_set_dev_meas.addLayout(self.verticalLayout_9, 6, 0, 1, 1)

        self.time_const_enter_number.addItem("")
        # self.time_const_enter_number.addItem("")

        self.time_const_enter_factor.addItem("")
        self.time_const_enter_factor.addItem("")
        # self.time_const_enter_factor.addItem("")

        self.time_const_enter_decimal_factor.addItem("")
        self.time_const_enter_decimal_factor.addItem("")
        self.time_const_enter_decimal_factor.addItem("")
        # self.time_const_enter_decimal_factor.addItem("")

        self.Filt_slope_enter_level.addItem("")
        self.Filt_slope_enter_level.addItem("")
        self.Filt_slope_enter_level.addItem("")
        # self.Filt_slope_enter_level.addItem("")

        self.SYNK_enter.addItem("")
        # self.SYNK_enter.addItem("")

        self.sensitivity_enter_number.addItem("")
        self.sensitivity_enter_number.addItem("")
        # self.sensitivity_enter_number.addItem("")

        self.sensitivity_enter_factor.addItem("")
        self.sensitivity_enter_factor.addItem("")
        # self.sensitivity_enter_factor.addItem("")

        self.sensitivity_enter_decimal_factor.addItem("")
        self.sensitivity_enter_decimal_factor.addItem("")
        self.sensitivity_enter_decimal_factor.addItem("")
        # self.sensitivity_enter_decimal_factor.addItem("")

        self.input_channels_enter.addItem("")
        self.input_channels_enter.addItem("")
        self.input_channels_enter.addItem("")
        # self.input_channels_enter.addItem("")

        self.input_type_enter.addItem("")
        # self.input_type_enter.addItem("")

        self.connect_ch_enter.addItem("")
        # self.connect_ch_enter.addItem("")

        self.reserve_enter.addItem("")
        self.reserve_enter.addItem("")
        # self.reserve_enter.addItem("")

        self.filters_enter.addItem("")
        self.filters_enter.addItem("")
        self.filters_enter.addItem("")
        # self.filters_enter.addItem("")


        self.retranslateUi(self)

        self.time_const_enter_number.setCurrentText("1")
        self.time_const_enter_number.setItemText(0,"1")
        self.time_const_enter_number.setItemText(1,"3")
        self.time_const_enter_factor.setCurrentText(
            "X1"
        )
        self.time_const_enter_factor.setItemText(
            0, "X1"
        )
        self.time_const_enter_factor.setItemText(
            1, "X10"
        )
        self.time_const_enter_factor.setItemText(
            2, "X100"
        )
        self.time_const_enter_decimal_factor.setCurrentText(
            "ks"
        )
        self.time_const_enter_decimal_factor.setItemText(
            0, "ks"
        )
        self.time_const_enter_decimal_factor.setItemText(
            1, "s"
        )
        self.time_const_enter_decimal_factor.setItemText(
            2, "ms"
        )
        self.time_const_enter_decimal_factor.setItemText(
            3, "us"
        )
        self.label_16.setText("Filter slope")
        self.Filt_slope_enter_level.setCurrentText( "6")
        self.Filt_slope_enter_level.setItemText(0,  "6")
        self.Filt_slope_enter_level.setItemText(1,  "12")
        self.Filt_slope_enter_level.setItemText(2,  "18")
        self.Filt_slope_enter_level.setItemText(3,  "24")
        self.label_17.setText("SYNK < 200 Hz")
        self.SYNK_enter.setCurrentText("On")
        self.SYNK_enter.setItemText(0, "On")
        self.SYNK_enter.setItemText(1, "Off")
        self.sensitivity_enter_number.setCurrentText(
             "1"
        )
        self.sensitivity_enter_number.setItemText(
            0,  "1"
        )
        self.sensitivity_enter_number.setItemText(
            1,  "2"
        )
        self.sensitivity_enter_number.setItemText(
            2,  "5"
        )
        self.sensitivity_enter_factor.setCurrentText(
             "X1"
        )
        self.sensitivity_enter_factor.setItemText(
            0,  "X1"
        )
        self.sensitivity_enter_factor.setItemText(
            1,  "X10"
        )
        self.sensitivity_enter_factor.setItemText(
            2,  "X100"
        )
        self.sensitivity_enter_decimal_factor.setCurrentText(
           "V/uA"
        )
        self.sensitivity_enter_decimal_factor.setItemText(
            0, "V/uA"
        )
        self.sensitivity_enter_decimal_factor.setItemText(
            1, "mV/nA"
        )
        self.sensitivity_enter_decimal_factor.setItemText(
            2, "uV/pA"
        )
        self.sensitivity_enter_decimal_factor.setItemText(
            3, "nV/fA"
        )
        self.input_channels_enter.setCurrentText("A")
        self.input_channels_enter.setItemText(0, "A")
        self.input_channels_enter.setItemText(
            1,  "A - B"
        )
        self.input_channels_enter.setItemText(
            2,  "I (10^6)"
        )
        self.input_channels_enter.setItemText(
            3,  "I (10^8)"
        )
        self.input_type_enter.setCurrentText("AC")
        self.input_type_enter.setItemText(0, "AC")
        self.input_type_enter.setItemText(1, "DC")
        self.connect_ch_enter.setCurrentText("float")
        self.connect_ch_enter.setItemText(0, "float")
        self.connect_ch_enter.setItemText(1, "ground")
        self.label_18.setText("Reserve")
        self.reserve_enter.setCurrentText(
            "high reserve"
        )
        self.reserve_enter.setItemText(
            0,"high reserve"
        )
        self.reserve_enter.setItemText(1, "normal")
        self.reserve_enter.setItemText(2, "low noise")
        self.label_19.setText("Filters")
        self.filters_enter.setCurrentText("line")
        self.filters_enter.setItemText(0, "line")
        self.filters_enter.setItemText(1, "2X line")
        self.filters_enter.setItemText(2, "both")
        self.filters_enter.setItemText(3, "out")

    def retranslateUi(self, Set_power_supply):
        _translate = QtCore.QCoreApplication.translate
        Set_power_supply.setWindowTitle(_translate("SR830", "Set sr830"))
        self.label_12.setText(_translate("SR830", "Параметры генератора"))
        self.label_5.setText(_translate("SR830", "Частота(Гц)"))
        self.label_4.setText(_translate("SR830", "Амплитуда(В)"))
        self.label.setText(_translate("SR830", "Временная константа"))
        self.label_13.setText(_translate("SR830", "Чувствительность"))
        self.label_14.setText(_translate("SR830", "Вход сигнала"))

if __name__ == "__main__":
    import sys

    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = Ui_Set_sr830()
    a.setupUi()
    a.show()
    sys.exit(app.exec_())
