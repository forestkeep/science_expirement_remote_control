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


class Ui_Set_voltmeter(base_settings_window):
    def __init__(self) -> None:
        super().__init__()

    def setupUi(self):

        self.remove_act()

        self.second_value_limit_label = QtWidgets.QLabel()
        self.second_value_limit_label.setObjectName("second_value_limit_label")

        self.second_limit_enter = QtWidgets.QComboBox()
        self.second_limit_enter.setCurrentText("")
        self.second_limit_enter.setObjectName("second_limit_enter")
        self.second_limit_enter.setEditable(True)

        self.radioButton = QtWidgets.QRadioButton()
        self.radioButton.setObjectName("radioButton")

        self.range_label = QtWidgets.QLabel()
        self.range_label.setObjectName("label_4")

        self.range_enter = QtWidgets.QComboBox()
        self.range_enter.setCurrentText("")
        self.range_enter.setObjectName("type_step_enter")

        self.mode_label = QtWidgets.QLabel()
        self.mode_label.setObjectName("label_5")

        self.type_work_enter = QtWidgets.QComboBox()
        self.type_work_enter.setCurrentText("")
        self.type_work_enter.setObjectName("type_work_enter")

        self.Layout_set_dev_meas.addWidget(self.settings_dev, 0, 0, 1, 3)

        self.Layout_set_dev_meas.addWidget(self.mode_label, 1, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.type_work_enter, 1, 1, 1, 2)

        self.Layout_set_dev_meas.addWidget(self.range_label, 2, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.range_enter, 2, 1, 1, 2)

        self.retranslateUi(self)

    def retranslateUi(self, Set_window):
        _translate = QtCore.QCoreApplication.translate
        Set_window.setWindowTitle(
            _translate("Set_voltemeter", "Настройка вольтметра")
        )
        self.range_label.setText(_translate("Set_voltemeter", "Диапазон"))
        self.mode_label.setText(_translate("Set_voltemeter", "Что измеряем?"))
        self.COM_label.setText(_translate("Set_voltemeter", "COM"))
        self.baud_label.setText(_translate("Set_voltemeter", "Baudrate"))
        self.label_connection.setText(
            _translate("Set_voltemeter", "Параметры подключения")
        )


if __name__ == "__main__":
    import sys

    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = Ui_Set_voltmeter()
    a.setupUi()
    a.show()
    sys.exit(app.exec_())
