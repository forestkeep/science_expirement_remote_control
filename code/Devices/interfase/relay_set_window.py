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


class Ui_Set_relay(base_settings_window):
    def __init__(self) -> None:
        super().__init__()

    def setupUi(self):

        self.radioButton = QtWidgets.QRadioButton()
        self.radioButton.setEnabled(True)
        self.radioButton.setObjectName("radioButton")

        self.change_pol_button = QtWidgets.QRadioButton()
        self.change_pol_button.setChecked(True)
        self.change_pol_button.setObjectName("change_pol_button")

        self.acts_label = QtWidgets.QLabel()
        self.acts_label.setFont(self.font)

        self.Layout_set_dev_act.addWidget(self.acts_label, 0, 0, 1, 3)
        self.Layout_set_dev_act.addWidget(self.radioButton, 1, 0, 1, 1)
        self.Layout_set_dev_act.addWidget(self.change_pol_button, 2, 0, 1, 1)

        self.hall1_meas = QtWidgets.QCheckBox()
        self.hall2_meas = QtWidgets.QCheckBox()
        self.hall3_meas = QtWidgets.QCheckBox()
        self.hall4_meas = QtWidgets.QCheckBox()
        self.temp_meas = QtWidgets.QCheckBox()

        self.meas_label = QtWidgets.QLabel()
        self.meas_label.setFont(self.font)

        self.Layout_set_dev_meas.addWidget(self.meas_label)
        self.Layout_set_dev_meas.addWidget(self.hall1_meas, 1, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.hall2_meas, 2, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.hall3_meas, 3, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.hall4_meas, 4, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.temp_meas, 5, 0, 1, 1)

        self.retranslateUi(self)

    def retranslateUi(self, Set_power_supply):
        _translate = QtCore.QCoreApplication.translate
        Set_power_supply.setWindowTitle(_translate("Device", "Relay_set"))
        self.radioButton.setText(
            _translate("Device", "Включение - Выключение")
        )
        self.change_pol_button.setText(
            _translate("Device", "Смена полярности")
        )

        self.acts_label.setText(_translate("Device", "Действия"))
        self.meas_label.setText(_translate("Device", "Измерения"))
        self.hall1_meas.setText(_translate("Device", "Датчик холла 1"))
        self.hall2_meas.setText(_translate("Device", "Датчик холла 2"))
        self.hall3_meas.setText(_translate("Device", "Датчик холла 3"))
        self.hall4_meas.setText(_translate("Device", "Датчик холла 4"))
        self.temp_meas.setText(_translate("Device", "Температурный датчик"))


# sourse_enter -> sourse_act_enter || sourse_meas_enter
# triger_enter -> triger_act_enter || triger_meas_enter

if __name__ == "__main__":
    import sys

    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = Ui_Set_relay()
    a.setupUi()
    a.show()
    sys.exit(app.exec_())
