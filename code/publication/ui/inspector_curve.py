"""Состояние «Curve» — выделена кривая."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
	QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
	QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout,
	QWidget,
)


class CurveInspector(QWidget):
	visible_changed         = pyqtSignal(bool)
	axis_changed            = pyqtSignal(str)
	legend_label_changed    = pyqtSignal(str)
	from_source_toggled     = pyqtSignal(bool)
	color_changed           = pyqtSignal(str)
	line_style_changed      = pyqtSignal(str)
	line_width_changed      = pyqtSignal(float)
	marker_changed          = pyqtSignal(str)
	marker_size_changed     = pyqtSignal(float)
	marker_edge_changed     = pyqtSignal(str)
	marker_face_changed     = pyqtSignal(str)
	refresh_data_requested  = pyqtSignal()
	refresh_style_requested = pyqtSignal()
	artifact_toggled        = pyqtSignal(str, bool)
	artifact_show_requested = pyqtSignal(str)

	def __init__(self, parent=None):
		super().__init__(parent)
		self._suppress = False
		self._build_ui()

	def _build_ui(self):
		outer = QVBoxLayout(self)
		outer.setContentsMargins(0, 0, 0, 0)
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		body = QWidget()
		lay = QVBoxLayout(body)

		header = QHBoxLayout()
		self.title = QLabel("Кривая:")
		header.addWidget(self.title)
		self.reset_btn = QPushButton("↺")
		self.reset_btn.setToolTip("Сбросить все slot.style_overrides к StyleSnapshot")
		self.reset_btn.clicked.connect(self.refresh_style_requested.emit)
		header.addWidget(self.reset_btn)
		self.pin_btn = QPushButton("📌")
		self.pin_btn.setCheckable(True)
		self.pin_btn.setToolTip(
			"Закрепить все текущие slot.style_overrides — не сбрасываются "
			"кнопкой «Применить ко всем»"
		)
		header.addWidget(self.pin_btn)
		header.addStretch()
		lay.addLayout(header)

		ident = QGroupBox("Идентичность")
		ident_form = QFormLayout(ident)
		self.session_label = QLabel()
		self.session_label.setStyleSheet("color: #888;")
		ident_form.addRow("Сессия:", self.session_label)
		self.series_label = QLabel()
		self.series_label.setStyleSheet("color: #888;")
		ident_form.addRow("Серия:", self.series_label)
		self.axis_combo = QComboBox()
		self.axis_combo.addItems(["Y1", "Y2"])
		self.axis_combo.currentIndexChanged.connect(self._on_axis)
		ident_form.addRow("Ось:", self.axis_combo)
		self.visible_check = QCheckBox("видима")
		self.visible_check.stateChanged.connect(self._on_visible)
		ident_form.addRow(self.visible_check)
		self.legend_edit = QLineEdit()
		self.legend_edit.editingFinished.connect(self._on_legend)
		ident_form.addRow("подпись:", self.legend_edit)
		lay.addWidget(ident)

		style_box = QGroupBox("Стиль")
		style_form = QFormLayout(style_box)
		self.from_source_check = QCheckBox("из источника")
		self.from_source_check.setChecked(True)
		self.from_source_check.stateChanged.connect(self._on_from_source)
		self.from_source_check.stateChanged.connect(
			self._update_style_controls_enabled
		)
		style_form.addRow(self.from_source_check)

		self.color_btn = QPushButton()
		self.color_btn.clicked.connect(self._on_color_click)
		style_form.addRow("Цвет линии:", self.color_btn)

		self.link_marker_check = QCheckBox("Цвет маркера как у линии")
		self.link_marker_check.setChecked(True)
		self.link_marker_check.setToolTip(
			"Если включено, цвет маркера и заливки меняется вместе с цветом "
			"линии. Снимите, чтобы редактировать цвет контура и заливки "
			"маркера отдельно."
		)
		style_form.addRow(self.link_marker_check)

		self.marker_edge_btn = QPushButton()
		self.marker_edge_btn.clicked.connect(self._on_marker_edge_click)
		self._marker_edge_label = QLabel("Цвет маркера:")
		style_form.addRow(self._marker_edge_label, self.marker_edge_btn)

		self.marker_face_btn = QPushButton()
		self.marker_face_btn.clicked.connect(self._on_marker_face_click)
		self._marker_face_label = QLabel("Цвет заливки:")
		style_form.addRow(self._marker_face_label, self.marker_face_btn)

		self.line_style_combo = QComboBox()
		for text, val in (
			("solid", "Solid"), ("dash", "Dash"),
			("dot", "Dot"), ("dashdot", "DashDot"),
			("dashdotdot", "DashDotDot"),
		):
			self.line_style_combo.addItem(text, val)
		self.line_style_combo.currentIndexChanged.connect(self._on_line_style)
		style_form.addRow("Линия:", self.line_style_combo)
		self.width_spin = QDoubleSpinBox()
		self.width_spin.setRange(0.1, 20.0)
		self.width_spin.setSingleStep(0.25)
		self.width_spin.setSuffix(" pt")
		self.width_spin.valueChanged.connect(self._on_width)
		style_form.addRow("Толщина:", self.width_spin)
		self.marker_combo = QComboBox()
		for text, val in (
			("none", ""), ("circle", "o"), ("square", "s"),
			("triangle", "t1"), ("diamond", "d"), ("+", "+"),
		):
			self.marker_combo.addItem(text, val)
		self.marker_combo.currentIndexChanged.connect(self._on_marker)
		style_form.addRow("Маркер:", self.marker_combo)
		self.marker_size_spin = QDoubleSpinBox()
		self.marker_size_spin.setRange(0.0, 40.0)
		self.marker_size_spin.setSuffix(" px")
		self.marker_size_spin.valueChanged.connect(self._on_marker_size)
		style_form.addRow("Размер:", self.marker_size_spin)
		lay.addWidget(style_box)

		data_box = QGroupBox("Данные (snapshot)")
		data_lay = QVBoxLayout(data_box)
		self.data_info = QLabel()
		self.data_info.setStyleSheet("font-family: monospace; color: #666;")
		data_lay.addWidget(self.data_info)
		self.refresh_data_btn = QPushButton("Обновить из источника")
		self.refresh_data_btn.clicked.connect(self.refresh_data_requested.emit)
		data_lay.addWidget(self.refresh_data_btn)
		lay.addWidget(data_box)

		self.artifacts_box = QGroupBox("Артефакты анализа")
		self.artifacts_lay = QVBoxLayout(self.artifacts_box)
		lay.addWidget(self.artifacts_box)

		lay.addStretch()
		scroll.setWidget(body)
		outer.addWidget(scroll)

		# Подключаем сигнал link_marker_check ПОСЛЕ создания всех виджетов,
		# чтобы обработчик _apply_link_visibility не упал.
		self.link_marker_check.stateChanged.connect(self._on_link_marker_changed)

		self._apply_link_visibility()
		self._update_style_controls_enabled()

	# ------------------------------------------------------------------
	def _apply_link_visibility(self) -> None:
		linked = self.link_marker_check.isChecked()
		for w in (
			self.marker_edge_btn,
			self._marker_edge_label,
			self.marker_face_btn,
			self._marker_face_label,
		):
			w.setVisible(not linked)

	def _update_style_controls_enabled(self, *_):
		"""Контролы стиля доступны только когда снят «из источника»."""
		enabled = not self.from_source_check.isChecked()
		for w in (
			self.color_btn,
			self.link_marker_check,
			self.marker_edge_btn,
			self.marker_face_btn,
			self.line_style_combo,
			self.width_spin,
			self.marker_combo,
			self.marker_size_spin,
		):
			w.setEnabled(enabled)
		for w in (self._marker_edge_label, self._marker_face_label):
			w.setEnabled(enabled)

	def set_curve(self, panel, slot_index: int) -> None:
		if panel is None or slot_index >= len(panel.curves):
			return
		slot = panel.curves[slot_index]
		ref = slot.data_ref
		self._suppress = True
		try:
			self.session_label.setText(ref.session_id if ref else "—")
			self.series_label.setText(ref.series_root_name if ref else "—")
			self.axis_combo.setCurrentText("Y2" if slot.axis == "y2" else "Y1")
			self.visible_check.setChecked(slot.visible)
			self.legend_edit.setText(slot.legend_label or "")

			# ---- стиль берём из override, если есть, иначе из snapshot ----
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

			linked = (edge == color and face == color)
			self.link_marker_check.setChecked(linked)

			width = slot.style_overrides.get("line.width")
			if width is None and line_style is not None:
				width = getattr(line_style, "line_width", 1.0)
			try:
				self.width_spin.setValue(float(width or 1.0))
			except (TypeError, ValueError):
				self.width_spin.setValue(1.0)

			ls_name = slot.style_overrides.get("line.style")
			if ls_name is None and line_style is not None:
				from PyQt5.QtCore import Qt as _Qt
				_map = {
					_Qt.SolidLine: "Solid",
					_Qt.DashLine: "Dash",
					_Qt.DotLine: "Dot",
					_Qt.DashDotLine: "DashDot",
					_Qt.DashDotDotLine: "DashDotDot",
				}
				ls_name = _map.get(getattr(line_style, "line_style", None), "Solid")
			idx = self.line_style_combo.findData(str(ls_name or "Solid"))
			if idx >= 0:
				self.line_style_combo.setCurrentIndex(idx)

			sym = slot.style_overrides.get("marker.symbol")
			if sym is None and line_style is not None:
				sym = getattr(line_style, "symbol", None) or ""
			idx = self.marker_combo.findData(str(sym or ""))
			if idx >= 0:
				self.marker_combo.setCurrentIndex(idx)

			msize = slot.style_overrides.get("marker.size")
			if msize is None and line_style is not None:
				msize = getattr(line_style, "symbol_size", 5.0)
			try:
				self.marker_size_spin.setValue(float(msize or 5.0))
			except (TypeError, ValueError):
				self.marker_size_spin.setValue(5.0)

			# «из источника» = нет НЕ-pinned overrides
			PIN_KEY = "__pinned__"
			PIN_KEYS_KEY = "__pinned_keys__"
			real_ovr = [
				k for k in slot.style_overrides
				if k not in (PIN_KEY, PIN_KEYS_KEY)
			]
			self.from_source_check.setChecked(not real_ovr)
			self.pin_btn.setChecked(
				bool(slot.style_overrides.get(PIN_KEY))
				or bool(slot.style_overrides.get(PIN_KEYS_KEY))
			)

			# data snapshot
			snap = ref.data if ref is not None else None
			if snap is not None:
				n = len(getattr(snap, "x", []))
				fingerprint = getattr(snap, "fingerprint", "")[:12]
				self.data_info.setText(
					f"Точек: {n}\n"
					f"fingerprint: {fingerprint}…\n"
					f"взято: {getattr(snap, 'taken_at', '?')}"
				)
			else:
				self.data_info.setText("snapshot отсутствует")

			self._rebuild_artifacts(ref, panel)
		finally:
			self._suppress = False
		self._apply_link_visibility()
		self._update_style_controls_enabled()

	def _rebuild_artifacts(self, ref, panel):
		while self.artifacts_lay.count():
			item = self.artifacts_lay.takeAt(0)
			w = item.widget()
			if w is not None:
				w.deleteLater()

		style = getattr(ref, "style", None) if ref else None
		arts = list(getattr(style, "artifacts", []) or []) if style else []
		uncertainty = list(getattr(style, "uncertainty_records", []) or []) if style else []

		if not arts and not uncertainty:
			self.artifacts_box.setVisible(False)
			return

		self.artifacts_box.setVisible(True)

		for art in arts:
			tool_id = getattr(art, "tool_id", "")
			if not tool_id:
				continue
			row = QWidget()
			lay = QHBoxLayout(row)
			lay.setContentsMargins(0, 0, 0, 0)
			cb = QCheckBox(tool_id)
			cb.setChecked(bool(panel.show_tools.get(tool_id, False)))
			cb.stateChanged.connect(
				lambda st, t=tool_id: self.artifact_toggled.emit(t, st != 0)
			)
			lay.addWidget(cb, 1)
			show_btn = QPushButton("показать")
			show_btn.clicked.connect(
				lambda _c=False, t=tool_id: self.artifact_show_requested.emit(t)
			)
			lay.addWidget(show_btn)
			self.artifacts_lay.addWidget(row)

		if uncertainty:
			rec = uncertainty[0]
			method = str(getattr(rec, "method", "std"))
			n = len(getattr(rec, "y_err", []) or [])
			text = f"uncertainty.estimate  ({method}, N={n})"
			row = QWidget()
			lay = QHBoxLayout(row)
			lay.setContentsMargins(0, 0, 0, 0)
			cb = QCheckBox(text)
			cb.setChecked(bool(panel.show_tools.get("uncertainty.estimate", False)))
			cb.stateChanged.connect(
				lambda st: self.artifact_toggled.emit("uncertainty.estimate", st != 0)
			)
			lay.addWidget(cb, 1)
			show_btn = QPushButton("показать")
			show_btn.clicked.connect(
				lambda _c=False: self.artifact_show_requested.emit(
					"uncertainty.estimate"
				)
			)
			lay.addWidget(show_btn)
			self.artifacts_lay.addWidget(row)

	# ------------------------------------------------------------------
	def _set_color_btn(self, color: str):
		self.color_btn.setText(color)
		self.color_btn.setStyleSheet(f"background-color: {color}; padding: 2px;")

	def _set_marker_edge_btn(self, color: str):
		self.marker_edge_btn.setText(color)
		self.marker_edge_btn.setStyleSheet(
			f"background-color: {color}; padding: 2px;"
		)

	def _set_marker_face_btn(self, color: str):
		self.marker_face_btn.setText(color)
		self.marker_face_btn.setStyleSheet(
			f"background-color: {color}; padding: 2px;"
		)

	def _on_visible(self, st):
		if not self._suppress:
			self.visible_changed.emit(st != 0)

	def _on_axis(self, _idx):
		if not self._suppress:
			self.axis_changed.emit(self.axis_combo.currentText().lower())

	def _on_legend(self):
		if not self._suppress:
			self.legend_label_changed.emit(self.legend_edit.text())

	def _on_from_source(self, st):
		if not self._suppress:
			self.from_source_toggled.emit(st != 0)

	def _on_link_marker_changed(self, st):
		# Видимость контролов переключаем всегда, даже при программной установке.
		self._apply_link_visibility()
		if self._suppress:
			return
		if st != 0:
			# Синхронизировать цвета маркеров с текущим цветом линии.
			color = self.color_btn.text() or "#1f77b4"
			self._set_marker_edge_btn(color)
			self._set_marker_face_btn(color)
			self.marker_edge_changed.emit(color)
			self.marker_face_changed.emit(color)

	def _on_color_click(self):
		from PyQt5.QtGui import QColor
		from common.color_picker import pick_color
		current = self.color_btn.text() or "#1f77b4"
		def on_selected(c: QColor) -> None:
			color = c.name()
			self._set_color_btn(color)
			self.color_changed.emit(color)
			if self.link_marker_check.isChecked():
				self._set_marker_edge_btn(color)
				self._set_marker_face_btn(color)
				self.marker_edge_changed.emit(color)
				self.marker_face_changed.emit(color)
		pick_color(self.color_btn, current, on_selected, self)

	def _on_marker_edge_click(self):
		from PyQt5.QtGui import QColor
		from common.color_picker import pick_color
		current = self.marker_edge_btn.text() or "#1f77b4"
		def on_selected(c: QColor) -> None:
			self._set_marker_edge_btn(c.name())
			self.marker_edge_changed.emit(c.name())
		pick_color(self.marker_edge_btn, current, on_selected, self)

	def _on_marker_face_click(self):
		from PyQt5.QtGui import QColor
		from common.color_picker import pick_color
		current = self.marker_face_btn.text() or "#1f77b4"
		def on_selected(c: QColor) -> None:
			self._set_marker_face_btn(c.name())
			self.marker_face_changed.emit(c.name())
		pick_color(self.marker_face_btn, current, on_selected, self)

	def _on_line_style(self, _idx):
		if not self._suppress:
			self.line_style_changed.emit(
				self.line_style_combo.currentData() or "Solid"
			)

	def _on_width(self, v):
		if not self._suppress:
			self.line_width_changed.emit(float(v))

	def _on_marker(self, _idx):
		if not self._suppress:
			self.marker_changed.emit(self.marker_combo.currentData() or "")

	def _on_marker_size(self, v):
		if not self._suppress:
			self.marker_size_changed.emit(float(v))