"""Валидатор. Все правила берутся из constraints пресета журнала.

Что проверяем:
  - min_font_pt: минимальный размер шрифта в фигуре.
  - min_line_pt: минимальная толщина линии.
  - dpi_min: минимальный DPI.
  - margin_mm: содержимое не выходит за поля.
  - colorblind_safe: если требует журнал — предупредить о палитре.
  - размер колонки: ширина/высота панелей не должна превышать колонку.
  - unresolved data-bound overrides: warning.
"""
from __future__ import annotations
from typing import Dict, List

from .rules import Issue, Report
from ..core.sentinel import MISSING


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

    # --------------------------------------------------------------- helpers
    def _issue(self, sev: str, code: str, msg: str,
               panel_id=None, element_id=None) -> Issue:
        return Issue(severity=sev, code=code, message=msg,
                     panel_id=panel_id, element_id=element_id)

    # --------------------------------------------------------------- rules
    def _check_font(self, report: Report):
        min_pt = self.constraints.get("min_font_pt")
        if min_pt is None:
            return
        sizes = [
            ("figure.font.size", None),
            ("panel.title_size", None),
            ("annotation.text_size", None),
            ("figure.axes.tick_size", None),
            ("figure.axes.label_size", None),
        ]
        for path, pid in sizes:
            v = self.stack.resolve(path)
            if v is MISSING:
                continue
            try:
                if float(v) < float(min_pt):
                    report.warnings.append(self._issue(
                        "warning", "font.size",
                        f"{path}={v} < min_font_pt={min_pt}", panel_id=pid,
                    ))
            except (TypeError, ValueError):
                pass

    def _check_line_width(self, report: Report):
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

    def _check_dpi(self, report: Report):
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

    def _check_margins(self, report: Report):
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

    def _check_column_size(self, report: Report):
        # Проверить, что панели не выходят за пределы ширины колонки
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

    def _check_colorblind(self, report: Report):
        if not self.constraints.get("colorblind_safe"):
            return
        palette = self.stack.resolve("color.palette")
        if palette is MISSING or palette == "okabe_ito":
            return
        report.warnings.append(self._issue(
            "warning", "palette.colorblind",
            f"palette={palette} not colorblind-safe; use 'okabe_ito'",
        ))

    def _check_overrides(self, report: Report):
        # Если у пользователя есть override поверх отсутствующей аннотации —
        # это unresolved, но мы не рендерим, только предупреждаем.
        for ann_id, ov in self.spec.data_bound_overrides.items():
            if ov.resolved is False:
                report.warnings.append(self._issue(
                    "warning", "annotation.unresolved",
                    f"data-bound annotation {ann_id} unresolved: {ov.unresolved_reason}",
                    element_id=ann_id,
                ))

    def _check_unresolved(self, report: Report):
        """Проверить, что все overrides ссылаются на существующие аннотации.

        Если data_resolver доступен — спросим у него актуальные id для
        каждой панели.
        """
        if self.data_resolver is None:
            return
        present_ids = set()
        for p in self.spec.panels:
            if p.data_ref is None:
                continue
            try:
                data = self.data_resolver(p, p.data_ref)
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