from __future__ import annotations
from typing import Optional
from PyQt5.QtCore import QTimer
from ...model.panel import CurveSlot
from ...model.session_ref import DataSnapshot, StyleSnapshot


class PublicationWidgetSlotsMixin:
    def _on_slot_add_requested(self, panel_id: str):
        self._current_panel_id = panel_id
        self._import_session_to_panel()

    def _on_slot_visible_changed(self, idx: int, visible: bool):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].visible = bool(visible)
        self._schedule_render()

    def _on_slot_from_source_toggled(self, idx: int, from_source: bool):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        slot = panel.curves[idx]
        if slot.data_ref is None:
            return
        if from_source:
            for key in list(slot.style_overrides.keys()):
                if key not in (self._PIN_KEY, self._PIN_KEYS_KEY):
                    slot.style_overrides.pop(key, None)
        else:
            style = getattr(slot.data_ref.style, "line_style", None)
            overrides = self._style_to_override_dict(style)
            for k, v in overrides.items():
                slot.style_overrides.setdefault(k, v)
            if self._inspector_panel.get_link_state(slot):
                color = slot.style_overrides.get("line.color")
                if color:
                    slot.style_overrides["marker.edge"] = color
                    slot.style_overrides["marker.face"] = color
        self._schedule_render()

    def _on_slot_color_changed(self, idx: int, color: str):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].style_overrides["line.color"] = str(color)
        self._schedule_render()

    def _on_slot_line_style_changed(self, idx: int, style_name: str):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].style_overrides["line.style"] = str(style_name)
        self._schedule_render()

    def _on_slot_width_changed(self, idx: int, value: float):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].style_overrides["line.width"] = float(value)
        self._schedule_render()

    def _on_slot_marker_changed(self, idx: int, marker: str):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].style_overrides["marker.symbol"] = str(marker)
        self._schedule_render()

    def _on_slot_marker_size_changed(self, idx: int, size: float):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].style_overrides["marker.size"] = float(size)
        self._schedule_render()

    def _on_slot_marker_edge_changed(self, idx: int, color: str):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].style_overrides["marker.edge"] = str(color)
        self._schedule_render()

    def _on_slot_marker_face_changed(self, idx: int, color: str):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].style_overrides["marker.face"] = str(color)
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

    def _on_slot_refresh_data_requested(self, idx: int):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        slot = panel.curves[idx]
        if slot.data_ref is None or slot.data_ref.is_empty():
            return
        sess, curve = self.data_loader._get_curve(slot.data_ref.session_id, slot.data_ref.series_root_name)
        if curve is not None:
            slot.data_ref.data = DataSnapshot.take(curve)
            slot.data_ref.stale_data = False
            self._schedule_render()

    def _on_slot_refresh_style_requested(self, idx: int):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        slot = panel.curves[idx]
        if slot.data_ref is None or slot.data_ref.is_empty():
            return
        sess, curve = self.data_loader._get_curve(slot.data_ref.session_id, slot.data_ref.series_root_name)
        if curve is not None:
            slot.data_ref.style = StyleSnapshot.take(curve, lambda c: self._artifacts_for_curve(c))
            slot.data_ref.stale_style = False
            self._schedule_render()

    def _on_slot_artifact_toggled(self, idx: int, tool_id: str, checked: bool):
        panel = self._current_panel()
        if panel is None:
            return
        panel.show_tools[tool_id] = bool(checked)
        self._schedule_render()

    def _on_slot_artifact_show_requested(self, idx: int, tool_id: str):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        slot = panel.curves[idx]
        slot.style_overrides["__highlight_tool__"] = str(tool_id)
        self._set_status_state(f"Показать артефакт: {tool_id}")
        self._schedule_render()

        def _clear():
            if slot.style_overrides.get("__highlight_tool__") == tool_id:
                slot.style_overrides.pop("__highlight_tool__", None)
                self._schedule_render()

        QTimer.singleShot(1500, _clear)

    def _on_slot_pinned(self, idx: int, pinned: bool):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        slot = panel.curves[idx]
        if pinned:
            snapshot = [k for k in slot.style_overrides.keys()
                        if k not in (self._PIN_KEY, self._PIN_KEYS_KEY)]
            slot.style_overrides[self._PIN_KEYS_KEY] = snapshot
            slot.style_overrides[self._PIN_KEY] = True
        else:
            slot.style_overrides.pop(self._PIN_KEYS_KEY, None)
            slot.style_overrides.pop(self._PIN_KEY, None)
        self._refresh_tree()
        self._schedule_render()

    def _on_slot_reset_requested(self, idx: int):
        panel = self._current_panel()
        if panel is None or not (0 <= idx < len(panel.curves)):
            return
        panel.curves[idx].style_overrides.clear()
        self._refresh_tree()
        self._schedule_render()

    def _on_slot_reset_style(self, panel_id_or_idx, idx=None):
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
        sess, curve = self.data_loader._get_curve(s.data_ref.session_id, s.data_ref.series_root_name)
        if curve is not None:
            s.data_ref.data = DataSnapshot.take(curve)
            s.data_ref.stale_data = False
            self._inspector_curve.set_curve(self._current_panel(), self._current_slot_index)
            self._schedule_render()

    def _on_curve_refresh_style(self):
        s = self._current_slot()
        if s is None or s.data_ref is None:
            return
        sess, curve = self.data_loader._get_curve(s.data_ref.session_id, s.data_ref.series_root_name)
        if curve is not None:
            s.data_ref.style = StyleSnapshot.take(curve, lambda c: self._artifacts_for_curve(c))
            s.data_ref.stale_style = False
            self._inspector_curve.set_curve(self._current_panel(), self._current_slot_index)
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
                if key not in (self._PIN_KEY, self._PIN_KEYS_KEY):
                    s.style_overrides.pop(key, None)
        else:
            style = getattr(s.data_ref.style, "line_style", None)
            overrides = self._style_to_override_dict(style)
            for k, v in overrides.items():
                s.style_overrides.setdefault(k, v)
        self._inspector_curve.set_curve(self._current_panel(), self._current_slot_index)
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