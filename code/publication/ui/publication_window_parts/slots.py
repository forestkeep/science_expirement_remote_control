from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QTimer

from ...model.panel import CurveSlot
from ...model.session_ref import DataSnapshot, StyleSnapshot


class PublicationWidgetSlotsMixin:
    # ==================================================================
    # Слоты
    # ==================================================================
    def _on_slot_add_requested(self, panel_id: str):
        self._current_panel_id = panel_id
        self._import_session_to_panel()

    def _on_slot_color_clicked(self, idx: int) -> None:
		panel = self._current_panel()
		if panel is None or not (0 <= idx < len(panel.curves)):
			return
		from PyQt5.QtGui import QColor
		from common.color_picker import pick_color
		slot = panel.curves[idx]
		current = slot.style_overrides.get("line.color")
		if current is None:
			ls = getattr(getattr(slot.data_ref, "style", None), "line_style", None)
			current = getattr(ls, "color", "#1f77b4") if ls else "#1f77b4"

		def on_selected(c: QColor) -> None:
			slot.style_overrides["line.color"] = c.name()
			self._auto_pin_slot(slot)
			self._inspector_panel.set_panel(panel.id)
			self._schedule_render()

		pick_color(None, current, on_selected, self)

    def _on_slot_style_clicked(self, idx: int):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        from PyQt5.QtWidgets import QMenu
        from PyQt5.QtGui import QCursor
        slot = panel.curves[idx]
        current = slot.style_overrides.get("line.style", "Solid")
        menu = QMenu(self)
        for label, val in (("— solid", "Solid"), ("-- dash", "Dash"),
                           ("·· dot", "Dot"), ("-·- dashdot", "DashDot"),
                           ("-··- dashdotdot", "DashDotDot")):
            act = menu.addAction(("● " if val == current else "   ") + label)
            act.triggered.connect(
                lambda _c=False, v=val, s=slot: self._apply_slot_line_style(s, v))
        menu.exec_(QCursor.pos())

    def _apply_slot_line_style(self, slot, style_name: str):
        slot.style_overrides["line.style"] = style_name
        self._auto_pin_slot(slot)
        panel = self._current_panel()
        if panel is not None:
            self._inspector_panel.set_panel(panel.id)
        self._schedule_render()

    def _on_slot_width_changed(self, idx: int, value: float):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].style_overrides["line.width"] = float(value)
        self._schedule_render()

    def _on_slot_legend_changed(self, idx: int, text: str):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].legend_label = text
        self._refresh_tree()
        self._schedule_render()

    def _on_slot_axis_changed(self, idx: int, axis: str):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].axis = "y2" if axis == "y2" else "y1"
        self._refresh_tree()
        self._schedule_render()

    def _on_slot_reset_style(self, panel_id_or_idx, idx=None):
        """Сброс стиля слота.

        Вызывается:
          * из дерева: slot_reset_style(panel_id: str, idx: int);
          * из инспектора панели: slot_reset_clicked(idx: int).
        """
        if idx is None:
            panel_id = self._current_panel_id
            idx = int(panel_id_or_idx)
        else:
            panel_id = panel_id_or_idx

        panel = self.spec.find_panel(panel_id) if panel_id else None
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].style_overrides.clear()
        if self._current_panel_id == panel_id:
            self._inspector_panel.set_panel(panel_id)
        self._schedule_render()

    def _on_slot_removed(self, panel_id_or_idx, idx=None):
        """Удаление слота.

        Вызывается:
          * из дерева: slot_removed(panel_id: str, idx: int);
          * из инспектора панели: slot_deleted(idx: int).
        """
        if idx is None:
            panel_id = self._current_panel_id
            idx = int(panel_id_or_idx)
        else:
            panel_id = panel_id_or_idx

        panel = self.spec.find_panel(panel_id) if panel_id else None
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves.pop(idx)
        self._refresh_tree()
        if self._current_panel_id == panel_id:
            self._inspector_panel.set_panel(panel_id)
        self._schedule_render()

    def _on_slot_moved(self, from_panel_id, from_idx, to_panel_id, to_idx):
        src = self.spec.find_panel(from_panel_id)
        dst = self.spec.find_panel(to_panel_id)
        if src is None or dst is None or not (0 <= from_idx < len(src.curves)):
            return
        slot = src.curves.pop(from_idx)
        if to_idx is None or to_idx < 0:
            dst.curves.append(slot)
        else:
            dst.curves.insert(to_idx, slot)
        self._refresh_tree()
        self._schedule_render()

    # ==================================================================
    # Curve inspector
    # ==================================================================
    def _on_curve_visible(self, visible: bool):
        s = self._current_slot()
        if s is not None:
            s.visible = bool(visible)
            self._schedule_render()

    def _on_curve_axis(self, axis: str):
        s = self._current_slot()
        if s is not None:
            s.axis = "y2" if axis == "y2" else "y1"
            self._refresh_tree()
            self._schedule_render()

    def _on_curve_legend(self, text: str):
        s = self._current_slot()
        if s is not None:
            s.legend_label = text
            self._refresh_tree()
            self._schedule_render()

    def _on_curve_color(self, color: str):
        s = self._current_slot()
        if s is not None:
            s.style_overrides["line.color"] = color
            self._schedule_render()

    def _on_curve_marker_edge(self, color: str):
        s = self._current_slot()
        if s is not None:
            s.style_overrides["marker.edge"] = color
            self._schedule_render()

    def _on_curve_marker_face(self, color: str):
        s = self._current_slot()
        if s is not None:
            s.style_overrides["marker.face"] = color
            self._schedule_render()

    def _on_curve_line_style(self, style_name: str):
        s = self._current_slot()
        if s is not None:
            s.style_overrides["line.style"] = style_name
            self._schedule_render()

    def _on_curve_line_width(self, width: float):
        s = self._current_slot()
        if s is not None:
            s.style_overrides["line.width"] = float(width)
            self._schedule_render()

    def _on_curve_marker(self, marker: str):
        s = self._current_slot()
        if s is not None:
            s.style_overrides["marker.symbol"] = marker
            self._schedule_render()

    def _on_curve_marker_size(self, size: float):
        s = self._current_slot()
        if s is not None:
            s.style_overrides["marker.size"] = float(size)
            self._schedule_render()

    def _on_curve_refresh_data(self):
        s = self._current_slot()
        if s is None or s.data_ref is None:
            return
        sess, curve = self.data_loader._get_curve(
            s.data_ref.session_id, s.data_ref.series_root_name)
        if curve is not None:
            s.data_ref.data = DataSnapshot.take(curve)
            s.data_ref.stale_data = False
            self._inspector_curve.set_curve(self._current_panel(), self._current_slot_index)
            self._schedule_render()

    def _on_curve_refresh_style(self):
        """Обновить StyleSnapshot из живого источника.

        Overrides кривой НЕ сбрасываются — их сбрасывает отдельная кнопка ↺.
        Иначе невозможно «обновить стиль источника, сохранив мой цвет».
        """
        s = self._current_slot()
        if s is None or s.data_ref is None:
            return
        sess, curve = self.data_loader._get_curve(
            s.data_ref.session_id, s.data_ref.series_root_name)
        if curve is not None:
            s.data_ref.style = StyleSnapshot.take(
                curve, lambda c: self._artifacts_for_curve(c))
            s.data_ref.stale_style = False
            self._inspector_curve.set_curve(
                self._current_panel(), self._current_slot_index)
            self._schedule_render()

    def _on_curve_artifact_toggle(self, tool_id: str, checked: bool):
        p = self._current_panel()
        if p is not None:
            p.show_tools[tool_id] = bool(checked)
            self._schedule_render()

    def _on_curve_from_source(self, from_source: bool):
        s = self._current_slot()
        if s is None or s.data_ref is None:
            return

        if from_source:
            for key in list(s.style_overrides.keys()):
                if key != self._PIN_KEY:
                    s.style_overrides.pop(key, None)
        else:
            style = getattr(s.data_ref.style, "line_style", None)
            overrides = self._style_to_override_dict(style)
            for k, v in overrides.items():
                s.style_overrides.setdefault(k, v)

        self._inspector_curve.set_curve(
            self._current_panel(), self._current_slot_index
        )
        self._schedule_render()

    def _on_curve_artifact_show(self, tool_id: str):
        s = self._current_slot()
        if s is None:
            return
        s.style_overrides["__highlight_tool__"] = tool_id
        self._set_status_state(f"Показать артефакт: {tool_id}")
        self._schedule_render()

        def _clear():
            if s.style_overrides.get("__highlight_tool__") == tool_id:
                s.style_overrides.pop("__highlight_tool__", None)
                self._schedule_render()

        QTimer.singleShot(1500, _clear)