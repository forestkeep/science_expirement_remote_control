"""FigureSpec — дерево Figure → Panels → Annotations + overrides.

Не хранит data-bound аннотации целиком (только overrides). Данные
резолвятся в момент рендера через DataResolver.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .annotations import DataBoundOverride, PresentationAnnotation
from .panel import PanelSpec
from .session_ref import DataRef
from ..core.ids import IdGen
from ..core.sentinel import MISSING

logger = logging.getLogger(__name__)


@dataclass
class FigureSpec:
    schema_version: int = 1
    id: str = "fig_0001"
    column_preset_id: str = ""
    width_mm: float = 180.0
    height_mm: float = 120.0
    panels: List[PanelSpec] = field(default_factory=list)
    presentation_annotations: List[PresentationAnnotation] = field(default_factory=list)
    data_bound_overrides: Dict[str, DataBoundOverride] = field(default_factory=dict)
    figure_overrides: Dict[str, Any] = field(default_factory=dict)
    style_profile_id: str = "default"
    journal_preset_id: str = ""
    lab_profile_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    _panel_gen: IdGen = field(default_factory=lambda: IdGen("pn"), repr=False, compare=False)
    _annot_gen: IdGen = field(default_factory=lambda: IdGen("ann"), repr=False, compare=False)

    # -------------------------------------------------------------- panels
    def add_panel(self, data_ref: Optional[DataRef] = None,
                  x_mm: float = 5.0, y_mm: float = 5.0,
                  w_mm: float = 40.0, h_mm: float = 30.0,
                  title: str = "", **kwargs) -> PanelSpec:
        existing = {p.id for p in self.panels}
        while True:
            pid = self._panel_gen.next()
            if pid not in existing:
                break
        panel = PanelSpec(id=pid, x_mm=x_mm, y_mm=y_mm, w_mm=w_mm, h_mm=h_mm,
                          data_ref=data_ref, title=title, **kwargs)
        panel.z = len(self.panels) + 1
        self.panels.append(panel)
        return panel

    def find_panel(self, panel_id: str) -> Optional[PanelSpec]:
        for p in self.panels:
            if p.id == panel_id:
                return p
        return None

    def remove_panel(self, panel_id: str) -> bool:
        before = len(self.panels)
        self.panels = [p for p in self.panels if p.id != panel_id]
        self.presentation_annotations = [
            a for a in self.presentation_annotations if a.panel_id != panel_id
        ]
        return len(self.panels) != before

    def sorted_panels(self) -> List[PanelSpec]:
        """Детерминированный z-order: сначала z, потом id (стабильно)."""
        return sorted(self.panels, key=lambda p: (int(p.z), p.id))

    # ----------------------------------------------------------- annotations
    def add_presentation(self, kind: str = "text",
                         coordinate_space: str = "figure_mm",
                         panel_id: Optional[str] = None,
                         coords: tuple = (0.0, 0.0),
                         text: str = "", **style) -> PresentationAnnotation:
        existing = {a.id for a in self.presentation_annotations}
        while True:
            aid = self._annot_gen.next()
            if aid not in existing:
                break
        ann = PresentationAnnotation(
            id=aid, kind=kind, coordinate_space=coordinate_space,
            panel_id=panel_id, coords=tuple(coords), text=text,
            style=dict(style),
        )
        self.presentation_annotations.append(ann)
        return ann

    def find_presentation(self, ann_id: str) -> Optional[PresentationAnnotation]:
        for a in self.presentation_annotations:
            if a.id == ann_id:
                return a
        return None

    # ---------------------------------------------------------------- overrides
    def get_data_bound_override(self, ann_id: str) -> DataBoundOverride:
        ov = self.data_bound_overrides.get(ann_id)
        if ov is None:
            ov = DataBoundOverride(annotation_id=ann_id)
            self.data_bound_overrides[ann_id] = ov
        return ov

    # ------------------------------------------------------------- serialization
    def to_dict(self) -> Dict[str, Any]:
        from ..core.sentinel import MISSING as _M
        fig_ov = {k: v for k, v in self.figure_overrides.items() if v is not _M}
        return {
            "schema_version": int(self.schema_version),
            "id": self.id,
            "column_preset_id": self.column_preset_id,
            "width_mm": float(self.width_mm),
            "height_mm": float(self.height_mm),
            "panels": [p.to_dict() for p in self.panels],
            "presentation_annotations": [
                a.to_dict() for a in self.presentation_annotations
            ],
            "data_bound_overrides": {
                k: v.to_dict() for k, v in self.data_bound_overrides.items()
            },
            "figure_overrides": fig_ov,
            "style_profile_id": self.style_profile_id,
            "journal_preset_id": self.journal_preset_id,
            "lab_profile_id": self.lab_profile_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FigureSpec":
        spec = cls(
            schema_version=int(d.get("schema_version", 1)),
            id=str(d.get("id", "fig_0001")),
            column_preset_id=str(d.get("column_preset_id", "")),
            width_mm=float(d.get("width_mm", 180.0)),
            height_mm=float(d.get("height_mm", 120.0)),
            style_profile_id=str(d.get("style_profile_id", "default")),
            journal_preset_id=str(d.get("journal_preset_id", "")),
            lab_profile_id=str(d.get("lab_profile_id", "")),
            metadata=dict(d.get("metadata") or {}),
        )
        spec.panels = [PanelSpec.from_dict(p) for p in d.get("panels", [])]
        spec.presentation_annotations = [
            PresentationAnnotation.from_dict(a)
            for a in d.get("presentation_annotations", [])
        ]
        spec.data_bound_overrides = {
            k: DataBoundOverride.from_dict(v)
            for k, v in (d.get("data_bound_overrides") or {}).items()
        }
        spec.figure_overrides = dict(d.get("figure_overrides") or {})
        # восстановить счётчики из занятых ID
        max_panel = 0
        for p in spec.panels:
            try:
                n = int(p.id.rsplit("_", 1)[1])
                max_panel = max(max_panel, n)
            except Exception:
                pass
        spec._panel_gen = IdGen("pn", start=max_panel)
        max_ann = 0
        for a in spec.presentation_annotations:
            try:
                n = int(a.id.rsplit("_", 1)[1])
                max_ann = max(max_ann, n)
            except Exception:
                pass
        spec._annot_gen = IdGen("ann", start=max_ann)
        return spec