# code/file_io/__init__.py
"""Публичный API файлового слоя.

Точки входа для UI и Store'ов:
    load_file(path, *, hint, on_ambiguous) — единое чтение;
    save_file(obj, path, *, format) — единая запись;
    scan_folder(path, extensions, *, hint) — pull-режим поверх load_file.

Регистрация парсеров/writer'ов — через @register / @register_writer
рядом с моделями. register_all_parsers(model_modules) вызывается на
старте приложения; assert_registry_complete / assert_writer_registry_complete
проверяют, что набор моделей совпадает с ожидаемым.
"""
from .document import RawDocument, Reader, Table
from .dispatch import load_file
from .errors import (
    AmbiguousFileError,
    AmbiguousWriterError,
    FileError,
    MissingFieldError,
    NoWriterError,
    ReadError,
    UnknownKindError,
    UnsupportedFormatError,
    UnsupportedVersionError,
    WriteError,
)
from .pull import ScanResult, scan_folder
from .readers import read_file, register_reader
from .registry import (
    ParserInfo,
    WriterInfo,
    assert_registry_complete,
    assert_writer_registry_complete,
    parsers_snapshot,
    register,
    register_all_parsers,
    register_writer,
    writers_snapshot,
)
from .writers import save_file

__all__ = [
    # контракт данных
    "RawDocument", "Table", "Reader",
    # точки входа
    "load_file", "save_file", "scan_folder", "ScanResult", "read_file",
    # регистрация
    "register", "register_writer", "register_all_parsers",
    "assert_registry_complete", "assert_writer_registry_complete",
    "register_reader",
    "ParserInfo", "WriterInfo",
    "parsers_snapshot", "writers_snapshot",
    # ошибки
    "FileError", "ReadError", "UnsupportedFormatError", "UnknownKindError",
    "AmbiguousFileError", "MissingFieldError", "UnsupportedVersionError",
    "NoWriterError", "AmbiguousWriterError", "WriteError",
]