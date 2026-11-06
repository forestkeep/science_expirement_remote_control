from __future__ import annotations
from typing import Callable, Dict, Optional
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QTabWidget, QToolButton,
    QVBoxLayout, QWidget,
)
from ..model.panel import PanelSpec, CurveSlot


class _CurveEditorSection(QWidget):
    visible_changed = pyqtSignal(int, bool)
    axis_changed = pyqtSignal(int, str)
    legend_changed = pyqtSignal(int, str)
    from_source_toggled = pyqtSignal(int, bool)
    color_changed = pyqtSignal(int, str)
    line_style_changed = pyqtSignal(int, str)
    line_width_changed = pyqtSignal(int, float)
    marker_changed = pyqtSignal(int, str)
    marker_size_changed = pyqtSignal(int, float)
    marker_edge_changed = pyqtSignal(int, str)
    marker_face_changed = pyqtSignal(int, str)
    refresh_data_requested = pyqtSignal(int)
    refresh_style_requested = pyqtSignal(int)
    artifact_toggled = pyqtSignal(int, str, bool)
    artifact_show_requested = pyqtSignal(int, str)
    pinned_toggled = pyqtSignal(int, bool)
    reset_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)

    _PIN_KEY = "__pinned__"
    _PIN_KEYS_KEY = "__pinned_keys__"

    def __init__(
        self,
        idx: int,
        slot: CurveSlot,
        panel: PanelSpec,
        link_state: bool = True,
        on_link_state_changed: Optional[Callable[[int, bool], None]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._idx = idx
        self._slot = slot
        self._panel = panel
        self._suppress = False
        self._link_marker_state = bool(link_state)
        self._on_link_state_changed = on_link_state_changed
        self._build_ui()
        self._link_marker_check.setChecked(self._link_marker_state)
        self._apply_link_visibility()
        self._refresh_from_slot()

    # ---------- UI ----------

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 4)
        outer.setSpacing(1)

        # --- строка 1: заголовок + сервисные кнопки ---
        row1 = QHBoxLayout()
        row1.setSpacing(2)
        row1.setContentsMargins(0, 0, 0, 0)

        self._toggle = QToolButton()
        self._toggle.setArrowType(Qt.RightArrow)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(False)
        self._toggle.setAutoRaise(True)
        self._toggle.setFixedSize(16, 20)
        self._toggle.toggled.connect(self._on_toggle)
        row1.addWidget(self._toggle)

        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(18, 20)
        self._color_btn.setToolTip("Цвет линии")
        self._color_btn.clicked.connect(self._on_color_click)
        row1.addWidget(self._color_btn)

        self._legend_edit = QLineEdit()
        self._legend_edit.setPlaceholderText("auto")
        self._legend_edit.setFixedHeight(20)
        self._legend_edit.editingFinished.connect(self._on_legend_changed)
        row1.addWidget(self._legend_edit, 1)

        self._pin_btn = QPushButton("📌")
        self._pin_btn.setFixedSize(20, 20)
        self._pin_btn.setCheckable(True)
        self._pin_btn.setToolTip("Закрепить overrides")
        self._pin_btn.toggled.connect(self._on_pin_toggled)
        row1.addWidget(self._pin_btn)

        self._reset_btn = QPushButton("↺")
        self._reset_btn.setFixedSize(20, 20)
        self._reset_btn.setToolTip("Сбросить к источнику")
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        row1.addWidget(self._reset_btn)

        self._del_btn = QPushButton("✕")
        self._del_btn.setFixedSize(20, 20)
        self._del_btn.setToolTip("Удалить кривую")
        self._del_btn.clicked.connect(self._on_delete_clicked)
        row1.addWidget(self._del_btn)

        outer.addLayout(row1)

        # --- строка 2: толщина + стиль линии ---
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        row2.setContentsMargins(20, 0, 0, 0)

        lbl_w = QLabel("Линия:")
        lbl_w.setStyleSheet("color: #777;")
        row2.addWidget(lbl_w)
        self._width_spin = QDoubleSpinBox()
        self._width_spin.setRange(0.1, 20.0)
        self._width_spin.setSingleStep(0.25)
        self._width_spin.setDecimals(2)
        self._width_spin.setSuffix(" pt")
        self._width_spin.setFixedHeight(20)
        self._width_spin.valueChanged.connect(self._on_width_changed)
        row2.addWidget(self._width_spin, 1)

        self._line_style_combo = QComboBox()
        for text, val in (
            ("—", "Solid"), ("--", "Dash"), ("··", "Dot"),
            ("-·-", "DashDot"), ("-··-", "DashDotDot"),
        ):
            self._line_style_combo.addItem(text, val)
        self._line_style_combo.setFixedHeight(20)
        self._line_style_combo.setToolTip("Стиль линии")
        self._line_style_combo.currentIndexChanged.connect(self._on_line_style_changed)
        row2.addWidget(self._line_style_combo, 1)

        outer.addLayout(row2)

        # --- строка 3: маркер + размер ---
        row3 = QHBoxLayout()
        row3.setSpacing(4)
        row3.setContentsMargins(20, 0, 0, 0)

        lbl_ms = QLabel("Маркер:")
        lbl_ms.setStyleSheet("color: #777;")
        row3.addWidget(lbl_ms)
        self._marker_size_spin = QDoubleSpinBox()
        self._marker_size_spin.setRange(0.0, 40.0)
        self._marker_size_spin.setDecimals(1)
        self._marker_size_spin.setSuffix(" pt")
        self._marker_size_spin.setFixedHeight(20)
        self._marker_size_spin.valueChanged.connect(self._on_marker_size_changed)
        row3.addWidget(self._marker_size_spin, 1)

        self._marker_combo = QComboBox()
        for text, val in (
            ("×", ""), ("○", "o"), ("□", "s"), ("△", "t1"), ("◇", "d"), ("+", "+"),
        ):
            self._marker_combo.addItem(text, val)
        self._marker_combo.setFixedHeight(20)
        self._marker_combo.setToolTip("Стиль маркера")
        self._marker_combo.currentIndexChanged.connect(self._on_marker_changed)
        row3.addWidget(self._marker_combo, 1)

        outer.addLayout(row3)

        # --- разделитель между кривыми ---
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Plain)
        sep.setStyleSheet("color: #444;")
        outer.addWidget(sep)

        # --- разворачиваемый контент ---
        self._content = QWidget()
        cl = QVBoxLayout(self._content)
        cl.setContentsMargins(20, 4, 4, 4)
        cl.setSpacing(4)

        ident = QFormLayout()
        ident.setContentsMargins(0, 0, 0, 0)
        ident.setSpacing(2)
        self._session_label = QLabel("—")
        self._session_label.setStyleSheet("color: #888;")
        ident.addRow("Сессия:", self._session_label)
        self._series_label = QLabel("—")
        self._series_label.setStyleSheet("color: #888;")
        ident.addRow("Серия:", self._series_label)
        cl.addLayout(ident)

        row_ax = QHBoxLayout()
        row_ax.addWidget(QLabel("Ось:"))
        self._axis_combo = QComboBox()
        self._axis_combo.addItems(["Y1", "Y2"])
        self._axis_combo.currentIndexChanged.connect(self._on_axis_changed)
        row_ax.addWidget(self._axis_combo)
        self._visible_check = QCheckBox("видима")
        self._visible_check.stateChanged.connect(self._on_visible_changed)
        row_ax.addWidget(self._visible_check)
        row_ax.addStretch()
        cl.addLayout(row_ax)

        self._from_source_check = QCheckBox("из источника (сброс overrides)")
        self._from_source_check.stateChanged.connect(self._on_from_source_toggled)
        cl.addWidget(self._from_source_check)

        self._link_marker_check = QCheckBox("цвет маркера как у линии")
        self._link_marker_check.setChecked(True)
        self._link_marker_check.toggled.connect(self._on_link_marker_toggled)
        cl.addWidget(self._link_marker_check)

        self._marker_edge_container = QWidget()
        mel = QHBoxLayout(self._marker_edge_container)
        mel.setContentsMargins(0, 0, 0, 0)
        mel.addWidget(QLabel("Цвет маркера:"))
        self._marker_edge_btn = QPushButton()
        self._marker_edge_btn.clicked.connect(self._on_marker_edge_click)
        mel.addWidget(self._marker_edge_btn, 1)
        cl.addWidget(self._marker_edge_container)

        self._marker_face_container = QWidget()
        mfl = QHBoxLayout(self._marker_face_container)
        mfl.setContentsMargins(0, 0, 0, 0)
        mfl.addWidget(QLabel("Цвет заливки:"))
        self._marker_face_btn = QPushButton()
        self._marker_face_btn.clicked.connect(self._on_marker_face_click)
        mfl.addWidget(self._marker_face_btn, 1)
        cl.addWidget(self._marker_face_container)

        data_box = QGroupBox("Данные")
        data_lay = QVBoxLayout(data_box)
        self._data_info = QLabel("snapshot отсутствует")
        self._data_info.setStyleSheet("font-family: monospace; color: #666;")
        data_lay.addWidget(self._data_info)
        row_refresh = QHBoxLayout()
        self._refresh_data_btn = QPushButton("Обновить данные")
        self._refresh_data_btn.clicked.connect(self._on_refresh_data)
        row_refresh.addWidget(self._refresh_data_btn)
        self._refresh_style_btn = QPushButton("Обновить стиль")
        self._refresh_style_btn.clicked.connect(self._on_refresh_style)
        row_refresh.addWidget(self._refresh_style_btn)
        data_lay.addLayout(row_refresh)
        cl.addWidget(data_box)

        self._artifacts_box = QGroupBox("Артефакты анализа")
        self._artifacts_lay = QVBoxLayout(self._artifacts_box)
        cl.addWidget(self._artifacts_box)

        outer.addWidget(self._content)
        self._content.setVisible(False)

    # ---------- expand / state ----------

    def is_expanded(self) -> bool:
        return self._toggle.isChecked()

    def set_expanded(self, value: bool) -> None:
        self._toggle.setChecked(bool(value))

    def _on_toggle(self, checked: bool):
        self._toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self._content.setVisible(checked)

    def _apply_link_visibility(self):
        linked = self._link_marker_state
        self._marker_edge_container.setVisible(not linked)
        self._marker_face_container.setVisible(not linked)

    # ---------- refresh ----------

    def _refresh_from_slot(self):
        self._suppress = True
        try:
            slot = self._slot
            ref = slot.data_ref
            self._session_label.setText(ref.session_id if ref and ref.session_id else "—")
            self._series_label.setText(ref.series_root_name if ref and ref.series_root_name else "—")
            default_name = ""
            if ref is not None and ref.series_root_name:
                default_name = ref.series_root_name
            self._legend_edit.setPlaceholderText(default_name or "auto")
            self._legend_edit.setText(slot.legend_label or "")

            self._axis_combo.setCurrentText("Y2" if slot.axis == "y2" else "Y1")
            self._visible_check.setChecked(slot.visible)

            style = getattr(ref, "style", None) if ref else None
            line_style = getattr(style, "line_style", None) if style else None

            color = slot.style_overrides.get("line.color")
            if color is None and line_style is not None:
                color = getattr(line_style, "color", "#1f77b4")
            color = str(color or "#1f77b4")
            self._set_color_btn(color)

            edge = slot.style_overrides.get("marker.edge")
            if edge is None and line_style is not None:
                edge = getattr(line_style, "symbol_color", color)
            edge = str(edge or color)
            self._set_marker_edge_btn(edge)

            face = slot.style_overrides.get("marker.face")
            if face is None and line_style is not None:
                face = getattr(line_style, "fill_color", color)
            face = str(face or color)
            self._set_marker_face_btn(face)

            width = slot.style_overrides.get("line.width")
            if width is None and line_style is not None:
                width = getattr(line_style, "line_width", 1.0)
            try:
                self._width_spin.setValue(float(width or 1.0))
            except (TypeError, ValueError):
                self._width_spin.setValue(1.0)

            ls_name = slot.style_overrides.get("line.style")
            if ls_name is None and line_style is not None:
                from PyQt5.QtCore import Qt as _Qt
                _map = {
                    _Qt.SolidLine: "Solid", _Qt.DashLine: "Dash", _Qt.DotLine: "Dot",
                    _Qt.DashDotLine: "DashDot", _Qt.DashDotDotLine: "DashDotDot",
                }
                ls_name = _map.get(getattr(line_style, "line_style", None), "Solid")
            idx = self._line_style_combo.findData(str(ls_name or "Solid"))
            if idx >= 0:
                self._line_style_combo.setCurrentIndex(idx)

            sym = slot.style_overrides.get("marker.symbol")
            if sym is None and line_style is not None:
                sym = getattr(line_style, "symbol", None) or ""
            idx = self._marker_combo.findData(str(sym or ""))
            if idx >= 0:
                self._marker_combo.setCurrentIndex(idx)

            msize = slot.style_overrides.get("marker.size")
            if msize is None and line_style is not None:
                msize = getattr(line_style, "symbol_size", 5.0)
            try:
                self._marker_size_spin.setValue(float(msize or 5.0))
            except (TypeError, ValueError):
                self._marker_size_spin.setValue(5.0)

            real_ovr = [k for k in slot.style_overrides
                        if k not in (self._PIN_KEY, self._PIN_KEYS_KEY)]
            self._from_source_check.setChecked(not real_ovr)
            self._pin_btn.setChecked(
                bool(slot.style_overrides.get(self._PIN_KEY))
                or bool(slot.style_overrides.get(self._PIN_KEYS_KEY))
            )

            snap = ref.data if ref is not None else None
            if snap is not None:
                n = len(getattr(snap, "x", []))
                fp = getattr(snap, "fingerprint", "")[:12]
                self._data_info.setText(
                    f"Точек: {n}\nfingerprint: {fp}…\nвзято: {getattr(snap, 'taken_at', '?')}"
                )
            else:
                self._data_info.setText("snapshot отсутствует")

            self._rebuild_artifacts()
            self._apply_link_visibility()
        finally:
            self._suppress = False

    def _rebuild_artifacts(self):
        while self._artifacts_lay.count():
            item = self._artifacts_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        ref = self._slot.data_ref
        style = getattr(ref, "style", None) if ref else None
        arts = list(getattr(style, "artifacts", []) or []) if style else []
        uncertainty = list(getattr(style, "uncertainty_records", []) or []) if style else []
        if not arts and not uncertainty:
            self._artifacts_box.setVisible(False)
            return
        self._artifacts_box.setVisible(True)
        for art in arts:
            tool_id = getattr(art, "tool_id", "")
            if not tool_id:
                continue
            row = QWidget()
            lay = QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
            cb = QCheckBox(tool_id)
            cb.setChecked(bool(self._panel.show_tools.get(tool_id, False)))
            cb.stateChanged.connect(lambda st, t=tool_id: self._on_artifact_toggled(t, st != 0))
            lay.addWidget(cb, 1)
            show_btn = QPushButton("показать")
            show_btn.clicked.connect(
                lambda _c=False, t=tool_id: self.artifact_show_requested.emit(self._idx, t)
            )
            lay.addWidget(show_btn)
            self._artifacts_lay.addWidget(row)
        if uncertainty:
            rec = uncertainty[0]
            method = str(getattr(rec, "method", "std"))
            n = len(getattr(rec, "y_err", []) or [])
            text = f"uncertainty.estimate  ({method}, N={n})"
            row = QWidget()
            lay = QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
            cb = QCheckBox(text)
            cb.setChecked(bool(self._panel.show_tools.get("uncertainty.estimate", False)))
            cb.stateChanged.connect(
                lambda st: self._on_artifact_toggled("uncertainty.estimate", st != 0)
            )
            lay.addWidget(cb, 1)
            show_btn = QPushButton("показать")
            show_btn.clicked.connect(
                lambda _c=False: self.artifact_show_requested.emit(self._idx, "uncertainty.estimate")
            )
            lay.addWidget(show_btn)
            self._artifacts_lay.addWidget(row)

    # ---------- helpers ----------

    def _set_color_btn(self, color: str):
        self._color_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #333;")
        self._color_btn.setToolTip(f"Цвет линии: {color}")

    def _set_marker_edge_btn(self, color: str):
        self._marker_edge_btn.setText(color)
        self._marker_edge_btn.setStyleSheet(f"background-color: {color}; padding: 2px;")

    def _set_marker_face_btn(self, color: str):
        self._marker_face_btn.setText(color)
        self._marker_face_btn.setStyleSheet(f"background-color: {color}; padding: 2px;")

    def _after_field_edit(self):
        if self._suppress:
            return
        self._suppress = True
        try:
            self._from_source_check.setChecked(False)
        finally:
            self._suppress = False

    # ---------- compact row handlers ----------

    def _on_visible_changed(self, st):
        if not self._suppress:
            self.visible_changed.emit(self._idx, st != 0)

    def _on_axis_changed(self, _i):
        if not self._suppress:
            self.axis_changed.emit(self._idx, self._axis_combo.currentText().lower())

    def _on_legend_changed(self):
        if not self._suppress:
            self.legend_changed.emit(self._idx, self._legend_edit.text())

    def _on_from_source_toggled(self, st):
        if self._suppress:
            return
        self.from_source_toggled.emit(self._idx, st != 0)
        self._refresh_from_slot()

    def _on_link_marker_toggled(self, checked: bool):
        self._link_marker_state = bool(checked)
        self._apply_link_visibility()
        if self._on_link_state_changed:
            try:
                self._on_link_state_changed(id(self._slot), bool(checked))
            except Exception:
                pass
        if self._suppress:
            return
        if checked:
            color = self._color_btn.text() or "#1f77b4"
            if not color.startswith("#"):
                color = "#1f77b4"
            self._set_marker_edge_btn(color)
            self._set_marker_face_btn(color)
            self.marker_edge_changed.emit(self._idx, color)
            self.marker_face_changed.emit(self._idx, color)
            self._after_field_edit()

    def _on_color_click(self):
        from PyQt5.QtGui import QColor
        from common.color_picker import pick_color
        current = self._color_btn.text() or "#1f77b4"

        def on_selected(c: QColor):
            color = c.name()
            self._set_color_btn(color)
            self.color_changed.emit(self._idx, color)
            if self._link_marker_check.isChecked():
                self._set_marker_edge_btn(color)
                self._set_marker_face_btn(color)
                self.marker_edge_changed.emit(self._idx, color)
                self.marker_face_changed.emit(self._idx, color)
            self._after_field_edit()

        pick_color(self._color_btn, current, on_selected, self)

    def _on_marker_edge_click(self):
        from PyQt5.QtGui import QColor
        from common.color_picker import pick_color
        current = self._marker_edge_btn.text() or "#1f77b4"

        def on_selected(c: QColor):
            self._set_marker_edge_btn(c.name())
            self.marker_edge_changed.emit(self._idx, c.name())
            self._after_field_edit()

        pick_color(self._marker_edge_btn, current, on_selected, self)

    def _on_marker_face_click(self):
        from PyQt5.QtGui import QColor
        from common.color_picker import pick_color
        current = self._marker_face_btn.text() or "#1f77b4"

        def on_selected(c: QColor):
            self._set_marker_face_btn(c.name())
            self.marker_face_changed.emit(self._idx, c.name())
            self._after_field_edit()

        pick_color(self._marker_face_btn, current, on_selected, self)

    def _on_line_style_changed(self, _i):
        if self._suppress:
            return
        self.line_style_changed.emit(self._idx, self._line_style_combo.currentData() or "Solid")
        self._after_field_edit()

    def _on_width_changed(self, v):
        if self._suppress:
            return
        self.line_width_changed.emit(self._idx, float(v))
        self._after_field_edit()

    def _on_marker_changed(self, _i):
        if self._suppress:
            return
        self.marker_changed.emit(self._idx, self._marker_combo.currentData() or "")
        if self._link_marker_state:
            color = self._color_btn.text() or "#1f77b4"
            if not color.startswith("#"):
                color = "#1f77b4"
            self.marker_edge_changed.emit(self._idx, color)
            self.marker_face_changed.emit(self._idx, color)
        self._after_field_edit()

    def _on_marker_size_changed(self, v):
        if self._suppress:
            return
        self.marker_size_changed.emit(self._idx, float(v))
        self._after_field_edit()

    def _on_refresh_data(self):
        self.refresh_data_requested.emit(self._idx)
        self._refresh_from_slot()

    def _on_refresh_style(self):
        self.refresh_style_requested.emit(self._idx)
        self._refresh_from_slot()

    def _on_artifact_toggled(self, tool_id: str, checked: bool):
        if not self._suppress:
            self.artifact_toggled.emit(self._idx, tool_id, checked)

    def _on_pin_toggled(self, checked: bool):
        if not self._suppress:
            self.pinned_toggled.emit(self._idx, bool(checked))

    def _on_reset_clicked(self):
        self.reset_requested.emit(self._idx)
        self._refresh_from_slot()

    def _on_delete_clicked(self):
        self.delete_requested.emit(self._idx)


class PanelInspector(QWidget):
    panel_label_changed = pyqtSignal(str, str)
    panel_reset_all = pyqtSignal(str)
    panel_pinned_toggled = pyqtSignal(str, bool)
    panel_geometry_changed = pyqtSignal(str, float, float, float, float)
    panel_axis_visibility = pyqtSignal(str, str, bool)
    panel_axis_linked = pyqtSignal(str, str, str)
    panel_axis_label = pyqtSignal(str, str, str)
    panel_axis_range = pyqtSignal(str, str, object, object)
    panel_axis_auto = pyqtSignal(str, str, bool)
    panel_axis_log = pyqtSignal(str, str, bool)
    panel_y2_toggled = pyqtSignal(str, bool)
    slot_add_requested = pyqtSignal(str)
    slot_visible_changed = pyqtSignal(int, bool)
    slot_axis_changed = pyqtSignal(int, str)
    slot_legend_changed = pyqtSignal(int, str)
    slot_from_source_toggled = pyqtSignal(int, bool)
    slot_color_changed = pyqtSignal(int, str)
    slot_line_style_changed = pyqtSignal(int, str)
    slot_width_changed = pyqtSignal(int, float)
    slot_marker_changed = pyqtSignal(int, str)
    slot_marker_size_changed = pyqtSignal(int, float)
    slot_marker_edge_changed = pyqtSignal(int, str)
    slot_marker_face_changed = pyqtSignal(int, str)
    slot_refresh_data_requested = pyqtSignal(int)
    slot_refresh_style_requested = pyqtSignal(int)
    slot_artifact_toggled = pyqtSignal(int, str, bool)
    slot_artifact_show_requested = pyqtSignal(int, str)
    slot_pinned_toggled = pyqtSignal(int, bool)
    slot_reset_requested = pyqtSignal(int)
    slot_deleted = pyqtSignal(int)
    legend_mode_changed = pyqtSignal(str)
    legend_position_changed = pyqtSignal(str)
    legend_visible_changed = pyqtSignal(bool)
    legend_pinned_toggled = pyqtSignal(bool)
    annotation_create = pyqtSignal(str)
    annotation_edit = pyqtSignal(str)
    annotation_delete = pyqtSignal(str)
    curves_added = pyqtSignal(str, list)

    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.panel_id = ""
        self._suppress = False
        self._curve_sections: list = []
        self._link_states: Dict[int, bool] = {}
        self._build_ui()

    def set_spec(self, spec) -> None:
        self.spec = spec
        self.panel_id = ""
        self._curve_sections = []
        self._link_states = {}
        self._clear_panel_ui()

    def get_link_state(self, slot) -> bool:
        return bool(self._link_states.get(id(slot), True))

    def _set_link_state(self, slot_id: int, value: bool) -> None:
        self._link_states[slot_id] = bool(value)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._tabs = QTabWidget()
        outer.addWidget(self._tabs)
        self._build_geometry_tab()
        self._build_curves_tab()
        self._build_axes_tab()
        self._build_legend_tab()
        self._build_annotations_tab()

    def _build_geometry_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        header = QHBoxLayout()
        header.addWidget(QLabel("Метка:"))
        self.label_edit = QLineEdit()
        self.label_edit.setFixedWidth(80)
        self.label_edit.editingFinished.connect(self._on_label)
        header.addWidget(self.label_edit)
        header.addStretch()
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setToolTip("Закрепить все текущие overrides панели")
        self.pin_btn.toggled.connect(lambda st: self.panel_pinned_toggled.emit(self.panel_id, bool(st)))
        header.addWidget(self.pin_btn)
        self.reset_all_btn = QPushButton("↺")
        self.reset_all_btn.setToolTip("Сбросить все panel_overrides")
        self.reset_all_btn.clicked.connect(lambda: self.panel_reset_all.emit(self.panel_id))
        header.addWidget(self.reset_all_btn)
        lay.addLayout(header)

        geom_box = QGroupBox("Геометрия (мм)")
        geom_form = QFormLayout(geom_box)
        self.x_spin = self._coord_spin()
        self.y_spin = self._coord_spin()
        self.w_spin = self._coord_spin()
        self.h_spin = self._coord_spin()
        for label, sp in (("x:", self.x_spin), ("y:", self.y_spin), ("w:", self.w_spin), ("h:", self.h_spin)):
            geom_form.addRow(label, sp)
            sp.valueChanged.connect(self._on_geom)
        lay.addWidget(geom_box)

        reset_row = QHBoxLayout()
        reset_geom = QPushButton("↺ на панель (30, 20, 60×45)")
        reset_geom.clicked.connect(self._reset_geom)
        reset_row.addWidget(reset_geom)
        reset_row.addStretch()
        lay.addLayout(reset_row)
        lay.addStretch()
        self._tabs.addTab(w, "Геометрия")

    def _build_curves_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.curves_rows_container = QWidget()
        self.curves_rows_lay = QVBoxLayout(self.curves_rows_container)
        self.curves_rows_lay.setContentsMargins(0, 0, 0, 0)
        self.curves_rows_lay.setSpacing(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.curves_rows_container)
        lay.addWidget(scroll, 1)
        add_row = QHBoxLayout()
        self.add_slot_btn = QPushButton("+ из сессии ▾")
        self.add_slot_btn.clicked.connect(self._toggle_add_panel)
        add_row.addWidget(self.add_slot_btn)
        add_row.addStretch()
        lay.addLayout(add_row)
        self.add_panel_container = QWidget()
        self.add_panel_layout = QVBoxLayout(self.add_panel_container)
        self.add_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.add_panel_container.hide()
        lay.addWidget(self.add_panel_container)
        self._tabs.addTab(w, "Кривые")

    def _build_axes_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.axis_widgets = {}
        for key, title in (("x", "X"), ("y1", "Y1"), ("y2", "Y2")):
            lay.addWidget(self._build_axis_row(key, title))
        lay.addStretch()
        self._tabs.addTab(w, "Оси")

    def _build_legend_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        mode_row = QHBoxLayout()
        self.legend_panel_radio = QPushButton("в панели")
        self.legend_fig_radio = QPushButton("общая фигуры")
        self.legend_inline_radio = QPushButton("у кривых")
        for b in (self.legend_panel_radio, self.legend_fig_radio, self.legend_inline_radio):
            b.setCheckable(True)
            b.setFixedHeight(22)
            mode_row.addWidget(b)
        mode_row.addStretch()
        lay.addLayout(mode_row)
        self.legend_panel_radio.clicked.connect(lambda: self._on_legend_mode_clicked("panel"))
        self.legend_fig_radio.clicked.connect(lambda: self._on_legend_mode_clicked("figure"))
        self.legend_inline_radio.clicked.connect(lambda: self._on_legend_mode_clicked("inline"))

        self.legend_visible_check = QCheckBox("показывать")
        self.legend_visible_check.stateChanged.connect(lambda st: self.legend_visible_changed.emit(st != 0))
        lay.addWidget(self.legend_visible_check)

        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("позиция:"))
        self.legend_pos_combo = QComboBox()
        for text, val in (
            ("best", "best"), ("верх-лево", "upper left"), ("верх-право", "upper right"),
            ("низ-лево", "lower left"), ("низ-право", "lower right"), ("снаружи-право", "outside right"),
        ):
            self.legend_pos_combo.addItem(text, val)
        self.legend_pos_combo.currentIndexChanged.connect(
            lambda _i: self.legend_position_changed.emit(self.legend_pos_combo.currentData() or "best")
        )
        pos_row.addWidget(self.legend_pos_combo, 1)
        self.legend_pin_btn = QPushButton("📌")
        self.legend_pin_btn.setCheckable(True)
        self.legend_pin_btn.toggled.connect(self.legend_pinned_toggled.emit)
        pos_row.addWidget(self.legend_pin_btn)
        lay.addLayout(pos_row)
        lay.addStretch()
        self._tabs.addTab(w, "Легенда")

    def _build_annotations_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        btn_row = QHBoxLayout()
        for kind, label in (("text", "+ Текст"), ("arrow", "+ Стрелка"), ("scale_bar", "+ Scale bar")):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _c=False, k=kind: self.annotation_create.emit(k))
            btn_row.addWidget(btn)
        lay.addLayout(btn_row)
        self.ann_lay = QVBoxLayout()
        lay.addLayout(self.ann_lay)
        lay.addStretch()
        self._tabs.addTab(w, "Аннотации")

    def _on_legend_mode_clicked(self, mode: str) -> None:
        self.legend_panel_radio.setChecked(mode == "panel")
        self.legend_fig_radio.setChecked(mode == "figure")
        self.legend_inline_radio.setChecked(mode == "inline")
        self.legend_mode_changed.emit(mode)

    def _coord_spin(self):
        s = QDoubleSpinBox()
        s.setRange(-1000.0, 1000.0)
        s.setDecimals(1)
        s.setSingleStep(0.1)
        s.setSuffix(" мм")
        s.setFixedWidth(80)
        return s

    def _toggle_add_panel(self):
        if not hasattr(self, "session_controller") or self.session_controller is None:
            return
        if self.add_panel_container.isVisible():
            self.add_panel_container.hide()
            return
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
        vis.stateChanged.connect(lambda st, k=key: self.panel_axis_visibility.emit(self.panel_id, k, st != 0))
        linked.currentIndexChanged.connect(lambda _i, k=key: self._on_axis_linked_changed(k))
        label_edit.editingFinished.connect(
            lambda k=key, e=label_edit: self.panel_axis_label.emit(self.panel_id, k, e.text())
        )
        min_spin.valueChanged.connect(
            lambda v, k=key: self.panel_axis_range.emit(
                self.panel_id, k, float(v), float(self.axis_widgets[k]["max"].value())
            )
        )
        max_spin.valueChanged.connect(
            lambda v, k=key: self.panel_axis_range.emit(
                self.panel_id, k, float(self.axis_widgets[k]["min"].value()), float(v)
            )
        )
        auto.stateChanged.connect(lambda st, k=key: self.panel_axis_auto.emit(self.panel_id, k, st != 0))
        log.stateChanged.connect(lambda st, k=key: self.panel_axis_log.emit(self.panel_id, k, st != 0))
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

    def set_panel(self, panel_id: str) -> None:
        self.panel_id = panel_id or ""
        panel = self.spec.find_panel(self.panel_id) if self.spec is not None and self.panel_id else None
        if panel is None:
            self._clear_panel_ui()
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
            for key in ("x", "y1", "y2"):
                combo = self.axis_widgets[key]["linked"]
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("—", "")
                for p in self.spec.sorted_panels():
                    if p.id != self.panel_id:
                        combo.addItem(f"{p.title or p.id}", p.id)
                linked_value = panel.style_overrides.get(f"axis.{key}.linked", "")
                idx_linked = combo.findData(linked_value)
                if idx_linked >= 0:
                    combo.setCurrentIndex(idx_linked)
                combo.blockSignals(False)
            self._update_axis_enabled_state(panel)
            self._rebuild_curve_sections(panel)
            mode = panel.style_overrides.get("legend.mode", "panel")
            self.legend_panel_radio.setChecked(mode == "panel")
            self.legend_fig_radio.setChecked(mode == "figure")
            self.legend_inline_radio.setChecked(mode == "inline")
            self.legend_visible_check.setChecked(bool(panel.style_overrides.get("legend.enabled", True)))
            pos = panel.style_overrides.get("legend.pos", "best")
            idx = self.legend_pos_combo.findData(pos)
            if idx >= 0:
                self.legend_pos_combo.setCurrentIndex(idx)
            self.x_spin.setValue(float(panel.x_mm))
            self.y_spin.setValue(float(panel.y_mm))
            self.w_spin.setValue(float(panel.w_mm))
            self.h_spin.setValue(float(panel.h_mm))
            self._rebuild_annotations(panel)
        finally:
            self._suppress = False

    def _clear_panel_ui(self) -> None:
        self._suppress = True
        self._curve_sections = []
        try:
            self.label_edit.clear()
            self.pin_btn.setChecked(False)
            for sp in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
                sp.setValue(0.0)
            while self.curves_rows_lay.count():
                item = self.curves_rows_lay.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
            while self.ann_lay.count():
                item = self.ann_lay.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
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

    def _rebuild_curve_sections(self, panel: PanelSpec) -> None:
        expanded_slots = set()
        for section in self._curve_sections:
            try:
                if section.is_expanded():
                    expanded_slots.add(id(section._slot))
                self._link_states[id(section._slot)] = section._link_marker_state
            except Exception:
                pass

        while self.curves_rows_lay.count():
            item = self.curves_rows_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        self._curve_sections = []
        for idx, slot in enumerate(panel.curves):
            link_initial = self._link_states.get(id(slot), True)
            section = _CurveEditorSection(
                idx, slot, panel,
                link_state=link_initial,
                on_link_state_changed=self._set_link_state,
            )
            section.visible_changed.connect(self.slot_visible_changed.emit)
            section.axis_changed.connect(self.slot_axis_changed.emit)
            section.legend_changed.connect(self.slot_legend_changed.emit)
            section.from_source_toggled.connect(self.slot_from_source_toggled.emit)
            section.color_changed.connect(self.slot_color_changed.emit)
            section.line_style_changed.connect(self.slot_line_style_changed.emit)
            section.line_width_changed.connect(self.slot_width_changed.emit)
            section.marker_changed.connect(self.slot_marker_changed.emit)
            section.marker_size_changed.connect(self.slot_marker_size_changed.emit)
            section.marker_edge_changed.connect(self.slot_marker_edge_changed.emit)
            section.marker_face_changed.connect(self.slot_marker_face_changed.emit)
            section.refresh_data_requested.connect(self.slot_refresh_data_requested.emit)
            section.refresh_style_requested.connect(self.slot_refresh_style_requested.emit)
            section.artifact_toggled.connect(self.slot_artifact_toggled.emit)
            section.artifact_show_requested.connect(self.slot_artifact_show_requested.emit)
            section.pinned_toggled.connect(self.slot_pinned_toggled.emit)
            section.reset_requested.connect(self.slot_reset_requested.emit)
            section.delete_requested.connect(self.slot_deleted.emit)
            self.curves_rows_lay.addWidget(section, 0, Qt.AlignTop)
            self._curve_sections.append(section)
            if id(slot) in expanded_slots:
                section.set_expanded(True)
        self.curves_rows_lay.addStretch()

    def _rebuild_annotations(self, panel: PanelSpec) -> None:
        while self.ann_lay.count():
            item = self.ann_lay.takeAt(0)
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

    def _on_label(self):
        if self._suppress or not self.panel_id:
            return
        text = self.label_edit.text().strip()
        self.panel_label_changed.emit(self.panel_id, text)

    def _on_geom(self, *_):
        if self._suppress or not self.panel_id:
            return
        self.panel_geometry_changed.emit(
            self.panel_id,
            float(self.x_spin.value()),
            float(self.y_spin.value()),
            float(self.w_spin.value()),
            float(self.h_spin.value()),
        )

    def _reset_geom(self):
        if not self.panel_id:
            return
        self.panel_geometry_changed.emit(self.panel_id, 30.0, 20.0, 60.0, 45.0)


class AddCurveInlinePanel(QWidget):
    curves_added = pyqtSignal(str, list)

    def __init__(self, panel_id: str, session_controller, parent=None):
        super().__init__(parent)
        self.panel_id = panel_id
        self.session_controller = session_controller
        self._connected_session = None
        self._connected_signals = []
        self._build_ui()
        self._reload_sessions()
        self.destroyed.connect(lambda *args: self._disconnect_session())

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Сессия:"))
        self.session_combo = QComboBox()
        self.session_combo.currentIndexChanged.connect(self._reload_series)
        row1.addWidget(self.session_combo, 1)
        layout.addLayout(row1)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Фильтр:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("поиск...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        row2.addWidget(self.filter_edit, 1)
        layout.addLayout(row2)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMaximumHeight(200)
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.list_widget)
        layout.addWidget(self.scroll)
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Добавить выбранные")
        self.add_btn.clicked.connect(self._on_add)
        self.cancel_btn = QPushButton("Отмена")
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
            self._connected_session = None
            self._connected_signals.clear()

    def _connect_session(self, sess):
        if sess is self._connected_session:
            return
        self._disconnect_session()
        if sess is None:
            return
        gm = getattr(sess, "graph_main", None)
        if gm is not None:
            sig_add = getattr(gm, "curve_added", None)
            if sig_add is not None:
                slot = lambda *args: self._reload_series()
                sig_add.connect(slot)
                self._connected_signals.append((sig_add, slot))
            sig_rem = getattr(gm, "curve_removed", None)
            if sig_rem is not None:
                slot = lambda *args: self._reload_series()
                sig_rem.connect(slot)
                self._connected_signals.append((sig_rem, slot))
        self._connected_session = sess

    def _reload_sessions(self):
        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        sessions = getattr(self.session_controller, "graph_sessions", {}) or {}
        for sid, sess in sessions.items():
            try:
                name = sess.session_name
            except Exception:
                name = sid
            self.session_combo.addItem(f"{sid}: {name}", sid)
        self.session_combo.blockSignals(False)
        self._reload_series()

    def _reload_series(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        sid = self.session_combo.currentData()
        if not sid:
            return
        sess = self.session_controller.graph_sessions.get(sid)
        if not sess:
            return
        self._connect_session(sess)
        gm = getattr(sess, "graph_main", None)
        if not gm:
            return
        curves = gm.get_curves()
        for root_name, curve in curves.items():
            name = getattr(curve, "curve_name", root_name)
            cb = QCheckBox(name)
            cb.setProperty("root_name", root_name)
            cb.setProperty("session_id", sid)
            self.list_layout.addWidget(cb)
        self.list_layout.addStretch()

    def _apply_filter(self, text):
        text = text.strip().lower()
        for i in range(self.list_layout.count()):
            item = self.list_layout.itemAt(i)
            w = item.widget()
            if isinstance(w, QCheckBox):
                w.setVisible(not text or text in w.text().lower())

    def _on_add(self):
        from ..model.session_ref import DataRef, DataSnapshot, StyleSnapshot
        selected = []
        for i in range(self.list_layout.count()):
            item = self.list_layout.itemAt(i)
            w = item.widget()
            if isinstance(w, QCheckBox) and w.isChecked():
                sid = w.property("session_id")
                root_name = w.property("root_name")
                if sid and root_name:
                    ref = DataRef(session_id=sid, series_root_name=root_name)
                    sess = self.session_controller.graph_sessions.get(sid)
                    if sess:
                        gm = getattr(sess, "graph_main", None)
                        if gm:
                            curve = gm.get_curve(root_name)
                            if curve:
                                ref.data = DataSnapshot.take(curve)
                                ref.style = StyleSnapshot.take(curve, None)
                                ref.refresh_policy = "snapshot"
                    selected.append(ref)
        if selected:
            self.curves_added.emit(self.panel_id, selected)
        self.hide()