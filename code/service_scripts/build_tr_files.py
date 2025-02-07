import os
import subprocess

current_directory = os.path.dirname(os.path.abspath(__file__))

directory = os.path.dirname(current_directory)

common_ts_file = os.path.join(directory, r'translations\translation_en.ts')

excluded_files = ['excluded_file.py']
excluded_dirs = ['miscellaneous', 'dataset', 'log_files'] 

def should_exclude(path):
    return (any(os.path.basename(path) == file for file in excluded_files) or
            any(os.path.basename(path) in excluded_dirs for dir in excluded_dirs) or
            any(os.path.dirname(path).endswith(dir) for dir in excluded_dirs))

def find_python_files_and_generate_common_ts():
    python_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]

        for file in files:
            if file.endswith('.py') and not should_exclude(os.path.join(root, file)):
                python_files.append(os.path.join(root, file))
                print(file)

    if python_files:

        command = 'pylupdate5 ' + " ".join(python_files) + ' -ts ' + common_ts_file
        try:
            subprocess.run(command, check=True)
            print(f'Created: {common_ts_file}')
        except subprocess.CalledProcessError as e:
            print(f'Error generating ts for files: {e}')

if __name__ == "__main__":
    find_python_files_and_generate_common_ts()