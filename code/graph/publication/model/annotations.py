"""Модель аннотаций.

DataBoundOverride — публикационный слой хранит ТОЛЬКО overrides над
data-bound аннотациями источника. Базовая аннотация приходит из
AnalysisController/сессии.

PresentationAnnotation — presentation-only, полностью принадлежит
публикационному слою.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class DataBoundOverride:
    annotation_id: str
    position_override: Optional[Tuple[float, float]] = None
    style_override: Dict[str, Any] = field(default_factory=dict)
    visible_override: Optional[bool] = None
    resolved: bool = True
    unresolved_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "annotation_id": self.annotation_id,
            "position_override": list(self.position_override) if self.position_override else None,
            "style_override": dict(self.style_override),
            "visible_override": self.visible_override,
            "resolved": bool(self.resolved),
            "unresolved_reason": self.unresolved_reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DataBoundOverride":
        pos = d.get("position_override")
        return cls(
            annotation_id=str(d["annotation_id"]),
            position_override=tuple(pos) if pos else None,
            style_override=dict(d.get("style_override") or {}),
            visible_override=d.get("visible_override"),
            resolved=bool(d.get("resolved", True)),
            unresolved_reason=str(d.get("unresolved_reason", "")),
        )


@dataclass
class PresentationAnnotation:
    id: str
    kind: str = "text"                          # text | panel_label | scale_bar | bracket | arrow
    coordinate_space: str = "figure_mm"         # figure_mm | panel_mm | axes_data
    panel_id: Optional[str] = None
    coords: Tuple[float, ...] = (0.0, 0.0)
    text: str = ""
    style: Dict[str, Any] = field(default_factory=dict)
    z: int = 100
    visible: bool = True
    locked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "coordinate_space": self.coordinate_space,
            "panel_id": self.panel_id,
            "coords": list(self.coords),
            "text": self.text,
            "style": dict(self.style),
            "z": int(self.z),
            "visible": bool(self.visible),
            "locked": bool(self.locked),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PresentationAnnotation":
        return cls(
            id=str(d["id"]),
            kind=str(d.get("kind", "text")),
            coordinate_space=str(d.get("coordinate_space", "figure_mm")),
            panel_id=d.get("panel_id"),
            coords=tuple(d.get("coords", (0.0, 0.0))),
            text=str(d.get("text", "")),
            style=dict(d.get("style") or {}),
            z=int(d.get("z", 100)),
            visible=bool(d.get("visible", True)),
            locked=bool(d.get("locked", False)),
        )