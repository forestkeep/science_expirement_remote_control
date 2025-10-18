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

VERSION_APP = "1.2.0"

if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method('spawn')

    # Настройка окружения
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"

    logger.handlers.clear()

    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter(FORMAT))

    folder_path = os.path.join(os.getenv('USERPROFILE'), "AppData", "Local", "Installation_Controller")
    if not os.path.exists( folder_path ):
        os.makedirs( folder_path )

    log_file_path = os.path.join( folder_path, "loginstallation.log" )

    file_handler = RotatingFileHandler( log_file_path, maxBytes=1000000, backupCount=5 )
    
    file_handler.setLevel( logging.WARNING )
    file_handler.setFormatter( logging.Formatter(FORMAT) )

    logging.basicConfig(handlers=[file_handler, console], level=logging.DEBUG)

    # Создание приложения
    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    os.environ["APP_THEME"] = "dark"

    # Настройка перевода
    translator = QTranslator()
    QtWidgets.QApplication.instance().installTranslator(translator)

    # Загрузка настроек
    settings = QtCore.QSettings(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.UserScope,
        "misis_lab",
        "exp_control" + VERSION_APP,
    )

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
