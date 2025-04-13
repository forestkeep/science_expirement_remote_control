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

import pyvisa
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QComboBox, QGridLayout, QLabel,
                             QTextEdit, QLineEdit, QMainWindow, QPushButton, QWidget)
try:
    from Adapter import instrument
except:
    pass

NOT_READY_STYLE_BORDER = "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
READY_STYLE_BORDER = "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
WARNING_STYLE_BORDER = "border: 1px solid rgb(180, 180, 0); border-radius: 5px;"

SCAN_INTERVAL = 2000
DEFAULT_TIMEOUT = 2000


class queryCommand(QThread):
    finished = pyqtSignal(str)

    def __init__(self, client, command):
        super().__init__()
        self.command = command
        self.client = client

    def run(self):
        print(self.command)
        try:
            answer = self.client.query(self.command)
        except Exception as e:
            print(e)
            answer = ""
        self.finished.emit(answer)

class TestCommands(QMainWindow):
    def __init__(self):
        super().__init__()
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.active_ports = []
        self.client = None
        self.setWindowTitle(QApplication.translate("create_dev_window", "Тест команд"))
        self.timer_for_scan_com_port = QTimer(self)
        self.timer_for_scan_com_port.timeout.connect(self._scan_com_ports)
        self.timer_for_scan_com_port.start(100)
        self.is_reading = False 
        
        layout = QGridLayout()
        self._create_widgets(layout)
        self.main_widget.setLayout(layout)

        self.retranslateuI(self)

    def _create_widgets(self, layout):
        self.entry = QLineEdit(self)
        layout.addWidget(self.entry, 0, 1)

        self.send_button = QPushButton(QApplication.translate("create_dev_window", "Отправить"), self)
        self.send_button.clicked.connect(self.send_action)
        layout.addWidget(self.send_button, 0, 0)

        self.answ_label = QLabel(QApplication.translate("create_dev_window", "Ответ:"), self)
        layout.addWidget(self.answ_label, 1, 0)
        self.answer = QTextEdit(self)
        self.answer.setText("-------")
        self.answer.setReadOnly(True)
        layout.addWidget(self.answer, 1, 1)

        self.timeout_entry = QLineEdit(self)
        self.timeout_entry.setText(str(DEFAULT_TIMEOUT))
        layout.addWidget(QLabel(QApplication.translate("create_dev_window", "Таймаут(мс)"), self), 2, 0)
        layout.addWidget(self.timeout_entry, 2, 1)

        self.source_combo = QComboBox(self)
        self.source_combo.addItems([QApplication.translate("create_dev_window", "Нет подключенных портов")])
        layout.addWidget(QLabel(QApplication.translate("create_dev_window", "Порт"), self), 3, 0)
        layout.addWidget(self.source_combo, 3, 1)

        self.speed_combo = QComboBox(self)
        self.speed_combo.addItems(
            map(
                str,
                [
                    50,
                    75,
                    110,
                    150,
                    300,
                    600,
                    1200,
                    2400,
                    4800,
                    9600,
                    19200,
                    38400,
                    57600,
                    115200,
                ],
            )
        )
        self.speed_combo.setCurrentText("9600")
        layout.addWidget(QLabel(QApplication.translate("create_dev_window", "Скорость(бод)"), self), 4, 0)
        layout.addWidget(self.speed_combo, 4, 1)

    def send_action(self):
        if self.source_combo.currentText() == QApplication.translate("create_dev_window", "Нет подключенных портов"):
            return

        self._update_client()
        if self.client:
            try:
                self.answer.clear()
                self.timeout = float(self.timeout_entry.text())
                self.client.timeout = self.timeout
                self.client.baud_rate = int(self.speed_combo.currentText())
                self.answ_label.setText(QApplication.translate("create_dev_window", "Принимаем"))
                self.entry.setEnabled(False)
                self.send_button.setEnabled(False)
                self.timer_for_scan_com_port.stop()
                self.is_reading = True
                self.read_ans_thread = queryCommand(self.client, self.entry.text())
                self.read_ans_thread.finished.connect(self.callback_query)
                self.read_ans_thread.start()

            except Exception as e:
                logging.error(f"Error in send_action: {e}")
                self._handle_client_error()
    def callback_query(self, answer):
        self.is_reading = False
        print("callback_query", answer)
        if answer:
            self.answer.setStyleSheet(READY_STYLE_BORDER)
        else:
            answer = QApplication.translate("create_dev_window","Истек таймаут")
            self.answer.setStyleSheet(NOT_READY_STYLE_BORDER)

        self.answer.setText(answer)
        self.entry.setEnabled(True)
        self.send_button.setEnabled(True)
        self.answ_label.setText(QApplication.translate("create_dev_window", "Ответ"))

    def _update_client(self):
        current_port = self.source_combo.currentText()
        if self.client is None or self.client.resource_name != current_port:
            rm = pyvisa.ResourceManager()
            try:
                self.client = rm.open_resource(current_port)
                print(f"{self.client=}")
            except:
                self._handle_client_error()
        else:
            rm = instrument.get_visa_resourses()
            if current_port not in rm:
                self._handle_client_error()
                
    def _handle_client_error(self):
        self.client = None
        self.source_combo.setStyleSheet(NOT_READY_STYLE_BORDER)
     
    def retranslateuI(self, creat_window):
        _translate = QApplication.translate
        creat_window.setWindowTitle(_translate("creat_dev_window", "Тест команд"))

    def _scan_com_ports(self):
        self.timer_for_scan_com_port.stop()
        if not self.is_reading:
            local_list_com_ports = []
            for port in instrument.get_visa_resourses():
                try:
                    rm = pyvisa.ResourceManager()
                    client = rm.open_resource(port)
                    client.close()
                    local_list_com_ports.append(port)
                except:
                    pass
            if local_list_com_ports == []:
                self.client = None
                local_list_com_ports = ["Нет подключенных портов"]

            current_val = self.source_combo.currentText()
            if set(local_list_com_ports) != set(self.active_ports):
                self.source_combo.clear()
                self.source_combo.addItems(local_list_com_ports)
                
            if current_val in local_list_com_ports:
                self.source_combo.setCurrentText(current_val)

            self.source_combo.setStyleSheet(
                READY_STYLE_BORDER
                if self.source_combo.currentText() != "Нет подключенных портов"
                else NOT_READY_STYLE_BORDER
            )
            self.active_ports = local_list_com_ports
        self.timer_for_scan_com_port.start(SCAN_INTERVAL)


if __name__ == "__main__":

    rm = pyvisa.ResourceManager()
    name = rm.list_resources()

    with rm.open_resource(name[0]) as Power_Analyser:

        Power_Analyser.timeout = 25000

        Data = Power_Analyser.query(":DDS:ARB:DAC16:BIN#504096")

