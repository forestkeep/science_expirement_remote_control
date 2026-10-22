"""JournalPreset и его хранилище.

Пресеты — JSON-файлы на диске. Пользователь редактирует их ТОЛЬКО через UI
(минимальный редактор), не руками.
"""
from __future__ import annotations
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .builtin import BUILTIN_JOURNALS

logger = logging.getLogger(__name__)


@dataclass
class JournalPreset:
    schema_version: int = 1
    id: str = ""
    name: str = ""
    column: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)

    def column_width_mm(self) -> float:
        return float(self.column.get("width_mm", 183.0))

    def column_height_mm(self) -> float:
        return float(self.column.get("height_mm", 247.0))

    def column_dpi(self) -> int:
        return int(self.column.get("dpi", 300))

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "JournalPreset":
        return cls(
            schema_version=int(d.get("schema_version", 1)),
            id=str(d.get("id", "")),
            name=str(d.get("name", "")),
            column=dict(d.get("column") or {}),
            constraints=dict(d.get("constraints") or {}),
            defaults=dict(d.get("defaults") or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "name": self.name,
            "column": dict(self.column),
            "constraints": dict(self.constraints),
            "defaults": dict(self.defaults),
        }


class JournalPresetStore:
    """Загрузка/сохранение пресетов журналов (JSON на диске)."""

    def __init__(self, presets_dir: Optional[str] = None):
        self.presets_dir = presets_dir or self._default_dir()
        self._cache: Dict[str, JournalPreset] = {}

    @staticmethod
    def _default_dir() -> str:
        # Пакетная папка examples/presets/journals; при отсутствии — пусто.
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(here, "examples", "presets", "journals")
        return path

    def _path_for(self, preset_id: str) -> str:
        return os.path.join(self.presets_dir, f"{preset_id}.json")

    def list_ids(self) -> List[str]:
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
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            preset = JournalPreset.from_dict(data)
            self._cache[preset_id] = preset
            return preset
        except Exception:
            logger.exception("JournalPresetStore.load(%r) failed", preset_id)
            return None

    def save(self, preset: JournalPreset) -> str:
        os.makedirs(self.presets_dir, exist_ok=True)
        path = self._path_for(preset.id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(preset.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)
        self._cache[preset.id] = preset
        return path