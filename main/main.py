import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import qdarktheme
from PyQt5 import QtCore, QtGui, QtWidgets

import interface.info_window_dialog
from available_devices import dict_device_class
from Installation_class import installation_class
from interface.installation_check_devices import installation_Ui_Dialog
from interface.main_window import Ui_MainWindow
from interface.maisheng_window import maisheng_ui_window
from interface.relay_window import Relay_Ui_MainWindow
from interface.selectdevice_window import Ui_Selectdevice
from svps34_control import Ui_SVPS34_control
from dev_creator import deviceCreator

logger = logging.getLogger(__name__)

class MyWindow(QtWidgets.QMainWindow):
    def __init__(self, device_creator):
        self.settings = QtCore.QSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "misis_lab",
            "exp_control",
        )

        self.device_creator = device_creator

        super().__init__()
        self.dict_device_class = dict_device_class
        self.available_dev = list(self.dict_device_class.keys())
        self.ui = Ui_MainWindow()
        logger.debug("запуск программы")
        self.ui.setupUi(self)
        self.dict_active_local_devices = {}
        self.key_to_new_window_installation = False
        self.ui.pushButton.clicked.connect(self.open_select_device_window)
        self.ui.pushButton_2.clicked.connect(self.open_installation_window)
        self.ui.actionCreateNew.triggered.connect(self.open_create_new_device)
        self.cur_install = installation_class(
            settings=self.settings, dict_device_class=self.dict_device_class
        )
        self.current_installation_list = []

        if False:
            if os.path.isfile("picture/tray.png"):
                try:
                    # Создаем системный трей и устанавливаем иконку
                    self.tray_icon = QtWidgets.QSystemTrayIcon(self)
                    self.tray_icon.setIcon(QtGui.QIcon("picture/tray.png"))
                    self.tray_icon.activated.connect(self.tray_icon_activated)

                    # Создаем контекстное меню
                    self.tray_menu = QtWidgets.QMenu()

                    # Добавляем пункты в меню
                    self.show_action = self.tray_menu.addAction("Развернуть")
                    self.quit_action = self.tray_menu.addAction("Закрыть приложение")

                    self.show_action.triggered.connect(self.show)
                    self.quit_action.triggered.connect(self.quit_application)

                    self.tray_icon.setContextMenu(self.tray_menu)

                    self.tray_icon.setToolTip("Управление экспериментальной установкой")
                    self.tray_icon.show()

                    # Сигнал для закрытия окна
                    self.close_event = QtWidgets.QShortcut(
                        QtGui.QKeySequence("Ctrl+Q"), self
                    )
                    self.close_event.activated.connect(self.close)
                except:
                    logger.warning("Функционал сворачивания в трей не добавлен")

    def toggle_key_installation(self, answer_signal):
        self.key_to_new_window_installation = not self.key_to_new_window_installation

    def open_create_new_device(self):
        self.device_creator.show()

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
            self.ui_window.setupUi(self.new_window, self, self.available_dev)
            # self.key_to_new_window_installation = True
            self.new_window.show()

    def message_from_new_installation(self, device_list):
        if device_list:
            self.key_to_new_window_installation = True
            self.current_installation_list = device_list
            self.cur_install.reconstruct_installation(
                self.current_installation_list
            )
            self.cur_install.show_window_installation()

            if self.ui.is_design_mode:
                self.cur_install.change_check_debug()

            self.close()
            self.device_creator.close()
            self.cur_install.installation_window.installation_close_signal.connect(
                self.unlock_to_create_new_installation
            )
        else:
            self.key_to_new_window_installation = False

    def info_window(self, text):
        self.dialog = QtWidgets.QDialog()
        self.dialog_info = interface.info_window_dialog.Ui_Dialog()
        self.dialog_info.setupUi(self.dialog, self)
        self.dialog.show()

    def message_from_info_dialog(self, answer):
        if answer:
            self.key_to_new_window_installation = False
            self.cur_install.close_window_installation()
            self.open_installation_window()

    def message_from_new_device_local_control(self, name):
        self.select_local_device.close()
        if name not in self.dict_active_local_devices:
            if name == "Maisheng":
                self.dict_active_local_devices[name] = maisheng_ui_window()
            elif name == "Polarity Relay":
                self.dict_active_local_devices[name] = Relay_Ui_MainWindow()
            elif name == "SVPS34":
                self.dict_active_local_devices[name] = Ui_SVPS34_control()
                self.dict_active_local_devices[name].setupUi()
                self.dict_active_local_devices[name].show()

            elif name == "SR830":
                self.dict_active_local_devices[name] = 1
            elif name == "АКИП":
                self.dict_active_local_devices[name] = 2
            else:
                pass
        else:
            del self.dict_active_local_devices[name]

    def closeEvent(self, event):
        """Событие закрытия окна"""
        # эти пункты испльзуются при добавлении в трей
        # event.ignore()  # Игнорируем событие закрытия
        # self.hide()     # Скрываем окно

        event.accept()  # Закрытие окна

    def tray_icon_activated(self, reason):
        """Сигнал при активации трей-иконки"""
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.show()  # Показываем окно при нажатии на трей-иконку
            self.activateWindow()

    def quit_application(self):
        """Закрывает приложение."""
        QtWidgets.QApplication.quit()


if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    logger = logging.getLogger(__name__)
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"

    # Настройка консольного обработчика
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(FORMAT))

    # Настройка файлового обработчика
    folder_path = "log_files"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    file_handler = RotatingFileHandler(
        "log_files/logfile.log", maxBytes=100000, backupCount=3
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(FORMAT))

    # Общая настройка логгирования
    logging.basicConfig(handlers=[file_handler, console], level=logging.DEBUG)

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")

    # Создаем экземпляр deviceCreator
    device_creator = deviceCreator()


    start_window = MyWindow(device_creator=device_creator)
    start_window.show()
    sys.exit(app.exec_())
