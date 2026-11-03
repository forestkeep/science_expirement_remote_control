# code/publication/presets/style_profile.py
"""Загрузка/хранение style profile и lab profile.

Два слоя `StyleStack`: `style_profile` — базовый стиль лаборатории/проекта,
`lab_profile` — опциональный более высокий уровень. Оба хранятся как
плоский dict вида {"figure.font.size": 9.0, ...}; раскладка по слоям —
забота `StyleStack`, не этого модуля.

Обе модели зарегистрированы (@register/@register_writer). После добавления
этого файла в `main.py::register_all_parsers(...)` list достаточно один
импорт этого модуля — оба класса регистрируются одновременно.

Старые файлы без `kind` читаются через can_parse-fallback: плоский dict,
в котором есть хотя бы один ключ с точкой (например `figure.font.size`).
Это защищает от случайного совпадения с `FigureSpec` (`width_mm`, `panels`)
и другими JSON-моделями без dotted-keys. Для надёжного разрешения
вызывающий передаёт hint="style_profile"/"lab_profile".
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, ClassVar

from file_io import (
    RawDocument, load_file, register, register_writer,
)
from file_io.errors import (
    FileError, ReadError, UnsupportedVersionError,
)

from .builtin import STYLE_PROFILE_DEFAULT

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared parse logic для двух плоских default-слоёв
# ---------------------------------------------------------------------------

def _can_parse_flat_defaults(doc: RawDocument, kind: str) -> bool:
    """True, если payload похож на плоский dict стилевых дефолтов."""
    if doc.format != "json":
        return False
    data = doc.payload
    if not isinstance(data, dict) or not data:
        return False
    if data.get("kind") == kind:
        return True
    # fallback для старых файлов без kind: хотя бы один dotted-key.
    # Не путается с FigureSpec (width_mm, panels) и прочими моделями
    # без точек в ключах.
    return any(isinstance(k, str) and "." in k for k in data)


def _parse_flat_defaults(
    doc: RawDocument, kind: str, schema_version: int
) -> tuple[dict[str, Any], int]:
    data = doc.payload
    assert isinstance(data, dict)
    version = int(data.get("schema_version", schema_version))
    if version > schema_version:
        raise UnsupportedVersionError(
            path=doc.path, got=version, supported=schema_version
        )
    if data.get("kind") == kind:
        raw_defaults = data.get("defaults")
        if not isinstance(raw_defaults, dict):
            raise ReadError(
                path=doc.path,
                position=None,
                reason="'defaults' must be an object",
            )
        return dict(raw_defaults), version
    # старый плоский формат: всё, кроме наших meta-ключей
    defaults = {
        k: v for k, v in data.items()
        if k not in ("kind", "schema_version", "defaults")
    }
    return defaults, version


# ---------------------------------------------------------------------------
# StyleProfile
# ---------------------------------------------------------------------------

@register(kind="style_profile", formats=("json",))
@register_writer(kind="style_profile", formats=("json",))
@dataclass
class StyleProfile:
    """Базовый стилевой профиль лаборатории/проекта."""

    KIND: ClassVar[str] = "style_profile"
    FORMATS: ClassVar[tuple[str, ...]] = ("json",)
    SCHEMA_VERSION: ClassVar[int] = 1

    defaults: dict[str, Any] = field(default_factory=dict)
    kind: str = KIND
    schema_version: int = SCHEMA_VERSION

    @classmethod
    def can_parse(cls, doc: RawDocument) -> bool:
        return _can_parse_flat_defaults(doc, cls.KIND)

    @classmethod
    def parse(cls, doc: RawDocument) -> "StyleProfile":
        defaults, version = _parse_flat_defaults(
            doc, cls.KIND, cls.SCHEMA_VERSION
        )
        return cls(defaults=defaults, schema_version=version, kind=cls.KIND)

    @classmethod
    def can_write(cls, obj: Any) -> bool:
        return isinstance(obj, cls)

    @classmethod
    def serialize(cls, obj: "StyleProfile") -> RawDocument:
        payload = {
            "kind": cls.KIND,
            "schema_version": int(obj.schema_version),
            "defaults": dict(obj.defaults),
        }
        return RawDocument(
            format="json", path=None, size=0, payload=payload, meta={}
        )


# ---------------------------------------------------------------------------
# LabProfile
# ---------------------------------------------------------------------------

@register(kind="lab_profile", formats=("json",))
@register_writer(kind="lab_profile", formats=("json",))
@dataclass
class LabProfile:
    """Опциональный верхний слой стиля над StyleProfile."""

    KIND: ClassVar[str] = "lab_profile"
    FORMATS: ClassVar[tuple[str, ...]] = ("json",)
    SCHEMA_VERSION: ClassVar[int] = 1

    defaults: dict[str, Any] = field(default_factory=dict)
    kind: str = KIND
    schema_version: int = SCHEMA_VERSION

    @classmethod
    def can_parse(cls, doc: RawDocument) -> bool:
        return _can_parse_flat_defaults(doc, cls.KIND)

    @classmethod
    def parse(cls, doc: RawDocument) -> "LabProfile":
        defaults, version = _parse_flat_defaults(
            doc, cls.KIND, cls.SCHEMA_VERSION
        )
        return cls(defaults=defaults, schema_version=version, kind=cls.KIND)

    @classmethod
    def can_write(cls, obj: Any) -> bool:
        return isinstance(obj, cls)

    @classmethod
    def serialize(cls, obj: "LabProfile") -> RawDocument:
        payload = {
            "kind": cls.KIND,
            "schema_version": int(obj.schema_version),
            "defaults": dict(obj.defaults),
        }
        return RawDocument(
            format="json", path=None, size=0, payload=payload, meta={}
        )


# ---------------------------------------------------------------------------
# Loaders — существующий публичный API, теперь через dispatch.load_file
# ---------------------------------------------------------------------------

def load_style_profile(path: str = None) -> dict[str, Any]:
    """Прочитать style profile. Нет файла или ошибка — STYLE_PROFILE_DEFAULT."""
    if not path or not os.path.exists(path):
        return dict(STYLE_PROFILE_DEFAULT)
    try:
        profile = load_file(path, hint="style_profile")
    except FileError:
        logger.exception("load_style_profile(%r) failed", path)
        return dict(STYLE_PROFILE_DEFAULT)
    return dict(profile.defaults)


def load_lab_profile(path: str = None) -> dict[str, Any]:
    """Прочитать lab profile. Нет файла или ошибка — пустой dict."""
    if not path or not os.path.exists(path):
        return {}
    try:
        profile = load_file(path, hint="lab_profile")
    except FileError:
        logger.exception("load_lab_profile(%r) failed", path)
        return {}
    return dict(profile.defaults)