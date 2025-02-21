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

    def __init__(self, available_devices, json_devices = None):
        super().__init__()
        self.setupUi(available_devices, json_devices)

    def setupUi(self, available_devices, json_devices):
        self.setObjectName("Dialog")
        self.resize(330, 243)
        self.setSizeGripEnabled(True)
        
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_2.setContentsMargins(5, 5, 5, 5)
        
        self.label = QtWidgets.QLabel()
        self.font = QtGui.QFont()
        self.font.setPointSize(12)
        self.label.setFont(self.font)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.verticalLayout_2.addWidget(self.label)
        
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.verticalLayout_2.addWidget(self.splitter)
        
        self.widget1 = QtWidgets.QWidget()
        self.widget1_layout = QtWidgets.QVBoxLayout(self.widget1)
        self.widget1_layout.setContentsMargins(10, 10, 10, 10)
        
        self.checkBoxes = []
        self.checkBoxes_create_dev = []
        self.generic_label_dev = []

        self.uncorrect_label = QtWidgets.QLabel()
        self.uncorrect_label.setFont(self.font)
        self.open_new_path = QtWidgets.QPushButton()
        self.widget1_layout.addWidget( self.open_new_path )

        for dev in available_devices:
            checkBox = QtWidgets.QCheckBox(dev)
            checkBox.setFont(self.font)
            self.checkBoxes.append(checkBox)
            self.widget1_layout.addWidget(checkBox)
        
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.widget1_layout.addWidget(separator)

        if json_devices is not None:
            self.reload_json_dev(json_devices)

        self.splitter.addWidget(self.widget1)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        self.verticalLayout_2.addWidget(self.buttonBox)
        
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.send_signal)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)

    def reload_json_dev(self, JSON_devices):
        for but in self.checkBoxes_create_dev:
            but.deleteLater()
        for lab in self.generic_label_dev:
            lab.deleteLater()

        self.checkBoxes_create_dev = []
        self.generic_label_dev = []
        not_correct_devices = []
        if JSON_devices is not None:
            for dev in JSON_devices.values():   
                if dev.status:
                    check = QtWidgets.QCheckBox(dev.name)
                    check.setFont(self.font)
                    self.widget1_layout.addWidget(check)
                    self.checkBoxes_create_dev.append(check) 
                else:
                    not_correct_devices.append(dev)

            self.widget1_layout.addWidget(self.uncorrect_label)

            for dev in not_correct_devices:
                label = QtWidgets.QLabel(dev.name)
                label.setFont(self.font)
                self.widget1_layout.addWidget(label)
                self.generic_label_dev.append(label)
                label.setToolTip(dev.message)

        if not_correct_devices:
            self.uncorrect_label.show()
        else:
            self.uncorrect_label.hide()
        self.widget1_layout.removeWidget( self.open_new_path )
        self.widget1_layout.addWidget( self.open_new_path )

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Мастер создания установки"))
        self.label.setText(_translate("Dialog", "Выберите приборы для установки"))
        self.open_new_path.setText(_translate("Dialog", "Укажите папку с приборами"))
        self.uncorrect_label.setText(_translate("Dialog", "Нераспознанные приборы:"))

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
