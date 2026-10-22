"""Минимальный редактор пресетов. Пользователь НЕ редактирует JSON напрямую."""
from __future__ import annotations
from typing import Any

from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QVBoxLayout, QPushButton,
    QDoubleSpinBox, QDialogButtonBox, QComboBox, QInputDialog,
)


class PresetEditorDialog(QDialog):
    def __init__(self, preset, parent=None):
        super().__init__(parent)
        self.preset = preset
        self.setWindowTitle(f"Пресет: {preset.id}")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name = QLineEdit(self.preset.name)
        form.addRow("Название", self._name)

        self._width = QDoubleSpinBox()
        self._width.setRange(1.0, 500.0)
        self._width.setValue(float(self.preset.column.get("width_mm", 183.0)))
        self._width.setSuffix(" мм")
        form.addRow("Ширина колонки", self._width)

        self._height = QDoubleSpinBox()
        self._height.setRange(1.0, 500.0)
        self._height.setValue(float(self.preset.column.get("height_mm", 247.0)))
        self._height.setSuffix(" мм")
        form.addRow("Макс. высота", self._height)

        self._dpi = QDoubleSpinBox()
        self._dpi.setRange(72.0, 1200.0)
        self._dpi.setDecimals(0)
        self._dpi.setValue(float(self.preset.column.get("dpi", 300)))
        form.addRow("DPI", self._dpi)

        self._min_font = QDoubleSpinBox()
        self._min_font.setRange(0.0, 100.0)
        self._min_font.setValue(float(self.preset.constraints.get("min_font_pt", 5.0)))
        form.addRow("Мин. шрифт (pt)", self._min_font)

        self._min_line = QDoubleSpinBox()
        self._min_line.setRange(0.0, 10.0)
        self._min_line.setDecimals(3)
        self._min_line.setValue(float(self.preset.constraints.get("min_line_pt", 0.25)))
        form.addRow("Мин. толщина (pt)", self._min_line)

        self._margin = QDoubleSpinBox()
        self._margin.setRange(0.0, 100.0)
        self._margin.setValue(float(self.preset.constraints.get("margin_mm", 3.0)))
        form.addRow("Поле (мм)", self._margin)

        self._colorblind = QComboBox()
        self._colorblind.addItems(["false", "true"])
        self._colorblind.setCurrentText(
            "true" if self.preset.constraints.get("colorblind_safe") else "false"
        )
        form.addRow("Colorblind-safe", self._colorblind)

        layout.addLayout(form)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def apply_to_preset(self):
        self.preset.name = self._name.text()
        self.preset.column["width_mm"] = float(self._width.value())
        self.preset.column["height_mm"] = float(self._height.value())
        self.preset.column["dpi"] = int(self._dpi.value())
        self.preset.constraints["min_font_pt"] = float(self._min_font.value())
        self.preset.constraints["min_line_pt"] = float(self._min_line.value())
        self.preset.constraints["margin_mm"] = float(self._margin.value())
        self.preset.constraints["colorblind_safe"] = (
            self._colorblind.currentText() == "true"
        )