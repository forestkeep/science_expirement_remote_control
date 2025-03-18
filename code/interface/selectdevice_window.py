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

    def __init__(self,JSON_devices = None):
        super().__init__()
        self.setupUi(JSON_devices)

    def setupUi(self, JSON_devices):

        self.resize(234, 261)
        self.widget = QtWidgets.QWidget(self)
        self.widget.setGeometry(QtCore.QRect(10, 20, 221, 231))
        self.widget.setObjectName("widget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.pushButton = QtWidgets.QPushButton(self.widget)
        self.font = QtGui.QFont()
        self.font.setPointSize(12)
        self.pushButton.setFont(self.font)
        self.verticalLayout.addWidget(self.pushButton)

        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.verticalLayout.addWidget(separator)

        self.generic_buttons = []
        self.generic_label_dev = []

        self.pushButton.clicked.connect(lambda: self.send_signal(self.pushButton.text()))

        self.uncorrect_label = QtWidgets.QLabel()
        self.uncorrect_label.setFont(self.font)

        self.open_new_path = QtWidgets.QPushButton()
        self.verticalLayout.addWidget( self.open_new_path )

        if JSON_devices is not None:
            self.reload_json_dev(JSON_devices)
        
        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)

    def reload_json_dev(self, JSON_devices):
        for but in self.generic_buttons:
            print(but)
            but.deleteLater()
        for lab in self.generic_label_dev:
            lab.deleteLater()
        self.generic_buttons = []
        self.generic_label_dev = []
        not_correct_devices = []
        if JSON_devices is not None:
            for dev in JSON_devices.values():   
                if dev.status:
                    button = QtWidgets.QPushButton(dev.name)
                    button.setFont(self.font)
                    self.verticalLayout.addWidget(button)
                    self.generic_buttons.append(button)
                    button.clicked.connect(lambda checked, key=dev.name: self.send_signal(key)) 
                else:
                    not_correct_devices.append(dev)

            self.verticalLayout.addWidget(self.uncorrect_label)

            for dev in not_correct_devices:
                label = QtWidgets.QLabel(dev.name)
                label.setFont(self.font)
                self.verticalLayout.addWidget(label)
                self.generic_label_dev.append(label)
                label.setToolTip(dev.message)

        if not_correct_devices:
            self.uncorrect_label.show()
        else:
            self.uncorrect_label.hide()
        self.verticalLayout.removeWidget( self.open_new_path )
        self.verticalLayout.addWidget( self.open_new_path )

    def retranslateUi(self, Selectdevice):
        _translate = QtCore.QCoreApplication.translate
        Selectdevice.setWindowTitle(_translate("Selectdevice", "Выбор прибора"))
        self.pushButton.setText("SVPS34")
        self.open_new_path.setText(_translate("Dialog", "Укажите папку с приборами"))
        self.uncorrect_label.setText(_translate("Dialog", "Нераспознанные приборы:"))
     
    def send_signal(self, text):
        self.choised_device = text
        self.accept()
