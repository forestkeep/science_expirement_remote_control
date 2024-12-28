import subprocess
import os
import shutil

import PyInstaller.__main__

from clear_dir import remove_pycaches
from installation_controller import VERSION_APP

def build_python_app():
    PyInstaller.__main__.run([
    'installation_controller.py',
    #'--onefile',
    '--noconsole', 
    '--hidden-import=pyvisa_py',
    #'--add-data=picture/*:picture',  
    '--exclude-module=PyQt6',  
    '--icon=picture/picture/cat.ico',
    '--clean',
    '--noconfirm'
    ])

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
        try:
            shutil.rmtree('dist')
        except Exception as e:
            print(f"Error deleting dist folder: {e}")
    
    
    move_file_up_one_directory('installation_controller.exe')

    remove_pycaches(os.getcwd())