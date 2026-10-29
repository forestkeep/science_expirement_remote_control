"""Инспектор: геометрия, стиль, кривые, анализ, палитра."""
from __future__ import annotations
import logging
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
    QListWidget, QListWidgetItem, QToolButton, QInputDialog,
)

from ..core.sentinel import MISSING
from ..model.stylestack import set_override, clear_override
from ..model.panel import CurveSlot
from .context_menus import ImportSessionDialog

logger = logging.getLogger(__name__)


STYLE_PATHS = [
    ("figure.font.size", "Размер шрифта (pt)"),
    ("figure.font.family", "Семейство шрифта"),
    ("figure.line.width", "Толщина линии"),
    ("figure.axes.line_width", "Толщина осей"),
    ("figure.axes.tick_size", "Размер тиков"),
    ("figure.axes.label_size", "Размер подписей осей"),
    ("annotation.text_size", "Размер текста аннотаций"),
    ("annotation.scalebar.width_mm", "Ширина scale bar (мм)"),
    ("annotation.bracket.width_pt", "Толщина bracket (pt)"),
    ("color.palette", "Палитра"),
]


class FigureInspector(QWidget):
    geometry_changed = pyqtSignal(str, float, float, float, float)
    style_override_changed = pyqtSignal(str, str, object)
    style_override_cleared = pyqtSignal(str, str)
    style_override_cleared_all = pyqtSignal(str)
    refresh_requested = pyqtSignal(str)

    def __init__(self, stack_getter, parent=None):
        super().__init__(parent)
        self._stack_getter = stack_getter
        self.spec = None
        self._current_panel_id: Optional[str] = None
        self._suppress = False

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        self._body_layout = QVBoxLayout(body)

        self._geom_label = QLabel("Панель не выбрана")
        self._geom_label.setStyleSheet("font-weight: bold;")
        self._body_layout.addWidget(self._geom_label)

        geom_form = QFormLayout()
        self._x = self._spin(0, 500)
        self._y = self._spin(0, 500)
        self._w = self._spin(1, 500)
        self._h = self._spin(1, 500)
        for label, w in (("x, мм", self._x), ("y, мм", self._y),
                         ("w, мм", self._w), ("h, мм", self._h)):
            w.valueChanged.connect(self._on_geom)
            geom_form.addRow(label, w)
        self._body_layout.addLayout(geom_form)

        # --- Секция «Кривые» ---
        self._curves_label = QLabel("Кривые")
        self._curves_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self._body_layout.addWidget(self._curves_label)
        self._curves_list = QListWidget()
        self._curves_list.setMaximumHeight(160)
        self._body_layout.addWidget(self._curves_list)
        self._add_curve_btn = QPushButton("Добавить кривую")
        self._add_curve_btn.clicked.connect(self._on_add_curve)
        self._body_layout.addWidget(self._add_curve_btn)

        # --- Цвет из источника ---
        self._use_source_color = QCheckBox("Брать цвет из кривой-источника")
        self._use_source_color.stateChanged.connect(self._on_use_source_color)
        self._body_layout.addWidget(self._use_source_color)

        # --- Секция «Анализ» ---
        self._analysis_label = QLabel("Анализ")
        self._analysis_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self._body_layout.addWidget(self._analysis_label)
        self._analysis_form = QFormLayout()
        self._analysis_widgets = {}
        self._body_layout.addLayout(self._analysis_form)

        # --- Стиль ---
        style_title = QLabel("Стиль")
        style_title.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self._body_layout.addWidget(style_title)

        self._form = QFormLayout()
        self._widgets = {}
        for path, label in STYLE_PATHS:
            row = QHBoxLayout()
            if path == "figure.font.family":
                w = QLineEdit()
                w.editingFinished.connect(lambda p=path, ww=w: self._on_style(p, ww.text()))
            elif path == "color.palette":
                w = QComboBox()
                w.addItems(["okabe_ito", "viridis", "default"])
                w.currentIndexChanged.connect(lambda _i, p=path, ww=w: self._on_style(p, ww.currentText()))
            else:
                w = QDoubleSpinBox()
                w.setDecimals(3)
                w.setRange(0.0, 1e6)
                w.setSingleStep(0.1)
                w.valueChanged.connect(lambda v, p=path: self._on_style(p, float(v)))
            reset_btn = QPushButton("↺")
            reset_btn.setFixedWidth(28)
            reset_btn.setToolTip("Сбросить к пресету")
            reset_btn.clicked.connect(lambda _c=False, p=path: self._reset_style(p))
            self._widgets[path] = (w, reset_btn)
            row.addWidget(w, 1)
            row.addWidget(reset_btn)
            self._form.addRow(label, row)
        self._body_layout.addLayout(self._form)

        reset_all = QPushButton("Сбросить все переопределения панели")
        reset_all.clicked.connect(self._reset_all)
        self._body_layout.addWidget(reset_all)
        self._body_layout.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll)

    def _spin(self, lo, hi):
        s = QDoubleSpinBox()
        s.setDecimals(2)
        s.setRange(lo, hi)
        s.setSuffix(" мм")
        return s

    def set_spec(self, spec):
        self.spec = spec

    def select_panel(self, panel_id: str) -> None:
        self._current_panel_id = panel_id or None
        if not panel_id:
            self._geom_label.setText("Панель не выбрана")
            self._curves_list.clear()
            return
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        self._geom_label.setText(f"Панель {p.id}")
        self._suppress = True
        try:
            self._x.setValue(p.x_mm)
            self._y.setValue(p.y_mm)
            self._w.setValue(p.w_mm)
            self._h.setValue(p.h_mm)
        finally:
            self._suppress = False
        self._use_source_color.blockSignals(True)
        self._use_source_color.setChecked(p.use_source_color)
        self._use_source_color.blockSignals(False)
        self._rebuild_curves_list(p)
        self._rebuild_analysis(p)
        self._refresh_style_indicators()

    def _rebuild_curves_list(self, panel):
        self._curves_list.clear()
        for i, slot in enumerate(panel.curves):
            ref = slot.data_ref
            name = ref.series_root_name if ref is not None and not ref.is_empty() else "(пустая ссылка)"
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(2, 2, 2, 2)
            vis = QCheckBox()
            vis.setChecked(slot.visible)
            vis.stateChanged.connect(lambda st, idx=i: self._on_slot_visibility(idx, st != 0))
            axis_combo = QComboBox()
            axis_combo.addItems(["Y1", "Y2"])
            axis_combo.setCurrentText("Y2" if slot.axis == "y2" else "Y1")
            axis_combo.currentIndexChanged.connect(
                lambda _ix, idx=i, cb=axis_combo: self._on_slot_axis(idx, cb.currentText().lower())
            )
            label = QLineEdit(slot.legend_label)
            label.editingFinished.connect(lambda idx=i, ww=label: self._on_slot_legend(idx, ww.text()))
            delete_btn = QPushButton("×")
            delete_btn.setFixedWidth(22)
            delete_btn.clicked.connect(lambda _c=False, idx=i: self._on_slot_delete(idx))
            hl.addWidget(vis)
            hl.addWidget(axis_combo)
            hl.addWidget(label, 1)
            hl.addWidget(delete_btn)
            item = QListWidgetItem(self._curves_list)
            item.setSizeHint(w.sizeHint())
            item.setText(name)
            self._curves_list.addItem(item)
            self._curves_list.setItemWidget(item, w)

    def _rebuild_analysis(self, panel):
        while self._analysis_form.count():
            item = self._analysis_form.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._analysis_widgets = {}
        all_tool_ids = set()
        for slot in panel.curves:
            if slot.data_ref is None or slot.data_ref.style is None:
                continue
            for art in getattr(slot.data_ref.style, "artifacts", []) or []:
                tid = getattr(art, "tool_id", "")
                if tid:
                    all_tool_ids.add(tid)
        for tid in ("attached", "domain"):
            all_tool_ids.add(tid)
        for tool_id in sorted(all_tool_ids):
            cb = QCheckBox(tool_id)
            cb.setChecked(bool(panel.show_tools.get(tool_id, False)))
            if tool_id in ("attached", "domain"):
                cb.setToolTip("не переносится в текущей версии; включение не окажет эффекта")
            cb.stateChanged.connect(
                lambda st, t=tool_id: self._on_show_tool(t, st != 0)
            )
            self._analysis_form.addRow(cb)
            self._analysis_widgets[tool_id] = cb

    def _on_slot_visibility(self, index, visible):
        p = self.spec.find_panel(self._current_panel_id)
        if p is None or index >= len(p.curves):
            return
        p.curves[index].visible = visible
        self.geometry_changed.emit(p.id, p.x_mm, p.y_mm, p.w_mm, p.h_mm)

    def _on_slot_axis(self, index, axis):
        p = self.spec.find_panel(self._current_panel_id)
        if p is None or index >= len(p.curves):
            return
        p.curves[index].axis = axis
        self.geometry_changed.emit(p.id, p.x_mm, p.y_mm, p.w_mm, p.h_mm)

    def _on_slot_legend(self, index, text):
        p = self.spec.find_panel(self._current_panel_id)
        if p is None or index >= len(p.curves):
            return
        p.curves[index].legend_label = text
        self.geometry_changed.emit(p.id, p.x_mm, p.y_mm, p.w_mm, p.h_mm)

    def _on_slot_delete(self, index):
        p = self.spec.find_panel(self._current_panel_id)
        if p is None or index >= len(p.curves):
            return
        p.curves.pop(index)
        self._rebuild_curves_list(p)
        self.geometry_changed.emit(p.id, p.x_mm, p.y_mm, p.w_mm, p.h_mm)

    def _on_add_curve(self):
        p = self.spec.find_panel(self._current_panel_id)
        if p is None:
            return
        ctrl = self._find_session_controller()
        if ctrl is None:
            return
        dialog = ImportSessionDialog(ctrl, self)
        if dialog.exec_() != __import__("PyQt5.QtWidgets", fromlist=["QDialog"]).QDialog.Accepted:
            return
        ref = dialog.get_data_ref()
        if ref.is_empty():
            return
        sess = getattr(ctrl, "graph_sessions", {}).get(ref.session_id)
        if sess is not None:
            gm = getattr(sess, "graph_main", None)
            if gm is not None:
                curve = gm.get_curve(ref.series_root_name)
                if curve is not None:
                    from ..model.session_ref import DataSnapshot, StyleSnapshot
                    ref.data = DataSnapshot.take(curve)
                    ref.style = StyleSnapshot.take(curve, None)
                    ref.refresh_policy = "snapshot"
        p.curves.append(CurveSlot(data_ref=ref))
        self._rebuild_curves_list(p)
        self.geometry_changed.emit(p.id, p.x_mm, p.y_mm, p.w_mm, p.h_mm)

    def _find_session_controller(self):
        w = self.parent()
        while w is not None:
            if hasattr(w, "session_controller"):
                return w.session_controller
            w = w.parent()
        return None

    def _on_use_source_color(self, state):
        p = self.spec.find_panel(self._current_panel_id)
        if p is None:
            return
        p.use_source_color = state != 0
        self.geometry_changed.emit(p.id, p.x_mm, p.y_mm, p.w_mm, p.h_mm)

    def _on_show_tool(self, tool_id, value):
        p = self.spec.find_panel(self._current_panel_id)
        if p is None:
            return
        p.show_tools[tool_id] = value
        self.geometry_changed.emit(p.id, p.x_mm, p.y_mm, p.w_mm, p.h_mm)

    def _refresh_style_indicators(self) -> None:
        stack = self._stack_getter()
        if stack is None:
            return
        for path, (w, btn) in self._widgets.items():
            full_path = self._path_for_panel(path)
            resolved = stack.resolve(full_path)
            default = stack.resolve(path)
            overridden = resolved is not MISSING and default is not MISSING and resolved != default
            if isinstance(w, QLineEdit):
                w.setText("" if resolved is MISSING else str(resolved))
            elif isinstance(w, QComboBox):
                idx = w.findText("" if resolved is MISSING else str(resolved))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            else:
                if resolved is not MISSING:
                    try:
                        w.setValue(float(resolved))
                    except Exception:
                        pass
            btn.setStyleSheet("color: #c00; font-weight: bold;" if overridden else "")

    def _path_for_panel(self, base_path: str) -> str:
        if self._current_panel_id:
            return f"panel.{self._current_panel_id}.{base_path}"
        return base_path

    def _on_geom(self, *_):
        if self._suppress or not self._current_panel_id:
            return
        self.geometry_changed.emit(
            self._current_panel_id,
            self._x.value(), self._y.value(),
            self._w.value(), self._h.value(),
        )

    def _on_style(self, path: str, value):
        if self._suppress:
            return
        full_path = self._path_for_panel(path)
        set_override(self.spec, full_path, value)
        self.style_override_changed.emit(self._current_panel_id or "", full_path, value)
        self._refresh_style_indicators()

    def _reset_style(self, path: str):
        full_path = self._path_for_panel(path)
        clear_override(self.spec, full_path)
        self.style_override_cleared.emit(self._current_panel_id or "", full_path)
        self._refresh_style_indicators()

    def _reset_all(self):
        if not self._current_panel_id:
            return
        p = self.spec.find_panel(self._current_panel_id)
        if p is not None:
            for k in list(p.style_overrides.keys()):
                clear_override(self.spec, k)
        self.style_override_cleared_all.emit(self._current_panel_id)
        self._refresh_style_indicators()