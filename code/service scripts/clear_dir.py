import os
import shutil

def remove_pycaches(start_dir):
    for root, dirs, files in os.walk(start_dir):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            shutil.rmtree(pycache_path)
            print(f'Удалена папка: {pycache_path}')

if __name__ == "__main__":
    current_directory = os.getcwd()
    parent_directory = os.path.dirname(current_directory)
    remove_pycaches(parent_directory)
    print("exit")
