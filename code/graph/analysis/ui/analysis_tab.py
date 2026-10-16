"""Вкладка «Анализ» инспектора."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QHeaderView, QSizePolicy,
)
from .. import ensure_tools_registered
from ..models import ParamDescriptor, ParamType, PlacementType, tr_analysis

from ..models import ParamDescriptor, ParamType, PlacementType
from ..registry import AnalysisToolRegistry
from ..presets import AnalysisPresetStore

logger = logging.getLogger(__name__)
_TR = lambda s: QApplication.translate("GraphWindow", s)


class AnalysisTab(QWidget):
    """Единственное место настройки, предпросмотра и применения инструментов."""

    def __init__(self, session, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.controller = session.analysis_controller
        self.registry = AnalysisToolRegistry.instance()
        self.presets = AnalysisPresetStore.instance()
        self.curves: List[Any] = []
        self._param_widgets: Dict[str, QWidget] = {}
        self._suppress = False

        self._build_ui()

        self.controller.tool_activated.connect(self._on_tool_activated)
        self.controller.tool_deactivated.connect(self._on_tool_deactivated)
        self.controller.preview_updated.connect(self._on_preview_updated)
        self.controller.artifacts_changed.connect(self._reload_artifacts)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content.setMinimumWidth(0)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        ensure_tools_registered()
        self.registry = AnalysisToolRegistry.instance()

        # 1. Применённые + пресеты
        self.applied_group = QGroupBox(_TR("Применённые инструменты"))
        applied_outer = QVBoxLayout(self.applied_group)
        applied_outer.setContentsMargins(4, 4, 4, 4)

        presets_row = QHBoxLayout()
        self.presets_combo = QComboBox()
        self.presets_combo.setMinimumWidth(0)
        self.presets_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.presets_combo.setMinimumContentsLength(10)
        self.presets_combo.addItem(_TR("— пресеты —"), None)
        self._reload_presets_combo()

        self.btn_apply_preset = QPushButton(_TR("Применить"))
        self.btn_apply_preset.clicked.connect(self._apply_selected_preset)

        presets_row.addWidget(self.presets_combo, 1)
        presets_row.addWidget(self.btn_apply_preset)
        applied_outer.addLayout(presets_row)

        self.btn_save_preset = QPushButton(_TR("Сохранить как пресет"))
        self.btn_save_preset.clicked.connect(self._save_preset)
        applied_outer.addWidget(self.btn_save_preset)

        # Контейнер именно для динамического списка результатов
        self.applied_results_layout = QVBoxLayout()
        self.applied_results_layout.setContentsMargins(0, 0, 0, 0)
        self.applied_empty_label = QLabel(_TR("Результаты отсутствуют"))
        self.applied_results_layout.addWidget(self.applied_empty_label)
        applied_outer.addLayout(self.applied_results_layout)

        layout.addWidget(self.applied_group)

        # 2. Добавить новый
        add_group = QGroupBox(_TR("Добавить новый"))
        add_layout = QVBoxLayout(add_group)
        add_layout.setContentsMargins(4, 4, 4, 4)
        self.tool_combo = QComboBox()
        self.tool_combo.setMinimumWidth(0)
        self.tool_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.tool_combo.setMinimumContentsLength(10)
        self.tool_combo.addItem(_TR("— выберите инструмент —"), None)

        # Явный порядок: интерполяции первыми, далее по категориям
        _ORDER = [
            "fit.linear", "fit.polynomial", "fit.gaussian", "fit.lorentz",
            "search.peaks", "search.valleys",
            "diff.derivative", "diff.integral",
            "spectral.fft", "spectral.autocorr",
            "uncertainty.estimate",
        ]
        tools_by_id = {d.tool_id: d for d in self.registry.list_all()}
        for tid in _ORDER:
            desc = tools_by_id.get(tid)
            if desc is None:
                continue
            self.tool_combo.addItem(self._resolve_title(desc), tid)
        # На случай, если появятся новые инструменты — добавим их в конец
        for tid, desc in tools_by_id.items():
            if tid in _ORDER:
                continue
            self.tool_combo.addItem(self._resolve_title(desc), tid)

        self.tool_combo.currentIndexChanged.connect(self._on_tool_selected)
        add_layout.addWidget(self.tool_combo)
        layout.addWidget(add_group)

         # 3. Активный инструмент (без кнопок Применить/Отменить — применяется сразу)
        self.active_group = QGroupBox(_TR("Активный инструмент"))
        active_layout = QVBoxLayout(self.active_group)
        active_layout.setContentsMargins(4, 4, 4, 4)
        self.active_title = QLabel("")
        self.active_title.setWordWrap(True)
        active_layout.addWidget(self.active_title)

        self.params_form = QFormLayout()
        self.params_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.params_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.params_form.setLabelAlignment(Qt.AlignLeft)
        self.params_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.params_form.setContentsMargins(0, 4, 0, 4)
        self.params_form.setHorizontalSpacing(6)
        self.params_form.setVerticalSpacing(4)
        params_widget = QWidget()
        params_widget.setMinimumWidth(0)
        params_widget.setLayout(self.params_form)
        active_layout.addWidget(params_widget)

        self.active_group.setVisible(False)
        layout.addWidget(self.active_group)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
    # ------------------------------------------------------------------
    def set_curves(self, curves: List[Any]) -> None:
        self.curves = [c for c in curves if hasattr(c, "rel_data")]
        self._reload_artifacts()
        # область применения
        if hasattr(self, "scope_label"):
            names = [c.curve_name for c in self.curves]
            self.scope_label.setText(", ".join(names) if names else "—")

    def _reload_artifacts(self) -> None:
        # очищаем только список результатов, оставляя UI пресетов
        while self.applied_results_layout.count():
            item = self.applied_results_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        artifacts = []
        uncertainty_entries = []
        for curve in self.curves:
            root = curve.rel_data.root_name
            artifacts.extend(self.controller.get_artifacts_for_curve(root))
            store = getattr(curve, "store", None)
            if store is not None:
                for rec in getattr(store, "uncertainty_records", []) or []:
                    uncertainty_entries.append((curve, rec))

        total = len(artifacts) + len(uncertainty_entries)
        if total == 0:
            self.applied_results_layout.addWidget(QLabel(_TR("Результаты отсутствуют")))
        else:
            for art in artifacts:
                self.applied_results_layout.addWidget(self._build_artifact_row(art))
            for curve, rec in uncertainty_entries:
                self.applied_results_layout.addWidget(self._build_uncertainty_row(curve, rec))

    def _reload_presets_combo(self) -> None:
        self.presets_combo.blockSignals(True)
        try:
            current = self.presets_combo.currentData()
            self.presets_combo.clear()
            self.presets_combo.addItem(_TR("— пресеты —"), None)
            for p in self.presets.all():
                self.presets_combo.addItem(p.name or "(без имени)", p.id)
            if current:
                idx = self.presets_combo.findData(current)
                if idx >= 0:
                    self.presets_combo.setCurrentIndex(idx)
        finally:
            self.presets_combo.blockSignals(False)

    def _apply_selected_preset(self) -> None:
        preset_id = self.presets_combo.currentData()
        if not preset_id:
            return
        preset = self.presets.get(preset_id)
        if preset is None:
            return
        n = self.controller.apply_preset(preset, sources=None)
        if n == 0:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self, _TR("Применить пресет"),
                _TR("Не удалось применить пресет: нет выделенных кривых."),
            )
        else:
            self._reload_artifacts()
    def _save_preset(self) -> None:
        # Собираем применённые инструменты текущего выделения
        artifacts: List[Dict[str, Any]] = []
        seen = set()
        for curve in self.curves:
            root = curve.rel_data.root_name
            for art in self.controller.get_artifacts_for_curve(root):
                key = (art.tool_id, tuple(sorted((art.params or {}).items())))
                if key in seen:
                    continue
                seen.add(key)
                artifacts.append({
                    "tool_id": art.tool_id,
                    "params": dict(art.params or {}),
                })

        if not artifacts:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self, _TR("Сохранить пресет"),
                _TR("Нет применённых инструментов для сохранения."),
            )
            return

        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, _TR("Сохранить пресет"),
                                        _TR("Имя пресета:"))
        if not ok or not name.strip():
            return
        self.presets.register(name.strip(), artifacts)
        self._reload_presets_combo()

    def _build_uncertainty_row(self, curve, record) -> QWidget:
        w = QWidget()
        hl = QHBoxLayout(w)
        hl.setContentsMargins(4, 2, 4, 2)

        method_label = tr_analysis(
            f"analysis.param.uncertainty.method.{record.method}",
            str(record.method),
        )
        cb = QCheckBox(f"{_TR('Погрешности точек')} ({method_label})")
        active_ids = getattr(curve.store, "active_uncertainty_ids", set()) or set()
        cb.setChecked(record.id in active_ids)
        cb.stateChanged.connect(
            lambda st, rn=curve.rel_data.root_name, rid=record.id:
                self.controller.set_uncertainty_visible(rn, rid, st != 0)
        )

        del_btn = QPushButton("×")
        del_btn.setFixedWidth(24)
        del_btn.clicked.connect(
            lambda _, rn=curve.rel_data.root_name, rid=record.id:
                self.controller.remove_uncertainty(rn, rid)
        )

        hl.addWidget(cb)
        hl.addStretch()
        hl.addWidget(del_btn)
        return w
    
    def _build_artifact_row(self, artifact) -> QWidget:
        w = QWidget()
        hl = QHBoxLayout(w)
        hl.setContentsMargins(4, 2, 4, 2)
        cb = QCheckBox(self._resolve_tool_title(artifact.tool_id))
        cb.setChecked(artifact.visibility)
        cb.stateChanged.connect(
            lambda st, aid=artifact.id: self.controller.set_artifact_visibility(aid, st != 0)
        )
        del_btn = QPushButton("×")
        del_btn.setFixedWidth(24)
        del_btn.clicked.connect(lambda _, aid=artifact.id: self.controller.remove_artifact(aid))
        hl.addWidget(cb)
        hl.addStretch()
        hl.addWidget(del_btn)
        return w

    # ------------------------------------------------------------------
    def _on_tool_selected(self, index: int) -> None:
        tool_id = self.tool_combo.itemData(index)
        if not tool_id:
            return
        # Сброс предыдущего инструмента и немедленное применение выбранного
        self.controller.cancel_preview()
        if self.controller.activate_tool(tool_id):
            self.controller.apply()

    def _on_tool_activated(self, tool_id: str) -> None:
        desc = self.registry.get(tool_id)
        if desc is None:
            return
        self.active_title.setText(self._resolve_title(desc))
        self._rebuild_params(desc)
        self.active_group.setVisible(True)

    def _on_tool_deactivated(self) -> None:
        self.active_group.setVisible(False)
        self._param_widgets.clear()
        self._clear_params_form()

    def _on_preview_updated(self) -> None:
        pass

    def _rebuild_params(self, desc) -> None:
        self._clear_params_form()
        self._param_widgets.clear()
        for param in desc.param_schema:
            w = self._build_param_widget(param)
            if w is not None:
                self._param_widgets[param.name] = w
                title = tr_analysis(param.title_key)
                self.params_form.addRow(title, w)

    def _clear_params_form(self) -> None:
        """Полностью убрать все строки формы, включая автолейблы от addRow."""
        while self.params_form.count():
            item = self.params_form.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            sub = item.layout()
            if sub is not None:
                while sub.count():
                    sub_item = sub.takeAt(0)
                    sw = sub_item.widget()
                    if sw is not None:
                        sw.setParent(None)
                        sw.deleteLater()

    def _build_param_widget(self, param: ParamDescriptor) -> Optional[QWidget]:
        if param.type == ParamType.INT:
            w = QSpinBox()
            w.setMinimumWidth(0)
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            w.setRange(int(param.min) if param.min is not None else -10**9,
                       int(param.max) if param.max is not None else 10**9)
            w.setValue(int(param.default or 0))
            w.valueChanged.connect(lambda v, n=param.name: self._param_changed(n, int(v)))
            return w
        if param.type == ParamType.FLOAT:
            w = QDoubleSpinBox()
            w.setMinimumWidth(0)
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            w.setRange(float(param.min) if param.min is not None else -1e12,
                       float(param.max) if param.max is not None else 1e12)
            w.setDecimals(6)
            w.setSingleStep(float(param.step) if param.step is not None else 0.01)
            w.setValue(float(param.default or 0.0))
            w.valueChanged.connect(lambda v, n=param.name: self._param_changed(n, float(v)))
            return w
        if param.type == ParamType.BOOL:
            w = QCheckBox()
            w.setChecked(bool(param.default))
            w.stateChanged.connect(lambda st, n=param.name: self._param_changed(n, st != 0))
            return w
        if param.type == ParamType.CHOICE:
            w = QComboBox()
            w.setMinimumWidth(0)
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            for ch in param.choices:
                if isinstance(ch, (tuple, list)) and len(ch) == 2:
                    value, label_key = ch
                    w.addItem(tr_analysis(str(label_key)), value)
                else:
                    w.addItem(str(ch), ch)
            # выбрать default
            for i in range(w.count()):
                if w.itemData(i) == param.default:
                    w.setCurrentIndex(i)
                    break
            w.currentIndexChanged.connect(
                lambda idx, n=param.name, ww=w: self._param_changed(n, ww.currentData()))
            return w
        if param.type == ParamType.TEXT:
            
            w = QLineEdit(str(param.default or ""))
            w.setMinimumWidth(0)
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            w.editingFinished.connect(lambda n=param.name, ww=w: self._param_changed(n, ww.text()))
            return w
        return None

    def _param_changed(self, name: str, value: Any) -> None:
        if self._suppress:
            return
        self.controller.set_preview_params({name: value})
        self.controller.apply()

    # ------------------------------------------------------------------
    def _save_preset(self) -> None:
        artifacts: List[Dict[str, Any]] = []
        seen = set()
        for curve in self.curves:
            root = curve.rel_data.root_name
            for art in self.controller.get_artifacts_for_curve(root):
                key = (art.tool_id, tuple(sorted((art.params or {}).items())))
                if key in seen:
                    continue
                seen.add(key)
                artifacts.append({
                    "tool_id": art.tool_id,
                    "params": dict(art.params or {}),
                })

        if not artifacts:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self, _TR("Сохранить пресет"),
                _TR("Нет применённых инструментов для сохранения."),
            )
            return

        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, _TR("Сохранить пресет"),
                                        _TR("Имя пресета:"))
        if not ok or not name.strip():
            return
        self.presets.register(name.strip(), artifacts)
        self._reload_presets_combo()

    # ------------------------------------------------------------------
    def _resolve_title(self, desc) -> str:
        from ..models import tr_analysis
        return tr_analysis(desc.title_key)

    def _resolve_tool_title(self, tool_id: str) -> str:
        d = self.registry.get(tool_id)
        return self._resolve_title(d) if d else tool_id