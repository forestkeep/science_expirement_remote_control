"""Canvas — Matplotlib + drag/resize панелей + stale-индикаторы + выделение."""
from __future__ import annotations
import logging
from typing import Optional, Tuple

from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt5.QtGui import QCursor, QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import (
    QAction, QApplication, QMenu, QSizePolicy, QVBoxLayout, QWidget, QScrollArea,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from ..core.units import mm_to_px

logger = logging.getLogger(__name__)


class _CanvasInner(FigureCanvasQTAgg):
    panel_selected              = pyqtSignal(str, bool)
    panel_geometry_changed      = pyqtSignal(str, float, float, float, float)
    annotation_selected         = pyqtSignal(str)
    annotation_geometry_changed = pyqtSignal(str, tuple)
    selection_cleared           = pyqtSignal()

    refresh_data_requested      = pyqtSignal(str)
    refresh_style_requested     = pyqtSignal(str)
    enable_live_requested       = pyqtSignal(str)

    add_panel_requested         = pyqtSignal()
    delete_panel_requested      = pyqtSignal(str)
    apply_layout_requested      = pyqtSignal()

    def __init__(self, widget: "PublicationCanvas"):
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

        self._selected_panel_id: Optional[str] = None

    # -------------------------------------------------- selection
    def set_selected_panel(self, panel_id: Optional[str]) -> None:
        if self._selected_panel_id == panel_id:
            return
        self._selected_panel_id = panel_id or None
        self.update()

    @property
    def selected_panel_id(self) -> Optional[str]:
        return self._selected_panel_id

    # -------------------------------------------------- figure lifecycle
    def _update_figure_size(self) -> None:
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return
        dpi = float(self.figure.dpi) or 100.0
        try:
            self.figure.set_size_inches(w / dpi, h / dpi, forward=False)
        except Exception:
            logger.exception("_update_figure_size failed")

    def resizeEvent(self, event):
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
        self.draw_idle()

    # -------------------------------------------------- coordinates
    def _pos_to_mm(self, pos) -> Optional[Tuple[float, float]]:
        spec = self.widget.spec
        if spec is None:
            return None
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return None
        return float(pos.x()) / float(w) * spec.width_mm, float(pos.y()) / float(h) * spec.height_mm

    def _hit_panel(self, x_mm: float, y_mm: float, tol_mm: float = 2.0):
        spec = self.widget.spec
        if spec is None:
            return None
        for panel in reversed(spec.sorted_panels()):
            if panel.contains_point_mm(x_mm, y_mm, tol_mm=tol_mm):
                return panel
        return None

    def _annotation_center_mm(self, ann) -> Optional[Tuple[float, float]]:
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
        for ann in sorted(spec.presentation_annotations, key=lambda a: (-int(a.z), a.id)):
            if not ann.visible or ann.locked:
                continue
            c = self._annotation_center_mm(ann)
            if c is None:
                continue
            if abs(x_mm - c[0]) <= tol_mm and abs(y_mm - c[1]) <= tol_mm:
                return ann
        return None

    # -------------------------------------------------- mouse
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

        additive = bool(event.modifiers() & Qt.ShiftModifier)

        ann = self._hit_annotation(x_mm, y_mm)
        if ann is not None:
            self._drag_mode = "move_annotation"
            self._drag_ann_id = ann.id
            self._press_pos = (x_mm, y_mm)
            self._orig_ann_coords = tuple(ann.coords)
            self.annotation_selected.emit(ann.id)
            event.accept()
            return

        for panel in reversed(spec.sorted_panels()):
            edge = panel.edge_hit(x_mm, y_mm, tol_mm=2.0)
            if edge:
                self._drag_mode = "resize_" + edge
                self._drag_panel_id = panel.id
                self._press_pos = (x_mm, y_mm)
                self._orig_geom = (panel.x_mm, panel.y_mm, panel.w_mm, panel.h_mm)
                self.set_selected_panel(panel.id)
                self.panel_selected.emit(panel.id, additive)
                event.accept()
                return
            if panel.contains_point_mm(x_mm, y_mm, tol_mm=0.5):
                self._drag_mode = "move"
                self._drag_panel_id = panel.id
                self._press_pos = (x_mm, y_mm)
                self._orig_geom = (panel.x_mm, panel.y_mm, panel.w_mm, panel.h_mm)
                self.set_selected_panel(panel.id)
                self.panel_selected.emit(panel.id, additive)
                event.accept()
                return

        self.set_selected_panel(None)
        self.selection_cleared.emit()
        super().mousePressEvent(event)

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
            dx = x_mm - self._press_pos[0]
            dy = y_mm - self._press_pos[1]
            new = list(self._orig_ann_coords)
            if ann.coordinate_space in ("figure_mm", "panel_mm") and len(new) >= 2:
                new[0] = self._orig_ann_coords[0] + dx
                new[1] = self._orig_ann_coords[1] + dy
            self.annotation_geometry_changed.emit(ann.id, tuple(new))
            event.accept()
            return

        panel = spec.find_panel(self._drag_panel_id or "")
        if panel is None or panel.locked:
            self._drag_mode = ""
            self._drag_panel_id = None
            return
        dx = x_mm - self._press_pos[0]
        dy = y_mm - self._press_pos[1]
        ox, oy, ow, oh = self._orig_geom
        if self._drag_mode == "move":
            nx = max(0.0, ox + dx)
            ny = max(0.0, oy + dy)
            self.panel_geometry_changed.emit(panel.id, nx, ny, ow, oh)
        elif self._drag_mode == "resize_br":
            nw = max(2.0, ow + dx)
            nh = max(2.0, oh + dy)
            self.panel_geometry_changed.emit(panel.id, ox, oy, nw, nh)
        elif self._drag_mode == "resize_r":
            nw = max(2.0, ow + dx)
            self.panel_geometry_changed.emit(panel.id, ox, oy, nw, oh)
        elif self._drag_mode == "resize_b":
            nh = max(2.0, oh + dy)
            self.panel_geometry_changed.emit(panel.id, ox, oy, ow, nh)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_mode = ""
        self._drag_panel_id = None
        self._drag_ann_id = None
        super().mouseReleaseEvent(event)

    # -------------------------------------------------- paint
    def paintEvent(self, event):
        super().paintEvent(event)
        spec = self.widget.spec
        if spec is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        try:
            w = self.width()
            h = self.height()
            if w <= 0 or h <= 0:
                return

            # Пустой холст — подсказка
            if not spec.panels:
                painter.setPen(QColor("#5a5a5a"))
                f = QFont()
                f.setPointSize(13)
                painter.setFont(f)
                painter.drawText(
                    self.rect(),
                    Qt.AlignCenter,
                    "Холст пуст\n\n"
                    "Правый клик → «Добавить панель» или «Разложить по шаблону»\n"
                    "или кнопки «+ Панель» / «Раскладка» на панели инструментов",
                )

            # Подсветка выбранной панели
            if self._selected_panel_id:
                for panel in spec.sorted_panels():
                    if panel.id != self._selected_panel_id:
                        continue
                    x_px = int(panel.x_mm / spec.width_mm * w)
                    y_px = int(panel.y_mm / spec.height_mm * h)
                    w_px = int(panel.w_mm / spec.width_mm * w)
                    h_px = int(panel.h_mm / spec.height_mm * h)
                    painter.setPen(QPen(QColor("#2a82da"), 2, Qt.DashLine))
                    painter.setBrush(QColor(42, 130, 218, 30))
                    painter.drawRect(x_px, y_px, w_px, h_px)
                    break

            # Stale-бейджи
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
                x_px = int(panel.x_mm / spec.width_mm * w) + int(panel.w_mm / spec.width_mm * w) - 22
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

    # -------------------------------------------------- context menu
    def contextMenuEvent(self, event):
        pt = self._pos_to_mm(event.pos())
        if pt is None:
            return
        x_mm, y_mm = pt
        spec = self.widget.spec
        if spec is None:
            return

        target_panel = self._hit_panel(x_mm, y_mm, tol_mm=2.0)
        menu = QMenu(self)

        act_layout = QAction("Разложить по шаблону…", menu)
        act_layout.triggered.connect(self.apply_layout_requested.emit)
        menu.addAction(act_layout)
        menu.addSeparator()

        if target_panel is None:
            act_add = QAction("Добавить панель", menu)
            act_add.triggered.connect(self.add_panel_requested.emit)
            menu.addAction(act_add)
        else:
            self.set_selected_panel(target_panel.id)

            act_delete = QAction("Удалить панель", menu)
            act_delete.triggered.connect(
                lambda _checked=False, pid=target_panel.id:
                    self.delete_panel_requested.emit(pid)
            )
            menu.addAction(act_delete)
            menu.addSeparator()

            act_refresh_data = QAction("Обновить данные из источника", menu)
            act_refresh_style = QAction("Обновить стиль из источника", menu)
            act_enable_live = QAction("Разрешить живое обновление данных", menu)

            live = any(
                c.data_ref and c.data_ref.refresh_policy == "live"
                for c in target_panel.curves
            )
            act_refresh_data.setEnabled(not live)
            act_refresh_data.triggered.connect(
                lambda _checked=False, pid=target_panel.id:
                    self.refresh_data_requested.emit(pid)
            )
            act_refresh_style.triggered.connect(
                lambda _checked=False, pid=target_panel.id:
                    self.refresh_style_requested.emit(pid)
            )
            act_enable_live.triggered.connect(
                lambda _checked=False, pid=target_panel.id:
                    self.enable_live_requested.emit(pid)
            )
            menu.addAction(act_refresh_data)
            menu.addAction(act_refresh_style)
            menu.addSeparator()
            menu.addAction(act_enable_live)

        menu.exec_(event.globalPos())


class PublicationCanvas(QWidget):
    panel_geometry_changed      = pyqtSignal(str, float, float, float, float)
    panel_selected              = pyqtSignal(str, bool)
    annotation_selected         = pyqtSignal(str)
    annotation_geometry_changed = pyqtSignal(str, tuple)
    selection_cleared           = pyqtSignal()

    refresh_data_requested      = pyqtSignal(str)
    refresh_style_requested     = pyqtSignal(str)
    enable_live_requested       = pyqtSignal(str)

    add_panel_requested         = pyqtSignal()
    delete_panel_requested      = pyqtSignal(str)
    apply_layout_requested      = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self._widget = _CanvasInner(self)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._widget)

        self._widget.panel_geometry_changed.connect(self.panel_geometry_changed)
        self._widget.panel_selected.connect(self.panel_selected)
        self._widget.annotation_selected.connect(self.annotation_selected)
        self._widget.annotation_geometry_changed.connect(self.annotation_geometry_changed)
        self._widget.selection_cleared.connect(self.selection_cleared)
        self._widget.refresh_data_requested.connect(self.refresh_data_requested)
        self._widget.refresh_style_requested.connect(self.refresh_style_requested)
        self._widget.enable_live_requested.connect(self.enable_live_requested)
        self._widget.add_panel_requested.connect(self.add_panel_requested)
        self._widget.delete_panel_requested.connect(self.delete_panel_requested)
        self._widget.apply_layout_requested.connect(self.apply_layout_requested)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)
        self._real_size = False

    def set_spec(self, spec) -> None:
        self.spec = spec
        self._widget.set_selected_panel(None)

    def set_selected_panel(self, panel_id: Optional[str]) -> None:
        self._widget.set_selected_panel(panel_id)

    def set_figure(self, figure: Figure) -> None:
        self._widget.set_figure(figure)
        if self._real_size:
            self.set_real_size(True)

    def set_real_size(self, enabled: bool) -> None:
        self._real_size = bool(enabled)
        if enabled and self.spec is not None:
            dpi = QApplication.primaryScreen().logicalDotsPerInch()
            w_px = mm_to_px(self.spec.width_mm, dpi)
            h_px = mm_to_px(self.spec.height_mm, dpi)
            self._widget.setMinimumSize(w_px, h_px)
            self._widget.setMaximumSize(w_px, h_px)
        else:
            self._widget.setMinimumSize(0, 0)
            self._widget.setMaximumSize(16777215, 16777215)
        self._widget._update_figure_size()
        self._widget.draw_idle()