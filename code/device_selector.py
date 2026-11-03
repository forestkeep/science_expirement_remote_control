
import logging
import os

from PyQt5 import QtWidgets
from dataclasses import dataclass

from installation.ui.installation_check_devices import installation_Ui_Dialog
from installation.ui.selectdevice_window import Ui_Selectdevice
from Devices.available_devices import dict_device_class, local_device_class
from controlDevicesJSON import get_new_JSON_devs

logger = logging.getLogger(__name__)


@dataclass
class devFile:
    path: str
    name: str
    message: str
    status: bool
    json_data: dict


class deviceSelector():
    def __init__(self, settings_manager):
        self.selection_type = None
        self.single_select_win = None
        self.multiple_select_win = None
        self.settings_manager = settings_manager

        ans, self.directory_devices = self.settings_manager.get_setting('JSON_default_path')
        if not ans:
            logger.warning("Не удалось получить путь к JSON приборам из настроек")
            self.JSON_devices = {}
        else:
            # get_new_JSON_devs делегирует в file_io.scan_folder и не бросает
            # исключений наружу: все ошибки упакованы в devFile(status=False).
            try:
                os.makedirs(self.directory_devices, exist_ok=True)
            except OSError as exc:
                logger.warning("Не удалось создать папку %s: %s",
                               self.directory_devices, exc)
            self.JSON_devices = get_new_JSON_devs(self.directory_devices)

    def get_single_device(self):
        if not self.single_select_win:
            self.single_select_win = Ui_Selectdevice(devices=local_device_class.keys())
            self.single_select_win.open_new_path.clicked.connect(self.callback_select_device)

        self.single_select_win.reload_json_dev(self.JSON_devices)
        self.selection_type = 'single'

        answer = self.single_select_win.exec_()
        if answer:
            try:
                answer = self.JSON_devices[self.single_select_win.choised_device]
            except Exception:
                answer = self.single_select_win.choised_device
        if answer == 0:
            answer = None

        return answer

    def get_multiple_devices(self):
        if not self.multiple_select_win:
            self.multiple_select_win = installation_Ui_Dialog(
                available_devices=dict_device_class.keys()
            )
            self.multiple_select_win.open_new_path.clicked.connect(self.callback_select_device)

        for check in self.multiple_select_win.checkBoxes_create_dev:
            check.setChecked(False)

        for check in self.multiple_select_win.checkBoxes:
            check.setChecked(False)

        self.selection_type = 'multiple'
        self.multiple_select_win.reload_json_dev(self.JSON_devices)

        answer = self.multiple_select_win.exec_()

        device_list, json_device_list = None, None

        if answer:
            device_list = []
            json_device_list = {}
            for check in self.multiple_select_win.checkBoxes:
                if check.isChecked():
                    device_list.append(check.text())
            for check in self.multiple_select_win.checkBoxes_create_dev:
                if check.isChecked():
                    json_device_list[check.text()] = self.JSON_devices[check.text()]

        return device_list, json_device_list

    def set_json_device_directory(self, directory):
        self.directory_devices = directory
        self.settings_manager.save_settings({'JSON_default_path': directory})

    def callback_select_device(self):
        directory = self.choice_json_devices_directory()
        if directory:
            self.set_json_device_directory(directory)
            # get_new_JSON_devs → scan_folder: ошибки чтения уже в devFile.
            self.JSON_devices = get_new_JSON_devs(directory)
            if self.multiple_select_win and self.multiple_select_win.isVisible():
                self.multiple_select_win.reload_json_dev(self.JSON_devices)

            if self.single_select_win and self.single_select_win.isVisible():
                self.single_select_win.reload_json_dev(self.JSON_devices)

    def choice_json_devices_directory(self):
        if self.selection_type == 'multiple':
            par_win = self.multiple_select_win
        elif self.selection_type == 'single':
            par_win = self.single_select_win
        else:
            par_win = None

        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        ans = QtWidgets.QFileDialog.getExistingDirectory(
            par_win,
            QtWidgets.QApplication.translate('base_install', "Выберите папку с приборами"),
            options=options,
        )
        if ans:
            logger.info("Выбран путь %s для приборов", ans)
        return ans