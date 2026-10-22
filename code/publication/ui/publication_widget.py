"""Основной UI-компонент (без окна). Работает и в QMainWindow, и в QDockWidget."""
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
from ..model.panel import PanelSpec
from ..model.session_ref import DataRef
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
from .context_menus import build_canvas_menu, ImportSessionDialog
from .inspector import FigureInspector
from .style_editor import PresetEditorDialog
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
        self.data_loader = SessionDataLoader(session_controller)
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

        # --- top toolbar ---
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

        # --- main splitter: tree | canvas | inspector ---
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
        self._canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        self._canvas.customContextMenuRequested.connect(self._on_canvas_context_menu)
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

        # --- bottom: validation status ---
        self._status_label = QLabel("—")
        self._status_label.setStyleSheet("padding: 4px; color: #333;")
        layout.addWidget(self._status_label)

    # -------------------------------------------------------------- preset
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

    # --------------------------------------------------------------- render
    def _schedule_render(self, *args, fast: bool = False):
        """Дебаунс 400 мс; во время drag — 50 мс для отзывчивости."""
        self._debounce_timer.setInterval(50 if fast else self.DEBOUNCE_MS)
        self._debounce_timer.start()

    def _render_now(self):
        self._render_generation += 1
        gen = self._render_generation
        # снапшот-проверка поколения после долгой операции
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
        # Обновить unresolved статусы в overrides
        self._update_override_resolution()

    def _resolve_data(self, panel, data_ref):
        return self.data_loader.resolve(panel, data_ref)

    def _resolve_override(self, ann_id):
        return self.spec.get_data_bound_override(ann_id)

    def _update_override_resolution(self):
        present = set()
        for p in self.spec.panels:
            data = self.data_loader.resolve(p, p.data_ref)
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

    # --------------------------------------------------------------- tree/canvas
    def _refresh_tree(self):
        self._tree.set_spec(self.spec)

    def _on_tree_selection(self, panel_id: str):
        self._current_panel_id = panel_id or None
        self._inspector.select_panel(panel_id)
        if panel_id:
            p = self.spec.find_panel(panel_id)
            if p:
                # подсветить на канвасе — простой способ: выбрать в дереве
                pass

    def _on_annotation_selected(self, ann_id: str):
        self._current_panel_id = None
        self._inspector.select_panel("")

    def _on_canvas_panel_selected(self, panel_id: str, additive: bool):
        self._current_panel_id = panel_id
        self._inspector.select_panel(panel_id)

    def _on_canvas_selection_cleared(self):
        self._current_panel_id = None
        self._inspector.select_panel("")

    #----------------------
    def _on_panel_geometry_changed(self, panel_id, x, y, w, h):
        p = self.spec.find_panel(panel_id)
        if p is None:
            return
        p.x_mm, p.y_mm, p.w_mm, p.h_mm = x, y, w, h
        self._schedule_render(fast=True)
        if self._current_panel_id == panel_id:
            self._inspector.select_panel(panel_id)

    def _on_canvas_panel_selected(self, panel_id: str, additive: bool):
        self._current_panel_id = panel_id
        self._inspector.select_panel(panel_id)

    def _on_annotation_selected_by_canvas(self, ann_id: str):
        self._current_panel_id = None
        self._inspector.select_panel("")

    def _on_annotation_geometry_changed(self, ann_id: str, coords: tuple):
        ann = self.spec.find_presentation(ann_id)
        if ann is None:
            return
        ann.coords = tuple(coords)
        self._schedule_render(fast=True)

    def _on_inspector_geometry_changed(self, panel_id, x, y, w, h):
        self._on_panel_geometry_changed(panel_id, x, y, w, h)

    #----------------------

    def _on_inspector_geometry_changed(self, panel_id, x, y, w, h):
        self._on_panel_geometry_changed(panel_id, x, y, w, h)

    # --------------------------------------------------------------- context
    def _on_canvas_context_menu(self, pos):
        from PyQt5.QtGui import QCursor
        menu = self._build_context_menu()
        menu.exec_(self._canvas.mapToGlobal(pos))

    def _build_context_menu(self):
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self._canvas)
        menu.addAction("Добавить панель", self._add_panel)
        menu.addAction("Импортировать сессию в панель", self._import_session_to_panel)
        pres = menu.addMenu("Presentation-элементы")
        for kind in ("text", "panel_label", "scale_bar", "bracket", "arrow"):
            pres.addAction(kind, lambda k=kind: self._add_presentation(k))
        align = menu.addMenu("Выровнять")
        for mode in ("left", "right", "top", "bottom", "center_h", "center_v"):
            align.addAction(mode, lambda m=mode: self._align_panel(m))
        menu.addSeparator()
        menu.addAction("Z-order: на передний план", self._zorder_front)
        menu.addAction("Z-order: на задний план", self._zorder_back)
        return menu

    def _add_panel(self):
        self.spec.add_panel(x_mm=5.0, y_mm=5.0, w_mm=40.0, h_mm=30.0)
        self._refresh_tree()
        self._schedule_render()

    def _import_session_to_panel(self):
        dialog = ImportSessionDialog(self.session_controller, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        ref = dialog.get_data_ref()
        if not ref.session_id or not ref.series_root_name:
            return
        if self._current_panel_id:
            panel = self.spec.find_panel(self._current_panel_id)
            if panel is not None:
                panel.data_ref = ref
        else:
            self.spec.add_panel(data_ref=ref)
        self._refresh_tree()
        self._schedule_render()

    def _add_presentation(self, kind: str):
        panel_id = self._current_panel_id
        if kind == "panel_label":
            text = "a"
            # авто-инкремент буквы
            used = {a.text for a in self.spec.presentation_annotations
                    if a.kind == "panel_label"}
            for cand in "abcdefghijklmnopqrstuvwxyz":
                if cand not in used:
                    text = cand
                    break
        else:
            text = {"text": "Текст", "scale_bar": "1 мм",
                    "bracket": "*", "arrow": ""}.get(kind, "")
        ann = self.spec.add_presentation(
            kind=kind,
            coordinate_space="panel_mm" if panel_id else "figure_mm",
            panel_id=panel_id,
            coords=(-10.0, -2.0) if kind == "panel_label" else (3.0, 3.0),
            text=text,
        )
        self._refresh_tree()
        self._schedule_render()

    def _align_panel(self, mode: str):
        if not self._current_panel_id:
            return
        p = self.spec.find_panel(self._current_panel_id)
        if p is None:
            return
        margin = float(self.preset.constraints.get("margin_mm", 3.0))
        if mode == "left":
            p.x_mm = margin
        elif mode == "right":
            p.x_mm = self.spec.width_mm - p.w_mm - margin
        elif mode == "top":
            p.y_mm = margin
        elif mode == "bottom":
            p.y_mm = self.spec.height_mm - p.h_mm - margin
        elif mode == "center_h":
            p.x_mm = (self.spec.width_mm - p.w_mm) / 2.0
        elif mode == "center_v":
            p.y_mm = (self.spec.height_mm - p.h_mm) / 2.0
        self._schedule_render()
        self._inspector.select_panel(p.id)

    def _zorder_front(self):
        if not self._current_panel_id:
            return
        max_z = max((p.z for p in self.spec.panels), default=0)
        p = self.spec.find_panel(self._current_panel_id)
        if p is not None:
            p.z = max_z + 1
            self._schedule_render()

    def _zorder_back(self):
        if not self._current_panel_id:
            return
        min_z = min((p.z for p in self.spec.panels), default=0)
        p = self.spec.find_panel(self._current_panel_id)
        if p is not None:
            p.z = min_z - 1
            self._schedule_render()

    # --------------------------------------------------------------- reload
    def _on_reload(self):
        """Перепривязать все сессии, сохраняя overrides и presentation-only."""
        self.source_bus.ensure_all_attached()
        # Проверить, что серии всё ещё существуют; если нет — DataRef остаётся,
        # но data_resolver вернёт None, и панель отрисуется "(no data)".
        # Overrides data-bound остаются в spec.
        self._schedule_render()
        self._refresh_tree()

    # --------------------------------------------------------------- zoom
    def _on_zoom_toggled(self, checked: bool):
        self._canvas.set_real_size(checked)

    # --------------------------------------------------------------- validate/export
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
        self._last_report = report
        if report.all_issues:
            lines = []
            for issue in report.all_issues[:20]:
                line = f"[{issue.severity}] {issue.code}: {issue.message}"
                if issue.panel_id:
                    line += f" (panel={issue.panel_id})"
                lines.append(line)
            QMessageBox.information(self, "Валидация", "\n".join(lines))

    def _on_export(self):
        # валидация перед экспортом
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
        # проверить, что каталог пуст, либо создать подкаталог
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
        bg.start(
            dir_path, include_png=False,
            on_finished=lambda p: self._on_export_done(p),
            on_failed=lambda m: self._status_label.setText(f"Ошибка экспорта: {m}"),
        )

    def _on_export_done(self, path: str):
        self._status_label.setText(f"Экспорт завершён: {path}")
        QMessageBox.information(self, "Экспорт", f"Готово:\n{path}")

    # --------------------------------------------------------------- file io
    def save_to_file(self, path: str):
        save_spec(self.spec, path)

    def load_from_file(self, path: str):
        self.spec = load_spec(path)
        self._canvas.set_spec(self.spec)
        self._inspector.set_spec(self.spec)
        self._load_preset(self.spec.journal_preset_id or "nature_double")
        self._refresh_tree()
        self._schedule_render()