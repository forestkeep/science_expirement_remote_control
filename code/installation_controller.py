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

import ctypes
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QTranslator
from PyQt5.QtWidgets import QApplication

import qdarktheme

import interface.info_window_dialog
#from available_devices import dict_device_class, JSON_dict_device_class
from device_creator.dev_creator import deviceCreator
from device_creator.test_commands import TestCommands
from Devices.svps34_control import Ui_SVPS34_control
from graph.online_graph import GraphWindow
from Installation_class import installation_class
from interface.main_window import Ui_MainWindow
from controlDevicesJSON import search_devices_json, get_new_JSON_devs
from localJSONControl import localDeviceControl
from device_selector import deviceSelector

VERSION_APP = "1.0.3"
logger = logging.getLogger(__name__)

def is_admin():
    if os.name == 'nt':  # Windows
        return ctypes.windll.shell32.IsUserAnAdmin()
    else:  # Linux/Unix
        return os.geteuid() == 0
    
@dataclass
class devFile:
    path: str
    name: str
    message: str
    status: bool
    json_data: dict

class MyWindow(QtWidgets.QMainWindow):
    global VERSION_APP
    def __init__(self):
        self.settings = QtCore.QSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "misis_lab",
            "exp_control" + VERSION_APP,
        )
        current_dir =os.path.dirname(os.path.realpath(__file__))
        self.directory_devices = os.path.join(current_dir, "my_devices")
        self.JSON_devices = get_new_JSON_devs(self.directory_devices)

        self.graph_window   = None
        self.device_creator = deviceCreator()
        self.device_selector = None

        self.select_local_device = None

        logger.warning(f"Start Version {VERSION_APP}, Admin {is_admin()}")

        super().__init__()

        self.ui = Ui_MainWindow(version = VERSION_APP, main_class=self)
        logger.debug("запуск программы")
        self.ui.setupUi(self)
        self.dict_active_local_devices = {}
        self.key_to_new_window_installation = False
        self.ui.pushButton.clicked.connect(self.open_select_device_window)
        self.ui.pushButton_2.clicked.connect(self.open_installation_window)
        self.ui.actionCreateNew.triggered.connect(self.open_create_new_device)
        self.cur_install = installation_class(
            settings=self.settings, 
            version = VERSION_APP
        )

        #======================languages load==========================

        self.translator = QTranslator() 
        self.lang = None

        lang = self.settings.value(
            "language", defaultValue="ENG"
        )

        self.change_language(lang)

        if False:
            if os.path.isfile("picture/tray.png"):
                try:
                    self.tray_icon = QtWidgets.QSystemTrayIcon(self)
                    self.tray_icon.setIcon(QtGui.QIcon("picture/tray.png"))
                    self.tray_icon.activated.connect(self.tray_icon_activated)

                    self.tray_menu = QtWidgets.QMenu()

                    self.show_action = self.tray_menu.addAction(QApplication.translate('main', "Развернуть"))
                    self.quit_action = self.tray_menu.addAction(QApplication.translate('main', "Закрыть приложение"))

                    self.show_action.triggered.connect(self.show)
                    self.quit_action.triggered.connect(self.quit_application)

                    self.tray_icon.setContextMenu(self.tray_menu)

                    self.tray_icon.setToolTip(QApplication.translate('main',"Управление экспериментальной установкой"))
                    self.tray_icon.show()

                    self.close_event = QtWidgets.QShortcut(
                        QtGui.QKeySequence("Ctrl+Q"), self
                    )
                    self.close_event.activated.connect(self.close)
                except:
                    logger.warning("Функционал сворачивания в трей не добавлен")

    def change_language(self, lang):

        if lang == self.lang:
            return
        
        QtWidgets.QApplication.instance().removeTranslator(self.translator)
        
        self.lang = lang
        self.load_language(lang)
        self.ui.retranslateUi(self)
        self.settings.setValue(
            "language",
            self.lang,
        )

    def open_graph_in_exp(self):
        if self.graph_window is None:
            self.graph_window = GraphWindow()

        self.graph_window.show()
        self.cur_install.stop_scan_thread = True#stop scanning thread
        self.close()
        del self

    def open_test_cmd(self):
        self.test_commands_window = TestCommands()
        current_size = self.size()
        width = current_size.width()
        main_window_pos = self.pos()
        self.test_commands_window.move(main_window_pos.x() + width, main_window_pos.y())
        self.test_commands_window.show()

    def load_language(self, lang):
        file_path = {
            'RUS': "translations/translation_ru.qm",
        }.get(lang, next((p for p in ["translations/translation_en.qm", "translation_en.qm"] if os.path.isfile(p)), None))

        if file_path is not None:
            self.translator.load(file_path)
            QtWidgets.QApplication.instance().installTranslator(self.translator)

    def toggle_key_installation(self, answer_signal):
        self.key_to_new_window_installation = not self.key_to_new_window_installation

    def open_create_new_device(self):  
        self.device_creator.cancel_click.connect(self.build_new_creator)
        self.device_creator.show()

    def build_new_creator(self):
        self.device_creator = deviceCreator()

    def unlock_to_create_new_installation(self, somewhere):
        self.key_to_new_window_installation = False

    def open_select_device_window(self):
        if not self.device_selector:
            self.device_selector = deviceSelector()
        device = self.device_selector.get_single_device()
        self.message_from_new_device_local_control( device )
            
    def set_json_device_directory(self, directory):
        self.directory_devices = directory

    def choice_json_devices_directory(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        ans = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            QApplication.translate('base_install',"Выберите папку с приборами"),
            options=options,
        )
        if ans:
            logger.info(f"Выбран путь {ans} для приборов")
        return ans

    def open_installation_window(self):
        if self.key_to_new_window_installation:
            self.info_window(QApplication.translate( "MyWindow" , "установка уже собрана"))
        else:
            if not self.device_selector:
                self.device_selector = deviceSelector()
            device_list, json_device_dict = self.device_selector.get_multiple_devices()

            self.message_from_new_installation(device_list, json_device_dict)

    def message_from_new_installation(self, device_list, json_device_dict):
        if device_list or json_device_dict:

            self.key_to_new_window_installation = True
            self.cur_install.reconstruct_installation(device_list, json_device_dict)
            self.cur_install.show_window_installation()
            if not self.device_selector:
                self.device_selector = deviceSelector()
            self.cur_install.device_selector = self.device_selector

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

    def message_from_new_device_local_control(self, device):
        if device:
            if isinstance(device, str):
                if device not in self.dict_active_local_devices.keys():
                    if device == "SVPS34":
                        self.dict_active_local_devices[device] = Ui_SVPS34_control()
                        self.dict_active_local_devices[device].setupUi()
                        self.dict_active_local_devices[device].show()
                else:
                    self.dict_active_local_devices[device].show()

            else: #этот пункт на случай переданного json прибора
                    if device.name not in self.dict_active_local_devices.keys():
                            self.dict_active_local_devices[device.name] = localDeviceControl(device)
                            self.dict_active_local_devices[device.name].show()
                    else:
                        self.dict_active_local_devices[device.name].show()

    def tray_icon_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.show()  
            self.activateWindow()

    def quit_application(self):
        QtWidgets.QApplication.quit()

    def search_devices_json(self, directory):
        return search_devices_json(directory)

def get_installation_controller_path():

    path = os.path.join(os.getenv('USERPROFILE'), "AppData", "Local", "Installation_Controller")
    return path

if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    logger = logging.getLogger(__name__)
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"

    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter(FORMAT))

    folder_path = os.path.join(os.getenv('USERPROFILE'), "AppData", "Local", "Installation_Controller")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    log_file_path = os.path.join(folder_path, "loginstallation.log")
    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=1000000, backupCount=5
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(FORMAT))

    logging.basicConfig(handlers=[file_handler, console], level=logging.DEBUG)

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    os.environ["APP_THEME"] = "dark"

    translator = QTranslator()
    
    QtWidgets.QApplication.instance().installTranslator(translator)

    start_window = MyWindow()
    start_window.show()
    sys.exit(app.exec_())
