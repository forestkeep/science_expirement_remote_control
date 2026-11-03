# code/file_io/writers.py
"""Единая точка записи: save_file.

Симметрично dispatch.load_file: находит writer модели, сериализует
в RawDocument, пишет атомарно (temp-файл + fsync + os.replace).
Частично записанных файлов не остаётся.

HDF5 в этот слой не входит: структурная запись идёт через
graphs.hdf5_io.HDF5Facade/HDF5File. Попытка save_file(..., "x.hdf5")
явно бросает WriteError.

meta в RawDocument используется здесь: `meta["sheet"]` задаёт имя
листа для xlsx (по умолчанию "Sheet").
"""
from __future__ import annotations

import csv
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from .document import RawDocument, Table
from .errors import AmbiguousWriterError, NoWriterError, WriteError
from .registry import WriterInfo, _WRITERS

logger = logging.getLogger(__name__)


def save_file(
    obj: Any,
    path: Path | str,
    *,
    format: str | None = None,
) -> None:
    """Сериализовать объект и записать атомарно.

    :param path: целевой путь; используется для вывода расширения.
    :param format: явный формат (если None — берётся из расширения).
    """
    path = Path(path)
    fmt = (format or path.suffix.lstrip(".") or "").lower()
    if not fmt:
        raise NoWriterError(
            path=path, format="<no extension>", obj_type=type(obj).__name__
        )

    candidates = [
        w for w in _WRITERS if fmt in w.formats and _safe_can_write(w, obj)
    ]
    if not candidates:
        raise NoWriterError(path=path, format=fmt, obj_type=type(obj).__name__)
    if len(candidates) > 1:
        raise AmbiguousWriterError(path=path, candidates=candidates)

    writer = candidates[0]
    try:
        doc = writer.serialize(obj)
    except Exception as exc:
        raise WriteError(
            path=path, position=None, reason=f"serialize: {exc}"
        ) from exc
    if not isinstance(doc, RawDocument):
        raise WriteError(
            path=path,
            position=None,
            reason=f"serialize returned {type(doc).__name__}, expected RawDocument",
        )

    # Сверка формата: writer зарегистрирован под fmt и мог вернуть
    # RawDocument с другим doc.format (баг в serialize). Без проверки
    # дальше упадёт _write_json/_write_table с невнятным
    # «payload must be dict». Явная проверка даёт точную причину.
    if doc.format != fmt:
        raise WriteError(
            path=path,
            position=None,
            reason=(
                f"writer {writer.kind!r} returned format={doc.format!r}, "
                f"target format={fmt!r}"
            ),
        )

    _atomic_write(doc, path, fmt)


def _safe_can_write(writer: WriterInfo, obj: Any) -> bool:
    try:
        return bool(writer.can_write(obj))
    except Exception:
        return False


def _atomic_write(doc: RawDocument, path: Path, fmt: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=".tmp_" + path.name + ".", suffix=".tmp"
    )
    os.close(fd)
    tmp = Path(tmp_name)
    meta = dict(doc.meta or {})
    try:
        _write_by_format(doc, tmp, fmt, meta)

        # fsync temp-файла: гарантируем, что все байты дошли до диска
        # до os.replace. Без fsync при краше питания между write и
        # replace данные могли остаться в page cache, и os.replace
        # «успешно» подменил бы старый файл на пустой/битый.
        with tmp.open("rb+") as fh:
            os.fsync(fh.fileno())

        os.replace(tmp, path)

        # POSIX: fsync директории, чтобы переименование тоже дошло
        # до диска. На Windows os.open(dir, O_RDONLY) не работает —
        # пропускаем; на NTFS метаданные и так синхронизируются.
        if os.name != "nt":
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)

    except Exception as exc:
        try:
            tmp.unlink()
        except OSError:
            pass
        if isinstance(exc, WriteError):
            raise
        raise WriteError(path=path, position=None, reason=str(exc)) from exc


def _write_by_format(
    doc: RawDocument, path: Path, fmt: str, meta: dict[str, Any]
) -> None:
    if fmt in ("json", "ns"):
        # ns — это тоже JSON, разница только в семантическом kind модели
        # (InstallationSpec) и расширении. Отдельного ns-writer'а не нужно.
        _write_json(doc.payload, path)
    elif fmt in ("csv", "xlsx", "xlsm"):
        _write_table(doc.payload, path, fmt, meta)
    elif fmt in ("buf", "txt"):
        _write_bytes(doc.payload, path)
    elif fmt in ("hdf5", "h5"):
        # HDF5 — не плоский writer. Структурная запись идёт через
        # graphs.hdf5_io.HDF5Facade.save_project / HDF5File.
        # Регистрировать writer для .hdf5 в общем реестре нельзя:
        # save_file записал бы сырые байты с расширением .hdf5,
        # и файл был бы невалидным.
        raise WriteError(
            path=path,
            position=None,
            reason=(
                "HDF5 writing is not supported via save_file; "
                "use graphs.hdf5_io.HDF5Facade.save_project"
            ),
        )
    else:
        raise WriteError(
            path=path, position=None, reason=f"no format writer for {fmt!r}"
        )


def _write_json(payload: Any, path: Path) -> None:
    if not isinstance(payload, dict):
        raise WriteError(
            path=path,
            position=None,
            reason=f"json payload must be dict, got {type(payload).__name__}",
        )
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")


def _write_table(
    payload: Any, path: Path, fmt: str, meta: dict[str, Any]
) -> None:
    if not isinstance(payload, Table):
        raise WriteError(
            path=path,
            position=None,
            reason=f"{fmt} payload must be Table, got {type(payload).__name__}",
        )
    if fmt == "csv":
        with path.open("w", encoding="utf-8", newline="") as f:
            if not payload.rows:
                if payload.columns:
                    f.write(",".join(payload.columns) + "\n")
                return
            writer = csv.DictWriter(f, fieldnames=payload.columns)
            writer.writeheader()
            for row in payload.rows:
                writer.writerow(row)
        return

    # xlsx / xlsm
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise WriteError(
            path=path, position=None, reason=f"openpyxl required: {exc}"
        ) from exc

    sheet_name = str(meta.get("sheet", "Sheet") or "Sheet")

    wb = Workbook()
    ws = wb.active
    try:
        ws.title = sheet_name
    except Exception:
        # Недопустимые символы в имени листа — оставляем дефолтное имя.
        # openpyxl сам валидирует при save, не глушим ошибку полностью,
        # а откатываемся на "Sheet".
        try:
            ws.title = "Sheet"
        except Exception:
            pass

    if payload.columns:
        ws.append(payload.columns)
    for row in payload.rows:
        ws.append([row.get(c) for c in payload.columns])

    try:
        wb.save(str(path))
    finally:
        try:
            wb.close()
        except Exception:
            pass


def _write_bytes(payload: Any, path: Path) -> None:
    if isinstance(payload, bytes):
        path.write_bytes(payload)
    elif isinstance(payload, (dict, Table)):
        raise WriteError(
            path=path,
            position=None,
            reason=f"binary format expects bytes, got {type(payload).__name__}",
        )
    else:
        path.write_bytes(str(payload).encode("utf-8"))