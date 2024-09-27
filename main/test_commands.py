import sys
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLineEdit,
    QPushButton,
    QLabel,
    QComboBox,
    QGridLayout,
    QMainWindow,
)
from Adapter import instrument
from PyQt5.QtCore import QTimer
import logging
import threading
import pyvisa

NOT_READY_STYLE_BORDER = "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
READY_STYLE_BORDER = "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
WARNING_STYLE_BORDER = "border: 1px solid rgb(180, 180, 0); border-radius: 5px;"

SCAN_INTERVAL = 2000
DEFAULT_TIMEOUT = 2000


class TestCommands(QMainWindow):
    def __init__(self):
        super().__init__()
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.active_ports = []
        self.client = None
        self.setWindowTitle("Тест команд")
        
        self.read_ans_thread = threading.Thread(target=self.read_answer_new)
        self.read_ans_thread.daemon = True
        
        self.timer_for_scan_com_port = QTimer(self)
        self.timer_for_scan_com_port.timeout.connect(self._scan_com_ports)
        self.timer_for_scan_com_port.start(100)
        

        layout = QGridLayout()
        self._create_widgets(layout)
        self.main_widget.setLayout(layout)

    def _create_widgets(self, layout):
        self.entry = QLineEdit(self)
        layout.addWidget(self.entry, 0, 1)

        self.send_button = QPushButton("Отправить", self)
        self.send_button.clicked.connect(self.send_action)
        layout.addWidget(self.send_button, 0, 0)

        self.answ_label = QLabel("Ответ:", self)
        layout.addWidget(self.answ_label, 1, 0)
        self.answer = QLineEdit(self)
        self.answer.setText("-------")
        self.answer.setReadOnly(True)
        layout.addWidget(self.answer, 1, 1)

        self.timeout_entry = QLineEdit(self)
        self.timeout_entry.setText(str(DEFAULT_TIMEOUT))
        layout.addWidget(QLabel("Таймаут(мс)", self), 2, 0)
        layout.addWidget(self.timeout_entry, 2, 1)

        self.source_combo = QComboBox(self)
        self.source_combo.addItems(["Нет подключенных портов"])
        layout.addWidget(QLabel("Порт", self), 3, 0)
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
        layout.addWidget(QLabel("Скорость(бод)", self), 4, 0)
        layout.addWidget(self.speed_combo, 4, 1)

    def send_action(self):
        if self.source_combo.currentText() == "Нет подключенных портов":
            return

        self._update_client()
        if self.client:
            try:
                self.answer.clear()
                self.timeout = float(self.timeout_entry.text())
                self.client.timeout = self.timeout
                self.client.baud_rate = int(self.speed_combo.currentText())
                self.answ_label.setText("Принимаем")
                self.entry.setEnabled(False)
                self.send_button.setEnabled(False)
                self.read_ans_thread = threading.Thread(target=self.read_answer_new)
                self.read_ans_thread.daemon = True
                self.client.write(self.entry.text())
                self.timer_for_scan_com_port.stop()
                self.read_ans_thread.start()

            except Exception as e:
                logging.error(f"Error in send_action: {e}")
                self._handle_client_error()


    def _update_client(self):
        current_port = self.source_combo.currentText()
        if self.client is None or self.client.resource_name != current_port:
            rm = pyvisa.ResourceManager()
            try:
                self.client = rm.open_resource(current_port)
            except:
                self._handle_client_error()
        else:
            rm = instrument.get_visa_resourses()
            if current_port not in rm:
                self._handle_client_error()
                

    def _handle_client_error(self):
        self.client = None
        self.source_combo.setStyleSheet(NOT_READY_STYLE_BORDER)

    def read_answer_new(self):
        self.entry.setEnabled(False)
        try:
            answer = self.client.read()
            self.answer.setStyleSheet(READY_STYLE_BORDER)
        except:
            answer = "Истек таймаут"
            self.answer.setStyleSheet(NOT_READY_STYLE_BORDER)
        if "..." in self.answ_label.text():
            self.answ_label.setText("Принимаем")
        else:
            self.answ_label.setText(self.answ_label.text() + ".")

            self.answer.setText(answer)
        self.entry.setEnabled(True)
        self.send_button.setEnabled(True)
        self.answ_label.setText("Ответ")
        

    def _scan_com_ports(self):
        self.timer_for_scan_com_port.stop()
        if not self.read_ans_thread.is_alive():
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
    logger = logging.getLogger(__name__)
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    console.setFormatter(logging.Formatter(FORMAT))
    logging.basicConfig(handlers=[console], level=logging.DEBUG)

    app = QApplication(sys.argv)
    window = TestCommands()
    window.show()
    sys.exit(app.exec_())
