
"""Состояние «Annotation» — выделена аннотация.

Содержит:
  * AnnotationInspector  — инспектор выделенной аннотации;
  * AnnotationPropertiesDialog — модальный диалог свойств;
  * create_annotation(spec, kind, panel_id) — фабрика с дефолтными координатами.
"""
from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QSpinBox, QVBoxLayout, QWidget,
)

from common.color_picker import pick_color


_KIND_TITLES = {
    "text":        "текст",
    "arrow":       "стрелка",
    "scale_bar":   "scale bar",
    "bracket":     "скобка",
    "panel_label": "метка панели",
}


def create_annotation(spec, kind: str, panel_id: str = None) -> object:
    """Создать PresentationAnnotation с дефолтными координатами.

    Для arrow/bracket — 4 координаты (start, end); для остальных — (x, y).
    Для panel_label текст автоматически = авто-метка панели.
    """
    if spec is None:
        raise ValueError("create_annotation: spec is None")

    is_pair = kind in ("arrow", "bracket")
    is_scale = kind == "scale_bar"
    coord_space = "panel_mm" if panel_id else "figure_mm"

    panel = spec.find_panel(panel_id) if panel_id else None
    if panel is not None:
        cx, cy = panel.w_mm / 2.0, panel.h_mm / 2.0
        if is_pair:
            coords = (max(1.0, cx - 5), max(1.0, cy - 5),
                      min(panel.w_mm - 1, cx + 5), min(panel.h_mm - 1, cy + 5))
        elif is_scale:
            coords = (max(1.0, cx - 5), min(panel.h_mm - 3, cy + 5))
        else:
            coords = (cx, cy)
    else:
        if is_pair:
            coords = (10.0, 10.0, 30.0, 20.0)
        else:
            coords = (10.0, 10.0)

    if kind == "text":
        text = "T = 300 K"
    elif kind == "scale_bar":
        text = "10 µm"
    elif kind == "panel_label":
        text = "a"  # TODO: авто-нумерация по индексу панели в спеке
    else:
        text = ""

    style = {"size": 8.0, "color": "#000000"}
    if kind == "scale_bar":
        style["width_mm"] = 5.0
        style["thickness_pt"] = 0.6
    elif kind == "bracket":
        style["thickness_pt"] = 0.6

    return spec.add_presentation(
        kind=kind,
        coordinate_space=coord_space,
        panel_id=panel_id,
        coords=coords,
        text=text,
        **style,
    )


class AnnotationPropertiesDialog(QDialog):
    """Модальный диалог свойств аннотации — поля по типу."""

    def __init__(self, ann, parent=None):
        super().__init__(parent)
        self.ann = ann
        self.setWindowTitle(f"Свойства: {_KIND_TITLES.get(ann.kind, ann.kind)}")
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Содержимое (для всех типов, кроме panel_label — тоже полезно)
        self.text_edit = QLineEdit(self.ann.text or "")
        form.addRow("Содержимое:", self.text_edit)

        # Цвет
        self.color_btn = QPushButton()
        self._set_color(self.ann.style.get("color", "#000000"))
        self.color_btn.clicked.connect(self._choose_color)
        form.addRow("Цвет:", self.color_btn)

        # Размер шрифта
        self.size_spin = QSpinBox()
        self.size_spin.setRange(2, 72)
        self.size_spin.setValue(int(self.ann.style.get("size", 8)))
        form.addRow("Размер, pt:", self.size_spin)

        # Координаты (в мм, зависят от coordinate_space)
        coords = list(self.ann.coords) + [0.0] * 4
        self.x_spin = self._coord(coords[0])
        self.y_spin = self._coord(coords[1])
        self.x2_spin = self._coord(coords[2])
        self.y2_spin = self._coord(coords[3])

        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("x:"))
        pos_row.addWidget(self.x_spin)
        pos_row.addWidget(QLabel("y:"))
        pos_row.addWidget(self.y_spin)
        if self.ann.kind in ("arrow", "bracket"):
            pos_row.addWidget(QLabel("x2:"))
            pos_row.addWidget(self.x2_spin)
            pos_row.addWidget(QLabel("y2:"))
            pos_row.addWidget(self.y2_spin)
        form.addRow("Координаты, мм:", pos_row)

        if self.ann.kind == "scale_bar":
            self.len_spin = self._coord(self.ann.style.get("width_mm", 5.0))
            self.len_spin.setRange(0.1, 1000.0)
            self.len_spin.setSuffix(" мм")
            self.thick_spin = self._coord(self.ann.style.get("thickness_pt", 0.6))
            self.thick_spin.setRange(0.1, 20.0)
            self.thick_spin.setSuffix(" pt")
            form.addRow("Длина:", self.len_spin)
            form.addRow("Толщина:", self.thick_spin)
        elif self.ann.kind == "bracket":
            self.thick_spin = self._coord(self.ann.style.get("thickness_pt", 0.6))
            self.thick_spin.setRange(0.1, 20.0)
            self.thick_spin.setSuffix(" pt")
            form.addRow("Толщина:", self.thick_spin)

        layout.addLayout(form)
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def _coord(self, value):
        s = QDoubleSpinBox()
        s.setRange(-1000.0, 1000.0)
        s.setDecimals(1)
        s.setValue(float(value))
        return s

    def _set_color(self, color: str):
        self.color_btn.setText(color)
        self.color_btn.setStyleSheet(f"background-color: {color};")

    def _choose_color(self):
        current = self.color_btn.text() or "#000000"
        def on_selected(c: QColor) -> None:
            self._set_color(c.name())
        pick_color(self.color_btn, current, on_selected, self)

    def apply(self):
        self.ann.text = self.text_edit.text()
        self.ann.style["color"] = self.color_btn.text()
        self.ann.style["size"] = int(self.size_spin.value())

        coords = [float(self.x_spin.value()), float(self.y_spin.value())]
        if self.ann.kind in ("arrow", "bracket"):
            coords += [float(self.x2_spin.value()), float(self.y2_spin.value())]
        self.ann.coords = tuple(coords)

        if self.ann.kind == "scale_bar":
            self.ann.style["width_mm"] = float(self.len_spin.value())
            self.ann.style["thickness_pt"] = float(self.thick_spin.value())
        elif self.ann.kind == "bracket":
            self.ann.style["thickness_pt"] = float(self.thick_spin.value())


class AnnotationInspector(QWidget):
    """Инспектор выделенной аннотации."""

    changed          = pyqtSignal()
    delete_requested = pyqtSignal(str)
    edit_requested   = pyqtSignal(str)

    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self._ann_id = ""
        self._suppress = False
        self._build_ui()

    # ----------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        lay = QVBoxLayout(body)

        header = QHBoxLayout()
        self.title_label = QLabel("Аннотация:")
        self.title_label.setStyleSheet("font-weight: bold;")
        header.addWidget(self.title_label)
        self.reset_btn = QPushButton("↺")
        self.reset_btn.setToolTip("Сбросить стиль к дефолту")
        self.reset_btn.clicked.connect(self._on_reset)
        header.addWidget(self.reset_btn)
        header.addStretch()
        lay.addLayout(header)

        self.kind_label = QLabel()
        self.kind_label.setStyleSheet("color: #888;")
        lay.addWidget(self.kind_label)

        info_box = QGroupBox("Содержимое")
        info_form = QFormLayout(info_box)
        self.text_edit = QLineEdit()
        self.text_edit.editingFinished.connect(self._on_text_changed)
        info_form.addRow("Содержимое:", self.text_edit)

        self.color_btn = QPushButton()
        self.color_btn.clicked.connect(self._choose_color)
        info_form.addRow("Цвет:", self.color_btn)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(2, 72)
        self.size_spin.valueChanged.connect(self._on_size_changed)
        info_form.addRow("Размер, pt:", self.size_spin)

        self.edit_btn = QPushButton("Свойства…")
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._ann_id))
        info_form.addRow(self.edit_btn)
        lay.addWidget(info_box)

        self.delete_btn = QPushButton("Удалить аннотацию")
        self.delete_btn.clicked.connect(
            lambda: self.delete_requested.emit(self._ann_id))
        lay.addWidget(self.delete_btn)

        lay.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)

    # ----------------------------------------------------------------
    def set_spec(self, spec):
        self.spec = spec

    def set_annotation(self, ann_id: str):
        self._ann_id = ann_id or ""
        if not ann_id:
            self.title_label.setText("Аннотация:")
            self.kind_label.clear()
            self.text_edit.clear()
            return
        ann = self.spec.find_presentation(ann_id) if self.spec is not None else None
        if ann is None:
            return
        self._suppress = True
        try:
            title = _KIND_TITLES.get(ann.kind, ann.kind)
            self.title_label.setText(f"Аннотация: {title}")
            self.kind_label.setText(f"Тип: {title}")
            self.text_edit.setText(ann.text or "")
            self._set_color_btn(ann.style.get("color", "#000000"))
            self.size_spin.setValue(int(ann.style.get("size", 8)))
        finally:
            self._suppress = False

    def _set_color_btn(self, color: str):
        self.color_btn.setText(color)
        self.color_btn.setStyleSheet(f"background-color: {color};")

    def _on_text_changed(self):
        if self._suppress or not self._ann_id:
            return
        ann = self.spec.find_presentation(self._ann_id)
        if ann is not None:
            ann.text = self.text_edit.text()
            self.changed.emit()

    def _on_size_changed(self, v):
        if self._suppress or not self._ann_id:
            return
        ann = self.spec.find_presentation(self._ann_id)
        if ann is not None:
            ann.style["size"] = int(v)
            self.changed.emit()

    def _choose_color(self):
        if not self._ann_id:
            return
        from PyQt5.QtGui import QColor as _QC
        from common.color_picker import pick_color as _pc
        current = self.color_btn.text() or "#000000"
        def on_selected(c: _QC) -> None:
            self._set_color_btn(c.name())
            ann = self.spec.find_presentation(self._ann_id)
            if ann is not None:
                ann.style["color"] = c.name()
                self.changed.emit()
        _pc(self.color_btn, current, on_selected, self)

    def _on_reset(self):
        if not self._ann_id:
            return
        ann = self.spec.find_presentation(self._ann_id)
        if ann is None:
            return
        ann.style = {"size": 8.0, "color": "#000000"}
        self.set_annotation(self._ann_id)
        self.changed.emit()


__all__ = [
    "AnnotationInspector",
    "AnnotationPropertiesDialog",
    "create_annotation",
]