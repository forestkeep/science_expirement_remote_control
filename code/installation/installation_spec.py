# code/installation/installation_spec.py
"""Модель InstallationSpec: семантический тип для .ns-файлов.

Заменяет ad-hoc разбор в Installation_class.read_info_by_saved_installation
и .write_data_to_save_installation_file. Формат .ns — JSON, но с отдельным
идентификатором формата, чтобы не конкурировать с другими JSON-моделями.

Старые .ns-файлы читаются через can_parse-fallback (плоский dict без kind
на верхнем уровне).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from file_io import RawDocument, register, register_writer
from file_io.errors import ReadError, UnsupportedVersionError


@register(kind="installation_spec", formats=("ns",))
@register_writer(kind="installation_spec", formats=("ns",))
@dataclass
class InstallationSpec:
    """Установка: словарь device_name_N → {settings, channels, JSON_temp?}."""

    KIND: ClassVar[str] = "installation_spec"
    FORMATS: ClassVar[tuple[str, ...]] = ("ns",)
    SCHEMA_VERSION: ClassVar[int] = 1

    devices: dict[str, dict[str, Any]] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION
    kind: str = KIND
    extras: dict[str, Any] = field(default_factory=dict)

    # ---------- helpers ----------

    def plain_device_names(self) -> list[str]:
        """Имена «обычных» приборов (у которых нет JSON_temp)."""
        return [name for name, data in self.devices.items() if "JSON_temp" not in data]

    def json_devices(self) -> dict[str, dict[str, Any]]:
        """Имена → JSON_temp-содержимое для custom-JSON-приборов."""
        result: dict[str, dict[str, Any]] = {}
        for name, data in self.devices.items():
            if "JSON_temp" in data:
                result[name] = dict(data["JSON_temp"] or {})
        return result

    # ---------- parser ----------

    @classmethod
    def can_parse(cls, doc: RawDocument) -> bool:
        if doc.format not in cls.FORMATS:
            return False
        data = doc.payload
        if not isinstance(data, dict) or not data:
            return False
        if data.get("kind") == cls.KIND:
            return isinstance(data.get("devices"), dict)
        # fallback для старых .ns без kind: все значения — dict-приборы
        for value in data.values():
            if not isinstance(value, dict):
                return False
            if "JSON_temp" in value:
                continue
            if "settings" not in value or "channels" not in value:
                return False
        return True

    @classmethod
    def parse(cls, doc: RawDocument) -> "InstallationSpec":
        data = doc.payload
        assert isinstance(data, dict)
        if data.get("kind") == cls.KIND:
            version = int(data.get("schema_version", cls.SCHEMA_VERSION))
            if version > cls.SCHEMA_VERSION:
                raise UnsupportedVersionError(
                    path=doc.path, got=version, supported=cls.SCHEMA_VERSION
                )
            devices_raw = data.get("devices")
            if not isinstance(devices_raw, dict):
                raise ReadError(
                    path=doc.path,
                    position=None,
                    reason="installation spec: 'devices' must be an object",
                )
            extras = {
                k: v
                for k, v in data.items()
                if k not in ("kind", "schema_version", "devices")
            }
            return cls(
                devices={str(k): dict(v) for k, v in devices_raw.items()},
                schema_version=version,
                kind=cls.KIND,
                extras=extras,
            )
        # старый плоский формат
        return cls(
            devices={str(k): dict(v) for k, v in data.items()},
            schema_version=1,
            kind=cls.KIND,
        )

    # ---------- writer ----------

    @classmethod
    def can_write(cls, obj: Any) -> bool:
        return isinstance(obj, cls)

    @classmethod
    def serialize(cls, obj: "InstallationSpec") -> RawDocument:
        payload: dict[str, Any] = {
            "kind": cls.KIND,
            "schema_version": int(obj.schema_version),
            "devices": dict(obj.devices),
        }
        if obj.extras:
            for k, v in obj.extras.items():
                if k not in payload:
                    payload[k] = v
        return RawDocument(
            format="ns", path=None, size=0, payload=payload, meta={}
        )