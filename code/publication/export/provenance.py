"""Provenance — данные, pipeline, пресет, overrides, версии, автор, время.

Попадает в export_package(). Единственное место, где допустим timestamp
(в рендере — нет).
"""
from __future__ import annotations
import getpass
import json
import os
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

PUBLICATION_VERSION = "0.1.0"


@dataclass
class Provenance:
    figure_id: str = ""
    schema_version: int = 1
    author: str = ""
    created_at: str = ""
    preset_id: str = ""
    style_profile_id: str = ""
    data_refs: List[Dict[str, Any]] = field(default_factory=list)
    overrides: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    versions: Dict[str, str] = field(default_factory=dict)
    system: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def collect(cls, spec, preset, overrides_snapshot: Dict[str, Any]) -> "Provenance":
        refs = []
        for p in spec.panels:
            if p.data_ref is not None and not p.data_ref.is_empty():
                refs.append(p.data_ref.to_dict())
        try:
            author = getpass.getuser()
        except Exception:
            author = os.environ.get("USER", "unknown")
        return cls(
            figure_id=spec.id,
            schema_version=spec.schema_version,
            author=author,
            created_at=datetime.now(timezone.utc).isoformat(),
            preset_id=preset.id if preset else "",
            style_profile_id=spec.style_profile_id,
            data_refs=refs,
            overrides=dict(overrides_snapshot or {}),
            notes=str(spec.metadata.get("notes", "")),
            versions={
                "publication_layer": PUBLICATION_VERSION,
                "schema": str(spec.schema_version),
            },
            system={
                "python": sys.version.split(" ")[0],
                "platform": platform.platform(),
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "figure_id": self.figure_id,
            "schema_version": self.schema_version,
            "author": self.author,
            "created_at": self.created_at,
            "preset_id": self.preset_id,
            "style_profile_id": self.style_profile_id,
            "data_refs": list(self.data_refs),
            "overrides": dict(self.overrides),
            "notes": self.notes,
            "versions": dict(self.versions),
            "system": dict(self.system),
        }