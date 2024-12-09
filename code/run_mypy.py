import os
import subprocess

def run_mypy_on_project(root_dir):
    py_files = []
    
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                py_files.append(os.path.join(dirpath, filename))
    
    if py_files:
        print("Найденные файлы проекта:")
        for py_file in py_files:
            print(f"- {py_file}")
        subprocess.run(['mypy'] + py_files)
    else:
        print("Не найдено файлов проекта")

project_directory = os.path.dirname(os.path.abspath(__file__))
run_mypy_on_project(project_directory)