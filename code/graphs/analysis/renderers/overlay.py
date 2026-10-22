"""Рендерер типа OVERLAY — наложение на основной график."""
from __future__ import annotations

import logging

import pyqtgraph as pg
from PyQt5 import QtCore

from .base import BaseRenderer, artifact_legend_name

logger = logging.getLogger(__name__)


class OverlayRenderer(BaseRenderer):
    def __init__(self, session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    def render(self, artifact, is_preview: bool = False):
        graph_view = self.session.graph_main.graphView
        payload = artifact.payload
        xs = getattr(payload, "x", None)
        ys = getattr(payload, "y", None)
        if xs is None or ys is None:
            return None

        handles = []
        for i, (x, y) in enumerate(zip(xs, ys)):
            curve_id = artifact.source_curve_ids[i] if i < len(artifact.source_curve_ids) else None
            color = self._color_for(curve_id)
            width = self._width_for(curve_id)
            pen = pg.mkPen(color=color, width=width, style=QtCore.Qt.DashLine)
            if is_preview:
                pen.setStyle(QtCore.Qt.DotLine)
                pen.setColor(self._fade(color))
            legend_name = self._legend_name(artifact, curve_id)
            item = pg.PlotDataItem(x, y, pen=pen, name=legend_name)
            # Запоминаем имя на самом item'е: pyqtgraph при removeItem/addItem
            # без явного имени может потерять или подменить opts['name'].
            item._legend_name = legend_name
            item.setZValue(150)
            graph_view.addItem(item)
            try:
                legend = getattr(graph_view, "legend", None)
                if legend is not None and legend.getLabel(item) is None:
                    legend.addItem(item, legend_name)
            except Exception:
                logger.exception("OverlayRenderer: legend add failed")
            handles.append(item)
        return handles

    def set_visible(self, handle, visible: bool) -> None:
        """Скрыть/показать артефакт вместе с записью в легенде.

        При visible=False запись физически удаляется из legend.removeItem;
        при visible=True — возвращается обратно с тем же именем, что было
        при первом render.
        """
        graph_view = self.session.graph_main.graphView
        legend = getattr(graph_view, "legend", None)
        for item in (handle or []):
            try:
                if visible:
                    item.setVisible(True)
                    if legend is not None and legend.getLabel(item) is None:
                        name = getattr(item, "_legend_name", None) or item.name()
                        if name is None:
                            logger.warning(
                                "OverlayRenderer.set_visible: no legend name for %r", item
                            )
                            continue
                        try:
                            legend.addItem(item, name)
                        except Exception:
                            logger.exception(
                                "OverlayRenderer.set_visible: legend add failed"
                            )
                else:
                    if legend is not None:
                        try:
                            legend.removeItem(item)
                        except Exception:
                            logger.exception(
                                "OverlayRenderer.set_visible: legend remove failed"
                            )
                    item.setVisible(False)
            except Exception:
                logger.exception("OverlayRenderer.set_visible failed")

    def update_legend_names(self, artifact) -> None:
        """Обновить подписи в легенде без перерисовки данных."""
        graph_view = self.session.graph_main.graphView
        legend = getattr(graph_view, "legend", None)
        handles = getattr(artifact, "handle", None) or []
        for i, item in enumerate(handles):
            curve_id = (artifact.source_curve_ids[i]
                        if i < len(artifact.source_curve_ids) else None)
            new_name = self._legend_name(artifact, curve_id)
            item._legend_name = new_name
            if legend is None or not item.isVisible():
                continue
            try:
                old = legend.getLabel(item)
                if old == new_name:
                    continue
                if old is not None:
                    legend.removeItem(item)
                legend.addItem(item, new_name)
            except Exception:
                logger.exception("OverlayRenderer.update_legend_names failed")

    def update(self, handle, payload) -> None:
        xs = getattr(payload, "x", None)
        ys = getattr(payload, "y", None)
        if xs is None or ys is None:
            return
        for i, item in enumerate(handle or []):
            if i < len(xs) and i < len(ys):
                item.setData(xs[i], ys[i])

    def remove(self, handle) -> None:
        graph_view = self.session.graph_main.graphView
        legend = getattr(graph_view, "legend", None)
        for item in (handle or []):
            try:
                if legend is not None:
                    legend.removeItem(item)
            except Exception:
                pass
            try:
                graph_view.removeItem(item)
            except Exception:
                logger.exception("OverlayRenderer.remove failed")


    def set_highlighted(self, handle, highlighted: bool) -> None:
        """Подсветка артефакта тем же стилем, что и основная кривая.

        Оригинальный QPen каждого item'а запоминается один раз и
        восстанавливается при снятии выделения.
        """
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
                logger.exception("OverlayRenderer.set_highlighted failed")
    # ------------------------------------------------------------------
    def _legend_name(self, artifact, curve_id) -> str:
        return artifact_legend_name(self.session, artifact, curve_id)

    def _color_for(self, curve_id):
        curve = self.session.graph_main.get_curve(curve_id) if curve_id else None
        if curve is not None and getattr(curve, "saved_style", None) is not None:
            return curve.saved_style.color
        return "#ffffff"

    def _width_for(self, curve_id):
        curve = self.session.graph_main.get_curve(curve_id) if curve_id else None
        if curve is not None and getattr(curve, "saved_style", None) is not None:
            try:
                return max(1, int(float(curve.saved_style.line_width) * 0.75))
            except Exception:
                return 1
        return 1

    @staticmethod
    def _fade(color):
        try:
            c = pg.mkColor(color)
            c.setAlpha(140)
            return c
        except Exception:
            return color