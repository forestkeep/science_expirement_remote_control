import logging

from PyQt5 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)


class Ui_Selectdevice(QtWidgets.QDialog):
    signal_to_main_window = QtCore.pyqtSignal(str)

    def setupUi(self, Selectdevice, mother_window):
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
        self.pushButton.setObjectName("pushButton")
        self.verticalLayout.addWidget(self.pushButton)
        self.pushButton_5 = QtWidgets.QPushButton(self.widget)
        self.pushButton_5.setFont(font)
        self.pushButton_5.setObjectName("pushButton_5")
        self.verticalLayout.addWidget(self.pushButton_5)

        self.pushButton_2 = QtWidgets.QPushButton(self.widget)
        self.pushButton_2.setFont(font)
        self.pushButton_2.setObjectName("pushButton_2")
        self.verticalLayout.addWidget(self.pushButton_2)
        self.pushButton_3 = QtWidgets.QPushButton(self.widget)

        self.pushButton_3.setFont(font)
        self.pushButton_3.setObjectName("pushButton_3")
        self.verticalLayout.addWidget(self.pushButton_3)
        self.pushButton_4 = QtWidgets.QPushButton(self.widget)
        self.pushButton_4.setFont(font)
        self.pushButton_4.setObjectName("pushButton_4")
        self.verticalLayout.addWidget(self.pushButton_4)

        self.retranslateUi(Selectdevice)
        self.set_color(mother_window)
        QtCore.QMetaObject.connectSlotsByName(Selectdevice)

        self.pushButton.clicked.connect(
            lambda: self.send_signal(self.pushButton.text())
        )
        self.pushButton_2.clicked.connect(
            lambda: self.send_signal(self.pushButton_2.text())
        )
        self.pushButton_3.clicked.connect(
            lambda: self.send_signal(self.pushButton_3.text())
        )
        self.pushButton_4.clicked.connect(
            lambda: self.send_signal(self.pushButton_4.text())
        )
        self.pushButton_5.clicked.connect(
            lambda: self.send_signal(self.pushButton_5.text())
        )

    def retranslateUi(self, Selectdevice):
        _translate = QtCore.QCoreApplication.translate
        Selectdevice.setWindowTitle(_translate("Selectdevice", "Выбор прибора"))
        self.pushButton.setText(_translate("Selectdevice", "Maisheng"))
        self.pushButton_5.setText(_translate("Selectdevice", "SVPS34"))
        self.pushButton_2.setText(_translate("Selectdevice", "Polarity Relay"))
        self.pushButton_3.setText(_translate("Selectdevice", "SR830"))
        self.pushButton_4.setText(_translate("Selectdevice", "АКИП"))

    def set_color(self, mother_window):
        if "Maisheng" in mother_window.dict_active_local_devices:
            self.pushButton.setStyleSheet("background-color: rgb(255, 85, 127);")
        else:
            self.pushButton.setStyleSheet("background-color: rgb(85, 255, 127);")
        if "SVPS34" in mother_window.dict_active_local_devices:
            self.pushButton_5.setStyleSheet("background-color: rgb(255, 85, 127);")
        else:
            self.pushButton_5.setStyleSheet("background-color: rgb(85, 255, 127);")
        if "Polarity Relay" in mother_window.dict_active_local_devices:
            self.pushButton_2.setStyleSheet("background-color: rgb(255, 85, 127);")
        else:
            self.pushButton_2.setStyleSheet("background-color: rgb(85, 255, 127);")
        if "SR830" in mother_window.dict_active_local_devices:
            self.pushButton_3.setStyleSheet("background-color: rgb(255, 85, 127);")
        else:
            self.pushButton_3.setStyleSheet("background-color: rgb(85, 255, 127);")
        if "АКИП" in mother_window.dict_active_local_devices:
            self.pushButton_4.setStyleSheet("background-color: rgb(255, 85, 127);")
        else:
            self.pushButton_4.setStyleSheet("background-color: rgb(85, 255, 127);")

    def send_signal(self, text):
        self.signal_to_main_window.emit(text)
