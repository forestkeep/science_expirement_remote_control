"""PanelSpec — контейнер нескольких кривых (CurveSlot) с backward-compat."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .session_ref import DataRef
from ..core.sentinel import MISSING


_DEFAULT_SHOW_TOOLS = {
    "fit.linear": False,
    "fit.polynomial": False,
    "fit.gaussian": False,
    "fit.lorentz": False,
    "search.peaks": True,
    "search.valleys": False,
    "uncertainty.estimate": False,
}


@dataclass
class CurveSlot:
    data_ref: DataRef
    axis: str = "y1"
    visible: bool = True
    legend_label: str = ""
    style_overrides: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        ov = {k: v for k, v in self.style_overrides.items() if v is not MISSING}
        return {
            "data_ref": self.data_ref.to_dict() if self.data_ref else None,
            "axis": self.axis if self.axis in ("y1", "y2") else "y1",
            "visible": bool(self.visible),
            "legend_label": self.legend_label,
            "style_overrides": ov,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CurveSlot":
        ref = DataRef.from_dict(d.get("data_ref"))
        return cls(
            data_ref=ref if ref is not None else DataRef(),
            axis=str(d.get("axis", "y1")) if d.get("axis") in ("y1", "y2") else "y1",
            visible=bool(d.get("visible", True)),
            legend_label=str(d.get("legend_label", "")),
            style_overrides=dict(d.get("style_overrides") or {}),
        )


@dataclass
class PanelSpec:
    id: str
    x_mm: float = 0.0
    y_mm: float = 0.0
    w_mm: float = 40.0
    h_mm: float = 30.0
    z: int = 0
    title: str = ""
    x_label: str = ""
    y_label: str = ""
    y2_label: str = ""
    x_range: Optional[Tuple[float, float]] = None
    y_range: Optional[Tuple[float, float]] = None
    y2_range: Optional[Tuple[float, float]] = None
    x_log: bool = False
    y_log: bool = False
    y2_log: bool = False
    y2_visible: bool = False
    use_source_color: bool = True
    show_tools: Dict[str, bool] = field(default_factory=lambda: dict(_DEFAULT_SHOW_TOOLS))
    curves: List[CurveSlot] = field(default_factory=list)
    visible: bool = True
    locked: bool = False
    style_overrides: Dict[str, Any] = field(default_factory=dict)

    # --- backward-compatible data_ref ---
    @property
    def data_ref(self) -> Optional[DataRef]:
        if len(self.curves) == 1:
            return self.curves[0].data_ref
        return None

    @data_ref.setter
    def data_ref(self, ref: Optional[DataRef]) -> None:
        self.curves = [CurveSlot(data_ref=ref if ref is not None else DataRef())]

    # --- geometry ---
    def contains_point_mm(self, x_mm: float, y_mm: float,
                          tol_mm: float = 0.5) -> bool:
        if self.locked or not self.visible:
            return False
        return (
            self.x_mm - tol_mm <= x_mm <= self.x_mm + self.w_mm + tol_mm
            and self.y_mm - tol_mm <= y_mm <= self.y_mm + self.h_mm + tol_mm
        )

    def edge_hit(self, x_mm: float, y_mm: float, tol_mm: float = 2.0) -> str:
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
        d: Dict[str, Any] = {
            "id": self.id,
            "x_mm": float(self.x_mm),
            "y_mm": float(self.y_mm),
            "w_mm": float(self.w_mm),
            "h_mm": float(self.h_mm),
            "z": int(self.z),
            "title": self.title,
            "x_label": self.x_label,
            "y_label": self.y_label,
            "y2_label": self.y2_label,
            "x_range": list(self.x_range) if self.x_range else None,
            "y_range": list(self.y_range) if self.y_range else None,
            "y2_range": list(self.y2_range) if self.y2_range else None,
            "x_log": bool(self.x_log),
            "y_log": bool(self.y_log),
            "y2_log": bool(self.y2_log),
            "y2_visible": bool(self.y2_visible),
            "use_source_color": bool(self.use_source_color),
            "show_tools": dict(self.show_tools),
            "curves": [c.to_dict() for c in self.curves],
            "visible": bool(self.visible),
            "locked": bool(self.locked),
            "style_overrides": ov,
        }
        # backward compat: пишем и data_ref, если ровно один слот
        if len(self.curves) == 1:
            d["data_ref"] = self.curves[0].data_ref.to_dict() if self.curves[0].data_ref else None
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PanelSpec":
        xr = d.get("x_range")
        yr = d.get("y_range")
        y2r = d.get("y2_range")
        show_tools = dict(_DEFAULT_SHOW_TOOLS)
        show_tools.update(dict(d.get("show_tools") or {}))
        if "curves" in d and d["curves"]:
            curves = [CurveSlot.from_dict(c) for c in d["curves"]]
        elif d.get("data_ref"):
            ref = DataRef.from_dict(d.get("data_ref"))
            curves = [CurveSlot(data_ref=ref if ref is not None else DataRef())]
        else:
            curves = []
        return cls(
            id=str(d["id"]),
            x_mm=float(d.get("x_mm", 0.0)),
            y_mm=float(d.get("y_mm", 0.0)),
            w_mm=float(d.get("w_mm", 40.0)),
            h_mm=float(d.get("h_mm", 30.0)),
            z=int(d.get("z", 0)),
            title=str(d.get("title", "")),
            x_label=str(d.get("x_label", "")),
            y_label=str(d.get("y_label", "")),
            y2_label=str(d.get("y2_label", "")),
            x_range=tuple(xr) if xr else None,
            y_range=tuple(yr) if yr else None,
            y2_range=tuple(y2r) if y2r else None,
            x_log=bool(d.get("x_log", False)),
            y_log=bool(d.get("y_log", False)),
            y2_log=bool(d.get("y2_log", False)),
            y2_visible=bool(d.get("y2_visible", False)),
            use_source_color=bool(d.get("use_source_color", True)),
            show_tools=show_tools,
            curves=curves,
            visible=bool(d.get("visible", True)),
            locked=bool(d.get("locked", False)),
            style_overrides=dict(d.get("style_overrides") or {}),
        )