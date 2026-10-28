"""Реестр кодеков типов для HDF5-сериализации.

Codec кодирует python-значение в примитив, который HDF5 умеет хранить
(str / int / float / bool / bytes / ndarray), и валидирует обратный путь.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class Codec(ABC):
    @abstractmethod
    def encode(self, value: Any) -> Any: ...

    @abstractmethod
    def decode(self, raw: Any) -> Any: ...


def _to_str(raw: Any) -> str:
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return "" if raw is None else str(raw)


class StrCodec(Codec):
    def encode(self, value): return _to_str(value)
    def decode(self, raw): return _to_str(raw)


class StrOrNoneCodec(Codec):
    def encode(self, value):
        return "" if value is None else str(value)
    def decode(self, raw):
        s = _to_str(raw)
        return None if s in ("", "None") else s


class IntCodec(Codec):
    def encode(self, value):
        return 0 if value is None else int(value)
    def decode(self, raw):
        return int(_to_str(raw)) if isinstance(raw, (bytes, str)) else int(raw)


class FloatCodec(Codec):
    def encode(self, value):
        return 0.0 if value is None else float(value)
    def decode(self, raw):
        return float(_to_str(raw)) if isinstance(raw, (bytes, str)) else float(raw)


class BoolCodec(Codec):
    def encode(self, value): return bool(value)
    def decode(self, raw):
        if isinstance(raw, (bytes, str)):
            return _to_str(raw).lower() in ("1", "true", "yes", "on")
        return bool(raw)


class IntOrNoneCodec(Codec):
    """None ↔ -1 (совместимо со старым форматом)."""
    MISSING = -1
    def encode(self, value):
        return self.MISSING if value is None else int(value)
    def decode(self, raw):
        v = int(_to_str(raw)) if isinstance(raw, (bytes, str)) else int(raw)
        return None if v == self.MISSING else v


class IntInSetCodec(Codec):
    """int со строгой валидацией принадлежности множеству.

    Невалидное значение → ValueError; reader сам подставит attr.default
    с записью в лог (единая политика «битых полей»).
    """
    def __init__(self, allowed, missing=-1):
        self.allowed = set(allowed)
        self.missing = missing

    def encode(self, value):
        if value is None:
            return self.missing
        try:
            iv = int(value)
        except (TypeError, ValueError):
            return self.missing
        return iv if iv in self.allowed else self.missing

    def decode(self, raw):
        v = int(_to_str(raw)) if isinstance(raw, (bytes, str)) else int(raw)
        if v not in self.allowed:
            raise ValueError(f"value {v} not in {sorted(self.allowed)}")
        return v


class DatetimeCodec(Codec):
    def encode(self, value):
        return "" if value is None else value.isoformat()
    def decode(self, raw):
        s = _to_str(raw)
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"not ISO datetime: {s!r}") from exc


class JsonCodec(Codec):
    def encode(self, value):
        if value is None:
            return "{}"
        return json.dumps(value, ensure_ascii=False, default=str)
    def decode(self, raw):
        s = _to_str(raw)
        if not s:
            return {}
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"invalid JSON: {s[:80]!r}") from exc


class TupleFloatCodec(Codec):
    def encode(self, value):
        if value is None:
            return ""
        return json.dumps([float(v) for v in value])
    def decode(self, raw):
        s = _to_str(raw)
        if not s:
            return None
        try:
            data = json.loads(s)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"invalid tuple: {s!r}") from exc
        if not isinstance(data, (list, tuple)) or len(data) != 2:
            raise ValueError(f"expected 2-tuple, got {data!r}")
        return (float(data[0]), float(data[1]))


class NumpyCodec(Codec):
    def encode(self, value):
        return None if value is None else np.asarray(value)
    def decode(self, raw):
        return None if raw is None else np.asarray(raw)


class PenStyleCodec(Codec):
    """Qt.PenStyle ↔ строка ("Solid", "Dash", "Dot", "DashDot", "DashDotDot")."""
    @staticmethod
    def _names():
        from PyQt5 import QtCore
        return {
            QtCore.Qt.SolidLine: "Solid",
            QtCore.Qt.DashLine: "Dash",
            QtCore.Qt.DotLine: "Dot",
            QtCore.Qt.DashDotLine: "DashDot",
            QtCore.Qt.DashDotDotLine: "DashDotDot",
        }

    def encode(self, value):
        names = self._names()
        if isinstance(value, str):
            return value if value in names.values() else "Solid"
        return names.get(value, "Solid")

    def decode(self, raw):
        s = _to_str(raw) or "Solid"
        names = self._names()
        for enum_val, name in names.items():
            if name == s:
                return enum_val
        # старое могло быть числом
        for enum_val, name in names.items():
            if str(int(enum_val)) == s:
                return enum_val
        return names_enum_solid()


def names_enum_solid():
    from PyQt5 import QtCore
    return QtCore.Qt.SolidLine


class ColorCodec(Codec):
    def encode(self, value):
        if value is None:
            return "#ffffff"
        if hasattr(value, "name"):
            return value.name()
        if isinstance(value, (tuple, list)) and len(value) >= 3:
            return f"#{int(value[0]):02x}{int(value[1]):02x}{int(value[2]):02x}"
        return str(value)
    def decode(self, raw):
        return _to_str(raw) or "#ffffff"


class QFontCodec(Codec):
    def encode(self, value):
        if value is None:
            return ""
        return value.toString() if hasattr(value, "toString") else str(value)
    def decode(self, raw):
        from PyQt5 import QtGui
        s = _to_str(raw)
        font = QtGui.QFont()
        if s:
            font.fromString(s)
        return font


# ---------------------------------------------------------------------------
# Реестр
# ---------------------------------------------------------------------------
_CODECS: dict[str, Codec] = {}


def register_codec(name: str, codec: Codec) -> None:
    if name in _CODECS:
        logger.warning("codec %r re-registered", name)
    _CODECS[name] = codec


def get_codec(name: str) -> Codec:
    try:
        return _CODECS[name]
    except KeyError as exc:
        raise KeyError(f"codec {name!r} not registered") from exc


register_codec("str", StrCodec())
register_codec("str_or_none", StrOrNoneCodec())
register_codec("int", IntCodec())
register_codec("float", FloatCodec())
register_codec("bool", BoolCodec())
register_codec("int_or_none", IntOrNoneCodec())
register_codec("int_axis", IntInSetCodec({1, 2}))
register_codec("datetime", DatetimeCodec())
register_codec("json", JsonCodec())
register_codec("tuple_float", TupleFloatCodec())
register_codec("ndarray", NumpyCodec())
register_codec("pen_style", PenStyleCodec())
register_codec("color", ColorCodec())
register_codec("qfont", QFontCodec())