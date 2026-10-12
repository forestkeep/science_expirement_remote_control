import subprocess
import os
import shutil

import PyInstaller.__main__

from service_scripts.clear_dir import remove_pycaches
from main import VERSION_APP
from service_scripts.convert_instruction import convert_docx_to_html


# =====================================================================
#  Список модулей, исключаемых из сборки PyInstaller.
#
#  ВНИМАНИЕ:
#  1. Список разбит на группы для удобства.
#  2. После каждого изменения обязательно проверяйте работу приложения
#     (запуск, все приборы, сохранение результатов, открытие установок,
#     графики, работа с VISA/Serial/Modbus).
#  3. Некоторые модули намеренно оставлены закомментированными —
#     они могут подтягиваться зависимостями (pyvisa, h5py, qdarktheme и др.).
# =====================================================================
EXCLUDED_MODULES = [
    # --- PyQt5: неиспользуемые подмодули ---------------------------------
    'PyQt5.QtWebEngine',
    'PyQt5.QtWebEngineCore',
    'PyQt5.QtWebEngineWidgets',
    'PyQt5.QtWebKit',
    'PyQt5.QtWebKitWidgets',
    'PyQt5.QtQuick',
    'PyQt5.QtQml',
    'PyQt5.QtQuickWidgets',
    'PyQt5.QtMultimedia',
    'PyQt5.QtMultimediaWidgets',
    'PyQt5.QtSql',
    'PyQt5.QtTest',
    'PyQt5.QtDesigner',
    'PyQt5.QtHelp',
    'PyQt5.QtLocation',
    'PyQt5.QtNfc',
    'PyQt5.QtPositioning',
    'PyQt5.QtSensors',
    'PyQt5.QtSerialPort',
    'PyQt5.QtWebSockets',
    'PyQt5.QtWebChannel',
    'PyQt5.QtXmlPatterns',
    'PyQt5.QtBluetooth',
    'PyQt5.QtDBus',
    'PyQt5.QtPrintSupport',
    'PyQt5.QtOpenGL',
    'PyQt5.QtXml',
    'PyQt5.uic',

    # --- Другие GUI-библиотеки -------------------------------------------
    'PyQt6',
    'PySide2',
    'PySide6',

    # --- Тяжёлые научные / data-пакеты, не нужные в рантайме -------------
    'matplotlib',
    #'scipy',
    #'pandas',
    'IPython',
    'jupyter',
    'notebook',
    'nbformat',
    'nbconvert',
    'zmq',
    'tornado',
    'jinja2',
    'pygments',
    'sphinx',
    'docutils',
    'babel',
    'pytz',
    'dateutil',

    # --- pyserial: только Windows-ветка нужна ----------------------------
    'serial.tools.list_ports_linux',
    'serial.tools.list_ports_posix',
    'serial.tools.list_ports_osx',

    # --- pymodbus: клиент используется, сервер — нет --------------------
    'pymodbus.server',
    'pymodbus.repl',
    'pymodbus.simulator',
    'pymodbus.datastore',

    # --- h5py: тесты не нужны -------------------------------------------
    'h5py.tests',
    'h5py._hl.tests',

    # --- multiprocessing: на Windows используется spawn ------------------
    'multiprocessing.popen_fork',
    'multiprocessing.popen_forkserver',
    'multiprocessing.popen_spawn_posix',
    'multiprocessing.dummy',
    'multiprocessing.managers',
    'multiprocessing.pool',

    # --- Тесты и отладка -------------------------------------------------
    'unittest',
    'doctest',
    'pydoc',
    'test',
    'pytest',
    'mammoth',
    'profilehooks',

    # --- Сборка / установка ---------------------------------------------
    'setuptools',
    'pkg_resources',
    'pip',
    'wheel',
    'distutils',
    'lib2to3',
    'idlelib',
    'ensurepip',
    'venv',

    # --- Стандартная библиотека, обычно не нужная в GUI ------------------
    'sqlite3',
    'bz2',
    'lzma',
    'gzip',
    'tarfile',
    'curses',
    'readline',
    'fcntl',
    'termios',
    'tty',
    'pty',
    'pwd',
    'grp',
    'crypt',
    'spwd',
    'nis',
    'syslog',
    'posix',

    # --- Прочее ----------------------------------------------------------
    'tkinter',
    'OpenGL',
    'pydantic',
    "uvicorn",
    "string",

    # раскомментировать только после проверки --------------
    # 'asyncio',
    # 'concurrent',
    # 'selectors',
    # 'email',
    # 'http',
    # 'urllib',
    # 'xml',
    # 'html',
    # 'ftplib',
    # 'telnetlib',
    # 'smtplib',
    # 'poplib',
    # 'imaplib',
    # 'nntplib',
    # 'uuid',
]


def build_python_app():
    """Сборка exe через PyInstaller с исключением ненужных модулей."""
    args = [
        'main.py',
        '--noconsole',
        '--hidden-import=pyvisa_py',
        '--hidden-import=multiprocessing',
        '--hidden-import=h5py._npystrings',
        '--icon=picture/picture/cat.ico',
        '--clean',
        '--noconfirm',
        # '--add-data="service_scripts;service_scripts"',
        # '--add-data="picture;picture"',
    ]
    args += [f'--exclude-module={mod}' for mod in EXCLUDED_MODULES]

    PyInstaller.__main__.run(args)


def move_file_up_one_directory(filename):
    global VERSION_APP
    current_dir = os.getcwd()
    target_file_path = os.path.join(current_dir, filename)

    if os.path.exists(target_file_path):
        parent_dir = os.path.dirname(current_dir)

        base_name, ext = os.path.splitext(filename)
        new_filename = f"{base_name}_v{VERSION_APP}{ext}"
        new_file_path = os.path.join(parent_dir, new_filename)

        target_path_in_parent = os.path.join(parent_dir, new_filename)

        if os.path.exists(target_path_in_parent):
            os.remove(target_path_in_parent)
            print(f"Существующий файл {new_filename} в родительской директории {target_path_in_parent} был удалён.")

        shutil.move(target_file_path, target_path_in_parent)
        print(f"Файл {filename} успешно перемещён в {parent_dir}.")

        os.rename(target_path_in_parent, new_file_path)
        print(f"Файл был переименован в {new_filename}.")
    else:
        print(f"Файл {filename} не найден в текущей директории.")


def find_inno_setup_compiler():
    possible_directories = [
        r"C:\Program Files (x86)\Inno Setup 6",
        r"C:\Program Files\Inno Setup 6",
    ]
    for directory in possible_directories:
        iscc_path = os.path.join(directory, 'iscc.exe')
        if os.path.exists(iscc_path):
            return iscc_path

    raise FileNotFoundError("Inno Setup Compiler (iscc.exe) не найден в стандартных директориях.")


def build_inno_setup(script_path):
    try:
        inno_setup_compiler = find_inno_setup_compiler()
        subprocess.run([inno_setup_compiler, script_path], check=True)
        print("Inno Setup build successful.")
    except subprocess.CalledProcessError as e:
        print(f"Error during Inno Setup build: {e}")
    except FileNotFoundError as e:
        print(e)


def build_instruction():
    # Определяем базовую директорию (на уровень выше скрипта)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    default_input = os.path.join(base_dir, "instruction.docx")
    default_output = os.path.dirname(os.path.abspath(__file__))

    if not os.path.exists(default_input):
        print(f"Ошибка: Файл инструкции {default_input} не найден")
        return False

    html_path = convert_docx_to_html(default_input, default_output)
    return html_path


def remove_all_exe(directory):
    if os.path.exists(directory):
        for file in os.listdir(directory):
            if file.endswith('.exe'):
                print(f"Удалено: {os.path.join(directory, file)}")
                os.remove(os.path.join(directory, file))

if __name__ == "__main__":

    instruction_path = build_instruction()
    if instruction_path:

        if os.path.exists('dist'):
            shutil.rmtree('dist')

        build_python_app()
        print("------------------------------------------------------------")

        if os.path.exists('build'):
            shutil.rmtree('build')

        if os.path.exists("main.spec"):
            os.remove("main.spec")

        inno_script_path = 'default.iss'
        build_inno_setup(inno_script_path)

        if os.path.exists('dist'):
            try:
                shutil.rmtree('dist')
            except Exception as e:
                print(f"Error deleting dist folder: {e}")

        current_dir = os.getcwd()
        remove_all_exe(os.path.dirname(current_dir))

        move_file_up_one_directory('installation_controller.exe')

        remove_pycaches(os.getcwd())

        os.remove(instruction_path)
        