"""Пользовательские пресеты анализа. Хранятся локально (JSON)."""
from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AnalysisPreset:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    tool_id: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class AnalysisPresetStore:
    _instance: Optional["AnalysisPresetStore"] = None

    def __init__(self, path: Optional[str] = None) -> None:
        self._presets: Dict[str, AnalysisPreset] = {}
        if path is None:
            base = os.path.expanduser("~/.science_analysis")
            os.makedirs(base, exist_ok=True)
            path = os.path.join(base, "presets.json")
        self._path = path
        self._load()

    @classmethod
    def instance(cls) -> "AnalysisPresetStore":
        if cls._instance is None:
            cls._instance = AnalysisPresetStore()
        return cls._instance

    def register(self, name: str, tool_id: str, params: Dict[str, Any]) -> AnalysisPreset:
        p = AnalysisPreset(name=name, tool_id=tool_id, params=dict(params))
        self._presets[p.id] = p
        self._save()
        return p

    def remove(self, preset_id: str) -> None:
        self._presets.pop(preset_id, None)
        self._save()

    def all(self) -> List[AnalysisPreset]:
        return list(self._presets.values())

    def get(self, preset_id: str) -> Optional[AnalysisPreset]:
        return self._presets.get(preset_id)

    # ------------------------------------------------------------------
    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                for item in data.get("presets", []):
                    p = AnalysisPreset(**item)
                    self._presets[p.id] = p
        except Exception:
            logger.exception("AnalysisPresetStore: load failed")

    def _save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump({"presets": [asdict(p) for p in self._presets.values()]},
                          fh, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception("AnalysisPresetStore: save failed")