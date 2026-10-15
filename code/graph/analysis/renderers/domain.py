"""Рендерер типа DOMAIN — отдельная вкладка с собственным X."""
from __future__ import annotations

import logging
from typing import Any, Dict

import pyqtgraph as pg

from graph.ui.customPlotWidget import PatchedPlotWidget

from .base import BaseRenderer

logger = logging.getLogger(__name__)


class DomainRenderer(BaseRenderer):
    def __init__(self, session) -> None:
        self.session = session
        self._tabs: Dict[str, dict] = {}

    def _ensure_tab(self, artifact_id: str, title: str) -> dict:
        if artifact_id in self._tabs:
            return self._tabs[artifact_id]
        plot = PatchedPlotWidget()
        idx = self.session.tabWidget.addTab(plot, title)
        info = {"plot": plot, "index": idx, "handles": []}
        self._tabs[artifact_id] = info
        return info

    def render(self, artifact, is_preview: bool = False):
        payload = artifact.payload
        title = payload.tab_title or artifact.tool_id
        info = self._ensure_tab(artifact.id, title)
        plot = info["plot"]
        xs = getattr(payload, "x", None)
        ys = getattr(payload, "y", None)
        handles = []
        for i, (x, y) in enumerate(zip(xs, ys)):
            curve_id = artifact.source_curve_ids[i] if i < len(artifact.source_curve_ids) else None
            curve = self.session.graph_main.get_curve(curve_id) if curve_id else None
            color = curve.saved_style.color if curve and curve.saved_style else "#ffffff"
            pen = pg.mkPen(color=color, width=2)
            item = plot.plot(x, y, pen=pen)
            handles.append(item)
        info["handles"].extend(handles)
        return handles

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

    def set_visible(self, handle, visible: bool) -> None:
        for item in (handle or []):
            try:
                item.setVisible(bool(visible))
            except Exception:
                pass

    def set_highlighted(self, handle, highlighted: bool) -> None:
        """Тот же стиль выделения, что и у основной кривой."""
        if not hasattr(self, "_original_pens"):
            self._original_pens = {}
        from graph.core.curve_presenter import make_selection_style
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