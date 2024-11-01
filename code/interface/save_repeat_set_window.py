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
        self.label_18 = QtWidgets.QLabel(self.horizontalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.label_18.setFont(font)
        self.label_18.setObjectName("label_18")
        self.horizontalLayout.addWidget(self.label_18)
        self.type_file_enter = QtWidgets.QComboBox(self.horizontalLayoutWidget)
        self.type_file_enter.setEditable(True)
        self.type_file_enter.setObjectName("type_file_enter")
        self.type_file_enter.addItem("")
        self.type_file_enter.addItem("")
        self.type_file_enter.addItem("")
        self.horizontalLayout.addWidget(self.type_file_enter)
        self.label_19 = QtWidgets.QLabel(settings_save)
        self.label_19.setGeometry(QtCore.QRect(10, 40, 162, 31))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.label_19.setFont(font)
        self.label_19.setObjectName("label_19")
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
        self.label_20 = QtWidgets.QLabel(self.horizontalLayoutWidget_2)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.label_20.setFont(font)
        self.label_20.setObjectName("label_20")
        self.horizontalLayout_2.addWidget(self.label_20)
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
        self.horizontalLayout_2.addWidget(self.repeat_exp_enter)
        self.horizontalLayoutWidget_3 = QtWidgets.QWidget(settings_save)
        self.horizontalLayoutWidget_3.setGeometry(QtCore.QRect(10, 120, 331, 31))
        self.horizontalLayoutWidget_3.setObjectName("horizontalLayoutWidget_3")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_3)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_21 = QtWidgets.QLabel(self.horizontalLayoutWidget_3)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.label_21.setFont(font)
        self.label_21.setObjectName("label_21")
        self.horizontalLayout_3.addWidget(self.label_21)
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
        settings_save.setWindowTitle(_translate("settings_save", "Dialog"))
        self.label_18.setText(
            _translate("settings_save", "Формат сохранения результатов")
        )
        self.type_file_enter.setCurrentText(_translate("settings_save", "Excel"))
        self.type_file_enter.setItemText(0, _translate("settings_save", "Excel"))
        self.type_file_enter.setItemText(1, _translate("settings_save", "Origin Pro"))
        self.type_file_enter.setItemText(2, _translate("settings_save", "TXT"))
        self.label_19.setText(_translate("settings_save", "Куда сохранить результаты?"))
        self.way_save_button.setText(_translate("settings_save", "Путь"))
        self.label_20.setText(
            _translate("settings_save", "Сколько раз повторить эксперимент?")
        )
        self.repeat_exp_enter.setCurrentText(_translate("settings_save", "1"))
        self.repeat_exp_enter.setItemText(0, _translate("settings_save", "1"))
        self.repeat_exp_enter.setItemText(1, _translate("settings_save", "2"))
        self.repeat_exp_enter.setItemText(2, _translate("settings_save", "3"))
        self.repeat_exp_enter.setItemText(3, _translate("settings_save", "4"))
        self.repeat_exp_enter.setItemText(4, _translate("settings_save", "5"))
        self.repeat_exp_enter.setItemText(5, _translate("settings_save", "6"))
        self.repeat_exp_enter.setItemText(6, _translate("settings_save", "7"))
        self.repeat_exp_enter.setItemText(7, _translate("settings_save", "8"))
        self.repeat_exp_enter.setItemText(8, _translate("settings_save", "9"))
        self.repeat_exp_enter.setItemText(9, _translate("settings_save", "10"))
        self.label_21.setText(
            _translate("settings_save", "Сколько измерений делать в каждой точке?")
        )
        self.repeat_measurement_enter.setCurrentText(_translate("settings_save", "1"))
        self.repeat_measurement_enter.setItemText(0, _translate("settings_save", "1"))
        self.repeat_measurement_enter.setItemText(1, _translate("settings_save", "2"))
        self.repeat_measurement_enter.setItemText(2, _translate("settings_save", "3"))
        self.repeat_measurement_enter.setItemText(3, _translate("settings_save", "4"))
        self.repeat_measurement_enter.setItemText(4, _translate("settings_save", "5"))
        self.repeat_measurement_enter.setItemText(5, _translate("settings_save", "6"))
        self.repeat_measurement_enter.setItemText(6, _translate("settings_save", "7"))
        self.repeat_measurement_enter.setItemText(7, _translate("settings_save", "8"))
        self.repeat_measurement_enter.setItemText(8, _translate("settings_save", "9"))
        self.repeat_measurement_enter.setItemText(9, _translate("settings_save", "10"))
