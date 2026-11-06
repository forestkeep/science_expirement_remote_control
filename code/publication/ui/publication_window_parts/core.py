from __future__ import annotations

import logging
import time
from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QSplitter, QStackedWidget, QVBoxLayout, QWidget,
)

from ...bus.source_bus import SourceBus
from ...bus.session_loader import SessionDataLoader
from ...model.figure_model import FigureSpec
from ...model.panel import CurveSlot, PanelSpec
from ...model.stylestack import StyleStack
from ...presets.builtin import (
    SAFE_DEFAULTS, STYLE_PROFILES, list_style_profiles,
)
from ...presets.loader import (
    list_journal_presets, load_journal_preset,
    load_lab_profile_auto, load_style_profile_by_id,
)
from ...presets.journal_preset import JournalPresetStore
from ...renderers.mpl_renderer import MatplotlibRenderer
from ..canvas import PublicationCanvas
from ..tree_view import FigureTree
from ..inspector_figure import FigureInspector as FigureStateInspector
from ..inspector_panel import PanelInspector
from ..inspector_curve import CurveInspector
from ..inspector_annotation import AnnotationInspector

logger = logging.getLogger(__name__)

SPLIT_TREE_W = 240
SPLIT_INSPECTOR_W = 340
DEBOUNCE_MS = 400


class PublicationWidgetCoreMixin:
    DEBOUNCE_MS = DEBOUNCE_MS

    def __init__(self, session_controller, spec: FigureSpec = None, parent=None):
        super().__init__(parent)
        self.session_controller = session_controller
        self._created_new = spec is None
        self.spec: FigureSpec = spec or FigureSpec(id="fig_0001")
        self.preset_store = JournalPresetStore()
        self.preset = None
        self.style_stack: Optional[StyleStack] = None
        self.renderer = MatplotlibRenderer()
        self.data_loader = SessionDataLoader(session_controller, artifacts_provider=self._artifacts_for_curve)
        self.source_bus = SourceBus(session_controller, parent=self)
        self.source_bus.source_changed.connect(self._schedule_render)
        self.source_bus.artifacts_changed.connect(self._schedule_render)
        self.source_bus.sessions_changed.connect(self._schedule_render)
        self._render_generation = 0
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._render_now)
        self._current_panel_id: Optional[str] = None
        self._current_slot_index: int = -1
        self._current_ann_id: Optional[str] = None
        self._last_validation = None
        self._last_render_ms: float = 0.0
        self._build_ui()
        self._load_journal(self.spec.journal_preset_id or "nature_double")
        self._load_style(self.spec.style_profile_id or "okabe_ito")
        initial_panel_id = None
        if self._created_new and not self.spec.panels:
            initial_panel_id = self._add_initial_panel()
        self._refresh_tree()
        self._refresh_counters()
        if initial_panel_id:
            self._on_panel_selected(initial_panel_id)
        self._render_now()

    def _add_initial_panel(self) -> Optional[str]:
        panel = self.spec.add_panel(x_mm=5.0, y_mm=5.0, w_mm=60.0, h_mm=45.0)
        return panel.id
    # ==================================================================
    # UI
    # ==================================================================
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_toolbar())
        splitter = QSplitter(Qt.Horizontal)
        self._tree = FigureTree()
        self._tree.setMinimumWidth(SPLIT_TREE_W)
        splitter.addWidget(self._tree)
        self._canvas = PublicationCanvas()
        self._canvas.set_spec(self.spec)
        splitter.addWidget(self._canvas)
        self._inspector_stack = QStackedWidget()
        self._inspector_stack.setMinimumWidth(SPLIT_INSPECTOR_W)
        self._inspector_figure = FigureStateInspector(self.spec, None, None)
        self._inspector_panel = PanelInspector(self.spec)
        self._inspector_panel.session_controller = self.session_controller
        self._inspector_panel.curves_added.connect(self._on_curves_added)
        self._inspector_curve = CurveInspector()
        self._inspector_annotation = AnnotationInspector(self.spec)
        self._inspector_stack.addWidget(self._inspector_figure)
        self._inspector_stack.addWidget(self._inspector_panel)
        self._inspector_stack.addWidget(self._inspector_curve)
        self._inspector_stack.addWidget(self._inspector_annotation)
        splitter.addWidget(self._inspector_stack)
        splitter.setSizes([SPLIT_TREE_W, 900, SPLIT_INSPECTOR_W])
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter, 1)
        outer.addWidget(self._build_status())
        self._canvas.panel_geometry_changed.connect(self._on_panel_geometry_changed)
        self._canvas.panel_selected.connect(self._on_canvas_panel_selected)
        self._canvas.selection_cleared.connect(self._on_canvas_selection_cleared)
        self._canvas.annotation_selected.connect(self._on_annotation_selected)
        self._canvas.annotation_geometry_changed.connect(self._on_annotation_geometry_changed)
        self._canvas.annotation_delete_requested.connect(self._on_annotation_delete)
        self._canvas.annotation_properties.connect(self._on_annotation_edit)
        self._canvas.refresh_data_requested.connect(self._on_refresh_data_requested)
        self._canvas.refresh_style_requested.connect(self._on_refresh_style_requested)
        self._canvas.enable_live_requested.connect(self._on_enable_live_requested)
        self._canvas.add_panel_requested.connect(self._add_panel)
        self._canvas.add_text_requested.connect(lambda: self._on_annotation_create("text"))
        self._canvas.add_arrow_requested.connect(lambda: self._on_annotation_create("arrow"))
        self._canvas.add_scale_bar_requested.connect(lambda: self._on_annotation_create("scale_bar"))
        self._canvas.add_bracket_requested.connect(lambda: self._on_annotation_create("bracket"))
        self._canvas.apply_layout_requested.connect(self._on_apply_layout)
        self._canvas.delete_panel_requested.connect(self._delete_panel)
        self._canvas.drag_finished.connect(self._on_canvas_drag_finished)
        self._canvas.spec_changed.connect(self._on_canvas_spec_changed)
        self._tree.figure_selected.connect(self._on_figure_selected)
        self._tree.panel_selected.connect(self._on_panel_selected)
        self._tree.slot_selected.connect(self._on_slot_selected)
        self._tree.annotation_selected.connect(self._on_annotation_selected)
        self._tree.panel_label_changed.connect(self._on_panel_label_changed)
        self._tree.panel_removed.connect(self._delete_panel)
        self._tree.panel_duplicated.connect(self._on_panel_duplicate)
        self._tree.panel_export_requested.connect(self._on_panel_export)
        self._tree.slot_removed.connect(self._on_slot_removed)
        self._tree.slot_reset_style.connect(self._on_slot_reset_style)
        self._tree.annotation_removed.connect(self._on_annotation_delete)
        self._tree.annotation_properties.connect(self._on_annotation_edit)
        self._tree.panel_reordered.connect(self._on_panel_reordered)
        self._tree.slot_moved.connect(self._on_slot_moved)
        self._inspector_panel.panel_label_changed.connect(self._on_panel_label_changed)
        self._inspector_panel.panel_reset_all.connect(self._on_panel_reset_all)
        self._inspector_panel.panel_pinned_toggled.connect(self._on_panel_pinned)
        self._inspector_panel.panel_geometry_changed.connect(self._on_panel_geometry_changed)
        self._inspector_panel.panel_axis_visibility.connect(self._on_panel_axis_visibility)
        self._inspector_panel.panel_axis_linked.connect(self._on_panel_axis_linked)
        self._inspector_panel.panel_axis_label.connect(self._on_panel_axis_label)
        self._inspector_panel.panel_axis_range.connect(self._on_panel_axis_range)
        self._inspector_panel.panel_axis_auto.connect(self._on_panel_axis_auto)
        self._inspector_panel.panel_axis_log.connect(self._on_panel_axis_log)
        self._inspector_panel.panel_y2_toggled.connect(self._on_panel_y2_toggled)
        self._inspector_panel.slot_add_requested.connect(self._on_slot_add_requested)
        self._inspector_panel.slot_visible_changed.connect(self._on_slot_visible_changed)
        self._inspector_panel.slot_axis_changed.connect(self._on_slot_axis_changed)
        self._inspector_panel.slot_legend_changed.connect(self._on_slot_legend_changed)
        self._inspector_panel.slot_from_source_toggled.connect(self._on_slot_from_source_toggled)
        self._inspector_panel.slot_color_changed.connect(self._on_slot_color_changed)
        self._inspector_panel.slot_line_style_changed.connect(self._on_slot_line_style_changed)
        self._inspector_panel.slot_width_changed.connect(self._on_slot_width_changed)
        self._inspector_panel.slot_marker_changed.connect(self._on_slot_marker_changed)
        self._inspector_panel.slot_marker_size_changed.connect(self._on_slot_marker_size_changed)
        self._inspector_panel.slot_marker_edge_changed.connect(self._on_slot_marker_edge_changed)
        self._inspector_panel.slot_marker_face_changed.connect(self._on_slot_marker_face_changed)
        self._inspector_panel.slot_refresh_data_requested.connect(self._on_slot_refresh_data_requested)
        self._inspector_panel.slot_refresh_style_requested.connect(self._on_slot_refresh_style_requested)
        self._inspector_panel.slot_artifact_toggled.connect(self._on_slot_artifact_toggled)
        self._inspector_panel.slot_artifact_show_requested.connect(self._on_slot_artifact_show_requested)
        self._inspector_panel.slot_pinned_toggled.connect(self._on_slot_pinned)
        self._inspector_panel.slot_reset_requested.connect(self._on_slot_reset_requested)
        self._inspector_panel.slot_deleted.connect(self._on_slot_removed)
        self._inspector_panel.legend_mode_changed.connect(self._on_legend_mode)
        self._inspector_panel.legend_position_changed.connect(self._on_legend_pos)
        self._inspector_panel.legend_visible_changed.connect(self._on_legend_visible)
        self._inspector_panel.legend_pinned_toggled.connect(self._on_legend_pinned)
        self._inspector_panel.annotation_create.connect(self._on_annotation_create)
        self._inspector_panel.annotation_edit.connect(self._on_annotation_edit)
        self._inspector_panel.annotation_delete.connect(self._on_annotation_delete)
        self._inspector_curve.visible_changed.connect(self._on_curve_visible)
        self._inspector_curve.axis_changed.connect(self._on_curve_axis)
        self._inspector_curve.legend_label_changed.connect(self._on_curve_legend)
        self._inspector_curve.from_source_toggled.connect(self._on_curve_from_source)
        self._inspector_curve.color_changed.connect(self._on_curve_color)
        self._inspector_curve.line_style_changed.connect(self._on_curve_line_style)
        self._inspector_curve.line_width_changed.connect(self._on_curve_line_width)
        self._inspector_curve.marker_changed.connect(self._on_curve_marker)
        self._inspector_curve.marker_size_changed.connect(self._on_curve_marker_size)
        self._inspector_curve.marker_edge_changed.connect(self._on_curve_marker_edge)
        self._inspector_curve.marker_face_changed.connect(self._on_curve_marker_face)
        self._inspector_curve.refresh_data_requested.connect(self._on_curve_refresh_data)
        self._inspector_curve.refresh_style_requested.connect(self._on_curve_refresh_style)
        self._inspector_curve.artifact_toggled.connect(self._on_curve_artifact_toggle)
        self._inspector_curve.artifact_show_requested.connect(self._on_curve_artifact_show)
        self._inspector_figure.figure_size_changed.connect(self._on_figure_size_changed)
        self._inspector_figure.figure_overrides_changed.connect(self._schedule_render)
        self._inspector_figure.panel_list_clicked.connect(self._on_panel_selected)
        self._inspector_figure.layout_requested.connect(self._on_apply_layout)
        self._inspector_annotation.changed.connect(self._schedule_render)
        self._inspector_annotation.edit_requested.connect(self._on_annotation_edit)
        self._inspector_annotation.delete_requested.connect(self._on_annotation_delete)

    def _on_curves_added(self, panel_id: str, refs: list):
        panel = self.spec.find_panel(panel_id)
        if panel is None:
            return

        for ref in refs:
            slot = CurveSlot(data_ref=ref, axis="y1", visible=True)
            panel.curves.append(slot)

        self._tree.set_spec(self.spec, preserve_selection=False)
        self._on_panel_selected(panel_id)
        self._refresh_counters()
        self._schedule_render()

    # -------------------------------------------------------------- toolbar
    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        h = QHBoxLayout(bar)
        h.setContentsMargins(6, 4, 6, 4)
        h.setSpacing(6)

        # 1) Журнал
        self._journal_combo = QComboBox()
        self._journal_combo.setMinimumWidth(170)
        for pid in list_journal_presets(self.preset_store):
            p = self.preset_store.load(pid)
            self._journal_combo.addItem(p.name if p else pid, pid)
        self._journal_combo.currentIndexChanged.connect(self._on_journal_changed)
        h.addWidget(QLabel("Журнал:"))
        h.addWidget(self._journal_combo)

        # 2) Стиль
        self._style_combo = QComboBox()
        self._style_combo.setMinimumWidth(140)
        for sid in list_style_profiles():
            profile = STYLE_PROFILES.get(sid, {})
            self._style_combo.addItem(profile.get("name", sid), sid)
        self._style_combo.currentIndexChanged.connect(self._on_style_changed)
        h.addWidget(QLabel("Стиль:"))
        h.addWidget(self._style_combo)

        # 3) Применить ко всем
        self._apply_all_btn = QPushButton("Применить ко всем")
        self._apply_all_btn.setToolTip(
            "Сбросить все overrides к значениям текущих журнала и стиля. "
            "Исключения — только 📌 (не реализовано)."
        )
        self._apply_all_btn.clicked.connect(self._on_apply_to_all)
        h.addWidget(self._apply_all_btn)

        h.addStretch()

        # 4) + Панель
        self._add_panel_btn = QPushButton("+ Панель")
        self._add_panel_btn.clicked.connect(self._add_panel)
        h.addWidget(self._add_panel_btn)

        # 5) Раскладка
        self._layout_btn = QPushButton("Раскладка")
        self._layout_btn.clicked.connect(self._on_apply_layout)
        h.addWidget(self._layout_btn)

        # 6) Валидировать
        self._validate_btn = QPushButton("Валидировать")
        self._validate_btn.clicked.connect(self._on_validate)
        h.addWidget(self._validate_btn)

        # 7) Экспорт
        self._export_btn = QPushButton("Экспорт")
        self._export_btn.clicked.connect(self._on_export)
        h.addWidget(self._export_btn)

        # 8) Реальный размер (по умолчанию вкл)
        self._zoom_btn = QPushButton("Реальный размер")
        self._zoom_btn.setCheckable(True)
        self._zoom_btn.setChecked(True)
        self._zoom_btn.toggled.connect(self._on_zoom_toggled)
        h.addWidget(self._zoom_btn)

        # 9) Перезагрузить сессии
        self._reload_btn = QPushButton("Перезагрузить сессии")
        self._reload_btn.clicked.connect(self._on_reload)
        h.addWidget(self._reload_btn)

        return bar

    # -------------------------------------------------------------- status
    def _build_status(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(6, 2, 6, 2)
        h.setSpacing(12)

        self._status_state = QLabel("Готово")
        self._status_state.setMinimumWidth(140)
        h.addWidget(self._status_state)

        self._status_counters = QLabel("—")
        h.addWidget(self._status_counters)

        self._validation_btn = QPushButton("валидация: —")
        self._validation_btn.setFlat(True)
        self._validation_btn.setStyleSheet(
            "text-align: left; color: #2a82da; text-decoration: underline;"
        )
        self._validation_btn.clicked.connect(self._show_validation_report)
        h.addWidget(self._validation_btn)

        self._render_time_label = QLabel("рендер: —")
        h.addWidget(self._render_time_label)

        h.addStretch()

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(220)
        self._progress_bar.setVisible(False)
        h.addWidget(self._progress_bar)

        return w

    # ==================================================================
    # Журнал / стиль / «применить ко всему»
    # ==================================================================
    def _load_journal(self, journal_id: str):
        self.preset = load_journal_preset(journal_id, self.preset_store)
        self.spec.journal_preset_id = self.preset.id
        # применить размер колонки
        try:
            self.spec.width_mm = float(self.preset.column_width_mm())
            self.spec.height_mm = float(self.preset.column_height_mm())
        except Exception:
            logger.exception("_load_journal: size update failed")
        self._rebuild_stack()

    def _load_style(self, style_id: str):
        self.spec.style_profile_id = style_id
        self._rebuild_stack()

    def _rebuild_stack(self):
        style_data = load_style_profile_by_id(self.spec.style_profile_id)
        journal_data = self.preset.defaults if self.preset else {}
        self.style_stack = StyleStack(
            self.spec,
            safe_defaults=SAFE_DEFAULTS,
            style_profile=style_data,
            journal_defaults=journal_data,
            lab_profile=load_lab_profile_auto(),
        )
        self._inspector_figure.update_from_spec(
            self.spec, self.preset, self.style_stack
        )

    def _on_journal_changed(self, idx: int):
        journal_id = self._journal_combo.itemData(idx)
        if not journal_id:
            return
        self._load_journal(journal_id)
        self._schedule_render()

    def _on_style_changed(self, idx: int):
        style_id = self._style_combo.itemData(idx)
        if not style_id:
            return
        self._load_style(style_id)
        self._schedule_render()

    # ==================================================================
    # Рендер
    # ==================================================================
    def _schedule_render(self, *args):
        self._debounce_timer.start()

    def _render_now(self):
        self._render_generation += 1
        gen = self._render_generation
        if gen != self._render_generation:
            return
        t0 = time.perf_counter()
        try:
            figure = self.renderer.create_figure(self.spec)
            self.renderer.render(
                figure, self.spec,
                self._resolve_data,
                self.style_stack.resolve,
                self._resolve_override,
            )
            self._canvas.set_figure(figure)
            self._canvas.set_real_size(self._zoom_btn.isChecked())
        except Exception:
            logger.exception("Publication render failed")
            self._set_status_state("Ошибка рендера")
            return
        self._last_render_ms = (time.perf_counter() - t0) * 1000.0
        self._render_time_label.setText(f"рендер: {self._last_render_ms:.0f} мс")
        self._refresh_counters()
        self._set_status_state("Готово")

    def _resolve_data(self, panel, data_ref):
        return self.data_loader.resolve(panel, data_ref)

    def _resolve_override(self, ann_id):
        return self.spec.get_data_bound_override(ann_id)

    def _artifacts_for_curve(self, curve):
        sess = getattr(curve, "_publication_session", None)
        if sess is None:
            for s in (getattr(self.session_controller, "graph_sessions", {}) or {}).values():
                gm = getattr(s, "graph_main", None)
                if gm is not None and gm.get_curve(curve.rel_data.root_name) is curve:
                    sess = s
                    break
        if sess is None:
            return []
        ac = getattr(sess, "analysis_controller", None)
        return ac.get_artifacts_for_curve(curve.rel_data.root_name) if ac else []

    # ==================================================================
    # Дерево / холст / инспектор
    # ==================================================================
    def _refresh_tree(self):
        self._tree.set_spec(self.spec)

    def _refresh_counters(self):
        n_panels = len(self.spec.panels)
        n_curves = sum(len(p.curves) for p in self.spec.panels)
        n_ann = len(self.spec.presentation_annotations)
        self._status_counters.setText(
            f"{n_panels} панелей · {n_curves} кривых · {n_ann} аннотаций"
        )

    def _set_status_state(self, text: str):
        self._status_state.setText(text)

    def _current_panel(self) -> Optional[PanelSpec]:
        return self.spec.find_panel(self._current_panel_id) if self._current_panel_id else None

    def _current_slot(self) -> Optional[CurveSlot]:
        p = self._current_panel()
        if p is None or not (0 <= self._current_slot_index < len(p.curves)):
            return None
        return p.curves[self._current_slot_index]