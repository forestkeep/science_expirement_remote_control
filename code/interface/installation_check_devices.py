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

class installation_Ui_Dialog(QtWidgets.QDialog):
    signal_to_main_window = QtCore.pyqtSignal(list, list)

    def setupUi(self, Dialog, mother_window, available_devices, json_devices = None):
        self.signal_to_main_window.connect(mother_window.message_from_new_installation)
        Dialog.setObjectName("Dialog")
        Dialog.resize(330, 243)
        Dialog.setSizeGripEnabled(True)
        
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout_2.setContentsMargins(5, 5, 5, 5)
        
        self.label = QtWidgets.QLabel()
        font = QtGui.QFont()
        font.setPointSize(14)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.verticalLayout_2.addWidget(self.label)
        
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.verticalLayout_2.addWidget(self.splitter)
        
        self.widget1 = QtWidgets.QWidget()
        self.widget1_layout = QtWidgets.QVBoxLayout(self.widget1)
        self.widget1_layout.setContentsMargins(0, 0, 0, 0)
        
        font = QtGui.QFont()
        font.setPointSize(12)

        self.checkBoxes = []
        self.checkBoxes_create_dev = []

        for dev in available_devices:
            checkBox = QtWidgets.QCheckBox(dev)
            checkBox.setFont(font)
            self.checkBoxes.append(checkBox)
            self.widget1_layout.addWidget(checkBox)

        if json_devices is not None:
            for name in json_devices:   
                checkBox = QtWidgets.QCheckBox(name)
                checkBox.setFont(font)
                self.widget1_layout.addWidget(checkBox)
                self.checkBoxes_create_dev.append(checkBox)

        self.splitter.addWidget(self.widget1)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        self.verticalLayout_2.addWidget(self.buttonBox)
        
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.send_signal)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        
        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Мастер создания установки"))
        self.label.setText(_translate("Dialog", "Выберите приборы для установки"))

    def send_signal(self):
        device_list = []
        json_device_list = []
        for check in self.checkBoxes:
            if check.isChecked():
                device_list.append(check.text())
        for check in self.checkBoxes_create_dev:
            if check.isChecked():
                json_device_list.append(check.text())
        self.signal_to_main_window.emit(device_list, json_device_list)
