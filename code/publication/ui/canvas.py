"""Canvas — Matplotlib + drag/resize панелей + snap 1 мм + stale + аннотации.

Три контекстных меню (по ТЗ):
  * на пустом месте — Добавить / Разложить;
  * на панели      — Удалить / Обновить / Включить live / Разложить;
  * на аннотации   — Удалить / Свойства.

Производительность drag-а: результат Matplotlib-рендера кэшируется в QPixmap.
Пока модель не помечена как грязная (``_content_dirty=False``), paintEvent
рисует только кэш + лёгкий overlay (рамка выделения, stale-бейджи). Поэтому
перетаскивание и клики не запускают полный matplotlib-render.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np
from PyQt5.QtCore import QEvent, QRect, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QFont, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QAction, QApplication, QMenu, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from ..core.units import mm_to_px

logger = logging.getLogger(__name__)

SNAP_MM = 1.0


def _snap(value: float) -> float:
    return round(value / SNAP_MM) * SNAP_MM


class _CanvasInner(FigureCanvasQTAgg):
    panel_selected              = pyqtSignal(str, bool)
    panel_geometry_changed      = pyqtSignal(str, float, float, float, float)
    annotation_selected         = pyqtSignal(str)
    annotation_geometry_changed = pyqtSignal(str, tuple)
    annotation_delete_requested = pyqtSignal(str)
    annotation_properties       = pyqtSignal(str)
    selection_cleared           = pyqtSignal()

    refresh_data_requested      = pyqtSignal(str)
    refresh_style_requested     = pyqtSignal(str)
    enable_live_requested       = pyqtSignal(str)

    add_panel_requested         = pyqtSignal()
    add_text_requested          = pyqtSignal()
    add_arrow_requested         = pyqtSignal()
    add_scale_bar_requested     = pyqtSignal()
    add_bracket_requested       = pyqtSignal()
    apply_layout_requested      = pyqtSignal()
    delete_panel_requested      = pyqtSignal(str)

    # Испускается после отпускания мыши в конце drag-а/resize-а.
    # Позволяет вызывающему коду запустить немедленный рендер без дебаунса.
    drag_finished               = pyqtSignal()

    def __init__(self, widget: "PublicationCanvas"):
        # Эти атрибуты должны существовать до super().__init__(),
        # потому что FigureCanvasQTAgg.__init__ вызывает self.draw().
        self._cached_pixmap: Optional[QPixmap] = None
        self._content_dirty: bool = True

        self._figure = Figure(figsize=(1, 1), dpi=100)
        super().__init__(self._figure)
        self.widget = widget
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)

        self._drag_mode = ""
        self._drag_panel_id: Optional[str] = None
        self._drag_ann_id: Optional[str] = None
        self._press_pos: Tuple[float, float] = (0.0, 0.0)
        self._orig_geom: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
        self._orig_ann_coords: Tuple[float, ...] = ()
        self._selected_panel_ids: list = []

    def set_selected_panels(self, panel_ids: list) -> None:
        self._selected_panel_ids = list(panel_ids or [])
        self.update()

    @property
    def selected_panel_ids(self) -> list:
        return list(self._selected_panel_ids)

    # ---------------------------------------------------- figure lifecycle
    def _invalidate_cache(self) -> None:
        self._cached_pixmap = None
        self._content_dirty = True

    def draw(self) -> None:
        """Переопределение: после успешного рендера кэшируем результат.

        Вызывается matplotlib-ом из paintEvent/draw_idle. Кэш нужен,
        чтобы повторные repaint-ы (клик по панели, drag) не запускали
        дорогой matplotlib-render.
        """
        super().draw()
        if hasattr(self, "_cached_pixmap"):
            self._cache_from_buffer()
            self._content_dirty = False

    def _cache_from_buffer(self) -> None:
        """Снять текущий RGBA-буфер фигуры в QPixmap.

        Используем ``buffer_rgba()``, а не ``self.grab()``: grab снова
        вызовет paintEvent, а paintEvent может использовать кэш — получим
        рекурсию. Буфер агрегата (FigureCanvasAgg) содержит только
        результат matplotlib-рендера, без наших dashed-рамок и бейджей —
        ровно то, что нужно кэшировать.
        """
        try:
            rgba = np.asarray(self.figure.canvas.buffer_rgba())
            h, w = rgba.shape[:2]
            if w <= 0 or h <= 0:
                self._cached_pixmap = None
                return
            image = QImage(
                rgba.data, w, h, 4 * w, QImage.Format_RGBA8888
            ).copy()
            self._cached_pixmap = QPixmap.fromImage(image)
        except Exception:
            logger.exception("_cache_from_buffer failed")
            self._cached_pixmap = None

    def _update_figure_size(self) -> None:
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        dpi = float(self.figure.dpi) or 100.0
        try:
            self.figure.set_size_inches(w / dpi, h / dpi, forward=False)
        except Exception:
            logger.exception("_update_figure_size failed")

    def resizeEvent(self, event):
        # Размер изменился — кэш невалиден (другая ширина/высота).
        self._invalidate_cache()
        super().resizeEvent(event)
        self._update_figure_size()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_figure_size()

    def set_figure(self, figure: Figure) -> None:
        if getattr(self, "figure", None) is figure:
            self.draw_idle()
            return
        figure.set_canvas(self)
        self.figure = figure
        self._figure = figure
        self._update_figure_size()
        self._invalidate_cache()
        self.draw_idle()

    # -------------------------------------------------------- coordinates
    def _pos_to_mm(self, pos) -> Optional[Tuple[float, float]]:
        spec = self.widget.spec
        if spec is None:
            return None
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return None
        return (pos.x() / w * spec.width_mm, pos.y() / h * spec.height_mm)

    def _hit_panel(self, x_mm, y_mm, tol_mm: float = 2.0):
        spec = self.widget.spec
        if spec is None:
            return None
        for panel in reversed(spec.sorted_panels()):
            if panel.contains_point_mm(x_mm, y_mm, tol_mm=tol_mm):
                return panel
        return None

    def _annotation_center_mm(self, ann):
        spec = self.widget.spec
        if spec is None or len(ann.coords) < 2:
            return None
        x0, y0 = float(ann.coords[0]), float(ann.coords[1])
        if ann.coordinate_space == "figure_mm":
            return x0, y0
        if ann.coordinate_space == "panel_mm" and ann.panel_id:
            panel = spec.find_panel(ann.panel_id)
            if panel is not None:
                return panel.x_mm + x0, panel.y_mm + y0
        return None

    def _hit_annotation(self, x_mm, y_mm, tol_mm=5.0):
        spec = self.widget.spec
        if spec is None:
            return None
        for ann in sorted(spec.presentation_annotations,
                          key=lambda a: (-int(a.z), a.id)):
            if not ann.visible or ann.locked:
                continue
            c = self._annotation_center_mm(ann)
            if c is None:
                continue
            if abs(x_mm - c[0]) <= tol_mm and abs(y_mm - c[1]) <= tol_mm:
                return ann
        return None

    def _hit_stale_badge(self, x_mm: float, y_mm: float):
        spec = self.widget.spec
        if spec is None:
            return None
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return None

        click_x_px = x_mm / spec.width_mm * w
        click_y_px = y_mm / spec.height_mm * h

        for panel in reversed(spec.sorted_panels()):
            if not panel.visible:
                continue
            stale_data = any(
                getattr(c.data_ref, "stale_data", False)
                for c in panel.curves if c.data_ref is not None
            )
            stale_style = any(
                getattr(c.data_ref, "stale_style", False)
                for c in panel.curves if c.data_ref is not None
            )
            if not (stale_data or stale_style):
                continue

            x_px = (panel.x_mm + panel.w_mm) / spec.width_mm * w - 22
            y_px = panel.y_mm / spec.height_mm * h + 4

            if x_px <= click_x_px <= x_px + 18 and \
               y_px <= click_y_px <= y_px + 18:
                return panel, stale_data, stale_style
        return None

    # ---------------------------------------------------------------- mouse
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        pt = self._pos_to_mm(event.localPos())
        if pt is None:
            super().mousePressEvent(event)
            return
        x_mm, y_mm = pt
        spec = self.widget.spec
        if spec is None:
            super().mousePressEvent(event)
            return

        # 1) stale-бейдж
        badge = self._hit_stale_badge(x_mm, y_mm)
        if badge is not None:
            panel, stale_data, stale_style = badge
            if stale_data:
                self.refresh_data_requested.emit(panel.id)
            elif stale_style:
                self.refresh_style_requested.emit(panel.id)
            event.accept()
            return

        additive = bool(event.modifiers() & Qt.ShiftModifier)

        # 2) аннотация
        ann = self._hit_annotation(x_mm, y_mm)
        if ann is not None:
            self._drag_mode = "move_annotation"
            self._drag_ann_id = ann.id
            self._press_pos = (x_mm, y_mm)
            self._orig_ann_coords = tuple(ann.coords)
            self.annotation_selected.emit(ann.id)
            event.accept()
            return

        # 3) панель
        for panel in reversed(spec.sorted_panels()):
            edge = panel.edge_hit(x_mm, y_mm, tol_mm=2.0)
            if edge:
                self._drag_mode = "resize_" + edge
                self._drag_panel_id = panel.id
                self._press_pos = (x_mm, y_mm)
                self._orig_geom = (panel.x_mm, panel.y_mm, panel.w_mm, panel.h_mm)
                self._select_panel(panel.id, additive)
                event.accept()
                return
            if panel.contains_point_mm(x_mm, y_mm, tol_mm=0.5):
                self._drag_mode = "move"
                self._drag_panel_id = panel.id
                self._press_pos = (x_mm, y_mm)
                self._orig_geom = (panel.x_mm, panel.y_mm, panel.w_mm, panel.h_mm)
                self._select_panel(panel.id, additive)
                event.accept()
                return

        self._selected_panel_ids = []
        self.selection_cleared.emit()
        super().mousePressEvent(event)

    def _select_panel(self, panel_id: str, additive: bool) -> None:
        if additive:
            if panel_id in self._selected_panel_ids:
                self._selected_panel_ids.remove(panel_id)
            else:
                self._selected_panel_ids.append(panel_id)
        else:
            self._selected_panel_ids = [panel_id]
        self.panel_selected.emit(panel_id, additive)
        self.update()

    def mouseMoveEvent(self, event):
        pt = self._pos_to_mm(event.localPos())
        if pt is None:
            super().mouseMoveEvent(event)
            return
        x_mm, y_mm = pt
        spec = self.widget.spec

        if not self._drag_mode:
            cursor = Qt.ArrowCursor
            if spec is not None:
                for panel in reversed(spec.sorted_panels()):
                    edge = panel.edge_hit(x_mm, y_mm, tol_mm=2.0)
                    if edge == "br":
                        cursor = Qt.SizeFDiagCursor
                        break
                    if edge == "r":
                        cursor = Qt.SizeHorCursor
                        break
                    if edge == "b":
                        cursor = Qt.SizeVerCursor
                        break
            self.setCursor(QCursor(cursor))
            super().mouseMoveEvent(event)
            return

        if self._drag_mode == "move_annotation":
            ann = spec.find_presentation(self._drag_ann_id or "")
            if ann is None or ann.locked:
                self._drag_mode = ""
                self._drag_ann_id = None
                return
            dx = _snap(x_mm - self._press_pos[0])
            dy = _snap(y_mm - self._press_pos[1])
            new = list(self._orig_ann_coords)
            if ann.coordinate_space in ("figure_mm", "panel_mm") and len(new) >= 2:
                new[0] = self._orig_ann_coords[0] + dx
                new[1] = self._orig_ann_coords[1] + dy
            self.annotation_geometry_changed.emit(ann.id, tuple(new))
            # Модель обновлена — достаточно перерисовать overlay (рамка
            # аннотации), без полного matplotlib-рендера.
            self.update()
            event.accept()
            return

        panel = spec.find_panel(self._drag_panel_id or "")
        if panel is None or panel.locked:
            self._drag_mode = ""
            self._drag_panel_id = None
            return
        dx = _snap(x_mm - self._press_pos[0])
        dy = _snap(y_mm - self._press_pos[1])
        ox, oy, ow, oh = self._orig_geom
        if self._drag_mode == "move":
            nx = max(0.0, _snap(ox + dx))
            ny = max(0.0, _snap(oy + dy))
            self.panel_geometry_changed.emit(panel.id, nx, ny, ow, oh)
        elif self._drag_mode == "resize_br":
            nw = max(2.0, _snap(ow + dx))
            nh = max(2.0, _snap(oh + dy))
            self.panel_geometry_changed.emit(panel.id, ox, oy, nw, nh)
        elif self._drag_mode == "resize_r":
            nw = max(2.0, _snap(ow + dx))
            self.panel_geometry_changed.emit(panel.id, ox, oy, nw, oh)
        elif self._drag_mode == "resize_b":
            nh = max(2.0, _snap(oh + dy))
            self.panel_geometry_changed.emit(panel.id, ox, oy, ow, nh)
        # Перерисовываем overlay — dashed-рамка идёт за курсором в реальном
        # времени, кэш фигуры не трогаем.
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event):
        was_dragging = bool(self._drag_mode)
        self._drag_mode = ""
        self._drag_panel_id = None
        self._drag_ann_id = None
        super().mouseReleaseEvent(event)
        if was_dragging:
            # Пусть PublicationWidget запустит рендер немедленно, без дебаунса.
            self.drag_finished.emit()

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event):
        # Сначала — фигура. Если модель не грязная и есть кэш,
        # используем QPixmap (1–5 мс) вместо полного matplotlib-render
        # (100–300 мс). super().paintEvent() вызывает draw(), который
        # сам обновит кэш и сбросит _content_dirty.
        if not self._content_dirty and self._cached_pixmap is not None:
            painter = QPainter(self)
            try:
                painter.drawPixmap(0, 0, self._cached_pixmap)
            finally:
                painter.end()
        else:
            super().paintEvent(event)

        # Поверх — «живой» overlay: selection, stale-бейджи, empty-state.
        self._paint_overlay()

    def _paint_overlay(self):
        spec = self.widget.spec
        if spec is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        try:
            w, h = self.width(), self.height()
            if w <= 0 or h <= 0:
                return

            if not spec.panels:
                painter.setPen(QColor("#5a5a5a"))
                f = QFont()
                f.setPointSize(13)
                painter.setFont(f)
                painter.drawText(
                    self.rect(), Qt.AlignCenter,
                    "Холст пуст\n\n"
                    "Правый клик → «Добавить панель» или «Разложить по шаблону»",
                )

            for panel in spec.sorted_panels():
                if panel.id not in self._selected_panel_ids:
                    continue
                x_px = int(panel.x_mm / spec.width_mm * w)
                y_px = int(panel.y_mm / spec.height_mm * h)
                w_px = int(panel.w_mm / spec.width_mm * w)
                h_px = int(panel.h_mm / spec.height_mm * h)
                painter.setPen(QPen(QColor("#2a82da"), 2, Qt.DashLine))
                painter.setBrush(QColor(42, 130, 218, 30))
                painter.drawRect(x_px, y_px, w_px, h_px)

            for panel in spec.sorted_panels():
                if not panel.visible:
                    continue
                stale_data = any(
                    getattr(c.data_ref, "stale_data", False)
                    for c in panel.curves if c.data_ref is not None
                )
                stale_style = any(
                    getattr(c.data_ref, "stale_style", False)
                    for c in panel.curves if c.data_ref is not None
                )
                if not (stale_data or stale_style):
                    continue
                x_px = int(panel.x_mm / spec.width_mm * w) + \
                       int(panel.w_mm / spec.width_mm * w) - 22
                y_px = int(panel.y_mm / spec.height_mm * h) + 4
                color = QColor("#ff4040") if stale_data else QColor("#f5c542")
                painter.setPen(QPen(color, 2))
                painter.setBrush(QColor(0, 0, 0, 120))
                painter.drawEllipse(x_px, y_px, 18, 18)
                f = QFont()
                f.setPointSize(11)
                f.setBold(True)
                painter.setFont(f)
                painter.setPen(color)
                painter.drawText(QRect(x_px, y_px, 18, 18), Qt.AlignCenter, "⟳")
        finally:
            painter.end()

    # ------------------------------------------------------------ context menu
    def contextMenuEvent(self, event):
        pt = self._pos_to_mm(event.pos())
        if pt is None:
            return
        x_mm, y_mm = pt
        spec = self.widget.spec
        if spec is None:
            return

        ann = self._hit_annotation(x_mm, y_mm)
        if ann is not None:
            self._annotation_menu(event.globalPos(), ann.id)
            return

        panel = self._hit_panel(x_mm, y_mm, tol_mm=2.0)
        if panel is not None:
            self._panel_menu(event.globalPos(), panel.id)
            return

        self._empty_menu(event.globalPos())

    def _empty_menu(self, global_pos):
        menu = QMenu(self)
        add_sub = menu.addMenu("Добавить")
        act_panel = add_sub.addAction("Панель")
        act_text = add_sub.addAction("Текст (presentation)")
        act_arrow = add_sub.addAction("Стрелка (presentation)")
        act_scale = add_sub.addAction("Scale bar (presentation)")
        act_bracket = add_sub.addAction("Скобка (presentation)")
        act_panel.triggered.connect(self.add_panel_requested.emit)
        act_text.triggered.connect(self.add_text_requested.emit)
        act_arrow.triggered.connect(self.add_arrow_requested.emit)
        act_scale.triggered.connect(self.add_scale_bar_requested.emit)
        act_bracket.triggered.connect(self.add_bracket_requested.emit)
        menu.addSeparator()
        act_layout = menu.addAction("Разложить по шаблону…")
        act_layout.triggered.connect(self.apply_layout_requested.emit)
        menu.exec_(global_pos)

    def _panel_menu(self, global_pos, panel_id: str):
        menu = QMenu(self)
        act_del = menu.addAction("Удалить панель")
        menu.addSeparator()
        act_data = menu.addAction("Обновить данные из источника")
        act_style = menu.addAction("Обновить стиль из источника")
        act_live = menu.addAction("Включить живое обновление данных")
        act_data.triggered.connect(lambda _c=False, p=panel_id: self.refresh_data_requested.emit(p))
        act_style.triggered.connect(lambda _c=False, p=panel_id: self.refresh_style_requested.emit(p))
        act_live.triggered.connect(lambda _c=False, p=panel_id: self.enable_live_requested.emit(p))
        act_del.triggered.connect(lambda _c=False, p=panel_id: self.delete_panel_requested.emit(p))
        menu.addSeparator()
        act_layout = menu.addAction("Разложить по шаблону…")
        act_layout.triggered.connect(self.apply_layout_requested.emit)
        menu.exec_(global_pos)

    def _annotation_menu(self, global_pos, ann_id: str):
        menu = QMenu(self)
        act_del = menu.addAction("Удалить")
        act_props = menu.addAction("Свойства…")
        act_del.triggered.connect(lambda _c=False, a=ann_id: self.annotation_delete_requested.emit(a))
        act_props.triggered.connect(lambda _c=False, a=ann_id: self.annotation_properties.emit(a))
        menu.exec_(global_pos)


class PublicationCanvas(QWidget):
    """Обёртка с QScrollArea + letterbox в режиме fit."""

    panel_geometry_changed      = pyqtSignal(str, float, float, float, float)
    panel_selected              = pyqtSignal(str, bool)
    annotation_selected         = pyqtSignal(str)
    annotation_geometry_changed = pyqtSignal(str, tuple)
    annotation_delete_requested = pyqtSignal(str)
    annotation_properties       = pyqtSignal(str)
    selection_cleared           = pyqtSignal()

    refresh_data_requested      = pyqtSignal(str)
    refresh_style_requested     = pyqtSignal(str)
    enable_live_requested       = pyqtSignal(str)

    add_panel_requested         = pyqtSignal()
    add_text_requested          = pyqtSignal()
    add_arrow_requested         = pyqtSignal()
    add_scale_bar_requested     = pyqtSignal()
    add_bracket_requested       = pyqtSignal()
    apply_layout_requested      = pyqtSignal()
    delete_panel_requested      = pyqtSignal(str)

    # Пробрасываем drag_finished из внутреннего canvas-а.
    drag_finished               = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self._real_size = False

        self._widget = _CanvasInner(self)

        self._center = QWidget()
        self._center.setStyleSheet("background-color: #808080;")
        center_lay = QVBoxLayout(self._center)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setAlignment(Qt.AlignCenter)
        center_lay.addWidget(self._widget, 0, Qt.AlignCenter)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._center)
        self._scroll.viewport().installEventFilter(self)

        for name in (
            "panel_geometry_changed", "panel_selected", "annotation_selected",
            "annotation_geometry_changed", "annotation_delete_requested",
            "annotation_properties", "selection_cleared",
            "refresh_data_requested", "refresh_style_requested",
            "enable_live_requested", "add_panel_requested",
            "add_text_requested", "add_arrow_requested",
            "add_scale_bar_requested", "add_bracket_requested",
            "apply_layout_requested", "delete_panel_requested",
            "drag_finished",
        ):
            getattr(self._widget, name).connect(getattr(self, name))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)

    def eventFilter(self, obj, event):
        if obj is self._scroll.viewport() and event.type() == QEvent.Resize and not self._real_size:
            QTimer.singleShot(0, self._update_fit_geometry)
        return super().eventFilter(obj, event)

    def _update_fit_geometry(self):
        if self.spec is None:
            return
        dpi = QApplication.primaryScreen().logicalDotsPerInch()

        if self._real_size:
            w_px = mm_to_px(self.spec.width_mm, dpi)
            h_px = mm_to_px(self.spec.height_mm, dpi)
            self._widget.setFixedSize(w_px, h_px)
            self._center.setMinimumSize(w_px, h_px)
            self._center.setMaximumSize(w_px, h_px)
            return

        vp = self._scroll.viewport().size()
        if vp.width() <= 0 or vp.height() <= 0:
            return
        aspect = self.spec.height_mm / max(1e-9, self.spec.width_mm)
        w = vp.width()
        h = int(w * aspect)
        if h > vp.height():
            h = vp.height()
            w = int(h / max(1e-9, aspect))
        w = max(1, w)
        h = max(1, h)
        self._widget.setFixedSize(w, h)
        self._center.setMinimumSize(vp)
        self._center.setMaximumSize(vp)

    def set_spec(self, spec) -> None:
        self.spec = spec
        self._widget.set_selected_panels([])
        self._update_fit_geometry()

    def set_selected_panels(self, panel_ids: list) -> None:
        self._widget.set_selected_panels(panel_ids)

    def set_figure(self, figure) -> None:
        self._widget.set_figure(figure)
        self._update_fit_geometry()

    def set_real_size(self, enabled: bool) -> None:
        self._real_size = bool(enabled)
        self._scroll.setWidgetResizable(not self._real_size)
        if self._real_size:
            self._center.setMaximumSize(16777215, 16777215)
        self._update_fit_geometry()
        self._widget._update_figure_size()
        self._widget.draw_idle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._real_size:
            QTimer.singleShot(0, self._update_fit_geometry)