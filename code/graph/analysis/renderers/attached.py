"""Рендерер типа ATTACHED — привязанная панель под основным графиком."""
from __future__ import annotations

import logging
from typing import Dict

import pyqtgraph as pg
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from graph.ui.customPlotWidget import PatchedPlotWidget

from .base import BaseRenderer

logger = logging.getLogger(__name__)


class AttachedRenderer(BaseRenderer):
    """Создаёт панель в QSplitter под основным графиком.

    Заголовок инструмента выводится как легенда на самом поле графика.
    Крестик закрытия отсутствует — панель исчезает, когда все её артефакты
    скрыты (или удалены).
    """

    def __init__(self, session) -> None:
        self.session = session
        self._panels: Dict[str, dict] = {}  # tool_id -> {widget, plot, handles}

    def _ensure_panel(self, tool_id: str, title: str) -> dict:
        if tool_id in self._panels:
            return self._panels[tool_id]
        page = self.session.graph_main.page
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
            page.setLayout(layout)

        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)

        plot = PatchedPlotWidget()
        plot.setXLink(self.session.graph_main.graphView.plotItem)
        # Легенда на самом поле графика — сюда попадут имена кривых
        plot.addLegend()
        # Подпись оси Y
        try:
            plot.setLabel("left", title)
        except Exception:
            pass

        outer.addWidget(plot)

        insert_index = max(0, layout.count() - 1)
        layout.insertWidget(insert_index, container)

        info = {"container": container, "plot": plot, "handles": [], "title": title}
        self._panels[tool_id] = info
        return info

    def _maybe_hide_panel(self, tool_id: str) -> None:
        info = self._panels.get(tool_id)
        if info is None:
            return
        any_visible = any(item.isVisible() for item in info["handles"])
        info["container"].setVisible(any_visible)

    # ------------------------------------------------------------------
    def render(self, artifact, is_preview: bool = False):
        title = getattr(artifact.payload, "panel_title", "") or artifact.tool_id
        info = self._ensure_panel(artifact.tool_id, title)
        info["container"].setVisible(True)
        plot = info["plot"]
        payload = artifact.payload
        xs = getattr(payload, "x", None) or []
        ys = getattr(payload, "y", None) or []
        handles = []
        for i, (x, y) in enumerate(zip(xs, ys)):
            curve_id = artifact.source_curve_ids[i] if i < len(artifact.source_curve_ids) else None
            curve = self.session.graph_main.get_curve(curve_id) if curve_id else None
            curve_name = curve.curve_name if curve else (curve_id or "?")
            color = curve.saved_style.color if curve and curve.saved_style else "#ffffff"
            pen = pg.mkPen(color=color, width=2)
            item = plot.plot(x, y, pen=pen, name=curve_name)
            handles.append(item)
        info["handles"].extend(handles)
        # при применении артефакт видим по своему флагу
        for item in handles:
            item.setVisible(bool(getattr(artifact, "visibility", True)))
        self._maybe_hide_panel(artifact.tool_id)
        return handles

    def update(self, handle, payload) -> None:
        xs = getattr(payload, "x", None)
        ys = getattr(payload, "y", None)
        for i, item in enumerate(handle or []):
            if i < len(xs) and i < len(ys):
                item.setData(xs[i], ys[i])

    def remove(self, handle) -> None:
        for tool_id, info in list(self._panels.items()):
            for item in (handle or []):
                if item in info["handles"]:
                    info["handles"].remove(item)
                    try:
                        # удаляем из легенды
                        legend = getattr(info["plot"], "legend", None)
                        if legend is not None:
                            legend.removeItem(item)
                    except Exception:
                        pass
                    try:
                        info["plot"].removeItem(item)
                    except Exception:
                        pass
            if not info["handles"]:
                parent = info["container"].parent()
                if parent is not None and parent.layout() is not None:
                    parent.layout().removeWidget(info["container"])
                info["container"].deleteLater()
                self._panels.pop(tool_id, None)

    def set_visible(self, handle, visible: bool) -> None:
        for item in (handle or []):
            try:
                item.setVisible(bool(visible))
            except Exception:
                pass
        # проверим, есть ли ещё видимые артефакты во всех панелях
        for tool_id in list(self._panels.keys()):
            self._maybe_hide_panel(tool_id)

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