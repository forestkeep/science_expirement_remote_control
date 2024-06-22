import sys
from interface.main_window import Ui_MainWindow
from interface.maisheng_window import maisheng_ui_window
from interface.relay_window import Relay_Ui_MainWindow, relay_class
from interface.installation_check_devices import installation_Ui_Dialog
from interface.selectdevice_window import Ui_Selectdevice
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QMessageBox
import interface.info_window_dialog
from svps34_control import Ui_SVPS34_control
from Installation_class import installation_class
import qdarktheme
from PyQt5 import QtCore, QtGui, QtWidgets
import os
import logging
from logging.handlers import RotatingFileHandler

class MyWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()  
        logger.debug("запуск программы")
        self.ui.setupUi(self)  
        self.dict_active_local_devices = {}
        self.key_to_new_window_installation = False
        self.ui.pushButton.clicked.connect(self.open_select_device_window)
        self.ui.pushButton_2.clicked.connect(self.open_installation_window)
        self.current_installation_class = installation_class()
        self.current_installation_list = []

    def toggle_key_installation(self, answer_signal):
        self.key_to_new_window_installation = not self.key_to_new_window_installation

    def unlock_to_create_new_installation(self, somewhere):
        self.key_to_new_window_installation = False

    def open_select_device_window(self):
        self.select_local_device = QtWidgets.QDialog()
        self.ui_window_local_device = Ui_Selectdevice()
        self.ui_window_local_device.setupUi(self.select_local_device, self)
        self.select_local_device.show()

    def open_installation_window(self):
        if self.key_to_new_window_installation:
            self.info_window("установка уже собрана")
        else:
            self.new_window = QtWidgets.QDialog()
            self.ui_window = installation_Ui_Dialog()
            self.ui_window.setupUi(self.new_window, self)
            self.key_to_new_window_installation = True
            self.new_window.show()
            #self.close()

    def message_from_new_installation(self, device_list):
        if device_list:
            self.current_installation_list = device_list
            self.current_installation_class.reconstruct_installation(self.current_installation_list)
            self.current_installation_class.show_window_installation()
            self.close()
            self.current_installation_class.installation_window.installation_close_signal.connect(self.unlock_to_create_new_installation)

    def info_window(self, text):
        self.dialog = QtWidgets.QDialog()
        self.dialog_info = interface.info_window_dialog.Ui_Dialog()
        self.dialog_info.setupUi(self.dialog, self)
        self.dialog.show()

    def message_from_info_dialog(self, answer):
        if answer:
            self.key_to_new_window_installation = False
            self.current_installation_class.close_window_installation()
            self.open_installation_window()

    def message_from_new_device_local_control(self, name):
        self.select_local_device.close()
        print(name)
        if name not in self.dict_active_local_devices:
            if name == "Maisheng":
                self.dict_active_local_devices[name] = maisheng_ui_window()
            elif name == "Polarity Relay":
                self.dict_active_local_devices[name] = Relay_Ui_MainWindow()
                self.dict_active_local_devices[name] = relay_class()
            elif name == "SVPS34":
                self.dict_active_local_devices[name] = Ui_SVPS34_control()
            elif name == "SR830":
                self.dict_active_local_devices[name] = 1
            elif name == "АКИП":
                self.dict_active_local_devices[name] = 2
            else :
                pass
        else:
            del self.dict_active_local_devices[name]

if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    logger = logging.getLogger(__name__)
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    folder_path = "log_files"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    file_handler = RotatingFileHandler('log_files\logfile.log', maxBytes=100000, backupCount=3)

    logging.basicConfig(encoding='utf-8', format=FORMAT, level=logging.WARNING, handlers=[file_handler, console])

    #auto-py-to-exe
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"


    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    start_window = MyWindow()
    start_window.show()
    sys.exit(app.exec_())

# pyuic5 name.ui -o name.py
#auto-py-to-exe