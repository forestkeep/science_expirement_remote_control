"""Основной UI-компонент публикации."""
from __future__ import annotations
import json
import logging
import os
from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QAction, QComboBox, QDialog, QFileDialog, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QSplitter, QToolBar,
    QVBoxLayout, QWidget, QTreeWidget, QTreeWidgetItem,
)

from ..bus.source_bus import SourceBus
from ..bus.session_loader import SessionDataLoader
from ..core.json_io import load_spec, save_spec
from ..model.figure_model import FigureSpec
from ..model.panel import PanelSpec, CurveSlot
from ..model.session_ref import DataRef, DataSnapshot, StyleSnapshot
from ..model.stylestack import StyleStack, list_overrides
from ..presets.builtin import SAFE_DEFAULTS
from ..presets.loader import (
    load_journal_preset, load_style_profile_auto, load_lab_profile_auto,
    list_journal_presets,
)
from ..presets.journal_preset import JournalPresetStore
from ..renderers.mpl_renderer import MatplotlibRenderer
from ..validation.validator import Validator
from ..export.exporter import Exporter, BackgroundExporter
from .canvas import PublicationCanvas
from .context_menus import ImportSessionDialog
from .inspector import FigureInspector
from .template_chooser import TemplateChooserDialog
from .tree_view import FigureTree

logger = logging.getLogger(__name__)


class PublicationWidget(QWidget):
    DEBOUNCE_MS = 400

    def __init__(self, session_controller, spec: FigureSpec = None, parent=None):
        super().__init__(parent)
        self.session_controller = session_controller
        self.spec = spec or FigureSpec(id="fig_0001")
        self.preset_store = JournalPresetStore()
        self.preset = None
        self.style_stack = None
        self.renderer = MatplotlibRenderer()
        self.data_loader = SessionDataLoader(
            session_controller,
            artifacts_provider=self._artifacts_for_curve,
        )
        self.source_bus = SourceBus(session_controller, parent=self)
        self.source_bus.source_changed.connect(self._schedule_render)
        self.source_bus.artifacts_changed.connect(self._schedule_render)

        self._render_generation = 0
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(self.DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._render_now)

        self._current_panel_id: Optional[str] = None
        self._build_ui()
        self._load_preset(self.spec.journal_preset_id or "nature_double")
        self._schedule_render()
        self._refresh_tree()

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        bar = QWidget()
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(4, 4, 4, 4)

        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(160)
        for pid in list_journal_presets(self.preset_store):
            p = self.preset_store.load(pid)
            self._preset_combo.addItem(p.name if p else pid, pid)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        bar_layout.addWidget(QLabel("Пресет:"))
        bar_layout.addWidget(self._preset_combo)

        self._add_panel_btn = QPushButton("+ Панель")
        self._add_panel_btn.setToolTip("Добавить новую пустую панель")
        self._add_panel_btn.clicked.connect(self._add_panel)
        bar_layout.addWidget(self._add_panel_btn)

        self._layout_btn = QPushButton("Раскладка")
        self._layout_btn.setToolTip("Разложить панели по шаблону")
        self._layout_btn.clicked.connect(self._on_apply_layout)
        bar_layout.addWidget(self._layout_btn)

        self._import_btn = QPushButton("Импорт в панель")
        self._import_btn.setToolTip("Импортировать кривую сессии в выбранную (или новую) панель")
        self._import_btn.clicked.connect(self._import_session_to_panel)
        bar_layout.addWidget(self._import_btn)

        self._validate_btn = QPushButton("Валидировать")
        self._validate_btn.clicked.connect(self._on_validate)
        bar_layout.addWidget(self._validate_btn)

        self._export_btn = QPushButton("Экспорт")
        self._export_btn.clicked.connect(self._on_export)
        bar_layout.addWidget(self._export_btn)

        self._reload_btn = QPushButton("Перезагрузить сессии")
        self._reload_btn.setToolTip("Перепривязать панели к актуальным данным сессий")
        self._reload_btn.clicked.connect(self._on_reload)
        bar_layout.addWidget(self._reload_btn)

        self._zoom_btn = QPushButton("Реальный размер")
        self._zoom_btn.setCheckable(True)
        self._zoom_btn.toggled.connect(self._on_zoom_toggled)
        bar_layout.addWidget(self._zoom_btn)

        bar_layout.addStretch()
        layout.addWidget(bar)

        splitter = QSplitter(Qt.Horizontal)
        self._tree = FigureTree()
        self._tree.selection_changed.connect(self._on_tree_selection)
        self._tree.annotation_selected.connect(self._on_annotation_selected)
        splitter.addWidget(self._tree)

        self._canvas = PublicationCanvas()
        self._canvas.set_spec(self.spec)
        self._canvas.panel_geometry_changed.connect(self._on_panel_geometry_changed)
        self._canvas.panel_selected.connect(self._on_canvas_panel_selected)
        self._canvas.selection_cleared.connect(self._on_canvas_selection_cleared)
        self._canvas.annotation_selected.connect(self._on_annotation_selected_by_canvas)
        self._canvas.annotation_geometry_changed.connect(self._on_annotation_geometry_changed)
        self._canvas.refresh_data_requested.connect(self._on_refresh_data_requested)
        self._canvas.refresh_style_requested.connect(self._on_refresh_style_requested)
        self._canvas.enable_live_requested.connect(self._on_enable_live_requested)
        self._canvas.add_panel_requested.connect(self._add_panel)
        self._canvas.delete_panel_requested.connect(self._delete_panel)
        self._canvas.apply_layout_requested.connect(self._on_apply_layout)
        splitter.addWidget(self._canvas)

        self._inspector = FigureInspector(self._get_stack)
        self._inspector.set_spec(self.spec)
        self._inspector.geometry_changed.connect(self._on_inspector_geometry_changed)
        self._inspector.style_override_changed.connect(lambda *_: self._schedule_render())
        self._inspector.style_override_cleared.connect(lambda *_: self._schedule_render())
        self._inspector.style_override_cleared_all.connect(lambda *_: self._schedule_render())
        splitter.addWidget(self._inspector)

        splitter.setSizes([240, 800, 280])
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self._status_label = QLabel("—")
        self._status_label.setStyleSheet("padding: 4px; color: #333;")
        layout.addWidget(self._status_label)

    # ---------------------------------------------------------------- helpers
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
        if ac is None:
            return []
        return ac.get_artifacts_for_curve(curve.rel_data.root_name)

    def _load_preset(self, preset_id: str):
        self.preset = load_journal_preset(preset_id, self.preset_store)
        self.spec.journal_preset_id = self.preset.id
        self.style_stack = StyleStack(
            self.spec,
            safe_defaults=SAFE_DEFAULTS,
            style_profile=load_style_profile_auto(),
            journal_defaults=self.preset.defaults,
            lab_profile=load_lab_profile_auto(),
        )
        idx = self._preset_combo.findData(preset_id)
        if idx >= 0 and idx != self._preset_combo.currentIndex():
            self._preset_combo.blockSignals(True)
            self._preset_combo.setCurrentIndex(idx)
            self._preset_combo.blockSignals(False)

    def _on_preset_changed(self, idx: int):
        preset_id = self._preset_combo.itemData(idx)
        if not preset_id:
            return
        self._load_preset(preset_id)
        self._schedule_render()

    def _get_stack(self):
        return self.style_stack

    # ---------------------------------------------------------------- render
    def _schedule_render(self, *args, fast: bool = False):
        self._debounce_timer.setInterval(50 if fast else self.DEBOUNCE_MS)
        self._debounce_timer.start()

    def _render_now(self):
        self._render_generation += 1
        gen = self._render_generation
        if gen != self._render_generation:
            return
        try:
            figure = self.renderer.create_figure(self.spec)
            self.renderer.render(
                figure, self.spec,
                self._resolve_data,
                self.style_stack.resolve,
                self._resolve_override,
            )
            self._canvas.set_figure(figure)
        except Exception:
            logger.exception("Publication render failed")
            self._status_label.setText("Ошибка рендера. См. лог.")
        self._update_override_resolution()
        self._update_stale_badges()

    def _update_stale_badges(self):
        try:
            self._canvas._widget.update()
        except Exception:
            logger.exception("update stale badges failed")

    def _resolve_data(self, panel, data_ref):
        return self.data_loader.resolve(panel, data_ref)

    def _resolve_override(self, ann_id):
        return self.spec.get_data_bound_override(ann_id)

    def _update_override_resolution(self):
        present = set()
        for p in self.spec.panels:
            for slot in p.curves:
                data = self.data_loader.resolve(p, slot.data_ref)
                if not data:
                    continue
                for ann in data.get("panel_annotations", []) or []:
                    present.add(ann["id"])
        for ann_id, ov in self.spec.data_bound_overrides.items():
            if ann_id in present:
                ov.resolved = True
                ov.unresolved_reason = ""
            else:
                ov.resolved = False
                ov.unresolved_reason = "annotation not present in source"

    # ---------------------------------------------------------------- tree/canvas
    def _refresh_tree(self):
        self._tree.set_spec(self.spec)

    def _on_tree_selection(self, panel_id: str):
        self._current_panel_id = panel_id or None
        self._canvas.set_selected_panel(panel_id or None)
        self._inspector.select_panel(panel_id)

    def _on_annotation_selected(self, ann_id: str):
        self._current_panel_id = None
        self._canvas.set_selected_panel(None)
        self._inspector.select_panel("")

    def _on_canvas_panel_selected(self, panel_id: str, additive: bool):
        self._current_panel_id = panel_id
        self._canvas.set_selected_panel(panel_id)
        self._inspector.select_panel(panel_id)

    def _on_canvas_selection_cleared(self):
        self._current_panel_id = None
        self._canvas.set_selected_panel(None)
        self._inspector.select_panel("")

    def _on_panel_geometry_changed(self, panel_id, x, y, w, h):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        p.x_mm, p.y_mm, p.w_mm, p.h_mm = x, y, w, h
        self._schedule_render(fast=True)
        if self._current_panel_id == panel_id:
            self._inspector.select_panel(panel_id)

    def _on_annotation_selected_by_canvas(self, ann_id: str):
        self._current_panel_id = None
        self._canvas.set_selected_panel(None)
        self._inspector.select_panel("")

    def _on_annotation_geometry_changed(self, ann_id: str, coords: tuple):
        ann = self.spec.find_presentation(ann_id)
        if ann is None:
            return
        ann.coords = tuple(coords)
        self._schedule_render(fast=True)

    def _on_inspector_geometry_changed(self, panel_id, x, y, w, h):
        self._on_panel_geometry_changed(panel_id, x, y, w, h)

    # ---------------------------------------------------------------- refresh/delete
    def _on_refresh_data_requested(self, panel_id: str):
        panel = self.spec.find_panel(panel_id)
        if panel is None:
            return
        for slot in panel.curves:
            if slot.data_ref is None or slot.data_ref.is_empty():
                continue
            sess, curve = self.data_loader._get_curve(
                slot.data_ref.session_id, slot.data_ref.series_root_name
            )
            if curve is None:
                continue
            slot.data_ref.data = DataSnapshot.take(curve)
            slot.data_ref.stale_data = False
        self._schedule_render()

    def _on_refresh_style_requested(self, panel_id: str):
        panel = self.spec.find_panel(panel_id)
        if panel is None:
            return
        for slot in panel.curves:
            if slot.data_ref is None or slot.data_ref.is_empty():
                continue
            sess, curve = self.data_loader._get_curve(
                slot.data_ref.session_id, slot.data_ref.series_root_name
            )
            if curve is None:
                continue
            slot.data_ref.style = StyleSnapshot.take(
                curve, lambda c: self._artifacts_for_curve(c)
            )
            slot.data_ref.stale_style = False
        self._schedule_render()

    def _on_enable_live_requested(self, panel_id: str):
        panel = self.spec.find_panel(panel_id)
        if panel is None:
            return
        for slot in panel.curves:
            if slot.data_ref is not None:
                slot.data_ref.refresh_policy = "live"
                slot.data_ref.stale_data = False
        self._schedule_render()

    def _delete_panel(self, panel_id: str):
        if not panel_id:
            return
        removed = self.spec.remove_panel(panel_id)
        if not removed:
            return
        if self._current_panel_id == panel_id:
            self._current_panel_id = None
            self._canvas.set_selected_panel(None)
            self._inspector.select_panel("")
        self._refresh_tree()
        self._schedule_render()

    # ---------------------------------------------------------------- add panel
    def _add_panel(self):
        panel = self.spec.add_panel(x_mm=5.0, y_mm=5.0, w_mm=40.0, h_mm=30.0)
        self._current_panel_id = panel.id
        self._canvas.set_selected_panel(panel.id)
        self._inspector.select_panel(panel.id)
        self._refresh_tree()
        self._schedule_render()

    def _import_session_to_panel(self):
        dialog = ImportSessionDialog(self.session_controller, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        ref = dialog.get_data_ref()
        if not ref.session_id or not ref.series_root_name:
            return
        sess, curve = self.data_loader._get_curve(ref.session_id, ref.series_root_name)
        if curve is not None:
            ref.data = DataSnapshot.take(curve)
            ref.style = StyleSnapshot.take(curve, lambda c: self._artifacts_for_curve(c))
            ref.refresh_policy = "snapshot"
        slot = CurveSlot(data_ref=ref, axis="y1", visible=True)
        if self._current_panel_id:
            panel = self.spec.find_panel(self._current_panel_id)
            if panel is not None:
                panel.curves.append(slot)
                self._refresh_tree()
                self._schedule_render()
                return
        panel = self.spec.add_panel(curves=[slot],
                                    x_mm=5.0, y_mm=5.0, w_mm=40.0, h_mm=30.0)
        self._current_panel_id = panel.id
        self._canvas.set_selected_panel(panel.id)
        self._inspector.select_panel(panel.id)
        self._refresh_tree()
        self._schedule_render()

    # ---------------------------------------------------------------- layout template
    def _on_apply_layout(self):
        default_margin = float(
            (self.preset.constraints or {}).get("margin_mm", 3.0)
        )
        default_gap = min(default_margin, 2.0)

        dialog = TemplateChooserDialog(
            self.spec,
            default_margin=default_margin,
            default_gap=default_gap,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return

        # После применения выбранная панель могла исчезнуть (replace) или
        # сохраниться (reflow). Аккуратно синхронизируем состояние.
        current = self._current_panel_id
        still_exists = (
            current is not None
            and any(p.id == current for p in self.spec.panels)
        )
        if still_exists:
            self._canvas.set_selected_panel(current)
            self._inspector.select_panel(current)
        else:
            self._current_panel_id = None
            self._canvas.set_selected_panel(None)
            self._inspector.select_panel("")
            if self.spec.panels:
                first_id = self.spec.panels[0].id
                self._current_panel_id = first_id
                self._canvas.set_selected_panel(first_id)
                self._inspector.select_panel(first_id)

        self._refresh_tree()
        self._schedule_render()
        self._status_label.setText(
            f"Шаблон применён: {len(self.spec.panels)} панелей."
        )

    # ---------------------------------------------------------------- reload/zoom
    def _on_reload(self):
        self.source_bus.ensure_all_attached()
        self._schedule_render()
        self._refresh_tree()

    def _on_zoom_toggled(self, checked: bool):
        self._canvas.set_real_size(checked)

    # ---------------------------------------------------------------- validate/export
    def _on_validate(self):
        report = Validator(self.spec, self.preset, self.style_stack,
                           self._resolve_data).validate()
        n_warn = len(report.warnings)
        n_err = len(report.errors)
        if n_err:
            self._status_label.setText(f"{n_err} ошибок, {n_warn} предупреждений")
        elif n_warn:
            self._status_label.setText(f"{n_warn} предупреждений")
        else:
            self._status_label.setText("Валидация пройдена")
        if report.all_issues:
            lines = []
            for issue in report.all_issues[:20]:
                line = f"[{issue.severity}] {issue.code}: {issue.message}"
                if issue.panel_id:
                    line += f" (panel={issue.panel_id})"
                lines.append(line)
            QMessageBox.information(self, "Валидация", "\n".join(lines))

    def _on_export(self):
        report = Validator(self.spec, self.preset, self.style_stack,
                           self._resolve_data).validate()
        if not report.ok:
            n_warn = len(report.warnings)
            n_err = len(report.errors)
            text = f"Валидатор нашёл проблемы:\nошибок: {n_err}, предупреждений: {n_warn}.\nПродолжить экспорт?"
            ans = QMessageBox.question(self, "Экспорт", text,
                                       QMessageBox.Yes | QMessageBox.No)
            if ans != QMessageBox.Yes:
                return
        dir_path = QFileDialog.getExistingDirectory(self, "Каталог пакета экспорта")
        if not dir_path:
            return
        if os.listdir(dir_path):
            import time
            dir_path = os.path.join(dir_path, f"pub_export_{int(time.time())}")
        exporter = Exporter(
            self.spec, self.preset, self.style_stack,
            self._resolve_data, self._resolve_override,
            validation_report=report,
        )
        bg = BackgroundExporter(exporter, self)
        self._status_label.setText("Экспорт...")
        bg.start(dir_path, include_png=False,
                 on_finished=lambda p: self._on_export_done(p),
                 on_failed=lambda m: self._status_label.setText(f"Ошибка экспорта: {m}"))

    def _on_export_done(self, path: str):
        self._status_label.setText(f"Экспорт завершён: {path}")
        QMessageBox.information(self, "Экспорт", f"Готово:\n{path}")

    # ---------------------------------------------------------------- file io
    def save_to_file(self, path: str):
        save_spec(self.spec, path)

    def load_from_file(self, path: str):
        self.spec = load_spec(path)
        self._current_panel_id = None
        self._canvas.set_spec(self.spec)
        self._canvas.set_selected_panel(None)
        self._inspector.set_spec(self.spec)
        self._inspector.select_panel("")
        self._load_preset(self.spec.journal_preset_id or "nature_double")
        self._refresh_tree()
        self._schedule_render()