# code/file_io/errors.py
"""Типизированные ошибки файлового слоя.

Каждая ошибка несёт путь и, где применимо, позицию (строка/колонка для
текстовых форматов, байтовое смещение для бинарных). UI показывает эти
поля в статус-баре/диалоге, поэтому они часть контракта.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

Position = Optional[Union[tuple[int, int], int]]  # (line, col) | byte offset | None


class FileError(Exception):
    """Базовый класс для всех ошибок файлового слоя."""

    def __init__(
        self,
        path: Optional[Union[str, Path]] = None,
        position: Position = None,
        reason: str = "",
    ) -> None:
        self.path: Optional[Path] = Path(path) if path is not None else None
        self.position: Position = position
        self.reason: str = reason
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts: list[str] = [type(self).__name__]
        if self.path is not None:
            parts.append(f"path={self.path}")
        if self.position is not None:
            parts.append(f"position={self.position}")
        if self.reason:
            parts.append(f"reason={self.reason}")
        return " ".join(parts)


class ReadError(FileError):
    """Битый или невалидный файл."""


class UnsupportedFormatError(FileError):
    """Нет reader'а для данного формата."""

    def __init__(self, path=None, format: str = "", position: Position = None) -> None:
        super().__init__(
            path=path,
            position=position,
            reason=f"unsupported format: {format!r}",
        )
        self.format = format


class UnknownKindError(FileError):
    """Не нашлось парсера после каскада hint → kind → can_parse."""

    def __init__(
        self,
        path=None,
        hint: Optional[str] = None,
        candidates: Optional[list] = None,
        position: Position = None,
    ) -> None:
        reason = "no parser matched"
        if hint:
            reason += f" (hint={hint!r})"
        if candidates:
            reason += f"; available kinds: {[c.kind for c in candidates]}"
        super().__init__(path=path, position=position, reason=reason)
        self.hint = hint
        self.candidates = list(candidates or [])


class AmbiguousFileError(FileError):
    """Несколько парсеров подошли, колбэка нет."""

    def __init__(self, path=None, candidates: Optional[list] = None, position: Position = None) -> None:
        kinds = [getattr(c, "kind", "?") for c in (candidates or [])]
        super().__init__(
            path=path,
            position=position,
            reason=f"multiple parsers matched: {kinds}",
        )
        self.candidates = list(candidates or [])


class MissingFieldError(FileError):
    """Отсутствует обязательное поле."""

    def __init__(self, path=None, field: str = "", position: Position = None) -> None:
        super().__init__(
            path=path,
            position=position,
            reason=f"missing required field: {field!r}",
        )
        self.field = field


class UnsupportedVersionError(FileError):
    """schema_version не поддержан."""

    def __init__(self, path=None, got: int = 0, supported: int = 0, position: Position = None) -> None:
        super().__init__(
            path=path,
            position=position,
            reason=f"unsupported schema_version={got}, supported={supported}",
        )
        self.got = got
        self.supported = supported


class NoWriterError(FileError):
    """Нет writer'а для (obj, format)."""

    def __init__(self, path=None, format: str = "", obj_type: str = "", position: Position = None) -> None:
        super().__init__(
            path=path,
            position=position,
            reason=f"no writer for format={format!r}, obj_type={obj_type!r}",
        )
        self.format = format
        self.obj_type = obj_type


class AmbiguousWriterError(FileError):
    """Несколько writer'ов подошли."""

    def __init__(self, path=None, candidates: Optional[list] = None, position: Position = None) -> None:
        kinds = [getattr(c, "kind", "?") for c in (candidates or [])]
        super().__init__(
            path=path,
            position=position,
            reason=f"multiple writers matched: {kinds}",
        )
        self.candidates = list(candidates or [])


class WriteError(FileError):
    """Ошибка сериализации или записи на диск."""