"""Canvas — Matplotlib + drag/resize панелей и presentation-аннотаций в мм.

События перехватываются напрямую через Qt (mousePressEvent/Move/Release),
а не через mpl_connect. Это снимает зависимость от внутренних
переключений canvas у FigureCanvasQTAgg и работает даже при
matplotlib.use("Agg"), если не создавать NavigationToolbar.
"""
from __future__ import annotations
import logging
from typing import Optional, Tuple

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication, QSizePolicy, QVBoxLayout, QWidget, QScrollArea

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from ..core.units import mm_to_px

logger = logging.getLogger(__name__)


class _CanvasInner(FigureCanvasQTAgg):
    """FigureCanvasQTAgg + Qt-нативные pointer/drag/resize (панели + аннотации)."""

    panel_selected              = pyqtSignal(str, bool)
    panel_geometry_changed      = pyqtSignal(str, float, float, float, float)
    annotation_selected         = pyqtSignal(str)
    annotation_geometry_changed = pyqtSignal(str, tuple)
    selection_cleared           = pyqtSignal()

    def __init__(self, widget: "PublicationCanvas"):
        self._figure = Figure(figsize=(1, 1), dpi=100)
        super().__init__(self._figure)
        self.widget = widget
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)

        self._drag_mode = ""             # "" | move | resize_br/r/b | move_annotation
        self._drag_panel_id: Optional[str] = None
        self._drag_ann_id: Optional[str] = None
        self._press_pos: Tuple[float, float] = (0.0, 0.0)
        self._orig_geom: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
        self._orig_ann_coords: Tuple[float, ...] = ()

    # ----------------------------------------------------- figure lifecycle
    def _update_figure_size(self) -> None:
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return
        # figure.bbox совпадает с (w, h): отношение event.x/bbox.width = event.x/w
        dpi = float(self.figure.dpi) or 100.0
        try:
            self.figure.set_size_inches(w / dpi, h / dpi, forward=False)
        except Exception:
            logger.exception("_update_figure_size failed")

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._update_figure_size()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self._update_figure_size()

    def set_figure(self, figure: Figure) -> None:
        """Подменить figure у существующего виджета. Никаких новых виджетов."""
        if getattr(self, "figure", None) is figure:
            self.draw_idle()
            return
        # 1) Связать новую фигуру с этим канвасом
        figure.set_canvas(self)
        # 2) КРИТИЧНО: обновить ПУБЛИЧНЫЙ атрибут FigureCanvasBase.
        #    Именно canvas.figure используется matplotlib в
        #    MouseEvent._process() → canvas.figure.pick().
        self.figure = figure
        # 3) Синхронизировать приватный дубликат (его используем в своём коде)
        self._figure = figure
        # 4) Старую фигуру НЕ трогаем: не вызываем old.set_canvas(None).
        #    Если canvas.figure когда-либо ещё укажет на старую фигуру,
        #    pick() упадёт на None.widgetlock. GC уберёт её сам, когда
        #    исчезнут все внешние ссылки.
        self._update_figure_size()
        self.draw_idle()

    # ----------------------------------------------------- coordinate map
    def _pos_to_mm(self, pos) -> Optional[Tuple[float, float]]:
        """event.localPos() (логические пиксели) → (x_mm, y_mm) в системе spec."""
        spec = self.widget.spec
        if spec is None:
            return None
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return None
        fx = float(pos.x()) / float(w)
        fy = float(pos.y()) / float(h)
        return fx * spec.width_mm, fy * spec.height_mm

    # ----------------------------------------------------- annotation hit
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

    def _hit_annotation(self, x_mm: float, y_mm: float, tol_mm: float = 5.0):
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

    # ----------------------------------------------------- press
    def mousePressEvent(self, event):  # noqa: N802
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

        # 1) аннотации (верхний слой)
        ann = self._hit_annotation(x_mm, y_mm)
        if ann is not None:
            self._drag_mode = "move_annotation"
            self._drag_ann_id = ann.id
            self._press_pos = (x_mm, y_mm)
            self._orig_ann_coords = tuple(ann.coords)
            self.annotation_selected.emit(ann.id)
            event.accept()
            return

        # 2) панели (по убыванию z)
        for panel in reversed(spec.sorted_panels()):
            edge = panel.edge_hit(x_mm, y_mm, tol_mm=2.0)
            if edge:
                self._drag_mode = "resize_" + edge
                self._drag_panel_id = panel.id
                self._press_pos = (x_mm, y_mm)
                self._orig_geom = (panel.x_mm, panel.y_mm, panel.w_mm, panel.h_mm)
                self.panel_selected.emit(panel.id, additive)
                event.accept()
                return
            if panel.contains_point_mm(x_mm, y_mm, tol_mm=0.5):
                self._drag_mode = "move"
                self._drag_panel_id = panel.id
                self._press_pos = (x_mm, y_mm)
                self._orig_geom = (panel.x_mm, panel.y_mm, panel.w_mm, panel.h_mm)
                self.panel_selected.emit(panel.id, additive)
                event.accept()
                return

        self.selection_cleared.emit()
        super().mousePressEvent(event)

    # ----------------------------------------------------- move
    def mouseMoveEvent(self, event):  # noqa: N802
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

        # --- drag аннотации ---
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

        # --- drag панели ---
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

    # ----------------------------------------------------- release
    def mouseReleaseEvent(self, event):  # noqa: N802
        self._drag_mode = ""
        self._drag_panel_id = None
        self._drag_ann_id = None
        super().mouseReleaseEvent(event)


class PublicationCanvas(QWidget):
    """Контейнер: FigureCanvasQTAgg + QScrollArea + проксирование сигналов."""

    panel_geometry_changed      = pyqtSignal(str, float, float, float, float)
    panel_selected              = pyqtSignal(str, bool)
    annotation_selected         = pyqtSignal(str)
    annotation_geometry_changed = pyqtSignal(str, tuple)
    selection_cleared           = pyqtSignal()

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)
        self._real_size = False

    def set_spec(self, spec) -> None:
        self.spec = spec

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