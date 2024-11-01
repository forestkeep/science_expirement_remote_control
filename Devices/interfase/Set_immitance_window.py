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

logger = logging.getLogger(__name__)

from Devices.interfase.base_set_window import base_settings_window


class Ui_Set_immitans(base_settings_window):
    def __init__(self) -> None:
        super().__init__()

    def setupUi(self):

        self.remove_act()

        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)

        self.check_resistance = QtWidgets.QCheckBox("Сопротивление")
        self.check_capacitance = QtWidgets.QCheckBox("Емкость")
        self.check_inductor = QtWidgets.QCheckBox("Индуктивность")
        self.check_impedance = QtWidgets.QCheckBox("Импеданс")
        self.check_current = QtWidgets.QCheckBox("Ток утечки")

        self.shift_label = QtWidgets.QLabel()
        self.shift_enter = QtWidgets.QComboBox()

        self.radioButton = QtWidgets.QRadioButton()
        self.radioButton.setObjectName("radioButton")

        self.level_label = QtWidgets.QLabel()
        self.level_label.setObjectName("label_4")

        self.level_enter = QtWidgets.QComboBox()
        self.level_enter.setCurrentText("")
        self.level_enter.setObjectName("level_enter")

        self.frequency_label = QtWidgets.QLabel()
        self.frequency_label.setObjectName("label_5")

        self.frequency_enter = QtWidgets.QComboBox()
        self.frequency_enter.setCurrentText("")
        self.frequency_enter.setObjectName("freq_enter")

        self.label_what_is_meas = QtWidgets.QLabel()

        self.settings_dev = QtWidgets.QLabel()
        self.settings_dev.setFont(font)

        self.Layout_set_dev_meas.addWidget(self.settings_dev, 0, 0, 1, 3)

        self.Layout_set_dev_meas.addWidget(self.frequency_label, 1, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.frequency_enter, 1, 1, 1, 2)

        self.Layout_set_dev_meas.addWidget(self.level_label, 2, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.level_enter, 2, 1, 1, 2)

        self.Layout_set_dev_meas.addWidget(self.shift_label, 3, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.shift_enter, 3, 1, 1, 2)

        self.Layout_set_dev_meas.addWidget(self.label_what_is_meas, 4, 0, 1, 1)

        self.Layout_set_dev_meas.addWidget(self.check_resistance, 4, 1, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.check_capacitance, 5, 1, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.check_inductor, 6, 1, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.check_impedance, 7, 1, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.check_current, 8, 1, 1, 1)

        self.retranslateUi(self)

    def closeEvent(self, event):
        pass
        # print("окно настройки закрыто крестиком")

    def retranslateUi(self, Set_power_supply):
        _translate = QtCore.QCoreApplication.translate
        Set_power_supply.setWindowTitle(
            _translate("Set_power_supply", "настройка измерителя иммитанса")
        )
        self.level_label.setText(_translate("Set_power_supply", "Уровень"))
        self.frequency_label.setText(_translate("Set_power_supply", "Частота"))

        self.settings_dev.setText(_translate("Set_power_supply", "Настройки прибора"))
        self.shift_label.setText(_translate("Set_power_supply", "Смещение"))
        self.label_what_is_meas.setText(
            _translate("Set_power_supply", "Параметры для измерения")
        )


if __name__ == "__main__":
    import sys

    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = Ui_Set_immitans()
    a.setupUi()
    a.show()
    sys.exit(app.exec_())
