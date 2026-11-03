# code/file_io/dispatch.py
"""Единая точка входа чтения: load_file.

Каскад разрешения конфликтов — в одной функции.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .document import RawDocument
from .errors import AmbiguousFileError, UnknownKindError
from .readers import read_file
from .registry import ParserInfo, _PARSERS


ParserChoice = Callable[[Path, list[ParserInfo]], ParserInfo]


def load_file(
    path: Path | str,
    *,
    hint: str | None = None,
    on_ambiguous: ParserChoice | None = None,
) -> Any:
    """Прочитать файл, найти парсер модели и вернуть объект.

    :param path: путь к файлу.
    :param hint: явный kind, если вызывающий его знает.
    :param on_ambiguous: колбэк выбора при неоднозначности. В headless-режиме
        None — тогда бросается AmbiguousFileError.
    """
    path = Path(path)
    doc = read_file(path)

    candidates = _parsers_for_format(doc.format)
    candidates = _filter_by_hint(candidates, hint)
    candidates = _filter_by_kind_field(candidates, doc)
    candidates = _filter_by_can_parse(candidates, doc)

    if not candidates:
        raise UnknownKindError(
            path=path, hint=hint, candidates=list(_PARSERS.values())
        )
    if len(candidates) == 1:
        return candidates[0].parse(doc)

    if on_ambiguous is not None:
        chosen = on_ambiguous(path, candidates)
        return chosen.parse(doc)

    raise AmbiguousFileError(path=path, candidates=candidates)


def _parsers_for_format(fmt: str) -> list[ParserInfo]:
    return [p for p in _PARSERS.values() if fmt in p.formats]


def _filter_by_hint(candidates: list[ParserInfo], hint: str | None) -> list[ParserInfo]:
    if not hint:
        return candidates
    return [p for p in candidates if p.kind == hint]


def _filter_by_kind_field(candidates: list[ParserInfo], doc: RawDocument) -> list[ParserInfo]:
    """Сужаем по kind в самом файле. Старые файлы без kind проходят дальше."""
    if not isinstance(doc.payload, dict):
        return candidates
    kind_in_file = doc.payload.get("kind")
    if not isinstance(kind_in_file, str) or not kind_in_file:
        return candidates
    return [p for p in candidates if p.kind == kind_in_file]


def _filter_by_can_parse(candidates: list[ParserInfo], doc: RawDocument) -> list[ParserInfo]:
    result: list[ParserInfo] = []
    for p in candidates:
        try:
            if p.can_parse(doc):
                result.append(p)
        except Exception:
            # Битый can_parse не должен ронять весь dispatch — просто пропускаем.
            continue
    return result