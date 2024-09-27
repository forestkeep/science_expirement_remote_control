import os
import shutil

import PyInstaller.__main__

PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--noconsole',  # или '--windowed'
    '--hidden-import=pyvisa_py',
    '--add-data=picture/*:picture',  # Добавление всех файлов из папки picture
    '--exclude-module=PyQt6',  # Исключение модуля PyQt6
    '--clean'
])


0.

# Путь к папке build
build_dir = 'build'

# Удаление папки build, если она существует
if os.path.exists(build_dir):
    shutil.rmtree(build_dir)