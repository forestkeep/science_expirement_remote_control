import logging
import os
import sys
import multiprocessing
from logging.handlers import RotatingFileHandler

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTranslator
from SettingsManager import SettingsManager

import pyvisa

import qdarktheme

from installation_controller import instController

logger = logging.getLogger(__name__)

VERSION_APP = "1.4.0"


def migrate_settings(old_settings: dict[str, any], current_version: str) -> dict[str, any]:
    """
    Миграция старых настроек к текущей версии
    """

    def version_to_tuple(version_str: str):
        parts = version_str.split('.')
        return tuple(int(part) for part in parts[:3])
    
    old_version_str = old_settings.get('version', '1.0.0')
    old_version = version_to_tuple(old_version_str)
    current_version_tuple = version_to_tuple(current_version)
    
    migrated_settings = old_settings.copy()
    
    migrated_settings['version'] = current_version
    
    return migrated_settings
def load_settings_with_backward_compatibility(app_name: str, version: str) -> QtCore.QSettings:
    """
    Загружает настройки с поддержкой обратной совместимости
    """

    temp_settings = QtCore.QSettings(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.UserScope,
        "misis_lab",
        app_name + version
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
                old_settings = QtCore.QSettings(old_file, QtCore.QSettings.IniFormat)
                
                migrated_values = {}
                for key in old_settings.allKeys():
                    migrated_values[key] = old_settings.value(key)
                
                migrated_values = migrate_settings(migrated_values, version)
                
                new_settings = QtCore.QSettings(
                    QtCore.QSettings.IniFormat,
                    QtCore.QSettings.UserScope,
                    "misis_lab",
                    app_name + version
                )
                
                for key, value in migrated_values.items():
                    new_settings.setValue(key, value)
                
                new_settings.sync()
                logger.warning(f"Настройки успешно загружены из файла старой версии {old_file}")
                return new_settings
                
            except Exception as e:
                logger.warning(f"Ошибка при миграции настроек из {old_file}: {str(e)}")
                continue
    
    return temp_settings

if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method('spawn')

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"

    log_level_consol = logging.INFO
    log_level_file = logging.INFO

    logger.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(log_level_consol)
    console.setFormatter(logging.Formatter(FORMAT))

    folder_path = os.path.join(os.getenv('USERPROFILE'), "AppData", "Local", "Installation_Controller")
    if not os.path.exists( folder_path ):
        os.makedirs( folder_path )

    log_file_path = os.path.join( folder_path, "loginstallation.log" )

    file_handler = RotatingFileHandler( log_file_path, maxBytes=1000000, backupCount=5 )
    
    file_handler.setLevel( log_level_file )
    file_handler.setFormatter( logging.Formatter(FORMAT) )

    logging.basicConfig(handlers=[file_handler, console], level=log_level_file)

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    os.environ["APP_THEME"] = "dark"

    translator = QTranslator()
    QtWidgets.QApplication.instance().installTranslator(translator)

    settings = load_settings_with_backward_compatibility("exp_control", VERSION_APP)

    current_dir =os.path.dirname(os.path.realpath(__file__))
    default_JSON_directory_devices = os.path.join(current_dir, "my_devices")
    
    persistent_settings = {
        'language': 'ENG',
        'theme': 'dark',
        "is_show_basic_instruction_again": True,
        "is_exp_run_anywhere": False,
        "is_delete_buf_file": False,
        "should_prompt_for_session_name": True,
        "JSON_default_path": default_JSON_directory_devices
    }
    
    file_path = os.path.normpath(sys.argv[1].strip('"')) if len(sys.argv) > 1 else ""

    try:
        rm_ivi = pyvisa.ResourceManager('@ivi')
    except OSError:
        rm_ivi = None
        logger.warning("IVI бэкенд НЕ доступен (не установлены драйверы VISA)")

    try:
        rm_py = pyvisa.ResourceManager('@py')
    except Exception as e:
        rm_py = None
        logger.warning(f"pyvisa-py бэкенд не работает: {str(e)}")

    # Создание менеджера настроек
    settings_manager = SettingsManager(
        settings=settings,
        VERSION_APP=VERSION_APP,
        def_persistent_sett=persistent_settings
    )

    start_window = instController( settings_manager, version=VERSION_APP )
    if not start_window.check_open_type(file_path):
        #TODO: добавить контроллер открывтия , открываться может установка, сессия обработки данных. Контроллер должен управлять открытием, выдавать сообщения в случае ошибок и т.д.
        start_window.show()
    sys.exit(app.exec_())
