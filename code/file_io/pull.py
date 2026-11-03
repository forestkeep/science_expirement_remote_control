# code/file_io/pull.py
"""Pull-режим: сканирование папки поверх load_file.

Store'ы используют scan_folder вместо собственных os.listdir+try/except.
Битый файл не роняет автозагрузку — попадает в ScanResult.errors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .dispatch import load_file
from .errors import FileError, ReadError


@dataclass
class ScanResult:
    objects: list[tuple[Path, Any]] = field(default_factory=list)
    errors: list[FileError] = field(default_factory=list)


def scan_folder(
    path: Path | str,
    extensions: list[str] | tuple[str, ...],
    *,
    hint: str | None = None,
) -> ScanResult:
    """Сканирует папку по набору расширений, вызывает load_file на каждом.

    :param extensions: расширения без точки, регистронезависимо.
    :param hint: передаётся в load_file как есть.
    """
    path = Path(path)
    result = ScanResult()
    if not path.is_dir():
        return result

    exts = tuple(e.lower().lstrip(".") for e in extensions)

    try:
        files = sorted(path.iterdir())
    except OSError as exc:
        result.errors.append(
            ReadError(path=path, position=None, reason=f"iterdir failed: {exc}")
        )
        return result

    for f in files:
        if not f.is_file():
            continue
        ext = f.suffix.lstrip(".").lower()
        if ext not in exts:
            continue
        try:
            obj = load_file(f, hint=hint)
            result.objects.append((f, obj))
        except FileError as exc:
            result.errors.append(exc)
        except Exception as exc:  # незапланированный баг в парсере
            result.errors.append(
                ReadError(
                    path=f,
                    position=None,
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
    return result