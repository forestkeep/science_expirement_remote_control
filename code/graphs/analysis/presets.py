# code/graphs/analysis/presets.py
"""Пользовательские пресеты анализа. Хранятся локально (JSON)."""
from __future__ import annotations

import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Optional

from file_io import (
    RawDocument, load_file, save_file, register, register_writer,
)
from file_io.errors import (
    FileError, ReadError, UnsupportedVersionError,
)

logger = logging.getLogger(__name__)


@dataclass
class AnalysisPreset:
    """Один пресет анализа (без привязки к файлу).

    Сериализуется в :class:`AnalysisPresetFile`; сам по себе файл не описывает.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def from_legacy(cls, data: dict[str, Any]) -> "AnalysisPreset":
        """Универсальный ридер для старого и нового формата пресета."""
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


@register(kind="analysis_preset_file", formats=("json",))
@register_writer(kind="analysis_preset_file", formats=("json",))
@dataclass
class AnalysisPresetFile:
    """Файловый контейнер пресетов: {"presets": [...]}.

    Один файл = весь store (см. AnalysisPresetStore). Старые файлы без kind
    читаются через can_parse-fallback (`presets` — список dict'ов).
    """

    KIND: ClassVar[str] = "analysis_preset_file"
    FORMATS: ClassVar[tuple[str, ...]] = ("json",)
    SCHEMA_VERSION: ClassVar[int] = 1

    presets: list[AnalysisPreset] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION
    kind: str = KIND

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
        return isinstance(data.get("presets"), list)

    @classmethod
    def parse(cls, doc: RawDocument) -> "AnalysisPresetFile":
        data = doc.payload
        assert isinstance(data, dict)
        version = int(data.get("schema_version", cls.SCHEMA_VERSION))
        if version > cls.SCHEMA_VERSION:
            raise UnsupportedVersionError(
                path=doc.path, got=version, supported=cls.SCHEMA_VERSION
            )
        items = data.get("presets") or []
        if not isinstance(items, list):
            raise ReadError(
                path=doc.path, position=None,
                reason="'presets' must be a list",
            )
        presets: list[AnalysisPreset] = []
        for item in items:
            if isinstance(item, dict):
                presets.append(AnalysisPreset.from_legacy(item))
        return cls(presets=presets, schema_version=version, kind=cls.KIND)

    # ---------- writer ----------

    @classmethod
    def can_write(cls, obj: Any) -> bool:
        return isinstance(obj, cls)

    @classmethod
    def serialize(cls, obj: "AnalysisPresetFile") -> RawDocument:
        payload = {
            "kind": cls.KIND,
            "schema_version": int(obj.schema_version),
            "presets": [asdict(p) for p in obj.presets],
        }
        return RawDocument(
            format="json", path=None, size=0, payload=payload, meta={}
        )


class AnalysisPresetStore:
    _instance: Optional["AnalysisPresetStore"] = None

    def __init__(self, path: Optional[str] = None) -> None:
        self._presets: dict[str, AnalysisPreset] = {}
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

    def register(self, name: str, artifacts: list[dict[str, Any]]) -> AnalysisPreset:
        clean = [
            {"tool_id": a["tool_id"], "params": dict(a.get("params") or {})}
            for a in artifacts if a.get("tool_id")
        ]
        p = AnalysisPreset(name=name, artifacts=clean)
        self._presets[p.id] = p
        self._save()
        return p

    def remove(self, preset_id: str) -> None:
        self._presets.pop(preset_id, None)
        self._save()

    def all(self) -> list[AnalysisPreset]:
        return list(self._presets.values())

    def get(self, preset_id: str) -> Optional[AnalysisPreset]:
        return self._presets.get(preset_id)

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            file_obj = load_file(self._path, hint="analysis_preset_file")
        except FileError:
            logger.exception("AnalysisPresetStore: load failed")
            return
        for p in file_obj.presets:
            self._presets[p.id] = p

    def _save(self) -> None:
        try:
            file_obj = AnalysisPresetFile(presets=list(self._presets.values()))
            save_file(file_obj, self._path)
        except FileError:
            logger.exception("AnalysisPresetStore: save failed")