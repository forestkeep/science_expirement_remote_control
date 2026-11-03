# code/file_io/readers.py
"""Единый слой чтения: формат → RawDocument.

Каждый reader знает только свой формат. Ошибки оборачиваются в типизированные
ReadError с позицией. Reader не бросает исключений «наружу» — только через
ReadError/UnsupportedFormatError.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable

from .document import RawDocument, Table
from .errors import ReadError, UnsupportedFormatError


_READERS: dict[str, Callable[[Path], RawDocument]] = {}


def register_reader(fmt: str, fn: Callable[[Path], RawDocument]) -> None:
    _READERS[fmt.lower()] = fn


def read_file(path: Path | str) -> RawDocument:
    path = Path(path)
    fmt = path.suffix.lstrip(".").lower()
    if fmt not in _READERS:
        raise UnsupportedFormatError(path=path, format=fmt or "<no extension>")
    return _READERS[fmt](path)


def _strip_bom(raw: bytes) -> bytes:
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:]
    return raw


def _read_bytes(path: Path) -> RawDocument:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ReadError(path=path, position=0, reason=str(exc)) from exc
    return RawDocument(
        format=path.suffix.lstrip(".").lower(),
        path=path,
        size=len(data),
        payload=data,
        meta={},
    )


def _read_json(path: Path) -> RawDocument:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ReadError(path=path, position=0, reason=str(exc)) from exc
    raw = _strip_bom(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReadError(path=path, position=exc.start, reason=f"utf-8: {exc.reason}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReadError(path=path, position=(exc.lineno, exc.colno), reason=exc.msg) from exc
    if not isinstance(data, dict):
        raise ReadError(path=path, position=0, reason="top-level JSON must be an object")
    return RawDocument(
        format="json",
        path=path,
        size=len(raw),
        payload=data,
        meta={"encoding": "utf-8"},
    )


def _read_ns(path: Path) -> RawDocument:
    """Файлы .ns — это JSON-объекты, но с отдельным форматом-идентификатором.

    Так парсер InstallationSpec не конкурирует с другими JSON-моделями.
    """
    doc = _read_json(path)
    return RawDocument(
        format="ns",
        path=doc.path,
        size=doc.size,
        payload=doc.payload,
        meta=dict(doc.meta),
    )


def _read_csv(path: Path) -> RawDocument:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ReadError(path=path, position=0, reason=str(exc)) from exc
    raw = _strip_bom(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReadError(path=path, position=exc.start, reason=f"utf-8: {exc.reason}") from exc
    try:
        reader = csv.DictReader(text.splitlines())
        rows = [dict(row) for row in reader]
        columns = list(reader.fieldnames or [])
    except csv.Error as exc:
        raise ReadError(path=path, position=None, reason=str(exc)) from exc
    return RawDocument(
        format="csv",
        path=path,
        size=len(raw),
        payload=Table(rows=rows, columns=columns),
        meta={"encoding": "utf-8"},
    )


def _read_xlsx(path: Path) -> RawDocument:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ReadError(path=path, position=None, reason=f"openpyxl required: {exc}") from exc
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        raise ReadError(path=path, position=0, reason=str(exc)) from exc
    try:
        sheet = wb.active
        rows_iter = sheet.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            return RawDocument(
                format="xlsx",
                path=path,
                size=path.stat().st_size,
                payload=Table(rows=[], columns=[]),
                meta={"sheet": sheet.title},
            )
        columns = [str(c) if c is not None else "" for c in header_row]
        rows: list[dict] = []
        for row in rows_iter:
            rows.append(
                {columns[i]: (row[i] if i < len(row) else None) for i in range(len(columns))}
            )
        return RawDocument(
            format="xlsx",
            path=path,
            size=path.stat().st_size,
            payload=Table(rows=rows, columns=columns),
            meta={"sheet": sheet.title},
        )
    finally:
        try:
            wb.close()
        except Exception:
            pass


def _read_hdf5(path: Path) -> RawDocument:
    """HDF5 читается как bytes. Структурный разбор — отдельная задача
    (HDF5Facade), reader в dispatch только гарантирует формат и размер.
    """
    return _read_bytes(path)


register_reader("json", _read_json)
register_reader("ns", _read_ns)
register_reader("csv", _read_csv)
register_reader("xlsx", _read_xlsx)
register_reader("xlsm", _read_xlsx)
register_reader("buf", _read_bytes)
register_reader("txt", _read_bytes)
register_reader("hdf5", _read_hdf5)
register_reader("h5", _read_hdf5)