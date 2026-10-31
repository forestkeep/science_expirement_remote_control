"""Состояние «Figure» — ничего не выделено.

Секции: Фигура, Палитра, Пресет, Стиль по умолчанию, Панели.
"""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFontComboBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)
from ..core.sentinel import MISSING
from ..presets.builtin import get_palette, list_style_profiles
from ..model.stylestack import set_override, clear_override


class FigureInspector(QWidget):
    figure_size_changed    = pyqtSignal(float, float)
    figure_overrides_changed = pyqtSignal()
    panel_list_clicked     = pyqtSignal(str)
    layout_requested       = pyqtSignal()

    def __init__(self, spec, preset, style_stack, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.preset = preset
        self.style_stack = style_stack
        self._suppress = False
        self._build_ui()


    def set_spec(self, spec) -> None:
        """Обновить спецификацию без пересоздания виджета.

        Вызывается из PublicationWidget.load_from_file(). Если стек стилей
        ещё не готов — обновляем только размеры/панели, чтобы не падать.
        """
        self.spec = spec
        if spec is None:
            return
        if self.style_stack is not None and self.preset is not None:
            self.update_from_spec(spec, self.preset, self.style_stack)
            return
        self._suppress = True
        try:
            self.width_spin.setValue(float(spec.width_mm))
            self.height_spin.setValue(float(spec.height_mm))
            self.preset_label.setText("—")
            self.constraints_label.setText("—")
            self._rebuild_panels()
        finally:
            self._suppress = False

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setSpacing(8)

        # --- Фигура ---
        fig_box = QGroupBox("Фигура")
        fig_form = QFormLayout(fig_box)
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(10.0, 500.0)
        self.width_spin.setDecimals(1)
        self.width_spin.setSuffix(" мм")
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(10.0, 500.0)
        self.height_spin.setDecimals(1)
        self.height_spin.setSuffix(" мм")
        size_row = QWidget()
        size_lay = QHBoxLayout(size_row)
        size_lay.setContentsMargins(0, 0, 0, 0)
        size_lay.addWidget(QLabel("Размер:"))
        size_lay.addWidget(self.width_spin)
        size_lay.addWidget(QLabel("×"))
        size_lay.addWidget(self.height_spin)
        size_lay.addStretch()
        size_lay.addWidget(QLabel("📌"))
        fig_form.addRow(size_row)

        self.font_family = QFontComboBox()
        self.font_size = QDoubleSpinBox()
        self.font_size.setRange(2.0, 48.0)
        self.font_size.setDecimals(1)
        self.font_size.setSuffix(" pt")
        font_row = QWidget()
        font_lay = QHBoxLayout(font_row)
        font_lay.setContentsMargins(0, 0, 0, 0)
        font_lay.addWidget(self.font_family, 1)
        font_lay.addWidget(self.font_size)
        font_lay.addWidget(QLabel("📌"))
        fig_form.addRow("Шрифт:", font_row)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)
        self.dpi_spin.setSuffix(" dpi")
        dpi_row = QWidget()
        dpi_lay = QHBoxLayout(dpi_row)
        dpi_lay.setContentsMargins(0, 0, 0, 0)
        dpi_lay.addWidget(self.dpi_spin)
        dpi_lay.addStretch()
        dpi_lay.addWidget(QLabel("📌"))
        fig_form.addRow("DPI:", dpi_row)
        body_layout.addWidget(fig_box)

        # --- Палитра ---
        pal_box = QGroupBox("Палитра")
        pal_lay = QVBoxLayout(pal_box)
        self.palette_combo = QComboBox()
        for pid in list_style_profiles():
            self.palette_combo.addItem(pid, pid)
        pal_lay.addWidget(self.palette_combo)
        self.swatches_label = QLabel()
        pal_lay.addWidget(self.swatches_label)
        body_layout.addWidget(pal_box)

        # --- Пресет ---
        preset_box = QGroupBox("Пресет")
        preset_form = QFormLayout(preset_box)
        self.preset_label = QLabel()
        self.preset_label.setStyleSheet("color: #888;")
        preset_form.addRow("Журнал:", self.preset_label)
        self.constraints_label = QLabel()
        self.constraints_label.setStyleSheet("font-family: monospace; color: #666;")
        self.constraints_label.setWordWrap(True)
        preset_form.addRow("Ограничения:", self.constraints_label)
        body_layout.addWidget(preset_box)

        # --- Стиль по умолчанию ---
        def_box = QGroupBox("Стиль по умолчанию")
        def_form = QFormLayout(def_box)
        self.line_width = QDoubleSpinBox()
        self.line_width.setRange(0.1, 20.0)
        self.line_width.setDecimals(2)
        self.line_width.setSuffix(" pt")
        def_form.addRow("Толщина линии:", self.line_width)
        self.axes_width = QDoubleSpinBox()
        self.axes_width.setRange(0.1, 10.0)
        self.axes_width.setDecimals(2)
        self.axes_width.setSuffix(" pt")
        def_form.addRow("Толщина осей:", self.axes_width)
        self.tick_size = QDoubleSpinBox()
        self.tick_size.setRange(2.0, 30.0)
        self.tick_size.setSuffix(" pt")
        def_form.addRow("Размер тиков:", self.tick_size)
        self.label_size = QDoubleSpinBox()
        self.label_size.setRange(2.0, 30.0)
        self.label_size.setSuffix(" pt")
        def_form.addRow("Размер подписей:", self.label_size)
        body_layout.addWidget(def_box)

        # --- Панели ---
        self.panels_box = QGroupBox("Панели")
        self.panels_lay = QVBoxLayout(self.panels_box)
        body_layout.addWidget(self.panels_box)
        self.layout_btn = QPushButton("Разложить по шаблону…")
        self.layout_btn.clicked.connect(self.layout_requested.emit)
        body_layout.addWidget(self.layout_btn)
        body_layout.addStretch()

        scroll.setWidget(body)
        outer.addWidget(scroll)

        self.width_spin.valueChanged.connect(self._on_size)
        self.height_spin.valueChanged.connect(self._on_size)
        self.font_family.currentFontChanged.connect(self._on_font)
        self.font_size.valueChanged.connect(self._on_font)
        self.dpi_spin.valueChanged.connect(self._on_dpi)
        self.line_width.valueChanged.connect(lambda v: self._set_default("figure.line.width", float(v)))
        self.axes_width.valueChanged.connect(lambda v: self._set_default("figure.axes.line_width", float(v)))
        self.tick_size.valueChanged.connect(lambda v: self._set_default("figure.axes.tick_size", float(v)))
        self.label_size.valueChanged.connect(lambda v: self._set_default("figure.axes.label_size", float(v)))
        self.palette_combo.currentIndexChanged.connect(self._on_palette)

    # ------------------------------------------------------------------
    def update_from_spec(self, spec, preset, style_stack) -> None:
        self.spec = spec
        self.preset = preset
        self.style_stack = style_stack
        self._suppress = True
        try:
            self.width_spin.setValue(float(spec.width_mm))
            self.height_spin.setValue(float(spec.height_mm))
            for path, widget in (
                ("figure.font.size", self.font_size),
                ("figure.line.width", self.line_width),
                ("figure.axes.line_width", self.axes_width),
                ("figure.axes.tick_size", self.tick_size),
                ("figure.axes.label_size", self.label_size),
            ):
                v = self.style_stack.resolve(path)
                if v is not MISSING and hasattr(widget, "setValue"):
                    try:
                        widget.setValue(float(v))
                    except (TypeError, ValueError):
                        pass
            family = self.style_stack.resolve("figure.font.family")
            if family is not MISSING and family:
                from PyQt5.QtGui import QFont
                self.font_family.setCurrentFont(QFont(str(family)))
            dpi = self.style_stack.resolve("figure.dpi")
            if dpi is not MISSING:
                try:
                    self.dpi_spin.setValue(int(dpi))
                except (TypeError, ValueError):
                    pass
            palette_id = self.style_stack.resolve("color.palette")
            if palette_id is not MISSING and palette_id:
                idx = self.palette_combo.findData(str(palette_id))
                if idx >= 0:
                    self.palette_combo.setCurrentIndex(idx)
            self.preset_label.setText(preset.name if preset else "—")
            self._render_constraints(preset)
            self._render_swatches()
            self._rebuild_panels()
        finally:
            self._suppress = False

    def _render_constraints(self, preset):
        c = getattr(preset, "constraints", {}) or {}
        lines = []
        if "min_font_pt" in c:
            lines.append(f"min шрифт: {c['min_font_pt']} pt")
        if "min_line_pt" in c:
            lines.append(f"min линия: {c['min_line_pt']} pt")
        if "dpi_min" in c:
            lines.append(f"DPI ≥ {c['dpi_min']}")
        if "margin_mm" in c:
            lines.append(f"margin: {c['margin_mm']} мм")
        if "colorblind_safe" in c:
            lines.append(f"colorblind-safe: {'✓' if c['colorblind_safe'] else '☐'}")
        self.constraints_label.setText("\n".join(lines) or "—")

    def _render_swatches(self):
        pid = self.palette_combo.currentData() or "okabe_ito"
        colors = get_palette(pid)
        html = "".join(
            f'<span style="display:inline-block;width:18px;height:18px;'
            f'background:{c};border:1px solid #333;margin-right:4px;"></span>'
            for c in colors
        )
        self.swatches_label.setText(html)

    def _rebuild_panels(self):
        while self.panels_lay.count():
            item = self.panels_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if self.spec is None:
            return
        for panel in self.spec.sorted_panels():
            label = panel.title or "(без имени)"
            marker = "● " if panel.style_overrides else ""
            btn = QPushButton(
                f"{marker}[{self._auto_label(panel.id)}]  {label}  "
                f"{panel.w_mm:.0f}×{panel.h_mm:.0f}"
            )
            btn.setStyleSheet("text-align: left; padding: 4px;")
            btn.clicked.connect(
                lambda _c=False, pid=panel.id: self.panel_list_clicked.emit(pid))
            self.panels_lay.addWidget(btn)

    def _auto_label(self, panel_id: str) -> str:
        """a, b, c, …, z, aa, ab, … по позиции в спеке."""
        if self.spec is None:
            return "a"
        letters = "abcdefghijklmnopqrstuvwxyz"
        for i, p in enumerate(self.spec.sorted_panels()):
            if p.id == panel_id:
                if i < len(letters):
                    return letters[i]
                return f"a{i}"
        return "a"

    # ------------------------------------------------------------------
    def _on_size(self, *_):
        if self._suppress:
            return
        self.figure_size_changed.emit(
            float(self.width_spin.value()), float(self.height_spin.value())
        )

    def _on_font(self, *_):
        if self._suppress:
            return
        family = self.font_family.currentFont().family()
        size = float(self.font_size.value())
        set_override(self.spec, "figure.font.family", family)
        set_override(self.spec, "figure.font.size", size)
        self.figure_overrides_changed.emit()

    def _on_dpi(self, value):
        if self._suppress:
            return
        set_override(self.spec, "figure.dpi", int(value))
        self.figure_overrides_changed.emit()

    def _on_palette(self, _idx):
        if self._suppress:
            return
        pid = self.palette_combo.currentData()
        set_override(self.spec, "color.palette", str(pid))
        self._render_swatches()
        self.figure_overrides_changed.emit()

    def _set_default(self, path: str, value):
        if self._suppress:
            return
        set_override(self.spec, path, value)
        self.figure_overrides_changed.emit()