"""
Сканирует папку с Python-файлами и собирает список реально используемых
импортов, разделяя их на:

    * ВНУТРЕННИЕ  — top-level модуль найден среди файлов/папок проекта;
    * ВНЕШНИЕ    — top-level модуль не найден в проекте
                   (стандартная библиотека или установленные пакеты).

Вывод сортируется по количеству вхождений (число файлов) по убыванию.

Использование:
    python scan_imports.py <путь_к_папке>
    python scan_imports.py . --all
    python scan_imports.py . --top-level
    python scan_imports.py . --json report.json
    python scan_imports.py . --min-count 2
    python scan_imports.py . --show-files
    python scan_imports.py . --internal
    python scan_imports.py . --external
"""

import ast
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict


SKIP_DIRS = {
    '__pycache__', '.git', '.hg', '.svn',
    '.venv', 'venv', 'env', '.env', '.venv_build',
    '.idea', '.vscode',
    'build', 'dist', 'node_modules',
    '.tox', '.mypy_cache', '.pytest_cache', '.ruff_cache',
}


# ---------------------------------------------------------------------
#  Определение стандартной библиотеки
# ---------------------------------------------------------------------
def _stdlib_names() -> set:
    """Возвращает множество имён top-level модулей стандартной библиотеки."""
    if hasattr(sys, 'stdlib_module_names'):
        return set(sys.stdlib_module_names)
    # Fallback для Python < 3.10 — только встроенные модули
    return set(sys.builtin_module_names)


STDLIB = _stdlib_names()


# ---------------------------------------------------------------------
#  AST-анализ одного файла
# ---------------------------------------------------------------------
def _root_name(node):
    """Возвращает корневое Name для Attribute-цепочки (a.b.c -> 'a')."""
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def analyze_file(path: Path):
    """
    Возвращает (used, all_imported):
        used         — полные имена модулей, которые реально используются;
        all_imported — все импортированные полные имена (для справки).
    """
    try:
        src = path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        return set(), set()

    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return set(), set()

    imported = {}       # local_name -> full_module_path
    star_imports = []   # for "from x import *"
    used_local = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split('.')[0]
                imported[local] = alias.name

        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ''
            for alias in node.names:
                if alias.name == '*':
                    star_imports.append(mod)
                else:
                    local = alias.asname or alias.name
                    imported[local] = f"{mod}.{alias.name}" if mod else alias.name

        elif isinstance(node, ast.Name):
            used_local.add(node.id)

        elif isinstance(node, ast.Attribute):
            root = _root_name(node)
            if root:
                used_local.add(root)

    used = {full for local, full in imported.items() if local in used_local}
    used.update(star_imports)

    all_imported = set(imported.values()) | set(star_imports)
    return used, all_imported


# ---------------------------------------------------------------------
#  Сканирование проекта
# ---------------------------------------------------------------------
def collect_local_names(folder: Path) -> set:
    """
    Возвращает множество top-level имён, которые есть в самом проекте:
    имена .py-файлов и имена папок верхнего уровня.
    """
    local = set()
    for child in folder.iterdir():
        if child.name in SKIP_DIRS:
            continue
        if child.is_file() and child.suffix == '.py':
            local.add(child.stem)
        elif child.is_dir():
            # папка считается пакетом, если в ней есть __init__.py
            # или .py-файлы (namespace-package)
            local.add(child.name)
    return local


def scan_folder(folder: Path):
    used_map = defaultdict(set)   # full_module -> files (где используется)
    all_map = defaultdict(set)    # full_module -> files (где импортируется)

    for py_file in folder.rglob('*.py'):
        if any(part in SKIP_DIRS for part in py_file.parts):
            continue
        used, all_imported = analyze_file(py_file)
        rel = str(py_file.relative_to(folder))
        for name in used:
            used_map[name].add(rel)
        for name in all_imported:
            all_map[name].add(rel)

    return used_map, all_map


# ---------------------------------------------------------------------
#  Агрегация / классификация
# ---------------------------------------------------------------------
def top_level(name: str) -> str:
    return name.split('.')[0]


def aggregate_top(mapping):
    result = defaultdict(set)
    for name, files in mapping.items():
        result[top_level(name)].update(files)
    return result


def split_by_origin(mapping, local_names):
    """
    Делит mapping {module -> files} на два словаря:
        internal — top-level модуль есть в проекте;
        external — top-level модуль не найден в проекте.
    """
    internal = {}
    external = {}
    for name, files in mapping.items():
        if top_level(name) in local_names:
            internal[name] = files
        else:
            external[name] = files
    return internal, external


def sort_by_count(mapping, min_count=1):
    """Сортирует {name -> files} по убыванию len(files), затем по имени."""
    items = [(name, files) for name, files in mapping.items() if len(files) >= min_count]
    items.sort(key=lambda kv: (-len(kv[1]), kv[0].lower()))
    return items


# ---------------------------------------------------------------------
#  Печать
# ---------------------------------------------------------------------
def _mark_origin(name: str) -> str:
    """Метка [stdlib]/[third-party] для внешних модулей."""
    return "[stdlib]     " if top_level(name) in STDLIB else "[third-party]"


def print_section(title, items, show_files=False, external=False):
    print()
    print("=" * 78)
    print(f"{title}  ({len(items)})")
    print("=" * 78)
    if not items:
        print("  (нет)")
        return
    for name, files in items:
        prefix = f"{_mark_origin(name)} " if external else "             "
        print(f"  {len(files):>4}× {prefix}{name}")
        if show_files:
            for f in sorted(files):
                print(f"           └─ {f}")


# ---------------------------------------------------------------------
#  main
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Сканер импортов в Python-файлах с сортировкой по количеству вхождений."
    )
    parser.add_argument('folder', nargs='?', default='.', help="Папка для сканирования")
    parser.add_argument('--all', action='store_true',
                        help="Показать также импорты, которые не используются")
    parser.add_argument('--top-level', action='store_true',
                        help="Агрегировать до верхнеуровневых пакетов (os, PyQt5, ...)")
    parser.add_argument('--json', metavar='FILE', help="Сохранить отчёт в JSON")
    parser.add_argument('--min-count', type=int, default=1,
                        help="Показывать модули, встречающиеся минимум N раз (по умолчанию 1)")
    parser.add_argument('--show-files', action='store_true',
                        help="Показывать список файлов для каждого модуля")
    parser.add_argument('--internal', action='store_true',
                        help="Показать только внутренние модули проекта")
    parser.add_argument('--external', action='store_true',
                        help="Показать только внешние модули")
    args = parser.parse_args()

    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        print(f"Не найдена папка: {folder}", file=sys.stderr)
        sys.exit(1)

    local_names = collect_local_names(folder)
    used_map, all_map = scan_folder(folder)

    if args.top_level:
        used_map = aggregate_top(used_map)
        all_map = aggregate_top(all_map)

    # Делим реально используемые на внутренние/внешние
    used_internal, used_external = split_by_origin(used_map, local_names)

    used_internal_items = sort_by_count(used_internal, args.min_count)
    used_external_items = sort_by_count(used_external, args.min_count)

    # Неиспользуемые (для --all)
    unused_map = {name: files for name, files in all_map.items() if name not in used_map}
    if args.top_level:
        unused_map = dict(aggregate_top(unused_map))
    unused_internal, unused_external = split_by_origin(unused_map, local_names)
    unused_internal_items = sort_by_count(unused_internal, args.min_count)
    unused_external_items = sort_by_count(unused_external, args.min_count)

    # ------------------- вывод -------------------
    print(f"Папка: {folder}")
    print(f"Локальных top-level имён в проекте: {len(local_names)}")
    print(f"Модулей реально используется:       {len(used_map)}")
    print(f"  ├─ внутренних:                   {len(used_internal)}")
    print(f"  └─ внешних:                      {len(used_external)}")

    show_all = args.all
    show_internal = not args.external or args.internal
    show_external = not args.internal or args.external

    if show_internal:
        print_section("ВНУТРЕННИЕ МОДУЛИ ПРОЕКТА (используются)",
                      used_internal_items, args.show_files)
        if show_all:
            print_section("ВНУТРЕННИЕ МОДУЛИ ПРОЕКТА (импортируются, но не используются)",
                          unused_internal_items, args.show_files)

    if show_external:
        print_section("ВНЕШНИЕ МОДУЛИ (не найдены в проекте) — используются",
                      used_external_items, args.show_files, external=True)
        if show_all:
            print_section("ВНЕШНИЕ МОДУЛИ (не найдены в проекте) — импортируются, но не используются",
                          unused_external_items, args.show_files, external=True)

    # ------------------- JSON -------------------
    if args.json:
        data = {
            'folder': str(folder),
            'local_top_level_names': sorted(local_names),
            'used': {
                'internal': {k: sorted(v) for k, v in used_internal.items()},
                'external': {k: sorted(v) for k, v in used_external.items()},
            },
            'unused': {
                'internal': {k: sorted(v) for k, v in unused_internal.items()},
                'external': {k: sorted(v) for k, v in unused_external.items()},
            },
        }
        Path(args.json).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        print(f"\nJSON сохранён в {args.json}")


if __name__ == '__main__':
    main()