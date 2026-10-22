"""PanelSpec — независимый контейнер с DataRef и геометрией в мм."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .session_ref import DataRef
from ..core.sentinel import MISSING


@dataclass
class PanelSpec:
    id: str
    x_mm: float = 0.0
    y_mm: float = 0.0
    w_mm: float = 40.0
    h_mm: float = 30.0
    z: int = 0
    data_ref: Optional[DataRef] = None
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    x_range: Optional[Tuple[float, float]] = None
    y_range: Optional[Tuple[float, float]] = None
    x_log: bool = False
    y_log: bool = False
    visible: bool = True
    locked: bool = False
    style_overrides: Dict[str, Any] = field(default_factory=dict)

    def contains_point_mm(self, x_mm: float, y_mm: float,
                          tol_mm: float = 0.5) -> bool:
        if self.locked or not self.visible:
            return False
        return (
            self.x_mm - tol_mm <= x_mm <= self.x_mm + self.w_mm + tol_mm
            and self.y_mm - tol_mm <= y_mm <= self.y_mm + self.h_mm + tol_mm
        )

    def edge_hit(self, x_mm: float, y_mm: float, tol_mm: float = 2.0) -> str:
        """Вернуть 'br', 'r', 'b', '' — какой угол/сторона."""
        if self.locked or not self.visible:
            return ""
        right = abs(x_mm - (self.x_mm + self.w_mm)) <= tol_mm
        bottom = abs(y_mm - (self.y_mm + self.h_mm)) <= tol_mm
        inside_x = self.x_mm - tol_mm <= x_mm <= self.x_mm + self.w_mm + tol_mm
        inside_y = self.y_mm - tol_mm <= y_mm <= self.y_mm + self.h_mm + tol_mm
        if right and bottom and inside_x and inside_y:
            return "br"
        if right and inside_y:
            return "r"
        if bottom and inside_x:
            return "b"
        return ""

    def to_dict(self) -> Dict[str, Any]:
        ov = {k: v for k, v in self.style_overrides.items() if v is not MISSING}
        return {
            "id": self.id,
            "x_mm": float(self.x_mm),
            "y_mm": float(self.y_mm),
            "w_mm": float(self.w_mm),
            "h_mm": float(self.h_mm),
            "z": int(self.z),
            "data_ref": self.data_ref.to_dict() if self.data_ref else None,
            "title": self.title,
            "x_label": self.x_label,
            "y_label": self.y_label,
            "x_range": list(self.x_range) if self.x_range else None,
            "y_range": list(self.y_range) if self.y_range else None,
            "x_log": bool(self.x_log),
            "y_log": bool(self.y_log),
            "visible": bool(self.visible),
            "locked": bool(self.locked),
            "style_overrides": ov,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PanelSpec":
        xr = d.get("x_range")
        yr = d.get("y_range")
        ov = dict(d.get("style_overrides") or {})
        return cls(
            id=str(d["id"]),
            x_mm=float(d.get("x_mm", 0.0)),
            y_mm=float(d.get("y_mm", 0.0)),
            w_mm=float(d.get("w_mm", 40.0)),
            h_mm=float(d.get("h_mm", 30.0)),
            z=int(d.get("z", 0)),
            data_ref=DataRef.from_dict(d.get("data_ref")),
            title=str(d.get("title", "")),
            x_label=str(d.get("x_label", "")),
            y_label=str(d.get("y_label", "")),
            x_range=tuple(xr) if xr else None,
            y_range=tuple(yr) if yr else None,
            x_log=bool(d.get("x_log", False)),
            y_log=bool(d.get("y_log", False)),
            visible=bool(d.get("visible", True)),
            locked=bool(d.get("locked", False)),
            style_overrides=ov,
        )