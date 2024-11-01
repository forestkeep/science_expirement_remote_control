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

import os
import shutil

import PyInstaller.__main__

if os.path.exists('dist'):
    shutil.rmtree('dist')

PyInstaller.__main__.run([
    'installation_controller.py',
    #'--onefile',
    '--noconsole', 
    '--hidden-import=pyvisa_py',
    #'--add-data=picture/*:picture',  # Добавление всех файлов из папки picture
    '--exclude-module=PyQt6',  # Исключение модуля PyQt6
    '--icon=picture/picture/cat.ico',  # Добавление иконки
    '--clean',
    '--noconfirm'
])

if os.path.exists('build'):
    shutil.rmtree('build')

if os.path.exists("installation_controller.spec"):
    os.remove("installation_controller.spec")