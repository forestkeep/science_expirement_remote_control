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
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def from_legacy(cls, data: Dict[str, Any]) -> "AnalysisPreset":
        if "artifacts" in data:
            return cls(
                id=data.get("id") or uuid.uuid4().hex,
                name=data.get("name") or "",
                artifacts=list(data.get("artifacts") or []),
                created_at=data.get("created_at") or datetime.now().isoformat(),
            )
        tool_id = data.get("tool_id") or ""
        params = data.get("params") or {}
        artifacts = [{"tool_id": tool_id, "params": dict(params)}] if tool_id else []
        return cls(
            id=data.get("id") or uuid.uuid4().hex,
            name=data.get("name") or "",
            artifacts=artifacts,
            created_at=data.get("created_at") or datetime.now().isoformat(),
        )


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

    def register(self, name: str, artifacts: List[Dict[str, Any]]) -> AnalysisPreset:
        clean = [{"tool_id": a["tool_id"], "params": dict(a.get("params") or {})}
                 for a in artifacts if a.get("tool_id")]
        p = AnalysisPreset(name=name, artifacts=clean)
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

    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                for item in data.get("presets", []):
                    p = AnalysisPreset.from_legacy(item)
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