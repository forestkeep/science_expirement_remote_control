# code/Devices/device_spec.py
"""Модель DeviceSpec: семантический тип для JSON-файлов приборов.

Заменяет ad-hoc парсинг в controlDevicesJSON.validate_json_schema.
Даёт типизированный объект для UI, скрывая dict-детали за dataclass'ом.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from file_io import RawDocument, register, register_writer
from file_io.errors import MissingFieldError, ReadError, UnsupportedVersionError


def _get_templates() -> dict[str, Any]:
    """Ленивый импорт, чтобы не ловить цикл при импорте models."""
    try:
        from device_creator.dev_template import templates
        return dict(templates)
    except ImportError:
        return {}


@register(kind="device_spec", formats=("json",))
@register_writer(kind="device_spec", formats=("json",))
@dataclass
class DeviceSpec:
    """Спецификация прибора из JSON-файла (device_creator / power_supply).

    Известные поля разложены по атрибутам; неизвестные — в extras, чтобы
    можно было сохранить вперёд-совместимо.
    """

    KIND: ClassVar[str] = "device_spec"
    FORMATS: ClassVar[tuple[str, ...]] = ("json",)
    SCHEMA_VERSION: ClassVar[int] = 1

    device_type: str
    device_name: str
    number_channels: int = 1
    channels_parameters: dict[str, Any] = field(default_factory=dict)
    commands: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION
    kind: str = KIND
    extras: dict[str, Any] = field(default_factory=dict)

    # ---------- parser ----------

    @classmethod
    def can_parse(cls, doc: RawDocument) -> bool:
        if doc.format not in cls.FORMATS:
            return False
        data = doc.payload
        if not isinstance(data, dict):
            return False
        if data.get("kind") == cls.KIND:
            return True
        # fallback для старых файлов без kind
        return (
            isinstance(data.get("device_type"), str)
            and isinstance(data.get("device_name"), str)
            and "commands" in data
        )

    @classmethod
    def parse(cls, doc: RawDocument) -> "DeviceSpec":
        data = doc.payload
        assert isinstance(data, dict)
        version = int(data.get("schema_version", cls.SCHEMA_VERSION))
        if version > cls.SCHEMA_VERSION:
            raise UnsupportedVersionError(
                path=doc.path, got=version, supported=cls.SCHEMA_VERSION
            )
        device_type = data.get("device_type")
        if not isinstance(device_type, str) or not device_type:
            raise MissingFieldError(path=doc.path, field="device_type")
        device_name = data.get("device_name")
        if not isinstance(device_name, str) or not device_name:
            raise MissingFieldError(path=doc.path, field="device_name")
        templates = _get_templates()
        if templates and device_type not in templates:
            raise ReadError(
                path=doc.path,
                position=None,
                reason=f"device_type {device_type!r} not in templates",
            )
        known = {
            "kind", "schema_version", "device_type", "device_name",
            "number_channels", "channels parameters", "commands",
        }
        extras = {k: v for k, v in data.items() if k not in known}
        return cls(
            device_type=device_type,
            device_name=device_name,
            number_channels=int(data.get("number_channels", 1)),
            channels_parameters=dict(data.get("channels parameters") or {}),
            commands=dict(data.get("commands") or {}),
            schema_version=version,
            kind=str(data.get("kind", cls.KIND)),
            extras=extras,
        )

    # ---------- writer ----------

    @classmethod
    def can_write(cls, obj: Any) -> bool:
        return isinstance(obj, cls)

    @classmethod
    def serialize(cls, obj: "DeviceSpec") -> RawDocument:
        payload: dict[str, Any] = dict(obj.extras)
        payload["kind"] = cls.KIND
        payload["schema_version"] = int(obj.schema_version)
        payload["device_type"] = obj.device_type
        payload["device_name"] = obj.device_name
        payload["number_channels"] = int(obj.number_channels)
        payload["commands"] = dict(obj.commands)
        if obj.channels_parameters:
            payload["channels parameters"] = dict(obj.channels_parameters)
        return RawDocument(
            format="json", path=None, size=0, payload=payload, meta={}
        )