import os
import importlib.util
import sys
import pathlib
import pytest

def import_all_modules(start_dir: str, exclude_patterns: list = None) -> list:
    """
    Рекурсивно импортирует все .py файлы в директории.
    Возвращает список ошибок в формате: (путь_к_файлу, имя_модуля, ошибка)
    """
    if exclude_patterns is None:
        exclude_patterns = []
    
    failed_imports = []
    start_path = pathlib.Path(start_dir)
    
    for file_path in start_path.rglob("*.py"):

        if any(pattern in str(file_path) for pattern in exclude_patterns):
            continue
            
        rel_path = file_path.relative_to(start_path)
        module_name = str(rel_path.with_suffix("")).replace(os.sep, ".")
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            #print(f"✓ Успех: {module_name}")
        except Exception as e:
            failed_imports.append((str(file_path), module_name, str(e)))
            print(f"✕ Ошибка: {module_name} -> {str(e)}")
    
    return failed_imports

def test_all_imports():
    print("test_all_imports")
    project_root = pathlib.Path(__file__).parent.parent
    source_dir = project_root / "code"
    
    exclude_patterns = [
        "myenv",
        "__pycache__",
        ".pytest_cache",
        "rebuild_all.py",
        "service_scripts",
        "web",
    ]
    
    errors = import_all_modules(str(source_dir), exclude_patterns)
    
    if errors:
        error_details = "\n".join(
            [f"Файл: {file}\nМодуль: {mod}\nОшибка: {err}\n" for file, mod, err in errors]
        )
        pytest.fail(f"Обнаружены ошибки импорта ({len(errors)}):\n{error_details}")

#pytest tests/test_imports.py -v