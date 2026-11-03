
import logging
import os
import sys
import multiprocessing
from logging.handlers import RotatingFileHandler

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTranslator
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer

import pyvisa

from infrastructure.settings import SettingsManager
from open_file_controller import FileTypeChecker
from app.main_window import UnifiedMainWindow

from file_io import (
    register_all_parsers,
    assert_registry_complete,
    assert_writer_registry_complete,
)

logger = logging.getLogger(__name__)

VERSION_APP = "1.6.2"


# Единственный список моделей, которые надо импортировать, чтобы
# сработали @register/@register_writer. При добавлении модели — одна
# строка здесь; file_io/registry.py, file_io/dispatch.py,
# file_io/writers.py не меняются.
_REGISTERED_MODELS: tuple[str, ...] = (
    # publication
    "publication.model.figure_model",           # FigureSpec          kind="figure_spec"
    "publication.presets.journal_preset",       # JournalPreset       kind="journal_preset"
    "publication.presets.style_profile",        # StyleProfile, LabProfile
    # analysis
    "graphs.analysis.presets",                  # AnalysisPresetFile  kind="analysis_preset_file"
    # devices / installation / saving
    "Devices.device_spec",                      # DeviceSpec          kind="device_spec"
    "installation.installation_spec",           # InstallationSpec    kind="installation_spec"
    "saving_data.buffer_data",                  # BufferData          kind="buffer_data"
    # common
    "common.color_picker",                      # ColorPaletteData    kind="color_palette"
)

# Ожидаемые kind — для проверки на старте. buffer_data включается только
# в парсеры (read-only модель), но не в writers.
_EXPECTED_PARSER_KINDS: tuple[str, ...] = (
    "figure_spec",
    "journal_preset",
    "style_profile",
    "lab_profile",
    "analysis_preset_file",
    "device_spec",
    "installation_spec",
    "buffer_data",
    "color_palette",
)

_EXPECTED_WRITER_KINDS: tuple[str, ...] = (
    "figure_spec",
    "journal_preset",
    "style_profile",
    "lab_profile",
    "analysis_preset_file",
    "device_spec",
    "installation_spec",
    # buffer_data — read-only, writer не регистрируется
    "color_palette",
)


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
                        level=log_level_file,
                        encoding="utf-8",)

    # ---------- регистрация semantic parsers/writers ----------
    # Выполняется ДО создания окна и до любого load_file/save_file.
    # Ошибки отдельных импортов логируются и не валят старт.
    register_all_parsers(model_modules=_REGISTERED_MODELS)
    try:
        assert_registry_complete(expected_kinds=_EXPECTED_PARSER_KINDS)
        assert_writer_registry_complete(expected_kinds=_EXPECTED_WRITER_KINDS)
    except RuntimeError:
        # В production не валим приложение из-за опечатки в реестре —
        # пишем громко в лог, но продолжаем старт. В dev/CI
        # assert-функции должны падать; при желании можно поднять
        # RuntimeError через переменную окружения.
        logger.exception(
            "registry incomplete: приложение стартует, но часть "
            "load_file/save_file вызовов может завершиться ошибкой"
        )
        if os.getenv("APP_STRICT_REGISTRY", "0") == "1":
            raise

    app = QtWidgets.QApplication(sys.argv)

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

    from common.theme import ThemeManager
    ThemeManager.instance(settings_manager).initialize()

    logger.info(f"приложение запущено, файл открытия {file_path!r}")

    # --------- единственное окно приложения ---------
    window = UnifiedMainWindow(settings_manager, VERSION_APP)
    window.show()

    # --------- открытие файла из командной строки ---------
    def _open_startup_file():
        if not file_path:
            return
        from open_file_controller import FileTypeChecker
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

    QTimer.singleShot(0, _open_startup_file)

    sys.exit(app.exec_())