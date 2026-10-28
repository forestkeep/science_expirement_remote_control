"""Рендерер типа OVERLAY — наложение на основной график.

Обрабатывает два вида payload:
  * kind="overlay"    — кривые-результаты (фитинги, производные);
  * kind="annotation" — точечные метки (пики/впадины): маркеры,
                        опциональные текстовые подписи, hover-tooltip.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5.QtWidgets import QToolTip
from PyQt5.QtGui import QCursor

from .base import BaseRenderer, artifact_legend_name
from graphs.core.curve_presenter import force_legend_layout

logger = logging.getLogger(__name__)

# Символы pyqtgraph для маркеров.
_ANNOTATION_SYMBOLS = {
    "peaks":   "t1",   # треугольник вверх
    "valleys": "t",    # треугольник вниз
}
_ANNOTATION_COLORS = {
    "peaks":   "#ffd23f",
    "valleys": "#3fb6ff",
}
_MARKER_SIZE = 14
_MARKER_HOVER_SIZE = 18


_HOVER_THRESHOLD = 500
_MAX_LABELS = 30 

class OverlayRenderer(BaseRenderer):
     
    def __init__(self, session) -> None:
        self.session = session
        self._original_pens: Dict[int, Any] = {}

    # ------------------------------------------------------------------
    def render(self, artifact, is_preview: bool = False):
        payload = artifact.payload
        kind = getattr(payload, "kind", None)
        if kind == "annotation":
            return self._render_annotation(artifact, is_preview)
        return self._render_overlay(artifact, is_preview)

    # ==================================================================
    # OVERLAY (кривые)
    # ==================================================================
    def _render_overlay(self, artifact, is_preview: bool = False):
        graph_view = self.session.graph_main.graphView
        payload = artifact.payload
        xs = getattr(payload, "x", None)
        ys = getattr(payload, "y", None)
        if xs is None or ys is None:
            return None

        handles = []
        for i, (x, y) in enumerate(zip(xs, ys)):
            curve_id = (artifact.source_curve_ids[i]
                        if i < len(artifact.source_curve_ids) else None)
            color = self._color_for(curve_id)
            width = self._width_for(curve_id)
            pen = pg.mkPen(color=color, width=width, style=QtCore.Qt.DashLine)
            if is_preview:
                pen.setStyle(QtCore.Qt.DotLine)
                pen.setColor(self._fade(color))
            legend_name = artifact_legend_name(self.session, artifact, curve_id)
            item = pg.PlotDataItem(x, y, pen=pen, name=legend_name)
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

    # ==================================================================
    # ANNOTATION (пики / впадины)
    # ==================================================================
    def _render_annotation(self, artifact, is_preview: bool = False):
        graph_view = self.session.graph_main.graphView
        payload = artifact.payload
        points = list(getattr(payload, "points", []) or [])
        if not points:
            return []

        label_kind = getattr(payload, "label", "peaks") or "peaks"
        symbol = _ANNOTATION_SYMBOLS.get(label_kind, "t1")
        fallback_color = _ANNOTATION_COLORS.get(label_kind, "#ffd23f")

        by_curve: Dict[Optional[str], List[Dict[str, Any]]] = {}
        for pt in points:
            cid = pt.get("curve")
            if not cid and artifact.source_curve_ids:
                cid = artifact.source_curve_ids[0]
            by_curve.setdefault(cid, []).append(pt)

        # --- ОДИН раз отключаем autoRange, включаем в finally ---
        plot_item = graph_view.plotItem
        was_auto = bool(plot_item.vb.autoRangeEnabled())
        if was_auto:
            plot_item.vb.disableAutoRange()

        handles: List[Any] = []
        legend = getattr(graph_view, "legend", None)
        total_points = sum(len(v) for v in by_curve.values())

        try:
            for curve_id, pts in by_curve.items():
                color = self._color_for(curve_id) or fallback_color
                fade = self._fade(color) if is_preview else color
                pen = pg.mkPen(color=fade, width=2)
                brush = pg.mkBrush(color=fade)

                xs = [float(p["x"]) for p in pts]
                ys = [float(p["y"]) for p in pts]
                spots_data = [
                    {
                        "x": float(p["x"]),
                        "y": float(p["y"]),
                        "index": int(p.get("index", -1)),
                        "prominence": p.get("prominence"),
                        "width": p.get("width"),
                    }
                    for p in pts
                ]

                n = len(xs)
                use_hover = n <= _HOVER_THRESHOLD

                scatter_kwargs = dict(
                    x=xs, y=ys,
                    symbol=symbol, size=_MARKER_SIZE,
                    pen=pen, brush=brush,
                    data=spots_data,
                    hoverable=use_hover,
                    pxMode=True,
                )
                if use_hover:
                    scatter_kwargs.update(
                        hoverSize=_MARKER_HOVER_SIZE,
                        hoverPen=pg.mkPen(color="#ffff00", width=2),
                    )
                scatter = pg.ScatterPlotItem(**scatter_kwargs)
                scatter.setZValue(200)
                scatter._annotation_curve_id = curve_id
                if use_hover:
                    scatter.sigHovered.connect(
                        lambda *a, s=scatter: self._on_scatter_hovered(s, *a)
                    )
                graph_view.addItem(scatter)
                handles.append(scatter)

                legend_name = self._annotation_legend_name(artifact, curve_id, n)
                scatter._legend_name = legend_name
                if legend is not None and legend.getLabel(scatter) is None:
                    try:
                        legend.addItem(scatter, legend_name)
                    except Exception:
                        logger.exception("OverlayRenderer: legend add failed")

            # Подписи — только если включены и общее число маленькое
            if (bool(artifact.params.get("show_labels", False))
                    and 0 < total_points <= _MAX_LABELS):
                handles.extend(
                    self._build_value_labels(by_curve, is_preview, plot_item)
                )
        finally:
            if was_auto:
                plot_item.vb.enableAutoRange()
                plot_item.vb.autoRange()

        return handles
    # ------------------------------------------------------------------
    def _build_value_labels(self, by_curve, is_preview: bool,
                            plot_item) -> List[Any]:
        """Текстовые подписи. Все идут через ignoreBounds=True — иначе
        ViewBox.updateViewRange() пересчитывает bounds после каждой вставки
        и получается O(N^2)."""
        labels: List[Any] = []
        for curve_id, pts in by_curve.items():
            color = self._color_for(curve_id) or "#ffffff"
            fade = self._fade(color) if is_preview else color
            for p in pts:
                try:
                    text = f"x={float(p['x']):.4g}\ny={float(p['y']):.4g}"
                except (TypeError, ValueError):
                    continue
                item = pg.TextItem(text=text, color=fade, anchor=(0.5, 1.3))
                item.setPos(float(p["x"]), float(p["y"]))
                item.setZValue(210)
                plot_item.addItem(item, ignoreBounds=True)   # ← ключевое
                labels.append(item)
        return labels

    def _on_scatter_hovered(self, scatter, *args):
        # --- mouse leave → скрыть ---
        for a in args:
            if a is not None and hasattr(a, "isExit") and a.isExit():
                QToolTip.hideText()
                return

        points = None
        event = None
        for a in args:
            if a is None:
                continue
            if isinstance(a, (list, tuple)) and not points:
                points = list(a)
                continue
            # event — QGraphicsSceneHoverEvent: имеет ОДНОВРЕМЕННО isEnter, isExit и pos.
            # ScatterPlotItem, SpotItem, QPointF — не имеют isEnter/isExit.
            if (event is None
                    and hasattr(a, "isEnter")
                    and hasattr(a, "isExit")
                    and hasattr(a, "pos")):
                event = a

        # Fallback: сигнал не передал список точек — берём у ScatterPlotItem по coord.
        if not points and event is not None:
            try:
                points = list(scatter.pointsAt(event.pos()))
            except Exception:
                logger.debug("hover: pointsAt failed", exc_info=True)
                points = None

        if not points:
            QToolTip.hideText()
            return

        pt = points[0]

        # SpotItem.data() обычно возвращает тот dict, что передан в
        # ScatterPlotItem(..., data=[...]). Но в редких сборках это может
        # быть сырое значение — защищаемся.
        try:
            data = pt.data() if hasattr(pt, "data") else None
        except Exception:
            data = None
        if not isinstance(data, dict):
            QToolTip.hideText()
            return

        x = data.get("x")
        y = data.get("y")
        if x is None or y is None:
            QToolTip.hideText()
            return

        parts = [f"x = {float(x):.6g}", f"y = {float(y):.6g}"]
        idx = data.get("index")
        if idx is not None and int(idx) >= 0:
            parts.append(f"index = {int(idx)}")
        prom = data.get("prominence")
        if prom is not None:
            try:
                parts.append(f"prominence = {float(prom):.6g}")
            except (TypeError, ValueError):
                pass
        w = data.get("width")
        if w is not None:
            try:
                parts.append(f"width = {float(w):.6g}")
            except (TypeError, ValueError):
                pass

        QToolTip.showText(QCursor.pos(), "\n".join(parts))
    # ==================================================================
    # Видимость / удаление / обновление
    # ==================================================================
    def set_visible(self, handle, visible: bool) -> None:
        graph_view = self.session.graph_main.graphView
        legend = getattr(graph_view, "legend", None)
        for item in (handle or []):
            try:
                item.setVisible(bool(visible))
                if legend is None:
                    continue
                in_legend = legend.getLabel(item) is not None
                name = getattr(item, "_legend_name", None)
                if visible:
                    if not in_legend and name:
                        try:
                            legend.addItem(item, name)
                        except Exception:
                            logger.exception(
                                "OverlayRenderer.set_visible: legend add failed"
                            )
                else:
                    if in_legend:
                        try:
                            legend.removeItem(item)
                        except Exception:
                            logger.exception(
                                "OverlayRenderer.set_visible: legend remove failed"
                            )
                        force_legend_layout(legend)
            except Exception:
                logger.exception("OverlayRenderer.set_visible failed")

    def update_legend_names(self, artifact) -> None:
        graph_view = self.session.graph_main.graphView
        legend = getattr(graph_view, "legend", None)
        handles = getattr(artifact, "handle", None) or []

        kind = getattr(artifact.payload, "kind", None)
        if kind == "annotation":
            counts: Dict[Optional[str], int] = {}
            for p in getattr(artifact.payload, "points", []) or []:
                cid = p.get("curve")
                if not cid and artifact.source_curve_ids:
                    cid = artifact.source_curve_ids[0]
                counts[cid] = counts.get(cid, 0) + 1

            for item in handles:
                if not isinstance(item, pg.ScatterPlotItem):
                    continue
                cid = getattr(item, "_annotation_curve_id", None)
                if cid is None and artifact.source_curve_ids:
                    cid = artifact.source_curve_ids[0]
                new_name = self._annotation_legend_name(artifact, cid, counts.get(cid, 0))
                item._legend_name = new_name
                if legend is None or not item.isVisible():
                    continue
                self._rename_in_legend(legend, item, new_name)
            return

        for i, item in enumerate(handles):
            curve_id = (artifact.source_curve_ids[i]
                        if i < len(artifact.source_curve_ids) else None)
            new_name = artifact_legend_name(self.session, artifact, curve_id)
            item._legend_name = new_name
            if legend is None or not item.isVisible():
                continue
            self._rename_in_legend(legend, item, new_name)

    def update(self, handle, payload) -> None:
        kind = getattr(payload, "kind", None)
        if kind == "annotation":
            # для аннотаций update не поддерживается — контроллер делает
            # remove+render (см. _do_update_params)
            return
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
        plot_item = graph_view.plotItem

        was_auto = bool(plot_item.vb.autoRangeEnabled())
        if was_auto:
            plot_item.vb.disableAutoRange()
        try:
            for item in (handle or []):
                self._original_pens.pop(id(item), None)
                if legend is not None and getattr(item, "_legend_name", None):
                    try:
                        legend.removeItem(item)
                    except (AttributeError, RuntimeError) as exc:
                        logger.debug(
                            "OverlayRenderer.remove: legend remove: %s", exc
                        )
                try:
                    graph_view.removeItem(item)
                except (AttributeError, RuntimeError) as exc:
                    logger.warning("OverlayRenderer.remove failed: %s", exc)
        finally:
            if was_auto:
                plot_item.vb.enableAutoRange()
                plot_item.vb.autoRange()
        if handle:
            force_legend_layout(legend)


    def set_highlighted(self, handle, highlighted: bool) -> None:
        from graphs.core.curve_presenter import make_selection_style
        sel_pen = make_selection_style().to_pen()

        for item in (handle or []):
            if isinstance(item, pg.TextItem):
                continue
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

    # ==================================================================
    # Утилиты
    # ==================================================================
    def _annotation_legend_name(self, artifact, curve_id, count: int) -> str:
        base = artifact_legend_name(self.session, artifact, curve_id)
        return f"{base} ({count})"

    def _rename_in_legend(self, legend, item, new_name: str) -> None:
        try:
            old = legend.getLabel(item)
            if old == new_name:
                return
            if old is not None:
                legend.removeItem(item)
            legend.addItem(item, new_name)
        except Exception:
            logger.exception("OverlayRenderer._rename_in_legend failed")

    def _color_for(self, curve_id):
        curve = self.session.graph_main.get_curve(curve_id) if curve_id else None
        if curve is not None and getattr(curve, "saved_style", None) is not None:
            return curve.saved_style.color
        return None

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