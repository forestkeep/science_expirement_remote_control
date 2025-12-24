import subprocess
import os
import shutil

import PyInstaller.__main__

from service_scripts.clear_dir import remove_pycaches
from main import VERSION_APP
from service_scripts.convert_instruction import convert_docx_to_html

def build_python_app():
    PyInstaller.__main__.run([
        'main.py',
        '--noconsole', 
        '--hidden-import=pyvisa_py', 
        '--hidden-import=multiprocessing',
        '--hidden-import=h5py._npystrings',
        '--exclude-module=PyQt6,PySide6,PySide2, mammoth, pytest, OpenGL',  
        '--icon=picture/picture/cat.ico',
        '--clean',
        '--noconfirm',
        #'--add-data="service_scripts;service_scripts"',
        #'--add-data="picture;picture"',
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

def build_instruction():
    # Определяем базовую директорию (на уровень выше скрипта)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Пути по умолчанию
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
        #time.sleep(1000)
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
        