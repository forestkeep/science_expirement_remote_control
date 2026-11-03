# code/file_io/document.py
"""Контракт данных слоя I/O: RawDocument, Table, Reader."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, Union


@dataclass
class Table:
    """Единый табличный payload для csv/xlsx. Никаких DataFrame-обёрток."""

    rows: list[dict[str, Any]]
    columns: list[str]


@dataclass
class RawDocument:
    """Единый результат чтения. См. ТЗ «Контракт RawDocument».

    payload нормализуется по формату:
      * json / yaml / toml / ns → dict[str, Any];
      * csv / xlsx → Table;
      * buf / binary → bytes.
    """

    format: str
    path: Path | None
    size: int
    payload: Union[dict[str, Any], Table, bytes]
    meta: dict[str, Any] = field(default_factory=dict)


class Reader(Protocol):
    """Протокол reader'а формата: путь → RawDocument или ReadError."""

    def __call__(self, path: Path) -> RawDocument: ...