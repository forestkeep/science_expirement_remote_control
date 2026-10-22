"""Инспектор: геометрия в мм + стиль с индикатором «переопределено»."""
from __future__ import annotations
import logging
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from ..core.sentinel import MISSING
from ..model.stylestack import set_override, clear_override

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
    style_override_changed = pyqtSignal(str, str, object)   # panel_id(может быть ""), path, value
    style_override_cleared = pyqtSignal(str, str)
    style_override_cleared_all = pyqtSignal(str)

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

        # --- геометрия ---
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

        # --- стиль ---
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

    # ------------------------------------------------------------- helpers
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
        self._refresh_style_indicators()

    def _refresh_style_indicators(self) -> None:
        stack = self._stack_getter()
        if stack is None:
            return
        panel_id = self._current_panel_id or ""
        for path, (w, btn) in self._widgets.items():
            full_path = self._path_for_panel(path)
            resolved = stack.resolve(full_path)
            # пресет-значение
            default = stack.resolve(path) if not full_path.startswith("panel.") else stack.resolve(path)
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
        """Все per-panel overrides храним как 'panel.<id>.<key>'."""
        if self._current_panel_id:
            return f"panel.{self._current_panel_id}.{base_path}"
        return base_path

    # ------------------------------------------------------------- callbacks
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