import logging
import os
import sys
import multiprocessing
from logging.handlers import RotatingFileHandler

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTranslator
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QColor, QPalette

import pyvisa
import qdarktheme

from infrastructure.settings import SettingsManager
from open_file_controller import FileTypeChecker
from app.main_window import UnifiedMainWindow

logger = logging.getLogger(__name__)

VERSION_APP = "1.6.2"


def migrate_settings(old_settings, current_version):
    def version_to_tuple(v):
        return tuple(int(p) for p in v.split('.')[:3])

    old_version = old_settings.get('version', '1.0.0')
    if version_to_tuple(old_version) == version_to_tuple(current_version):
        return old_settings

    migrated = old_settings.copy()
    migrated['version'] = current_version
    return migrated


def load_settings_with_backward_compatibility(app_name, version):
    temp_settings = QtCore.QSettings(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.UserScope,
        "misis_lab",
        app_name + version,
    )
    temp_file_path = temp_settings.fileName()
    settings_dir = os.path.dirname(temp_file_path)

    if os.path.exists(temp_file_path):
        return temp_settings

    old_settings_files = []
    if os.path.exists(settings_dir):
        for file in os.listdir(settings_dir):
            if file.endswith('.ini'):
                old_settings_files.append(os.path.join(settings_dir, file))

    if old_settings_files:
        old_settings_files.sort(key=os.path.getmtime, reverse=True)
        for old_file in old_settings_files:
            try:
                old_settings = QtCore.QSettings(
                    old_file, QtCore.QSettings.IniFormat)
                migrated_values = {
                    k: old_settings.value(k)
                    for k in old_settings.allKeys()
                }
                migrated_values = migrate_settings(migrated_values, version)

                new_settings = QtCore.QSettings(
                    QtCore.QSettings.IniFormat,
                    QtCore.QSettings.UserScope,
                    "misis_lab",
                    app_name + version,
                )
                for k, v in migrated_values.items():
                    new_settings.setValue(k, v)
                new_settings.sync()
                logger.warning(
                    f"Настройки загружены из старой версии {old_file}")
                return new_settings
            except Exception as e:
                logger.warning(f"Ошибка миграции из {old_file}: {e}")
                continue

    return temp_settings


if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method('spawn')

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    FORMAT = ("%(asctime)s - %(name)s - %(levelname)s - "
              "%(funcName)s - %(message)s")
    log_level_consol = logging.INFO
    log_level_file = logging.INFO
    logger.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(log_level_consol)
    console.setFormatter(logging.Formatter(FORMAT))

    folder_path = os.path.join(
        os.getenv('USERPROFILE', os.path.expanduser('~')),
        "AppData", "Local", "Installation_Controller")
    os.makedirs(folder_path, exist_ok=True)
    log_file_path = os.path.join(folder_path, "loginstallation.log")

    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=1000000, backupCount=5)
    file_handler.setLevel(log_level_file)
    file_handler.setFormatter(logging.Formatter(FORMAT))

    logging.basicConfig(handlers=[file_handler, console],
                        level=log_level_file)

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    os.environ["APP_THEME"] = "dark"

    palette = app.palette()
    palette.setColor(QPalette.ToolTipBase, QColor("#1e1e1e"))
    palette.setColor(QPalette.ToolTipText, QColor("#FFEB3B"))
    app.setPalette(palette)

    existing = app.styleSheet() or ""
    tooltip_css = (
        "QToolTip {"
        " background-color: #1e1e1e;"
        " color: #FFEB3B;"
        " border: 1px solid #4aa3f8;"
        " border-radius: 4px;"
        " padding: 6px 10px;"
        " font-size: 12px;"
        " }"
    )
    app.setStyleSheet(existing + "\n" + tooltip_css)

    translator = QTranslator()
    QtWidgets.QApplication.instance().installTranslator(translator)

    settings = load_settings_with_backward_compatibility(
        "exp_control", VERSION_APP)

    current_dir = os.path.dirname(os.path.realpath(__file__))
    default_JSON_directory_devices = os.path.join(current_dir, "my_devices")

    persistent_settings = {
        'language': 'ENG',
        'theme': 'dark',
        "is_show_basic_instruction_again": True,
        "is_exp_run_anywhere": False,
        "is_delete_buf_file": False,
        "should_prompt_for_session_name": True,
        "JSON_default_path": default_JSON_directory_devices,
    }

    file_path = (os.path.normpath(sys.argv[1].strip('"'))
                 if len(sys.argv) > 1 else "")

    try:
        rm_ivi = pyvisa.ResourceManager('@ivi')
    except OSError:
        rm_ivi = None
        logger.warning("IVI бэкенд НЕ доступен")

    try:
        rm_py = pyvisa.ResourceManager('@py')
    except Exception as e:
        rm_py = None
        logger.warning(f"pyvisa-py бэкенд не работает: {e}")

    settings_manager = SettingsManager(
        settings=settings,
        VERSION_APP=VERSION_APP,
        def_persistent_sett=persistent_settings,
    )

    logger.info(f"приложение запущено, файл открытия {file_path!r}")

    # --------- единственное окно приложения ---------
    window = UnifiedMainWindow(settings_manager, VERSION_APP)
    window.show()

    # --------- открытие файла из командной строки ---------
    if file_path:
        checker = FileTypeChecker(file_path)
        ok, msg = checker.validate()
        if ok:
            actual_path = checker.file_path
            type_file = checker.get_type()
            try:
                if type_file == "ns":
                    window.open_installation_file(actual_path)
                elif type_file == "hdf5":
                    window.open_project_file(actual_path)
            except Exception as e:
                logger.exception(f"open {type_file} failed")
                QMessageBox.critical(window, "Ошибка открытия", str(e))
        else:
            QMessageBox.critical(window, "Ошибка открытия", msg)

    sys.exit(app.exec_())