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

from PyQt5 import QtCore, QtWidgets

logger = logging.getLogger(__name__)


from Devices.interfase.base_set_window import base_settings_window


class Ui_Set_wave_generator(base_settings_window):
    def __init__(self) -> None:
        super().__init__()

    def setupUi(self):

        # self.remove_act()
        # self.remove_meas()


        self.radioButton = QtWidgets.QCheckBox()
        self.radioButton.setObjectName("radioButton")

        self.label_5 = QtWidgets.QLabel()
        self.label_5.setObjectName("label_5")

        self.type_work_enter = QtWidgets.QComboBox()
        self.type_work_enter.setCurrentText("")
        self.type_work_enter.setObjectName("type_work_enter")
        self.type_work_enter.addItems(["Изменение частоты", "Изменение амплитуды"])

        self.label_6 = QtWidgets.QLabel()
        self.label_6.setObjectName("label_6")

        self.label_2 = QtWidgets.QLabel()
        self.label_2.setObjectName("label_2")

        self.label = QtWidgets.QLabel()
        self.label.setObjectName("label")

        self.start_enter = QtWidgets.QComboBox()
        self.start_enter.setEditable(True)
        self.start_enter.setCurrentText("")
        self.start_enter.setObjectName("start_enter")

        self.stop_enter = QtWidgets.QComboBox()
        self.stop_enter.setEditable(True)
        self.stop_enter.setCurrentText("")
        self.stop_enter.setObjectName("stop_enter")

        self.step_enter = QtWidgets.QComboBox()
        self.step_enter.setEditable(True)

        self.label_8 = QtWidgets.QLabel()
        self.label_7 = QtWidgets.QLabel()
        self.label_9 = QtWidgets.QLabel()
        self.label_10 = QtWidgets.QLabel()
        self.label_11 = QtWidgets.QLabel()

        self.acts_label = QtWidgets.QLabel()
        self.acts_label.setFont(self.font)

        self.current_meas = QtWidgets.QCheckBox()
        self.set_current_meas = QtWidgets.QCheckBox()
        self.voltage_meas = QtWidgets.QCheckBox()
        self.set_voltage_meas = QtWidgets.QCheckBox()

        self.meas_label = QtWidgets.QLabel()
        self.meas_label.setFont(self.font)

        self.Layout_set_dev_act.addWidget(self.acts_label, 0, 0, 1, 1)
        self.Layout_set_dev_act.addWidget(self.label_5, 1, 0, 1, 1)
        self.Layout_set_dev_act.addWidget(self.type_work_enter, 1, 1, 1, 2)

        self.Layout_set_dev_act.addWidget(self.label, 3, 0, 1, 1)
        self.Layout_set_dev_act.addWidget(self.start_enter, 3, 1, 1, 2)

        self.Layout_set_dev_act.addWidget(self.label_2, 4, 0, 1, 1)
        self.Layout_set_dev_act.addWidget(self.stop_enter, 4, 1, 1, 2)

        self.Layout_set_dev_act.addWidget(self.label_6, 5, 0, 1, 1)
        self.Layout_set_dev_act.addWidget(self.step_enter, 5, 1, 1, 2)

        self.Layout_set_dev_act.addWidget(self.label_7, 3, 4, 1, 1)
        self.Layout_set_dev_act.addWidget(self.label_8, 4, 4, 1, 1)
        self.Layout_set_dev_act.addWidget(self.label_9, 5, 4, 1, 1)


        self.Layout_set_dev_act.addWidget(self.radioButton, 7, 1, 1, 1)

        self.Layout_set_dev_meas.addWidget(self.meas_label)
        self.Layout_set_dev_meas.addWidget(self.current_meas, 1, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.set_current_meas, 2, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.voltage_meas, 3, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.set_voltage_meas, 4, 0, 1, 1)

        self.retranslateUi(self)

    def closeEvent(self, event):  # эта функция вызывается при закрытии окна крестиком
        pass

    def retranslateUi(self, Set_power_supply):
        _translate = QtCore.QCoreApplication.translate
        Set_power_supply.setWindowTitle(
            _translate("Set_power_supply", "Настройка генератора сигналов")
        )
        self.radioButton.setText(_translate("Set_power_supply", "Пройти туда-обратно?"))
        # self.label_333.setText(_translate("Set_power_supply", "A"))
        self.label_5.setText(_translate("Set_power_supply", "Режим работы"))
        self.label_6.setText(_translate("Set_power_supply", "Шаг"))
        self.label_2.setText(_translate("Set_power_supply", "Конечное значение"))
        self.label.setText(_translate("Set_power_supply", "Начальное значение"))
        self.label_7.setText(_translate("Set_power_supply", "Гц"))
        self.label_8.setText(_translate("Set_power_supply", "Гц"))
        self.label_9.setText(_translate("Set_power_supply", "Гц"))

        self.meas_label.setText(_translate("Set_power_supply", "Измерения"))
        self.current_meas.setText(_translate("Set_power_supply", "Частота"))
        self.set_current_meas.setText(_translate("Set_power_supply", "Установка частоты"))
        self.voltage_meas.setText(_translate("Set_power_supply", "Амплитуда"))
        self.set_voltage_meas.setText(
            _translate("Set_power_supply", "Установка амплитуды")
        )

        self.acts_label.setText(_translate("Set_power_supply", "Действия"))


if __name__ == "__main__":
    import sys

    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = Ui_Set_wave_generator()
    a.setupUi()
    a.show()
    sys.exit(app.exec_())
