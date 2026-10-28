"""Рендерер типа DOMAIN — отдельная вкладка с собственным X."""
from __future__ import annotations

import logging
from typing import Dict
import pyqtgraph as pg
from graphs.ui.customPlotWidget import PatchedPlotWidget
from .base import BaseRenderer, artifact_legend_name
logger = logging.getLogger(__name__)

class DomainRenderer(BaseRenderer):
    def __init__(self, session) -> None:
        self.session = session
        self._tabs: Dict[str, dict] = {}


    def _ensure_tab(self, artifact_id: str, title: str) -> dict:
        if artifact_id in self._tabs:
            return self._tabs[artifact_id]
        plot = PatchedPlotWidget()

        # Стиль — как у основного графика
        from .base import apply_main_graph_style
        apply_main_graph_style(self.session, plot)

        idx = self.session.tabWidget.addTab(plot, title)

        # Запоминаем «смысловые» подписи осей, чтобы можно было их
        # восстановить после повторного apply_main_graph_style.
        info = {
            "plot": plot,
            "index": idx,
            "handles": [],
            "x_label": "",
            "y_label": "",
        }
        self._tabs[artifact_id] = info
        return info

    def _apply_axis_labels(self, plot, x_label: str, y_label: str) -> None:
        try:
            plot.setTitle("")
        except (AttributeError, RuntimeError) as exc:
            logger.warning("DomainRenderer: setTitle failed: %s", exc)

        for axis_name, label in (("bottom", x_label), ("left", y_label)):
            try:
                plot.setLabel(axis_name, label or "")
            except (AttributeError, RuntimeError) as exc:
                logger.warning(
                    "DomainRenderer: setLabel(%s) failed: %s", axis_name, exc
                )

            ctrl = getattr(plot, "axises", {}).get(axis_name)
            if ctrl is not None:
                try:
                    ctrl.settings.label = label or ""
                except (AttributeError, RuntimeError) as exc:
                    logger.debug(
                        "DomainRenderer: ctrl.settings.label: %s", exc
                    )


    def set_visible(self, handle, visible: bool) -> None:
        items = list(handle or [])
        for item in items:
            try:
                item.setVisible(bool(visible))
            except (AttributeError, RuntimeError) as exc:
                logger.debug("DomainRenderer.set_visible: setVisible: %s", exc)

        for info in self._tabs.values():
            legend = getattr(info.get("plot"), "legend", None)
            if legend is None:
                continue
            for item in items:
                if item not in info["handles"]:
                    continue
                try:
                    if visible:
                        if legend.getLabel(item) is None:
                            name = getattr(item, "_legend_name", None) or item.name()
                            if name is None:
                                continue
                            legend.addItem(item, name)
                    else:
                        legend.removeItem(item)
                except (AttributeError, RuntimeError, TypeError) as exc:
                    logger.warning(
                        "DomainRenderer.set_visible: legend update failed: %s",
                        exc,
                    )
    def reapply_labels(self) -> None:
        """Пере-применить подписи осей для всех открытых DOMAIN-вкладок.

        Вызывается после того, как ``apply_main_graph_style`` перезаписал
        подписи (например, при смене внешнего вида главного графика через
        инспектор или контекстное меню).
        """
        for info in self._tabs.values():
            plot = info.get("plot")
            if plot is None:
                continue
            self._apply_axis_labels(
                plot, info.get("x_label", ""), info.get("y_label", "")
            )

    def render(self, artifact, is_preview: bool = False):
        payload = artifact.payload
        title = payload.tab_title or artifact.tool_id
        info = self._ensure_tab(artifact.id, title)
        plot = info["plot"]

        # 1. Сохраняем «смысловые» подписи осей из payload …
        x_label = getattr(payload, "x_label", "") or ""
        y_label = getattr(payload, "y_label", "") or ""
        info["x_label"] = x_label
        info["y_label"] = y_label

        # 2. … и накладываем их поверх скопированных с главного графика.
        self._apply_axis_labels(plot, x_label, y_label)

        xs = getattr(payload, "x", None)
        ys = getattr(payload, "y", None)
        handles = []
        for i, (x, y) in enumerate(zip(xs, ys)):
            curve_id = (artifact.source_curve_ids[i]
                        if i < len(artifact.source_curve_ids) else None)
            curve = self.session.graph_main.get_curve(curve_id) if curve_id else None
            color = curve.saved_style.color if curve and curve.saved_style else "#ffffff"
            pen = pg.mkPen(color=color, width=2)

            name = artifact_legend_name(self.session, artifact, curve_id)
            item = plot.plot(x, y, name=name, pen=pen)
            item._legend_name = name

            try:
                legend = getattr(plot, "legend", None)
                if legend is not None and legend.getLabel(item) is None:
                    legend.addItem(item, name)
            except Exception:
                logger.exception("DomainRenderer: legend.addItem failed")
            handles.append(item)
        info["handles"].extend(handles)
        return handles

    # ------------------------------------------------------------------
    def update_legend_names(self, artifact) -> None:
        handles = getattr(artifact, "handle", None) or []
        info = self._tabs.get(artifact.id)
        if info is None:
            return
        legend = getattr(info.get("plot"), "legend", None)
        if legend is None:
            return
        for i, item in enumerate(handles):
            if item not in info["handles"]:
                continue
            curve_id = (artifact.source_curve_ids[i]
                        if i < len(artifact.source_curve_ids) else None)
            new_name = artifact_legend_name(self.session, artifact, curve_id)
            item._legend_name = new_name
            if not item.isVisible():
                continue
            try:
                old = legend.getLabel(item)
                if old == new_name:
                    continue
                if old is not None:
                    legend.removeItem(item)
                legend.addItem(item, new_name)
            except Exception:
                logger.exception("DomainRenderer.update_legend_names failed")

    def update(self, handle, payload) -> None:
        xs = getattr(payload, "x", None)
        ys = getattr(payload, "y", None)
        for i, item in enumerate(handle or []):
            if i < len(xs) and i < len(ys):
                item.setData(xs[i], ys[i])

    def remove(self, handle) -> None:
        for artifact_id, info in list(self._tabs.items()):
            for item in (handle or []):
                if item in info["handles"]:
                    info["handles"].remove(item)
            if not info["handles"]:
                idx = self.session.tabWidget.indexOf(info["plot"])
                if idx >= 0:
                    self.session.tabWidget.removeTab(idx)
                info["plot"].deleteLater()
                self._tabs.pop(artifact_id, None)


    def set_highlighted(self, handle, highlighted: bool) -> None:
        """Тот же стиль выделения, что и у основной кривой."""
        if not hasattr(self, "_original_pens"):
            self._original_pens = {}
        from graphs.core.curve_presenter import make_selection_style
        sel_pen = make_selection_style().to_pen()

        for item in (handle or []):
            try:
                key = id(item)
                if highlighted:
                    if key not in self._original_pens:
                        self._original_pens[key] = item.opts.get("pen")
                    item.setPen(sel_pen)
                else:
                    pen = self._original_pens.pop(key, None)
                    if pen is not None:
                        item.setPen(pen)
            except Exception:
                logger.exception("AttachedRenderer.set_highlighted failed")