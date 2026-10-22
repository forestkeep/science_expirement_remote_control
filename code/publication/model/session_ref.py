"""Ссылка на данные: session_id + series_root_name + имена осей."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class DataRef:
    session_id: str = ""
    series_root_name: str = ""
    x_name: str = ""
    y_name: str = ""

    def is_empty(self) -> bool:
        return not self.session_id or not self.series_root_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "series_root_name": self.series_root_name,
            "x_name": self.x_name,
            "y_name": self.y_name,
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["DataRef"]:
        if not d:
            return None
        return cls(
            session_id=str(d.get("session_id", "")),
            series_root_name=str(d.get("series_root_name", "")),
            x_name=str(d.get("x_name", "")),
            y_name=str(d.get("y_name", "")),
        )