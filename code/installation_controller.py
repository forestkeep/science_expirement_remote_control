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
import sys
import ctypes
from logging.handlers import RotatingFileHandler


from PyQt5 import QtCore, QtGui, QtWidgets
import qdarktheme
import interface.info_window_dialog
from available_devices import dict_device_class
from Installation_class import installation_class
from interface.installation_check_devices import installation_Ui_Dialog
from interface.main_window import Ui_MainWindow
from interface.selectdevice_window import Ui_Selectdevice
from Devices.svps34_control import Ui_SVPS34_control
from device_creator.dev_creator import deviceCreator


version_app = "1.0.0"
logger = logging.getLogger(__name__)

def is_admin():
    if os.name == 'nt':  # Windows
        return ctypes.windll.shell32.IsUserAnAdmin()
    else:  # Linux/Unix
        return os.geteuid() == 0


class MyWindow(QtWidgets.QMainWindow):
    global version_app
    def __init__(self, device_creator):
        self.settings = QtCore.QSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "misis_lab",
            "exp_control" + version_app,
        )

        self.device_creator = device_creator

        logger.warning(f"Start Version {version_app}, Admin {is_admin()}")

        super().__init__()
        self.dict_device_class = dict_device_class
        self.available_dev = list(self.dict_device_class.keys())
        self.ui = Ui_MainWindow(version = version_app)
        logger.debug("запуск программы")
        self.ui.setupUi(self)
        self.dict_active_local_devices = {}
        self.key_to_new_window_installation = False
        self.ui.pushButton.clicked.connect(self.open_select_device_window)
        self.ui.pushButton_2.clicked.connect(self.open_installation_window)
        self.ui.actionCreateNew.triggered.connect(self.open_create_new_device)
        self.cur_install = installation_class(
            settings=self.settings, 
            dict_device_class=self.dict_device_class,
            version = version_app
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
        if name not in self.dict_active_local_devices.keys():
            if name == "SVPS34":
                self.dict_active_local_devices[name] = Ui_SVPS34_control()
                self.dict_active_local_devices[name].setupUi()
                self.dict_active_local_devices[name].show()
            else:
                pass
        else:
            self.dict_active_local_devices[name].show()
            # del self.dict_active_local_devices[name]


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

def get_installation_controller_path():

    path = os.path.join(os.getenv('USERPROFILE'), "AppData", "Local", "Installation_Controller")
    return path

if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    logger = logging.getLogger(__name__)
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"

    # Настройка консольного обработчика
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(FORMAT))

    # Настройка файлового обработчика

    folder_path = os.path.join(os.getenv('USERPROFILE'), "AppData", "Local", "Installation_Controller")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    log_file_path = os.path.join(folder_path, "loginstallation.log")
    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=1000000, backupCount=5
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