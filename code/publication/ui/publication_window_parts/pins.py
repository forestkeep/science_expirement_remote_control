from __future__ import annotations

from PyQt5.QtCore import Qt


class PublicationWidgetPinsMixin:
    _PIN_KEY = "__pinned__"
    _PIN_KEYS_KEY = "__pinned_keys__"

    @classmethod
    def _dict_pinned_keys(cls, d: dict) -> set:
        """Множество ключей, реально закреплённых в дайле.

        Приоритет: ``__pinned_keys__`` (новый формат — точечное закрепление).
        Fallback: ``__pinned__`` (legacy — «закреплён весь дайл»).
        """
        if not isinstance(d, dict):
            return set()
        raw = d.get(cls._PIN_KEYS_KEY)
        if isinstance(raw, (list, tuple, set, frozenset)):
            return set(raw)
        if d.get(cls._PIN_KEY):
            return {k for k in d.keys()
                    if k not in (cls._PIN_KEY, cls._PIN_KEYS_KEY)}
        return set()

    @classmethod
    def _strip_unpinned(cls, d: dict, preserve_prefixes=()) -> None:
        """Удалить все ключи, кроме закреплённых и разрешённых префиксов.

        Закрепление — **по-ключевое** (см. ``__pinned_keys__``): если панель
        была закреплена с одним набором overrides, а пользователь потом
        добавил новые — при «Применить ко всем» новые сбрасываются,
        закреплённые сохраняются. Это соответствует ТЗ:
        «📌 Закрепить все *текущие* overrides».
        """
        if not isinstance(d, dict):
            return
        pinned = cls._dict_pinned_keys(d)
        prefixes = tuple(preserve_prefixes or ())
        for key in list(d.keys()):
            if key in (cls._PIN_KEY, cls._PIN_KEYS_KEY):
                continue
            if key in pinned:
                continue
            if prefixes and any(key.startswith(p) for p in prefixes):
                continue
            d.pop(key, None)
        # если после очистки не осталось ни одного «настоящего» ключа,
        # но остались pinned-маркеры — их тоже убираем, чтобы не
        # показывать «● закреплена» на пустой панели.
        real = [k for k in d.keys()
                if k not in (cls._PIN_KEY, cls._PIN_KEYS_KEY)]
        if not real:
            d.pop(cls._PIN_KEY, None)
            d.pop(cls._PIN_KEYS_KEY, None)

    @staticmethod
    def _style_to_override_dict(style) -> dict:
        if style is None:
            return {}
        names = {
            Qt.SolidLine: "Solid",
            Qt.DashLine: "Dash",
            Qt.DotLine: "Dot",
            Qt.DashDotLine: "DashDot",
            Qt.DashDotDotLine: "DashDotDot",
        }
        return {
            "line.color": str(getattr(style, "color", "#1f77b4")),
            "line.style": names.get(getattr(style, "line_style", None), "Solid"),
            "line.width": float(getattr(style, "line_width", 1.0)),
            "marker.symbol": getattr(style, "symbol", None) or "",
            "marker.size": float(getattr(style, "symbol_size", 5.0)),
            "marker.edge": str(getattr(style, "symbol_color", "#ffffff")),
            "marker.face": str(getattr(style, "fill_color", "#ffffff")),
        }

    @staticmethod
    def _set_axis_range(panel, axis: str, rng) -> None:
        if axis == "x":
            panel.x_range = rng
        elif axis == "y1":
            panel.y_range = rng
        elif axis == "y2":
            panel.y2_range = rng

    def _propagate_axis_link(self, source_panel_id: str, axis: str, rng) -> None:
        """Скопировать диапазон во все панели, связанные с source_panel_id."""
        for p in self.spec.panels:
            if p.id == source_panel_id:
                continue
            if p.style_overrides.get(f"axis.{axis}.linked") == source_panel_id:
                self._set_axis_range(p, axis, rng)

    def _on_apply_to_all(self):
        # figure: сбрасываем всё, кроме pinned
        self._strip_unpinned(self.spec.figure_overrides)

        for panel in self.spec.panels:
            legend_pinned = bool(panel.style_overrides.get("legend.pinned", False))
            preserve = ("legend.",) if legend_pinned else ()
            self._strip_unpinned(panel.style_overrides, preserve_prefixes=preserve)

            for slot in panel.curves:
                self._strip_unpinned(slot.style_overrides)

        self._inspector_figure.update_from_spec(
            self.spec, self.preset, self.style_stack
        )
        if self._current_panel_id:
            self._inspector_panel.set_panel(self._current_panel_id)
        self._refresh_tree()
        self._schedule_render()
        self._set_status_state("Применено ко всем (📌 сохранены)")

    def _auto_pin_slot(self, slot) -> None:
        """Авто-📌: добавить текущий набор override-ключей в pinned."""
        real = [k for k in slot.style_overrides.keys()
                if k not in (self._PIN_KEY, self._PIN_KEYS_KEY)]
        pinned = set(slot.style_overrides.get(self._PIN_KEYS_KEY, set()))
        pinned.update(real)
        slot.style_overrides[self._PIN_KEYS_KEY] = list(pinned)
        slot.style_overrides[self._PIN_KEY] = True

    def _on_panel_pinned(self, panel_id: str, pinned: bool):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        if pinned:
            snapshot = [k for k in p.style_overrides.keys()
                        if k not in (self._PIN_KEY, self._PIN_KEYS_KEY)]
            p.style_overrides[self._PIN_KEYS_KEY] = snapshot
            p.style_overrides[self._PIN_KEY] = True
        else:
            p.style_overrides.pop(self._PIN_KEYS_KEY, None)
            p.style_overrides.pop(self._PIN_KEY, None)
        self._refresh_tree()
        self._schedule_render()

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

    def _on_legend_pinned(self, pinned: bool):
        p = self._current_panel()
        if p is None:
            return
        if pinned:
            p.style_overrides["legend.pinned"] = True
        else:
            p.style_overrides.pop("legend.pinned", None)
        self._refresh_tree()
        self._schedule_render()