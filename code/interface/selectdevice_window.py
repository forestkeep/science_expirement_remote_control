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
import os
import json

from PyQt5 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)


class Ui_Selectdevice(QtWidgets.QDialog):
    signal_to_main_window = QtCore.pyqtSignal(str)

    def setupUi(self, Selectdevice, mother_window, path_device_templates = None):
        self.signal_to_main_window.connect(
            mother_window.message_from_new_device_local_control
        )
        Selectdevice.setObjectName("Selectdevice")
        Selectdevice.resize(234, 261)
        self.widget = QtWidgets.QWidget(Selectdevice)
        self.widget.setGeometry(QtCore.QRect(10, 20, 221, 231))
        self.widget.setObjectName("widget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.pushButton = QtWidgets.QPushButton(self.widget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.pushButton.setFont(font)
        self.verticalLayout.addWidget(self.pushButton)

        self.generic_buttons = []

        self.retranslateUi(Selectdevice)
        QtCore.QMetaObject.connectSlotsByName(Selectdevice)

        self.pushButton.clicked.connect(lambda: self.send_signal(self.pushButton.text()))

        if path_device_templates is not None:
            print(path_device_templates)
            self.dict_device_templates = mother_window.search_devices_json(path_device_templates)
            for name in self.dict_device_templates.keys():   
                button = QtWidgets.QPushButton(name)
                button.setFont(font)
                self.verticalLayout.addWidget(button)
                self.generic_buttons.append(button)

                button.clicked.connect(lambda checked, key=name: self.send_signal(self.dict_device_templates[key])) 

    def retranslateUi(self, Selectdevice):
        _translate = QtCore.QCoreApplication.translate
        Selectdevice.setWindowTitle(_translate("Selectdevice", "Выбор прибора"))
        self.pushButton.setText("SVPS34")
     
    def send_signal(self, text):
        self.signal_to_main_window.emit(text)

