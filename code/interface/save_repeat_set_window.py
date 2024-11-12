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

from PyQt5 import QtCore, QtGui, QtWidgets
import logging

logger = logging.getLogger(__name__)


class save_repeat_set_window(QtWidgets.QDialog):
    def setupUi(self, settings_save):
        settings_save.setObjectName("settings_save")
        settings_save.resize(351, 236)
        self.buttonBox = QtWidgets.QDialogButtonBox(settings_save)
        self.buttonBox.setGeometry(QtCore.QRect(10, 200, 331, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok
        )
        self.buttonBox.setObjectName("buttonBox")
        self.horizontalLayoutWidget = QtWidgets.QWidget(settings_save)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(10, 10, 331, 31))
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        font = QtGui.QFont()
        font.setPointSize(9)
        self.type_file_enter = QtWidgets.QComboBox(self.horizontalLayoutWidget)
        self.type_file_enter.setEditable(True)
        self.type_file_enter.setObjectName("type_file_enter")
        self.type_file_enter.addItem("")
        self.type_file_enter.addItem("")
        self.type_file_enter.addItem("")
        font = QtGui.QFont()
        font.setPointSize(9)
        self.way_save_text = QtWidgets.QLineEdit(settings_save)
        self.way_save_text.setGeometry(QtCore.QRect(10, 70, 261, 20))
        self.way_save_text.setObjectName("way_save_text")
        self.way_save_button = QtWidgets.QPushButton(settings_save)
        self.way_save_button.setGeometry(QtCore.QRect(280, 70, 61, 23))
        self.way_save_button.setObjectName("way_save_button")
        self.horizontalLayoutWidget_2 = QtWidgets.QWidget(settings_save)
        self.horizontalLayoutWidget_2.setGeometry(QtCore.QRect(10, 160, 331, 31))
        self.horizontalLayoutWidget_2.setObjectName("horizontalLayoutWidget_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_2)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        font = QtGui.QFont()
        font.setPointSize(9)
        self.repeat_exp_enter = QtWidgets.QComboBox(self.horizontalLayoutWidget_2)
        self.repeat_exp_enter.setEditable(True)
        self.repeat_exp_enter.setObjectName("repeat_exp_enter")
        self.repeat_exp_enter.addItem("")
        self.repeat_exp_enter.addItem("")
        self.repeat_exp_enter.addItem("")
        self.repeat_exp_enter.addItem("")
        self.repeat_exp_enter.addItem("")
        self.repeat_exp_enter.addItem("")
        self.repeat_exp_enter.addItem("")
        self.repeat_exp_enter.addItem("")
        self.repeat_exp_enter.addItem("")
        self.repeat_exp_enter.addItem("")
        self.horizontalLayoutWidget_3 = QtWidgets.QWidget(settings_save)
        self.horizontalLayoutWidget_3.setGeometry(QtCore.QRect(10, 120, 331, 31))
        self.horizontalLayoutWidget_3.setObjectName("horizontalLayoutWidget_3")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_3)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        font = QtGui.QFont()
        font.setPointSize(9)
        self.repeat_measurement_enter = QtWidgets.QComboBox(
            self.horizontalLayoutWidget_3
        )
        self.repeat_measurement_enter.setEditable(True)
        self.repeat_measurement_enter.setObjectName("repeat_measurement_enter")
        self.repeat_measurement_enter.addItem("")
        self.repeat_measurement_enter.addItem("")
        self.repeat_measurement_enter.addItem("")
        self.repeat_measurement_enter.addItem("")
        self.repeat_measurement_enter.addItem("")
        self.repeat_measurement_enter.addItem("")
        self.repeat_measurement_enter.addItem("")
        self.repeat_measurement_enter.addItem("")
        self.repeat_measurement_enter.addItem("")
        self.repeat_measurement_enter.addItem("")
        self.horizontalLayout_3.addWidget(self.repeat_measurement_enter)

        self.retranslateUi(settings_save)
        self.buttonBox.accepted.connect(settings_save.accept)  # type: ignore
        self.buttonBox.rejected.connect(settings_save.reject)  # type: ignore
        QtCore.QMetaObject.connectSlotsByName(settings_save)

    def retranslateUi(self, settings_save):
        _translate = QtCore.QCoreApplication.translate
        settings_save.setWindowTitle(_translate("settings_save", "Сохранение"))
        self.type_file_enter.setCurrentText(_translate("settings_save", "Excel"))
        self.type_file_enter.setItemText(0, "Excel")
        self.type_file_enter.setItemText(1, "Origin Pro")
        self.type_file_enter.setItemText(2, "TXT")
        self.way_save_button.setText(_translate("settings_save", "Путь"))

        self.repeat_exp_enter.setCurrentText("1")
        self.repeat_exp_enter.setItemText(0, "1")
        self.repeat_exp_enter.setItemText(1, "2")
        self.repeat_exp_enter.setItemText(2, "3")
        self.repeat_exp_enter.setItemText(3, "4")
        self.repeat_exp_enter.setItemText(4, "5")
        self.repeat_exp_enter.setItemText(5, "6")
        self.repeat_exp_enter.setItemText(6, "7")
        self.repeat_exp_enter.setItemText(7, "8")
        self.repeat_exp_enter.setItemText(8, "9")
        self.repeat_exp_enter.setItemText(9, "10")

        self.repeat_measurement_enter.setCurrentText("1")
        self.repeat_measurement_enter.setItemText(0, "1")
        self.repeat_measurement_enter.setItemText(1, "2")
        self.repeat_measurement_enter.setItemText(2, "3")
        self.repeat_measurement_enter.setItemText(3, "4")
        self.repeat_measurement_enter.setItemText(4, "5")
        self.repeat_measurement_enter.setItemText(5, "6")
        self.repeat_measurement_enter.setItemText(6, "7")
        self.repeat_measurement_enter.setItemText(7, "8")
        self.repeat_measurement_enter.setItemText(8, "9")
        self.repeat_measurement_enter.setItemText(9, "10")
