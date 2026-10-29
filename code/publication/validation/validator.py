"""Валидатор. Все правила берутся из constraints пресета журнала."""
from __future__ import annotations
from typing import Dict, List

from .rules import Issue, Report
from ..core.sentinel import MISSING
from ..presets.builtin import OKABE_ITO
from ..renderers.colors import resolve_line_color


class Validator:
    def __init__(self, spec, preset, style_stack, data_resolver=None):
        self.spec = spec
        self.preset = preset
        self.stack = style_stack
        self.data_resolver = data_resolver
        self.constraints = dict(getattr(preset, "constraints", {}) or {})

    def validate(self) -> Report:
        report = Report()
        self._check_font(report)
        self._check_line_width(report)
        self._check_dpi(report)
        self._check_margins(report)
        self._check_column_size(report)
        self._check_colorblind(report)
        self._check_overrides(report)
        self._check_unresolved(report)
        return report

    def _issue(self, sev, code, msg, panel_id=None, element_id=None) -> Issue:
        return Issue(severity=sev, code=code, message=msg,
                     panel_id=panel_id, element_id=element_id)

    def _check_font(self, report):
        min_pt = self.constraints.get("min_font_pt")
        if min_pt is None:
            return
        for path in ("figure.font.size", "panel.title_size",
                     "annotation.text_size", "figure.axes.tick_size",
                     "figure.axes.label_size"):
            v = self.stack.resolve(path)
            if v is MISSING:
                continue
            try:
                if float(v) < float(min_pt):
                    report.warnings.append(self._issue(
                        "warning", "font.size",
                        f"{path}={v} < min_font_pt={min_pt}",
                    ))
            except (TypeError, ValueError):
                pass

    def _check_line_width(self, report):
        min_pt = self.constraints.get("min_line_pt")
        if min_pt is None:
            return
        for path in ("figure.line.width", "figure.axes.line_width",
                     "annotation.scalebar.thickness_pt",
                     "annotation.bracket.width_pt"):
            v = self.stack.resolve(path)
            if v is MISSING:
                continue
            try:
                if float(v) < float(min_pt):
                    report.warnings.append(self._issue(
                        "warning", "line.width",
                        f"{path}={v} < min_line_pt={min_pt}",
                    ))
            except (TypeError, ValueError):
                pass

    def _check_dpi(self, report):
        min_dpi = self.constraints.get("dpi_min")
        if min_dpi is None:
            return
        dpi = self.stack.resolve("figure.dpi")
        if dpi is MISSING:
            dpi = 300
        if int(dpi) < int(min_dpi):
            report.warnings.append(self._issue(
                "warning", "dpi.low",
                f"figure.dpi={dpi} < dpi_min={min_dpi}",
            ))

    def _check_margins(self, report):
        margin = self.constraints.get("margin_mm")
        if margin is None:
            return
        m = float(margin)
        for p in self.spec.panels:
            if not p.visible:
                continue
            if p.x_mm < m or p.y_mm < m:
                report.warnings.append(self._issue(
                    "warning", "margin.out",
                    f"panel {p.id} near margin: x_mm={p.x_mm}, y_mm={p.y_mm} < {m}",
                    panel_id=p.id,
                ))
            if p.x_mm + p.w_mm > self.spec.width_mm - m:
                report.warnings.append(self._issue(
                    "warning", "margin.out",
                    f"panel {p.id} right edge exceeds by margin",
                    panel_id=p.id,
                ))
            if p.y_mm + p.h_mm > self.spec.height_mm - m:
                report.warnings.append(self._issue(
                    "warning", "margin.out",
                    f"panel {p.id} bottom edge exceeds by margin",
                    panel_id=p.id,
                ))

    def _check_column_size(self, report):
        col = getattr(self.preset, "column", {}) or {}
        cw = float(col.get("width_mm", 0.0))
        if cw <= 0:
            return
        for p in self.spec.panels:
            if p.visible and p.x_mm + p.w_mm > cw + 0.01:
                report.hints.append(self._issue(
                    "hint", "column.exceed",
                    f"panel {p.id} wider than column: right={p.x_mm + p.w_mm:.1f} mm > {cw:.1f} mm",
                    panel_id=p.id,
                ))

    def _check_colorblind(self, report):
        if not self.constraints.get("colorblind_safe"):
            return
        palette = set(OKABE_ITO)
        for panel in self.spec.panels:
            if not panel.visible:
                continue
            for idx, slot in enumerate(panel.curves):
                if not slot.visible:
                    continue
                line_style = None
                if slot.data_ref is not None and slot.data_ref.style is not None:
                    line_style = slot.data_ref.style.line_style
                try:
                    color = resolve_line_color(slot, idx, panel, line_style)
                except Exception:
                    continue
                if color not in palette:
                    report.hints.append(self._issue(
                        "hint", "palette.colorblind",
                        f"панель {panel.id}, кривая #{idx + 1}: цвет {color} вне палитры журнала; "
                        f"включите \"Использовать палитру пресета\" для соответствия",
                        panel_id=panel.id,
                        element_id=slot.data_ref.series_root_name if slot.data_ref else None,
                    ))

    def _check_overrides(self, report):
        for ann_id, ov in self.spec.data_bound_overrides.items():
            if ov.resolved is False:
                report.warnings.append(self._issue(
                    "warning", "annotation.unresolved",
                    f"data-bound annotation {ann_id} unresolved: {ov.unresolved_reason}",
                    element_id=ann_id,
                ))

    def _check_unresolved(self, report):
        if self.data_resolver is None:
            return
        present_ids = set()
        for p in self.spec.panels:
            for slot in p.curves:
                if slot.data_ref is None or slot.data_ref.is_empty():
                    continue
                try:
                    data = self.data_resolver(p, slot.data_ref)
                except Exception:
                    continue
                if not data:
                    continue
                for ann in data.get("panel_annotations", []) or []:
                    present_ids.add(ann["id"])
        for ann_id, ov in self.spec.data_bound_overrides.items():
            if ann_id not in present_ids and ov.resolved:
                report.warnings.append(self._issue(
                    "warning", "annotation.orphan_override",
                    f"override {ann_id} has no matching data-bound annotation",
                    element_id=ann_id,
                ))