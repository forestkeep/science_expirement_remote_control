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
from dataclasses import dataclass

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import QTranslator
from PyQt5.QtWidgets import QApplication
from SettingsManager import SettingsManager

import interface.info_window_dialog
from device_creator.dev_creator import deviceCreator
from device_creator.run_commands import TestCommands
from Devices.svps34_control import Ui_SVPS34_control
from graph.online_graph import sessionController
from Installation_class import installation_class
from interface.main_window import Ui_MainWindow
from controlDevicesJSON import search_devices_json
from localJSONControl import localDeviceControl
from device_selector import deviceSelector
from functions import open_log_file

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

class instController(QtWidgets.QMainWindow):
    def __init__(self, settings_manager: SettingsManager, version):
        self.settings_manager = settings_manager

        self.graph_controller   = None
        self.device_creator = deviceCreator()
        self.device_selector = None

        self.select_local_device = None

        logger.warning(f"Start Version {version}, Admin {is_admin()}")

        super().__init__()

        self.ui = Ui_MainWindow(version = version, main_class=self)
        logger.debug("запуск программы")
        self.ui.setupUi(self)
        self.dict_active_local_devices = {}
        self.key_to_new_window_installation = False
        self.ui.pushButton.clicked.connect(self.open_select_device_window)
        self.ui.pushButton_2.clicked.connect(self.open_installation_window)
        self.ui.actionCreateNew.triggered.connect(self.open_create_new_device)
        self.ui.log_path_open.triggered.connect(open_log_file)
        self.cur_install = installation_class(
            settings_manager=self.settings_manager, 
            version = version
        )

        #======================languages load==========================

        self.translator = QTranslator() 
        self.lang = None

        status, lang = self.settings_manager.get_setting("language")
        if not status:
            lang = "ENG"
            self.settings_manager.save_settings({"language": lang})

        self.change_language(lang)

        #----------------------
        #self.ui.is_design_mode = True
        #self.message_from_new_installation( ['Maisheng'], [])
        #----------------------


    def check_open_type(self, file_path):
        status = False
        if os.path.isfile(file_path):
            self.cur_install.reconstruct_installation([], [])
            status = self.cur_install.open_saved_installation(fileName=file_path)
            if status:
                self.cur_install.installation_window.installation_close_signal.connect(
                self.unlock_to_create_new_installation
            )
                if not self.device_selector:
                    self.device_selector = deviceSelector( self.settings_manager)
                self.cur_install.device_selector = self.device_selector

                if self.ui.is_design_mode:
                    self.cur_install.change_check_debug()

                self.close()
            else:
                print("ошибка восстановления установки")

        return status

    def change_language(self, lang):

        if lang == self.lang:
            return
        
        QtWidgets.QApplication.instance().removeTranslator(self.translator)
        
        self.lang = lang
        self.load_language(lang)
        self.ui.retranslateUi(self)
        self.settings_manager.save_settings({"language": lang})

    def open_graph_in_exp(self):
        if self.graph_controller is None:
            self.graph_controller = sessionController()

        self.graph_controller.graphics_win.show()
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
        file_path = {'RUS': "translations/translation_ru.qm"}.get(lang, next((p for p in ["translations/translation_en.qm", "translation_en.qm"] if os.path.isfile(p)), None))

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
            self.device_selector = deviceSelector( self.settings_manager)
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
                self.device_selector = deviceSelector( self.settings_manager)
            device_list, json_device_dict = self.device_selector.get_multiple_devices()

            self.message_from_new_installation(device_list, json_device_dict)

    def message_from_new_installation(self, device_list, json_device_dict):
        if device_list or json_device_dict:

            self.key_to_new_window_installation = True
            self.cur_install.reconstruct_installation(device_list, json_device_dict)
            self.cur_install.show_window_installation()
            if not self.device_selector:
                self.device_selector = deviceSelector( self.settings_manager)
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
    
class fileNotFound(Exception):
    def __init__(self, message, info):
        super().__init__(message)
        self.info = info
    
class savedTypeUnknow(Exception):
    def __init__(self, message, info):
        super().__init__(message)
        self.info = info

class savedSetError(Exception):
    def __init__(self, message, info):
        super().__init__(message)
        self.info = info

def get_installation_controller_path():

    path = os.path.join(os.getenv('USERPROFILE'), "AppData", "Local", "Installation_Controller")
    return path

