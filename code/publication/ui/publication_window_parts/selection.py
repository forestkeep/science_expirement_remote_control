from __future__ import annotations


class PublicationWidgetSelectionMixin:
    def _on_figure_selected(self):
        self._current_panel_id = None
        self._current_slot_index = -1
        self._current_ann_id = None
        self._canvas.set_selected_panels([])
        self._inspector_stack.setCurrentWidget(self._inspector_figure)
        self._inspector_figure.update_from_spec(
            self.spec, self.preset, self.style_stack
        )

    def _on_panel_selected(self, panel_id: str):
        if not panel_id:
            self._on_figure_selected()
            return
        self._current_panel_id = panel_id
        self._current_slot_index = -1
        self._current_ann_id = None
        self._canvas.set_selected_panels([panel_id])
        self._inspector_stack.setCurrentWidget(self._inspector_panel)
        self._inspector_panel.set_panel(panel_id)

    def _on_canvas_panel_selected(self, panel_id: str, additive: bool):
        self._on_panel_selected(panel_id)

    def _on_canvas_selection_cleared(self):
        self._on_figure_selected()

    def _on_canvas_drag_finished(self):
        """Drag/resize завершён: рендерим немедленно, без 400 мс дебаунса.

        Во время самого drag-а canvas рисует только кэшированную фигуру +
        dashed-рамку, поэтому перетаскивание остаётся плавным. Полный
        matplotlib-render нужен только по завершении — именно его мы
        запускаем сразу, чтобы пользователь не видел задержку в 400 мс.
        """
        if self._debounce_timer.isActive():
            self._debounce_timer.stop()
        self._render_now()

    def _on_slot_selected(self, panel_id: str, idx: int):
        self._current_panel_id = panel_id
        self._current_slot_index = idx
        self._current_ann_id = None
        self._canvas.set_selected_panels([panel_id])
        self._inspector_stack.setCurrentWidget(self._inspector_curve)
        panel = self.spec.find_panel(panel_id)
        if panel is not None and 0 <= idx < len(panel.curves):
            self._inspector_curve.set_curve(panel, idx)

    def _on_annotation_selected(self, ann_id: str):
        self._current_panel_id = None
        self._current_slot_index = -1
        self._current_ann_id = ann_id
        self._canvas.set_selected_panels([])
        self._inspector_stack.setCurrentWidget(self._inspector_annotation)
        self._inspector_annotation.set_annotation(ann_id)

    # ==================================================================
    # Панель: геометрия / label / прочее
    # ==================================================================
    def _on_panel_geometry_changed(self, panel_id, x, y, w, h):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        p.x_mm, p.y_mm, p.w_mm, p.h_mm = x, y, w, h
        self._schedule_render()

    def _on_panel_label_changed(self, panel_id: str, text: str):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        text = (text or "").strip()
        if text:
            p.style_overrides["panel.label"] = text
        else:
            p.style_overrides.pop("panel.label", None)
        self._refresh_tree()

    def _on_panel_reset_all(self, panel_id: str):
        p = self.spec.find_panel(panel_id)
        if p is not None:
            p.style_overrides.clear()
            for slot in p.curves:
                slot.style_overrides.clear()
        self._inspector_panel.set_panel(panel_id)
        self._schedule_render()

    def _on_panel_axis_visibility(self, panel_id, axis, visible):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        if axis == "y2":
            p.y2_visible = bool(visible)
        p.style_overrides[f"axis.{axis}.visible"] = bool(visible)
        self._schedule_render()

    def _on_panel_axis_linked(self, panel_id, axis, other_panel_id):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return

        p.style_overrides[f"axis.{axis}.linked"] = other_panel_id or ""

        if other_panel_id:
            src = self.spec.find_panel(other_panel_id)
            if src is not None:
                rng = {
                    "x": src.x_range,
                    "y1": src.y_range,
                    "y2": src.y2_range,
                }.get(axis)
                self._set_axis_range(p, axis, rng)
                self._propagate_axis_link(other_panel_id, axis, rng)
        else:
            # при отвязке оставляем текущий диапазон как есть
            pass

        if self._current_panel_id == panel_id:
            self._inspector_panel.set_panel(panel_id)
        self._schedule_render()

    def _on_panel_axis_label(self, panel_id, axis, text):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        if axis == "x":
            p.x_label = text
        elif axis == "y1":
            p.y_label = text
        elif axis == "y2":
            p.y2_label = text
        self._schedule_render()

    def _on_panel_axis_range(self, panel_id, axis, lo, hi):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        rng = (lo, hi)
        self._set_axis_range(p, axis, rng)
        self._propagate_axis_link(panel_id, axis, rng)
        self._schedule_render()

    def _on_panel_axis_auto(self, panel_id, axis, is_auto):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        if is_auto:
            self._set_axis_range(p, axis, None)
            self._propagate_axis_link(panel_id, axis, None)
        self._schedule_render()

    def _on_panel_axis_log(self, panel_id, axis, is_log):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        if axis == "x":
            p.x_log = is_log
        elif axis == "y1":
            p.y_log = is_log
        elif axis == "y2":
            p.y2_log = is_log
        self._schedule_render()

    def _on_panel_y2_toggled(self, panel_id: str, state: bool):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        p.y2_visible = bool(state)
        if not state:
            # При выключении Y2 все слоты переключаются на Y1
            for slot in p.curves:
                if slot.axis == "y2":
                    slot.axis = "y1"
        self._schedule_render()
        if self._current_panel_id == panel_id:
            self._inspector_panel.set_panel(panel_id)

    # ==================================================================
    # Легенда / оси (уровень панели)
    # ==================================================================
    def _on_legend_mode(self, mode: str):
        p = self._current_panel()
        if p is None:
            return

        # Удаляем старые legend.* с обоих уровней, сохраняя только pinned-флаг.
        for k in list(p.style_overrides.keys()):
            if k.startswith("legend.") and k != "legend.pinned":
                p.style_overrides.pop(k, None)
        for k in list(self.spec.figure_overrides.keys()):
            if k.startswith("legend."):
                self.spec.figure_overrides.pop(k, None)

        p.style_overrides["legend.mode"] = mode

        if mode == "figure":
            self.spec.figure_overrides["legend.mode"] = "figure"
            self.spec.figure_overrides["legend.enabled"] = bool(
                p.style_overrides.get("legend.enabled", True)
            )
        elif mode == "inline":
            p.style_overrides["legend.inline_pos"] = p.style_overrides.get(
                "legend.pos", "best"
            )
        else:  # panel
            p.style_overrides["legend.pos"] = p.style_overrides.get(
                "legend.pos", "best"
            )

        self._schedule_render()

    def _on_legend_pos(self, pos: str):
        p = self._current_panel()
        if p is None:
            return
        p.style_overrides["legend.pos"] = pos
        self._schedule_render()

    def _on_legend_visible(self, visible: bool):
        p = self._current_panel()
        if p is None:
            return
        p.style_overrides["legend.enabled"] = bool(visible)
        self._schedule_render()

    # ==================================================================
    # Figure inspector
    # ==================================================================
    def _on_figure_size_changed(self, w: float, h: float):
        self.spec.width_mm = float(w)
        self.spec.height_mm = float(h)
        if self._zoom_btn.isChecked():
            self._canvas.set_real_size(True)
        self._schedule_render()