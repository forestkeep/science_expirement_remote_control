"""Состояние «Panel» — выделена панель.

Секции: Оси, Кривые, Легенда, Аннотации, Геометрия (свёрнута).
"""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QToolButton,
    QVBoxLayout, QWidget,
)

from ..model.panel import PanelSpec, CurveSlot


class CurveSlotRow(QWidget):
    """Один горизонтальный ряд слота в секции «Кривые»."""

    color_clicked   = pyqtSignal(int)
    style_clicked   = pyqtSignal(int)
    width_changed   = pyqtSignal(int, float)
    legend_changed  = pyqtSignal(int, str)
    axis_changed    = pyqtSignal(int, str)
    pinned_toggled  = pyqtSignal(int, bool)
    reset_clicked   = pyqtSignal(int)
    delete_clicked  = pyqtSignal(int)

    def __init__(self, index: int, slot: CurveSlot, parent=None):
        super().__init__(parent)
        self.index = index
        self.slot = slot
        self._build_ui()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(3)
        self.setFixedHeight(28)

        # цвет
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(16, 16)
        color = "#1f77b4"
        if self.slot.style_overrides.get("line.color"):
            color = self.slot.style_overrides["line.color"]
        self.color_btn.setStyleSheet(f"background-color: {color};")
        self.color_btn.clicked.connect(lambda: self.color_clicked.emit(self.index))
        lay.addWidget(self.color_btn)

        # стиль
        self.style_btn = QPushButton("—")
        self.style_btn.setFixedSize(28, 22)
        self.style_btn.clicked.connect(lambda: self.style_clicked.emit(self.index))
        lay.addWidget(self.style_btn)

        # толщина
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.1, 10.0)
        self.width_spin.setSingleStep(0.25)
        self.width_spin.setDecimals(2)
        self.width_spin.setFixedWidth(60)
        try:
            self.width_spin.setValue(float(self.slot.style_overrides.get("line.width", 1.0)))
        except Exception:
            pass
        self.width_spin.valueChanged.connect(
            lambda v, i=self.index: self.width_changed.emit(i, float(v))
        )
        lay.addWidget(self.width_spin)

        # легенда
        self.legend_edit = QLineEdit(self.slot.legend_label or "")
        self.legend_edit.setPlaceholderText("auto")
        self.legend_edit.editingFinished.connect(
            lambda i=self.index, e=self.legend_edit: self.legend_changed.emit(i, e.text())
        )
        lay.addWidget(self.legend_edit, 1)

        # ось
        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["Y1", "Y2"])
        self.axis_combo.setCurrentText("Y2" if self.slot.axis == "y2" else "Y1")
        self.axis_combo.currentIndexChanged.connect(
            lambda _i, i=self.index, cb=self.axis_combo:
                self.axis_changed.emit(i, cb.currentText().lower())
        )
        lay.addWidget(self.axis_combo)

        # кнопки
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(22, 22)
        self.pin_btn.setCheckable(True)
        self.pin_btn.toggled.connect(
            lambda st, i=self.index: self.pinned_toggled.emit(i, bool(st))
        )
        lay.addWidget(self.pin_btn)

        self.reset_btn = QPushButton("↺")
        self.reset_btn.setFixedSize(22, 22)
        self.reset_btn.clicked.connect(lambda: self.reset_clicked.emit(self.index))
        lay.addWidget(self.reset_btn)

        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedSize(22, 22)
        self.del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.index))
        lay.addWidget(self.del_btn)


class PanelInspector(QWidget):
    panel_label_changed     = pyqtSignal(str, str)
    panel_reset_all         = pyqtSignal(str)
    panel_pinned_toggled    = pyqtSignal(str, bool)
    panel_geometry_changed  = pyqtSignal(str, float, float, float, float)
    panel_axis_visibility   = pyqtSignal(str, str, bool)
    panel_axis_linked       = pyqtSignal(str, str, str)
    panel_axis_label        = pyqtSignal(str, str, str)
    panel_axis_range        = pyqtSignal(str, str, object, object)
    panel_axis_auto         = pyqtSignal(str, str, bool)
    panel_axis_log          = pyqtSignal(str, str, bool)
    panel_y2_toggled        = pyqtSignal(str, bool)
    slot_add_requested      = pyqtSignal(str)
    slot_color_clicked      = pyqtSignal(int)
    slot_style_clicked      = pyqtSignal(int)
    slot_width_changed      = pyqtSignal(int, float)
    slot_legend_changed     = pyqtSignal(int, str)
    slot_axis_changed       = pyqtSignal(int, str)
    slot_pinned_toggled     = pyqtSignal(int, bool)
    slot_reset_clicked      = pyqtSignal(int)
    slot_deleted            = pyqtSignal(int)
    legend_mode_changed     = pyqtSignal(str)
    legend_position_changed = pyqtSignal(str)
    legend_visible_changed  = pyqtSignal(bool)
    legend_pinned_toggled   = pyqtSignal(bool)
    annotation_create       = pyqtSignal(str)
    annotation_edit         = pyqtSignal(str)
    annotation_delete       = pyqtSignal(str)
    curves_added = pyqtSignal(str, list)  # panel_id, list of DataRef

    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.panel_id = ""
        self._suppress = False
        self._build_ui()

    # ----------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        self.body_lay = QVBoxLayout(body)
        self.body_lay.setSpacing(8)

        # шапка
        header = QHBoxLayout()
        header.addWidget(QLabel("Панель:"))
        self.label_edit = QLineEdit()
        self.label_edit.setFixedWidth(40)
        self.label_edit.editingFinished.connect(self._on_label)
        header.addWidget(self.label_edit)
        self.reset_all_btn = QPushButton("↺")
        self.reset_all_btn.setToolTip("Сбросить все panel_overrides")
        self.reset_all_btn.clicked.connect(lambda: self.panel_reset_all.emit(self.panel_id))
        header.addWidget(self.reset_all_btn)
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setToolTip("Закрепить все текущие overrides")
        self.pin_btn.toggled.connect(lambda st: self.panel_pinned_toggled.emit(self.panel_id, bool(st)))
        header.addWidget(self.pin_btn)
        header.addStretch()
        self.body_lay.addLayout(header)

        # --- Оси ---
        axes_box = QGroupBox("Оси")
        axes_lay = QVBoxLayout(axes_box)
        self.axis_widgets = {}
        for key, title in (("x", "X"), ("y1", "Y1"), ("y2", "Y2")):
            axes_lay.addWidget(self._build_axis_row(key, title))
        self.body_lay.addWidget(axes_box)

        # --- Кривые ---
        curves_box = QGroupBox("Кривые")
        self.curves_lay = QVBoxLayout(curves_box)
        self.body_lay.addWidget(curves_box)

        add_row = QHBoxLayout()
        self.add_slot_btn = QPushButton("+ из сессии ▾")
        self.add_slot_btn.clicked.connect(self._toggle_add_panel)
        add_row.addWidget(self.add_slot_btn)
        add_row.addStretch()
        self.curves_lay.addLayout(add_row)

        # Inline-панель (скрыта по умолчанию)
        self.add_panel_container = QWidget()
        self.add_panel_layout = QVBoxLayout(self.add_panel_container)
        self.add_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.curves_lay.addWidget(self.add_panel_container)
        self.add_panel_container.hide()

        # --- Легенда ---
        legend_box = QGroupBox("Легенда")
        legend_lay = QVBoxLayout(legend_box)
        mode_row = QHBoxLayout()
        self.legend_panel_radio = QPushButton("◉ в панели")
        self.legend_panel_radio.setCheckable(True)
        self.legend_fig_radio = QPushButton("○ общая фигуры")
        self.legend_fig_radio.setCheckable(True)
        self.legend_inline_radio = QPushButton("○ у кривых")
        self.legend_inline_radio.setCheckable(True)
        for b in (self.legend_panel_radio, self.legend_fig_radio, self.legend_inline_radio):
            b.setFixedHeight(22)
            mode_row.addWidget(b)
        mode_row.addStretch()
        legend_lay.addLayout(mode_row)
        self.legend_panel_radio.clicked.connect(lambda: self.legend_mode_changed.emit("panel"))
        self.legend_fig_radio.clicked.connect(lambda: self.legend_mode_changed.emit("figure"))
        self.legend_inline_radio.clicked.connect(lambda: self.legend_mode_changed.emit("inline"))
        self.legend_visible_check = QCheckBox("показывать")
        self.legend_visible_check.stateChanged.connect(
            lambda st: self.legend_visible_changed.emit(st != 0))
        legend_lay.addWidget(self.legend_visible_check)
        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("позиция:"))
        self.legend_pos_combo = QComboBox()
        for text, val in (("best", "best"), ("верх-лево", "upper left"),
                          ("верх-право", "upper right"), ("низ-лево", "lower left"),
                          ("низ-право", "lower right"), ("снаружи-право", "outside right")):
            self.legend_pos_combo.addItem(text, val)
        self.legend_pos_combo.currentIndexChanged.connect(
            lambda _i: self.legend_position_changed.emit(self.legend_pos_combo.currentData() or "best")
        )
        pos_row.addWidget(self.legend_pos_combo, 1)
        self.legend_pin_btn = QPushButton("📌")
        self.legend_pin_btn.setCheckable(True)
        self.legend_pin_btn.toggled.connect(self.legend_pinned_toggled.emit)
        pos_row.addWidget(self.legend_pin_btn)
        legend_lay.addLayout(pos_row)
        self.body_lay.addWidget(legend_box)

        # --- Аннотации ---
        ann_box = QGroupBox("Аннотации")
        self.ann_lay = QVBoxLayout(ann_box)
        btn_row = QHBoxLayout()
        for kind, label in (("text", "+ Текст"), ("arrow", "+ Стрелка"), ("scale_bar", "+ Scale bar")):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _c=False, k=kind: self.annotation_create.emit(k))
            btn_row.addWidget(btn)
        self.ann_lay.addLayout(btn_row)
        self.body_lay.addWidget(ann_box)

        # --- Геометрия (свёрнута) ---
        self.geom_box = QGroupBox("Геометрия")
        self.geom_box.setCheckable(True)
        self.geom_box.setChecked(False)
        geom_lay = QHBoxLayout(self.geom_box)
        self.x_spin = self._coord_spin()
        self.y_spin = self._coord_spin()
        self.w_spin = self._coord_spin()
        self.h_spin = self._coord_spin()
        for lbl, sp in (("x", self.x_spin), ("y", self.y_spin),
                        ("w", self.w_spin), ("h", self.h_spin)):
            geom_lay.addWidget(QLabel(lbl))
            geom_lay.addWidget(sp)
        reset_geom = QPushButton("↺ на панель")
        reset_geom.clicked.connect(self._reset_geom)
        geom_lay.addWidget(reset_geom)
        for sp in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
            sp.valueChanged.connect(self._on_geom)
        self.body_lay.addWidget(self.geom_box)

        self.body_lay.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)

    def _toggle_add_panel(self):
        if not hasattr(self, 'session_controller') or self.session_controller is None:
            return
        if self.add_panel_container.isVisible():
            self.add_panel_container.hide()
            return

        # Очистить старый контент
        while self.add_panel_layout.count():
            item = self.add_panel_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        panel = AddCurveInlinePanel(self.panel_id, self.session_controller, self)
        panel.curves_added.connect(self._on_curves_added)
        self.add_panel_layout.addWidget(panel)
        self.add_panel_container.show()
        panel.show()

    def _on_curves_added(self, panel_id, refs):
        self.curves_added.emit(panel_id, refs)
        self.add_panel_container.hide()

    def _coord_spin(self):
        s = QDoubleSpinBox()
        s.setRange(-1000.0, 1000.0)
        s.setDecimals(1)
        s.setSingleStep(0.1)
        s.setSuffix(" мм")
        s.setFixedWidth(70)
        return s

    def _build_axis_row(self, key: str, title: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(2)
        row1 = QHBoxLayout()
        vis = QCheckBox(title)
        vis.setChecked(key != "y2")
        linked = QComboBox()
        linked.addItem("—", "")
        row1.addWidget(vis)
        row1.addWidget(QLabel("связана с:"))
        row1.addWidget(linked, 1)
        lay.addLayout(row1)
        row2 = QHBoxLayout()
        label_edit = QLineEdit()
        label_edit.setPlaceholderText("подпись")
        row2.addWidget(label_edit, 1)
        min_spin = QDoubleSpinBox()
        min_spin.setRange(-1e12, 1e12)
        min_spin.setDecimals(1)
        max_spin = QDoubleSpinBox()
        max_spin.setRange(-1e12, 1e12)
        max_spin.setDecimals(1)
        auto = QCheckBox("auto")
        auto.setChecked(True)
        log = QCheckBox("log")
        row2.addWidget(min_spin)
        row2.addWidget(QLabel("–"))
        row2.addWidget(max_spin)
        row2.addWidget(auto)
        row2.addWidget(log)
        lay.addLayout(row2)

        vis.stateChanged.connect(
            lambda st, k=key: self.panel_axis_visibility.emit(self.panel_id, k, st != 0))
        linked.currentIndexChanged.connect(
            lambda _i, k=key: self._on_axis_linked_changed(k))
        label_edit.editingFinished.connect(
            lambda k=key, e=label_edit: self.panel_axis_label.emit(self.panel_id, k, e.text()))
        min_spin.valueChanged.connect(
            lambda v, k=key: self.panel_axis_range.emit(self.panel_id, k,
                float(v), float(self.axis_widgets[k]["max"].value())))
        max_spin.valueChanged.connect(
            lambda v, k=key: self.panel_axis_range.emit(self.panel_id, k,
                float(self.axis_widgets[k]["min"].value()), float(v)))
        auto.stateChanged.connect(
            lambda st, k=key: self.panel_axis_auto.emit(self.panel_id, k, st != 0))
        log.stateChanged.connect(
            lambda st, k=key: self.panel_axis_log.emit(self.panel_id, k, st != 0))

        self.axis_widgets[key] = {
            "widget": w, "vis": vis, "linked": linked, "label": label_edit,
            "min": min_spin, "max": max_spin, "auto": auto, "log": log,
        }
        return w

    def _on_axis_linked_changed(self, key: str):
        if self._suppress:
            return
        w = self.axis_widgets.get(key)
        if w is None:
            return
        other = w["linked"].currentData() or ""
        self.panel_axis_linked.emit(self.panel_id, key, other)
        panel = self.spec.find_panel(self.panel_id) if self.spec is not None else None
        if panel is not None:
            self._update_axis_enabled_state(panel)

    def _update_axis_enabled_state(self, panel: PanelSpec) -> None:
        for key in ("x", "y1", "y2"):
            w = self.axis_widgets.get(key)
            if w is None:
                continue
            linked = bool(w["linked"].currentData())
            auto = w["auto"].isChecked()
            w["min"].setEnabled(not linked and not auto)
            w["max"].setEnabled(not linked and not auto)
            w["auto"].setEnabled(not linked)
            w["log"].setEnabled(True)
            w["label"].setEnabled(True)
            w["linked"].setEnabled(True)
            if key == "y2":
                enabled = bool(panel.y2_visible)
                w["vis"].setEnabled(True)
                if not enabled:
                    w["linked"].setEnabled(False)
                    w["label"].setEnabled(False)
                    w["min"].setEnabled(False)
                    w["max"].setEnabled(False)
                    w["auto"].setEnabled(False)
                    w["log"].setEnabled(False)

    # ----------------------------------------------------------------
    def set_panel(self, panel_id: str) -> None:
        self.panel_id = panel_id
        panel = self.spec.find_panel(panel_id) if self.spec is not None else None
        if panel is None:
            return
        self._suppress = True
        try:
            self.label_edit.setText(self._panel_label(panel))
            for key in ("x", "y1", "y2"):
                w = self.axis_widgets[key]
                w["vis"].setChecked(True if key != "y2" else panel.y2_visible)
                label_text = {"x": panel.x_label, "y1": panel.y_label, "y2": panel.y2_label}[key]
                w["label"].setText(label_text or "")
                auto_val = True
                if key == "x" and panel.x_range is not None:
                    auto_val = False
                elif key == "y1" and panel.y_range is not None:
                    auto_val = False
                elif key == "y2" and panel.y2_range is not None:
                    auto_val = False
                w["auto"].setChecked(auto_val)
                rng = {"x": panel.x_range, "y1": panel.y_range, "y2": panel.y2_range}[key]
                if rng is not None:
                    try:
                        w["min"].setValue(float(rng[0]))
                        w["max"].setValue(float(rng[1]))
                    except Exception:
                        pass
                log_val = {"x": panel.x_log, "y1": panel.y_log, "y2": panel.y2_log}[key]
                w["log"].setChecked(bool(log_val))
                w["vis"].setEnabled(key != "y2" or panel.y2_visible)
                w["linked"].setEnabled(True)
                w["label"].setEnabled(True)
                w["min"].setEnabled(auto_val)
                w["max"].setEnabled(auto_val)
                w["auto"].setEnabled(True)
                w["log"].setEnabled(True)
            # заполнить combo связей другими панелями
            for key in ("x", "y1", "y2"):
                combo = self.axis_widgets[key]["linked"]
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("—", "")
                for p in self.spec.sorted_panels():
                    if p.id != panel_id:
                        combo.addItem(f"{p.title or p.id}", p.id)
                combo.blockSignals(False)

            linked_value = panel.style_overrides.get(f"axis.{key}.linked", "")
            idx_linked = combo.findData(linked_value)
            if idx_linked >= 0:
                combo.setCurrentIndex(idx_linked)
            self._update_axis_enabled_state(panel)
            # кривые
            self._rebuild_curves(panel)
            # легенда
            mode = panel.style_overrides.get("legend.mode", "panel")
            self.legend_panel_radio.setChecked(mode == "panel")
            self.legend_fig_radio.setChecked(mode == "figure")
            self.legend_inline_radio.setChecked(mode == "inline")
            self.legend_visible_check.setChecked(
                bool(panel.style_overrides.get("legend.enabled", True)))
            pos = panel.style_overrides.get("legend.pos", "best")
            idx = self.legend_pos_combo.findData(pos)
            if idx >= 0:
                self.legend_pos_combo.setCurrentIndex(idx)
            # геометрия
            self.x_spin.setValue(float(panel.x_mm))
            self.y_spin.setValue(float(panel.y_mm))
            self.w_spin.setValue(float(panel.w_mm))
            self.h_spin.setValue(float(panel.h_mm))
            # аннотации
            self._rebuild_annotations(panel)
        finally:
            self._suppress = False

    def _panel_label(self, panel: PanelSpec) -> str:
        if panel is None:
            return "a"
        custom = panel.style_overrides.get("panel.label")
        if custom:
            return str(custom)
        return self._auto_label(panel.id)

    def _auto_label(self, panel_id: str) -> str:
        if self.spec is None:
            return "a"
        letters = "abcdefghijklmnopqrstuvwxyz"
        for i, p in enumerate(self.spec.sorted_panels()):
            if p.id == panel_id:
                return letters[i] if i < len(letters) else f"a{i}"
        return "a"

    def _rebuild_curves(self, panel: PanelSpec):
        # Сохранить контейнер inline-панели и кнопку добавления
        add_panel_container = getattr(self, 'add_panel_container', None)
        add_slot_btn = getattr(self, 'add_slot_btn', None)
        add_row_layout = None
        if self.curves_lay.count() > 0:
            # Найти layout с кнопкой
            for i in range(self.curves_lay.count()):
                item = self.curves_lay.itemAt(i)
                if item and item.layout():
                    # Проверим, есть ли в нём add_slot_btn
                    for j in range(item.layout().count()):
                        w = item.layout().itemAt(j).widget()
                        if w is add_slot_btn:
                            add_row_layout = item.layout()
                            break
                    if add_row_layout:
                        break

        # Удалить все виджеты и layout'ы, кроме сохранённых
        while self.curves_lay.count():
            item = self.curves_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                if w is add_panel_container:
                    continue
                w.deleteLater()
            sub = item.layout()
            if sub is not None:
                if sub is add_row_layout:
                    continue
                while sub.count():
                    sub_item = sub.takeAt(0)
                    sw = sub_item.widget()
                    if sw is not None and sw is not add_slot_btn:
                        sw.deleteLater()

        # Добавить строки слотов
        for idx, slot in enumerate(panel.curves):
            row = CurveSlotRow(idx, slot)
            row.color_clicked.connect(self.slot_color_clicked.emit)
            row.style_clicked.connect(self.slot_style_clicked.emit)
            row.width_changed.connect(self.slot_width_changed.emit)
            row.legend_changed.connect(self.slot_legend_changed.emit)
            row.axis_changed.connect(self.slot_axis_changed.emit)
            row.pinned_toggled.connect(self.slot_pinned_toggled.emit)
            row.reset_clicked.connect(self.slot_reset_clicked.emit)
            row.delete_clicked.connect(self.slot_deleted.emit)
            self.curves_lay.addWidget(row)

        # Восстановить кнопку и контейнер
        if add_row_layout is None:
            add_row_layout = QHBoxLayout()
            add_row_layout.addWidget(add_slot_btn)
            add_row_layout.addStretch()
        self.curves_lay.addLayout(add_row_layout)

        if add_panel_container is not None:
            self.curves_lay.addWidget(add_panel_container)

    def _rebuild_annotations(self, panel: PanelSpec):
        while self.ann_lay.count() > 1:  # оставляем строку с кнопками
            item = self.ann_lay.takeAt(1)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if self.spec is None:
            return
        for ann in self.spec.presentation_annotations:
            if ann.panel_id != panel.id:
                continue
            row = QWidget()
            lay = QHBoxLayout(row)
            lay.setContentsMargins(2, 2, 2, 2)
            color = ann.style.get("color", "#000000") if ann.style else "#000000"
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color};")
            lay.addWidget(dot)
            text = f"{ann.kind}  {(ann.text or '')[:24]}"
            lbl = QLabel(text)
            lay.addWidget(lbl, 1)
            props_btn = QPushButton("свойства")
            props_btn.clicked.connect(lambda _c=False, aid=ann.id: self.annotation_edit.emit(aid))
            lay.addWidget(props_btn)
            del_btn = QPushButton("✕")
            del_btn.setFixedWidth(22)
            del_btn.clicked.connect(lambda _c=False, aid=ann.id: self.annotation_delete.emit(aid))
            lay.addWidget(del_btn)
            self.ann_lay.addWidget(row)

    # ----------------------------------------------------------------
    def _on_label(self):
        if self._suppress or not self.panel_id:
            return
        text = self.label_edit.text().strip()
        self.panel_label_changed.emit(self.panel_id, text)

    def _on_y2_global(self, state):
        if self._suppress:
            return
        enabled = state != 0
        # Синхронизировать чекбокс видимости Y2
        self._suppress = True
        self.axis_widgets["y2"]["vis"].setChecked(enabled)
        self._suppress = False
        # Обновить доступность контролов
        panel = self.spec.find_panel(self.panel_id) if self.spec is not None else None
        if panel is not None:
            panel.y2_visible = enabled
            self._update_axis_enabled_state(panel)
        self.panel_y2_toggled.emit(self.panel_id, enabled)

    def _on_geom(self, *_):
        if self._suppress or not self.panel_id:
            return
        self.panel_geometry_changed.emit(
            self.panel_id,
            float(self.x_spin.value()), float(self.y_spin.value()),
            float(self.w_spin.value()), float(self.h_spin.value()),
        )

    def _reset_geom(self):
        if not self.panel_id:
            return
        self.panel_geometry_changed.emit(self.panel_id, 30.0, 20.0, 60.0, 45.0)

class AddCurveInlinePanel(QWidget):
	curves_added=pyqtSignal(str,list)
	def __init__(self,panel_id:str,session_controller,parent=None):
		super().__init__(parent)
		self.panel_id=panel_id
		self.session_controller=session_controller
		self._connected_session=None
		self._connected_signals=[]
		self._build_ui()
		self._reload_sessions()
		self.destroyed.connect(lambda *args: self._disconnect_session())

	def _build_ui(self):
		layout=QVBoxLayout(self)
		layout.setContentsMargins(0,0,0,0)
		layout.setSpacing(4)
		row1=QHBoxLayout()
		row1.addWidget(QLabel("Сессия:"))
		self.session_combo=QComboBox()
		self.session_combo.currentIndexChanged.connect(self._reload_series)
		row1.addWidget(self.session_combo,1)
		layout.addLayout(row1)
		row2=QHBoxLayout()
		row2.addWidget(QLabel("Фильтр:"))
		self.filter_edit=QLineEdit()
		self.filter_edit.setPlaceholderText("поиск...")
		self.filter_edit.textChanged.connect(self._apply_filter)
		row2.addWidget(self.filter_edit,1)
		layout.addLayout(row2)
		self.scroll=QScrollArea()
		self.scroll.setWidgetResizable(True)
		self.scroll.setMaximumHeight(200)
		self.list_widget=QWidget()
		self.list_layout=QVBoxLayout(self.list_widget)
		self.list_layout.setContentsMargins(0,0,0,0)
		self.scroll.setWidget(self.list_widget)
		layout.addWidget(self.scroll)
		btn_row=QHBoxLayout()
		self.add_btn=QPushButton("Добавить выбранные")
		self.add_btn.clicked.connect(self._on_add)
		self.cancel_btn=QPushButton("Отмена")
		self.cancel_btn.clicked.connect(self.hide)
		btn_row.addWidget(self.add_btn)
		btn_row.addWidget(self.cancel_btn)
		layout.addLayout(btn_row)
		self.hide()

	def _disconnect_session(self):
		if self._connected_session is not None:
			for sig, slot in self._connected_signals:
				try:
					sig.disconnect(slot)
				except TypeError:
					pass
			self._connected_session=None
			self._connected_signals.clear()

	def _connect_session(self, sess):
		if sess is self._connected_session:
			return
		self._disconnect_session()
		if sess is None:
			return
		gm=getattr(sess,"graph_main",None)
		if gm is not None:
			sig_add=getattr(gm,"curve_added",None)
			if sig_add is not None:
				slot=lambda *args: self._reload_series()
				sig_add.connect(slot)
				self._connected_signals.append((sig_add,slot))
			sig_rem=getattr(gm,"curve_removed",None)
			if sig_rem is not None:
				slot=lambda *args: self._reload_series()
				sig_rem.connect(slot)
				self._connected_signals.append((sig_rem,slot))
		self._connected_session=sess

	def _reload_sessions(self):
		self.session_combo.blockSignals(True)
		self.session_combo.clear()
		sessions=getattr(self.session_controller,"graph_sessions",{}) or {}
		for sid,sess in sessions.items():
			try:
				name=sess.session_name
			except Exception:
				name=sid
			self.session_combo.addItem(f"{sid}: {name}",sid)
		self.session_combo.blockSignals(False)
		self._reload_series()

	def _reload_series(self):
		while self.list_layout.count():
			item=self.list_layout.takeAt(0)
			w=item.widget()
			if w is not None:
				w.deleteLater()
		sid=self.session_combo.currentData()
		if not sid:
			return
		sess=self.session_controller.graph_sessions.get(sid)
		if not sess:
			return
		self._connect_session(sess)
		gm=getattr(sess,"graph_main",None)
		if not gm:
			return
		curves=gm.get_curves()
		for root_name,curve in curves.items():
			name=getattr(curve,"curve_name",root_name)
			cb=QCheckBox(name)
			cb.setProperty("root_name",root_name)
			cb.setProperty("session_id",sid)
			self.list_layout.addWidget(cb)
		self.list_layout.addStretch()

	def _apply_filter(self,text):
		text=text.strip().lower()
		for i in range(self.list_layout.count()):
			item=self.list_layout.itemAt(i)
			w=item.widget()
			if isinstance(w,QCheckBox):
				w.setVisible( not text or text in w.text().lower())

	def _on_add(self):
		from..model.session_ref import DataRef,DataSnapshot,StyleSnapshot
		selected=[]
		for i in range(self.list_layout.count()):
			item=self.list_layout.itemAt(i)
			w=item.widget()
			if isinstance(w,QCheckBox) and w.isChecked():
				sid=w.property("session_id")
				root_name=w.property("root_name")
				if sid and root_name:
					ref=DataRef(session_id=sid,series_root_name=root_name)
					sess=self.session_controller.graph_sessions.get(sid)
					if sess:
						gm=getattr(sess,"graph_main",None)
						if gm:
							curve=gm.get_curve(root_name)
							if curve:
								ref.data=DataSnapshot.take(curve)
								ref.style=StyleSnapshot.take(curve,None)
								ref.refresh_policy="snapshot"
					selected.append(ref)
		if selected:
			self.curves_added.emit(self.panel_id,selected)
		self.hide()
