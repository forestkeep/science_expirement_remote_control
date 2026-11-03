# code/publication/presets/journal_preset.py
"""JournalPreset и его хранилище.

Каждый пресет — отдельный JSON-файл. Модель JournalPreset сама
регистрируется как semantic type "journal_preset"; store не пишет
собственных циклов чтения/записи, а использует load_file/save_file.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional

from file_io import (
    RawDocument, load_file, save_file, register, register_writer,
)
from file_io.errors import (
    FileError, MissingFieldError, UnsupportedVersionError,
)

from .builtin import BUILTIN_JOURNALS

logger = logging.getLogger(__name__)


@register(kind="journal_preset", formats=("json",))
@register_writer(kind="journal_preset", formats=("json",))
@dataclass
class JournalPreset:
    KIND: ClassVar[str] = "journal_preset"
    FORMATS: ClassVar[tuple[str, ...]] = ("json",)
    SCHEMA_VERSION: ClassVar[int] = 1

    schema_version: int = SCHEMA_VERSION
    id: str = ""
    name: str = ""
    column: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    kind: str = KIND

    def column_width_mm(self) -> float:
        return float(self.column.get("width_mm", 183.0))

    def column_height_mm(self) -> float:
        return float(self.column.get("height_mm", 247.0))

    def column_dpi(self) -> int:
        return int(self.column.get("dpi", 300))

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
        pid = data.get("id")
        if not isinstance(pid, str) or not pid:
            return False
        return (
            isinstance(data.get("column"), dict)
            and isinstance(data.get("constraints"), dict)
        )

    @classmethod
    def parse(cls, doc: RawDocument) -> "JournalPreset":
        data = doc.payload
        assert isinstance(data, dict)
        version = int(data.get("schema_version", cls.SCHEMA_VERSION))
        if version > cls.SCHEMA_VERSION:
            raise UnsupportedVersionError(
                path=doc.path, got=version, supported=cls.SCHEMA_VERSION
            )
        pid = data.get("id")
        if not isinstance(pid, str) or not pid:
            raise MissingFieldError(path=doc.path, field="id")
        return cls(
            schema_version=version,
            id=pid,
            name=str(data.get("name", "")),
            column=dict(data.get("column") or {}),
            constraints=dict(data.get("constraints") or {}),
            defaults=dict(data.get("defaults") or {}),
            kind=cls.KIND,
        )

    # ---------- writer ----------

    @classmethod
    def can_write(cls, obj: Any) -> bool:
        return isinstance(obj, cls)

    @classmethod
    def serialize(cls, obj: "JournalPreset") -> RawDocument:
        payload = {
            "kind": cls.KIND,
            "schema_version": int(obj.schema_version),
            "id": obj.id,
            "name": obj.name,
            "column": dict(obj.column),
            "constraints": dict(obj.constraints),
            "defaults": dict(obj.defaults),
        }
        return RawDocument(
            format="json", path=None, size=0, payload=payload, meta={}
        )

    # ---------- backward-compatible helpers ----------

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "JournalPreset":
        """Используется для builtin-пресетов и обратной совместимости."""
        return cls(
            schema_version=int(d.get("schema_version", cls.SCHEMA_VERSION)),
            id=str(d.get("id", "")),
            name=str(d.get("name", "")),
            column=dict(d.get("column") or {}),
            constraints=dict(d.get("constraints") or {}),
            defaults=dict(d.get("defaults") or {}),
            kind=cls.KIND,
        )

    def to_dict(self) -> dict[str, Any]:
        """Обратная совместимость для мест, читающих to_dict() на модели."""
        return {
            "kind": self.kind,
            "schema_version": int(self.schema_version),
            "id": self.id,
            "name": self.name,
            "column": dict(self.column),
            "constraints": dict(self.constraints),
            "defaults": dict(self.defaults),
        }


class JournalPresetStore:
    """Загрузка/сохранение пресетов журналов (по одному файлу на пресет)."""

    def __init__(self, presets_dir: Optional[str] = None):
        self.presets_dir = presets_dir or self._default_dir()
        self._cache: dict[str, JournalPreset] = {}

    @staticmethod
    def _default_dir() -> str:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(here, "examples", "presets", "journals")

    def _path_for(self, preset_id: str) -> str:
        return os.path.join(self.presets_dir, f"{preset_id}.json")

    def list_ids(self) -> list[str]:
        ids = set(BUILTIN_JOURNALS.keys())
        if os.path.isdir(self.presets_dir):
            for name in os.listdir(self.presets_dir):
                if name.endswith(".json"):
                    ids.add(name[:-5])
        return sorted(ids)

    def load(self, preset_id: str) -> Optional[JournalPreset]:
        if preset_id in self._cache:
            return self._cache[preset_id]
        if preset_id in BUILTIN_JOURNALS:
            preset = JournalPreset.from_dict(BUILTIN_JOURNALS[preset_id])
            self._cache[preset_id] = preset
            return preset
        path = self._path_for(preset_id)
        if not os.path.exists(path):
            return None
        try:
            preset = load_file(path, hint="journal_preset")
        except FileError:
            logger.exception("JournalPresetStore.load(%r) failed", preset_id)
            return None
        self._cache[preset_id] = preset
        return preset

    def save(self, preset: JournalPreset) -> str:
        os.makedirs(self.presets_dir, exist_ok=True)
        path = self._path_for(preset.id)
        save_file(preset, path)
        self._cache[preset.id] = preset
        return path