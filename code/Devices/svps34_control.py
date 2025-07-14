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

import datetime
import sys
from enum import Enum

import qdarktheme
import serial
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

class On_Off_state(Enum):
    On = True
    Off = False

class state_device(Enum):
    Remote = True
    Hand = False

class channel:
    def __init__(self, number) -> None:
        self.number = number
        self.current_current_value = 0
        self.channel_status = On_Off_state.Off
        self.relay_status = On_Off_state.Off

    def set_current(self, value):
        self.current_current_value = value

    def set_channel_status(self, state):
        self.channel_status = state

    def set_relay_status(self, state):
        self.relay_status = state

    def get_relay_status(self):
        return self.relay_status

    def get_channel_status(self):
        return self.channel_status

    def toggle_channel_state(self):
        if self.channel_status == On_Off_state.Off:
            self.channel_status = On_Off_state.On
        else:
            self.channel_status = On_Off_state.Off

    def toggle_relay_state(self):
        if self.relay_status_status == On_Off_state.Off:
            self.relay_status_status = On_Off_state.On
        else:
            self.relay_status_status = On_Off_state.Off


class device:
    """device parameters"""

    def __init__(self, name, com_port, baudrate, window) -> None:
        self.name = name
        self.ser = serial.Serial(com_port, baudrate=baudrate, timeout=0.2)
        self.timtemp = QTimer()
        self.timtemp.timeout.connect(lambda: self.get_temperature())
        self.timtemp.start(1000)
        self.ui = window

        self.status = state_device.Hand
        self.current_temperature = ""

        self.ch1 = channel(1)
        self.ch2 = channel(2)
        self.ch3 = channel(3)
        self.ch4 = channel(4)
        self.ch5 = channel(5)
        self.ch6 = channel(6)
        self.ch7 = channel(7)
        self.channels = [
            self.ch1,
            self.ch2,
            self.ch3,
            self.ch4,
            self.ch5,
            self.ch6,
            self.ch7,
        ]

    def check_connect(self):
        self.ser.write(b"status")
        self.ui.log.append(
            str(datetime.datetime.now().strftime("%H:%M:%S")) + " send: " + "status"
        )
        answer = str(self.ser.read(50))
        self.ui.log.append(
            str(datetime.datetime.now().strftime("%H:%M:%S")) + " receive: " + answer
        )
        if answer.find("Remote control") != -1 or answer.find("Hand control") != -1:
            # self.status = state_device.Connect
            return True
        else:
            return False

    def get_temperature(self):
        self.ser.write(b"temp")
        # ui.log.append(str(datetime.datetime.now().strftime("%H:%M:%S"))+" send: " + "temp")
        answer = str(self.ser.read(50))
        # ui.log.append(str(datetime.datetime.now().strftime("%H:%M:%S"))+" receive: " + answer)
        try:
            end_index = answer.find("C")
            temp = float(answer[end_index - 6 : end_index - 1])
            self.ui.temp_label.setText("Temperature = " + str(temp) + "C")
            return temp
        except:
            return False

    def remote_connect(self):

        if self.check_connect():
            self.ser.write(b"status")
            self.ui.log.append(
                str(datetime.datetime.now().strftime("%H:%M:%S")) + " send: status"
            )
            answer = str(self.ser.read(50))
            self.ui.log.append(
                str(datetime.datetime.now().strftime("%H:%M:%S"))
                + " receive: "
                + answer
            )
            if self.status == state_device.Hand:
                if answer.find("Hand control") != -1:
                    self.ser.write(b"remote")
                    self.ui.log.append(
                        str(datetime.datetime.now().strftime("%H:%M:%S"))
                        + " send: remote"
                    )
                    answer2 = str(self.ser.read(50))
                    self.ui.log.append(
                        str(datetime.datetime.now().strftime("%H:%M:%S"))
                        + " receive: "
                        + answer2
                    )
                    if answer2.find("Remote control enable") != -1:
                        self.status = state_device.Remote
                        return True
                    else:
                        return False
                else:
                    self.status = state_device.Remote
                    return True
            elif self.status == state_device.Remote:
                if answer.find("Remote control") != -1:
                    self.ser.write(b"hand")
                    self.ui.log.append(
                        str(datetime.datetime.now().strftime("%H:%M:%S"))
                        + " send: hand"
                    )
                    answer2 = str(self.ser.read(50))
                    self.ui.log.append(
                        str(datetime.datetime.now().strftime("%H:%M:%S"))
                        + " receive: "
                        + answer2
                    )
                    if answer2.find("Remote control disable") != -1:
                        self.status = state_device.Hand
                        return True
                    else:
                        return False
                else:
                    self.status = state_device.Hand
                    return True
        else:
            return False

    def get_state(self):
        return self.status

    def button_action(self, number):
        if self.channels[number - 1].get_channel_status() == On_Off_state.Off:
            self.ser.write(bytes("C" + str(number) + "N", encoding="utf8"))
            self.ui.log.append(
                str(datetime.datetime.now().strftime("%H:%M:%S"))
                + " send: "
                + "C"
                + str(number)
                + "N"
            )
            answer = str(self.ser.read(20))
            self.ui.log.append(
                str(datetime.datetime.now().strftime("%H:%M:%S"))
                + " receive: "
                + answer
            )
            if answer.find("C" + str(number) + "N - OK") != -1:
                self.channels[number - 1].channel_status = On_Off_state.On
                return self.channels[number - 1].channel_status
            else:
                return False
        else:
            self.ser.write(bytes("C" + str(number) + "F", encoding="utf8"))
            self.ui.log.append(
                str(datetime.datetime.now().strftime("%H:%M:%S"))
                + " send: "
                + "C"
                + str(number)
                + "F"
            )
            answer = str(self.ser.read(20))
            self.ui.log.append(
                str(datetime.datetime.now().strftime("%H:%M:%S"))
                + " receive: "
                + answer
            )
            if answer.find("C" + str(number) + "F - OK") != -1:
                self.channels[number - 1].channel_status = On_Off_state.Off
                return self.channels[number - 1].channel_status
            else:
                return False

    def relay_action(self, number):
        if self.channels[number - 1].get_relay_status() == On_Off_state.Off:
            self.ser.write(bytes("R" + str(number) + "N", encoding="utf8"))
            self.ui.log.append(
                str(datetime.datetime.now().strftime("%H:%M:%S"))
                + " send: "
                + "R"
                + str(number)
                + "N"
            )
            answer = str(self.ser.read(20))
            self.ui.log.append(
                str(datetime.datetime.now().strftime("%H:%M:%S"))
                + " receive: "
                + answer
            )
            if answer.find("R" + str(number) + "N - OK") != -1:
                self.channels[number - 1].relay_status = On_Off_state.On
                return self.channels[number - 1].relay_status
            else:
                return False
        else:
            self.ser.write(bytes("R" + str(number) + "F", encoding="utf8"))
            self.ui.log.append(
                str(datetime.datetime.now().strftime("%H:%M:%S"))
                + " send: "
                + "R"
                + str(number)
                + "F"
            )
            answer = str(self.ser.read(20))
            self.ui.log.append(
                str(datetime.datetime.now().strftime("%H:%M:%S"))
                + " receive: "
                + answer
            )
            if answer.find("R" + str(number) + "F - OK") != -1:
                self.channels[number - 1].relay_status = On_Off_state.Off
                return self.channels[number - 1].relay_status
            else:
                return False

class Ui_SVPS34_control(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(Ui_SVPS34_control, self).__init__(parent)
        self.setupUi()

    def setupUi(self):
        # super.__init__()
        self.is_device_connect = False
        self.connect_devices = []
        self.setObjectName("SVPS34_control")
        self.resize(912, 638)
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.frame_2 = QtWidgets.QFrame(self.centralwidget)
        self.frame_2.setGeometry(QtCore.QRect(0, 410, 931, 211))
        self.frame_2.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_2.setObjectName("frame_2")
        self.frame = QtWidgets.QFrame(self.frame_2)
        self.frame.setGeometry(QtCore.QRect(20, 10, 171, 161))
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.verticalLayoutWidget_2 = QtWidgets.QWidget(self.frame)
        self.verticalLayoutWidget_2.setGeometry(QtCore.QRect(20, 20, 126, 141))
        self.verticalLayoutWidget_2.setObjectName("verticalLayoutWidget_2")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.verticalLayoutWidget_2)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.scan_button = QtWidgets.QPushButton(self.verticalLayoutWidget_2)
        self.scan_button.setMouseTracking(False)
        self.scan_button.setObjectName("scan_button")
        self.verticalLayout_2.addWidget(self.scan_button)
        self.comportslist = QtWidgets.QComboBox(self.verticalLayoutWidget_2)
        self.comportslist.setObjectName("comportslist")
        self.verticalLayout_2.addWidget(self.comportslist)
        self.comportslist_2 = QtWidgets.QComboBox(self.verticalLayoutWidget_2)
        self.comportslist_2.setObjectName("comportslist_2")
        self.verticalLayout_2.addWidget(self.comportslist_2)
        self.connect_button = QtWidgets.QPushButton(self.verticalLayoutWidget_2)
        self.connect_button.setMouseTracking(False)
        self.connect_button.setObjectName("connect_button")
        self.verticalLayout_2.addWidget(self.connect_button)
        self.label_2 = QtWidgets.QLabel(self.frame_2)
        self.label_2.setGeometry(QtCore.QRect(20, 175, 881, 31))
        self.label_2.setObjectName("label_2")

        self.log = QtWidgets.QTextEdit(self.frame_2)
        self.log.setGeometry(QtCore.QRect(200, 20, 701, 151))
        self.log.setObjectName("lineEdit_2")
        self.log.setReadOnly(True)

        self.label = QtWidgets.QLabel(self.frame_2)
        self.label.setGeometry(QtCore.QRect(200, 0, 511, 16))
        self.label.setObjectName("label")
        self.lcdNumber = QtWidgets.QLCDNumber(self.centralwidget)
        self.lcdNumber.setGeometry(QtCore.QRect(10, 10, 281, 121))
        self.lcdNumber.setObjectName("lcdNumber")
        self.common_button = QtWidgets.QPushButton(self.centralwidget)
        self.common_button.setGeometry(QtCore.QRect(20, 270, 81, 41))
        self.common_button.setMouseTracking(False)
        self.common_button.setObjectName("common_button")
        self.horizontalLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(150, 260, 751, 61))
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.ch1 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.ch1.setMouseTracking(False)
        self.ch1.setObjectName("ch1")
        self.horizontalLayout.addWidget(self.ch1)
        self.ch2 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.ch2.setMouseTracking(False)
        self.ch2.setObjectName("ch2")
        self.horizontalLayout.addWidget(self.ch2)
        self.ch3 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.ch3.setMouseTracking(False)
        self.ch3.setObjectName("ch3")
        self.horizontalLayout.addWidget(self.ch3)
        self.ch4 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.ch4.setMouseTracking(False)
        self.ch4.setObjectName("ch4")
        self.horizontalLayout.addWidget(self.ch4)
        self.ch5 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.ch5.setMouseTracking(False)
        self.ch5.setObjectName("ch5")
        self.horizontalLayout.addWidget(self.ch5)
        self.ch6 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.ch6.setMouseTracking(False)
        self.ch6.setObjectName("ch6")
        self.horizontalLayout.addWidget(self.ch6)
        self.ch7 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.ch7.setMouseTracking(False)
        self.ch7.setObjectName("ch7")
        self.horizontalLayout.addWidget(self.ch7)
        self.horizontalLayoutWidget_2 = QtWidgets.QWidget(self.centralwidget)
        self.horizontalLayoutWidget_2.setGeometry(QtCore.QRect(150, 320, 751, 51))
        self.horizontalLayoutWidget_2.setObjectName("horizontalLayoutWidget_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget_2)
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.rel1 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.rel1.setMouseTracking(False)
        self.rel1.setObjectName("rel1")
        self.horizontalLayout_2.addWidget(self.rel1)
        self.rel2 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.rel2.setMouseTracking(False)
        self.rel2.setObjectName("rel2")
        self.horizontalLayout_2.addWidget(self.rel2)
        self.rel3 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.rel3.setMouseTracking(False)
        self.rel3.setObjectName("rel3")
        self.horizontalLayout_2.addWidget(self.rel3)
        self.rel4 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.rel4.setMouseTracking(False)
        self.rel4.setObjectName("rel4")
        self.horizontalLayout_2.addWidget(self.rel4)
        self.rel5 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.rel5.setMouseTracking(False)
        self.rel5.setObjectName("rel5")
        self.horizontalLayout_2.addWidget(self.rel5)
        self.rel6 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.rel6.setMouseTracking(False)
        self.rel6.setObjectName("rel6")
        self.horizontalLayout_2.addWidget(self.rel6)
        self.rel7 = QtWidgets.QPushButton(self.horizontalLayoutWidget_2)
        self.rel7.setMouseTracking(False)
        self.rel7.setObjectName("rel7")
        self.horizontalLayout_2.addWidget(self.rel7)
        self.common_rel_button = QtWidgets.QPushButton(self.centralwidget)
        self.common_rel_button.setGeometry(QtCore.QRect(20, 320, 81, 41))
        self.common_rel_button.setMouseTracking(False)
        self.common_rel_button.setObjectName("common_rel_button")
        self.remote_button = QtWidgets.QPushButton(self.centralwidget)
        self.remote_button.setGeometry(QtCore.QRect(300, 50, 81, 41))
        self.remote_button.setMouseTracking(False)
        self.remote_button.setObjectName("remote_button")

        self.temp_label = QtWidgets.QLabel(self.centralwidget)
        self.temp_label.setGeometry(QtCore.QRect(700, 70, 201, 41))
        # self.temp_label.setStyleSheet("font: 75 14pt \"MS Shell Dlg 2\";")
        self.temp_label.setObjectName("temp_label")
        self.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)
        self.write_boud_rate(
            (
                "50",
                "75",
                "110",
                "150",
                "300",
                "600",
                "1200",
                "2400",
                "4800",
                "9600",
                "19200",
                "38400",
                "57600",
                "115200",
            )
        )

        self.retranslateUi(self)
        QtCore.QMetaObject.connectSlotsByName(self)

        self.functions()

    def functions(self):

        self.scan_button.clicked.connect(lambda: self.scan_active_com_ports())
        self.connect_button.clicked.connect(lambda: self.connect_to_com_port())

        self.ch1.clicked.connect(lambda: self.click_channel_button(1))
        self.ch2.clicked.connect(lambda: self.click_channel_button(2))
        self.ch3.clicked.connect(lambda: self.click_channel_button(3))
        self.ch4.clicked.connect(lambda: self.click_channel_button(4))
        self.ch5.clicked.connect(lambda: self.click_channel_button(5))
        self.ch6.clicked.connect(lambda: self.click_channel_button(6))
        self.ch7.clicked.connect(lambda: self.click_channel_button(7))
        self.rel1.clicked.connect(lambda: self.click_relay_button(1))
        self.rel2.clicked.connect(lambda: self.click_relay_button(2))
        self.rel3.clicked.connect(lambda: self.click_relay_button(3))
        self.rel4.clicked.connect(lambda: self.click_relay_button(4))
        self.rel5.clicked.connect(lambda: self.click_relay_button(5))
        self.rel6.clicked.connect(lambda: self.click_relay_button(6))
        self.rel7.clicked.connect(lambda: self.click_relay_button(7))
        self.remote_button.clicked.connect(lambda: self.remote_connect())

    def remote_connect(self):
        if self.is_device_connect:
            self.connect_devices[0].remote_connect()
            if self.connect_devices[0].get_state() == state_device.Hand:
                self.remote_button.setStyleSheet(
                    "background-color: rgb(206, 206, 206);"
                )
                self.label_2.setText(
                    QApplication.translate("Device","Устройство SVPS34 подключено к порту") + " "
                    + str(self.connect_devices[0].ser.name) + " "
                    + QApplication.translate("Device","в режиме ручного управления")
                )
            else:
                self.remote_button.setStyleSheet("background-color: rgb(85, 255, 127);")
                self.label_2.setText(
                    QApplication.translate("Device","Устройство SVPS34 подключено к порту") + " "
                    + str(self.connect_devices[0].ser.name) + " "
                    + QApplication.translate("Device","в режиме удаленного управления")
                )

    def get_temperature(self):
        if self.is_device_connect:
            temp = self.connect_devices[0].get_temperature()
            if temp != False:
                self.temp_label.setText("Temperature = " + str(temp) + "C")

    def connect_to_com_port(self):
        try:
            com = self.comportslist.currentText()
            baudrate = self.comportslist_2.currentText()
            SVPS34 = device("SVPS34", com, baudrate, self)
            if SVPS34.check_connect() and not self.is_device_connect:
                self.connect_devices.append(
                    SVPS34
                )  # добавляем в массив подключенных устройств svps34
                if self.connect_devices[0].status == state_device.Remote:
                    self.label_2.setText(
                    QApplication.translate("Device","Устройство SVPS34 подключено к порту") + " "
                    + str(self.connect_devices[0].ser.name) + " "
                    + QApplication.translate("Device","в режиме удаленного управления")
                    )
                else:
                    self.label_2.setText(
                    QApplication.translate("Device","Устройство SVPS34 подключено к порту") + " "
                    + str(self.connect_devices[0].ser.name) + " "
                    + QApplication.translate("Device","в режиме ручного управления")
                    )
                # self.label_2.setStyleSheet("background-color: rgb(85, 255, 127);")
                self.is_device_connect = True
        except:
            self.log.append("fail connect to svps34: check device")

    def click_channel_button(self, number_of_channel):
        if self.is_device_connect:
            answer = self.connect_devices[0].button_action(number_of_channel)
            if answer != False:
                if answer == On_Off_state.On:
                    if number_of_channel == 1:
                        self.ch1.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_channel == 2:
                        self.ch2.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_channel == 3:
                        self.ch3.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_channel == 4:
                        self.ch4.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_channel == 5:
                        self.ch5.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_channel == 6:
                        self.ch6.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_channel == 7:
                        self.ch7.setStyleSheet("background-color: rgb(85, 255, 127);")
                    else:
                        pass
                else:
                    if number_of_channel == 1:
                        self.ch1.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_channel == 2:
                        self.ch2.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_channel == 3:
                        self.ch3.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_channel == 4:
                        self.ch4.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_channel == 5:
                        self.ch5.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_channel == 6:
                        self.ch6.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_channel == 7:
                        self.ch7.setStyleSheet("background-color: rgb(206, 206, 206);")
                    else:
                        pass

    def click_relay_button(self, number_of_relay):
        if self.is_device_connect:
            answer = self.connect_devices[0].relay_action(number_of_relay)
            if answer != False:
                if answer == On_Off_state.On:
                    if number_of_relay == 1:
                        self.rel1.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_relay == 2:
                        self.rel2.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_relay == 3:
                        self.rel3.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_relay == 4:
                        self.rel4.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_relay == 5:
                        self.rel5.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_relay == 6:
                        self.rel6.setStyleSheet("background-color: rgb(85, 255, 127);")
                    elif number_of_relay == 7:
                        self.rel7.setStyleSheet("background-color: rgb(85, 255, 127);")
                    else:
                        pass
                else:
                    if number_of_relay == 1:
                        self.rel1.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_relay == 2:
                        self.rel2.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_relay == 3:
                        self.rel3.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_relay == 4:
                        self.rel4.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_relay == 5:
                        self.rel5.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_relay == 6:
                        self.rel6.setStyleSheet("background-color: rgb(206, 206, 206);")
                    elif number_of_relay == 7:
                        self.rel7.setStyleSheet("background-color: rgb(206, 206, 206);")
                    else:
                        pass

    def scan_active_com_ports(self):
        import serial.tools.list_ports

        ports = serial.tools.list_ports.comports()
        active_ports = []

        for port in ports:
            try:
                ser = serial.Serial(port.device)
                active_ports.append(port.device)
                ser.close()
            except (OSError, serial.SerialException):
                pass
        self.comportslist.clear()
        self.comportslist.addItems(active_ports)

    def write_boud_rate(self, list):
        self.comportslist_2.addItems(list)
        if "115200" in list:
            self.comportslist_2.setCurrentText("115200")
    # ==================================================================

    def retranslateUi(self, SVPS34_control):
        _translate = QtCore.QCoreApplication.translate
        SVPS34_control.setWindowTitle("SVPS34")
        self.scan_button.setText("Scan")
        self.connect_button.setText("Connect")
        self.label_2.setText(_translate("Device", "Нет подключенных портов"))
        self.label.setText(_translate("SVPS34_control", "Журнал"))
        self.common_button.setText("Common")
        self.ch1.setText("+3.3V")
        self.ch2.setText("+5V")
        self.ch3.setText("+12V")
        self.ch4.setText("Ch4")
        self.ch5.setText("Ch5")
        self.ch6.setText("Ch6")
        self.ch7.setText("Ch7")
        self.rel1.setText("Rel")
        self.rel2.setText("Rel")
        self.rel3.setText("Rel")
        self.rel4.setText("Rel")
        self.rel5.setText("Rel")
        self.rel6.setText("Rel")
        self.rel7.setText( "Rel")
        self.common_rel_button.setText("Common Rel")
        self.remote_button.setText("Remote")
        self.temp_label.setText(_translate("SVPS34_control", "Температура = "))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    ui = Ui_SVPS34_control()
    ui.setupUi()
    ui.show()
    sys.exit(app.exec_())
