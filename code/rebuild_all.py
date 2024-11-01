import subprocess
import os
import shutil

import PyInstaller.__main__

import clear_dir

def build_python_app():
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

def move_file_up_one_directory(filename='my.exe'):
    current_dir = os.getcwd()
    target_file_path = os.path.join(current_dir, filename)
    
    if os.path.exists(target_file_path):
        parent_dir = os.path.dirname(current_dir)
        parent_dir = os.path.dirname(parent_dir)
        shutil.move(target_file_path, os.path.join(parent_dir, filename))
        print(f"Файл {filename} успешно перемещён в {parent_dir}.")
    else:
        print(f"Файл {filename} не найден в текущей директории.")

def find_inno_setup_compiler():
    # Предположим, что Inno Setup установлен в этой стандартной директории
    possible_directories = [
        r"C:\Program Files (x86)\Inno Setup 6",
        r"C:\Program Files\Inno Setup 6"
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

if __name__ == "__main__":

    if os.path.exists('dist'):
        shutil.rmtree('dist')

    build_python_app()
    
    if os.path.exists('build'):
        shutil.rmtree('build')

    if os.path.exists("installation_controller.spec"):
        os.remove("installation_controller.spec")

    inno_script_path = 'default.iss'
    build_inno_setup(inno_script_path)

    if os.path.exists('dist'):
        shutil.rmtree('dist')
        

    move_file_up_one_directory('installation_controller.exe')

    clear_dir.remove_pycaches(os.getcwd())