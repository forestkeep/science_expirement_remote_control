import sys
from interface.main_window import Ui_MainWindow
from interface.maisheng_window import maisheng_ui_window
from interface.relay_window import Relay_Ui_MainWindow, relay_class
from installation_check_devices import installation_Ui_Dialog
from interface.selectdevice_window import Ui_Selectdevice
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QMessageBox
import interface.info_window_dialog 
from test3 import Ui_SVPS34_control
from Installation_class import installation_class
# pyuic5 name.ui -o name.py - запускаем из папки с файлом ui в cmd

class Mywindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()  # благодаря этой херне доступны методы родителя
        self.ui = Ui_MainWindow()  # создаем экземпляр класс ui_main_window
        self.ui.setupUi(self)  # вызываем метод из созданного класс
        self.dict_active_local_devices = {}
        self.dict_active_local_devices_window = {}

        self.key_to_new_window_installation = False
        self.key_to_new_window_devices = []
        self.ui.pushButton.clicked.connect(self.open_select_device_window)
        self.ui.pushButton_2.clicked.connect(self.open_installation_window)
        self.current_installation_class = installation_class()
        self.current_installation_list = []
        # self.current_installation_class.installation_window.closeEvent(lambda: self.toggle_key_installation())

    def toggle_key_installation(self, answer_signal):
        if self.key_to_new_window_installation:
            self.key_to_new_window_installation = False
        else:
            self.key_to_new_window_installation = True

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

    def message_from_new_installation(self, list):
        if len(list) != 0:
            self.current_installation_list = list
            self.current_installation_class.reconstruct_installation(
                self.current_installation_list)
            self.current_installation_class.show_window_installation()
            print("показано окно установки")
            self.current_installation_class.installation_window.installation_close_signal.connect(
                self.unlock_to_create_new_installation)

        else:
            print("установка не создана, лист пустой")
        print(self.current_installation_list)

    def info_window(self, text):
        self.dialog = QtWidgets.QDialog()
        self.dialog_info = interface.info_window_dialog.Ui_Dialog()
        self.dialog_info.setupUi(self.dialog, self)
        self.dialog.show()

    def message_from_info_dialog(self, answer):
        print(answer)
        if answer == True:
            self.key_to_new_window_installation = False
            self.current_installation_class.close_window_installation()
            self.open_installation_window()
            # self.current_installation_class = 0

            pass  # отправлено ок нужно закрыть уже созданную установку
        else:
            pass  # отправлено отмена

    def message_from_new_device_local_control(self, name):
        self.select_local_device.close()
        print(name)
        if name in self.dict_active_local_devices:
            msg = QMessageBox()
            msg.setWindowTitle("Ошибка")
            msg.setText("Окно управления прибором уже открыто")
            msg.setIcon(QMessageBox.Warning)

            msg.exec_()
            print("прибор уже создан бл!")
        else:
            if name == "Maisheng":
                self.dict_active_local_devices_window[name] = maisheng_ui_window(
                )
                # создаем в двух ращзных словарях значения по ключу
                # self.dict_active_local_devices[name] = maisheng_class()
            if name == "Polarity Relay":
                self.dict_active_local_devices_window[name] = Relay_Ui_MainWindow(
                )
                self.dict_active_local_devices[name] = relay_class()
            if name == "SVPS34":
                self.dict_active_local_devices_window[name] = Ui_SVPS34_control(
                )
                # self.dict_active_local_devices[name] = SVPS32_class()

            if name == "Lock in":
                pass
            '''
					self.dict_active_local_devices_window[i] = 
					self.dict_active_local_devices[i] = 
					'''
            if name == "АКИП":
                pass
            '''
					self.dict_active_local_devices_window[i] = 
					self.dict_active_local_devices[i] = 
					'''
            if name == "other...":
                pass

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    start_window = Mywindow()
    start_window.show()
    sys.exit(app.exec_())


# pyuic5 name.ui -o name.py
