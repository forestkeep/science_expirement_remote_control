# graph/ui/inspector.py
import logging
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import Qt, QTimer, QMimeData
from PyQt5.QtGui import QColor, QFont, QDrag, QPainter
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QPushButton, QGroupBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QStackedWidget, QScrollArea, QApplication,
    QColorDialog, QTextEdit, QFontDialog, QSlider,
    QAbstractButton, QAbstractSlider, QAbstractSpinBox,
    QSizePolicy, QToolButton,
)
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from graphs.helpers.ui import HelperTab

from graphs.core.curve_data import LineStyle
from graphs.core.filters_instance_class import FilterCommand
from graphs.core.undo_commands import (RenameCurveCommand, ChangeCurveStyleCommand,
                                      ApplyFilterCommand, RemoveFilterCommand,
                                      ResetFiltersCommand, EditPointCommand,
                                      ReorderFiltersCommand)
from graphs.utils.line_styles import PRESETS_LINE
from graphs.analysis.ui.analysis_tab import AnalysisTab

logger = logging.getLogger(__name__)

def _status(session, message: str, timeout: int = 3000) -> None:
    """Записать сообщение в общую строку состояния приложения.

    Использует существующий StatusBar через session.session_controller.
    Никогда не бросает — если что-то не готово, просто пропускает.
    """
    try:
        ctrl = getattr(session, "session_controller", None)
        sb = getattr(ctrl, "status_bar", None) if ctrl is not None else None
        if sb is not None:
            sb.set_status(message, timeout)
    except Exception:
        logger.exception("inspector: status bar update failed")
# =====================================================================
# Инспектор
# =====================================================================
class Inspector(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.selection_model = session.selection_model
        self.undo_manager = session.undo_manager
        self.graph_main = session.graph_main

        self.setMinimumWidth(240)

        self.stack = QStackedWidget()
        self.graph_settings = GraphSettingsWidget(session, self)
        self.curve_inspector = CurveInspectorWidget(session, self)

        # «График» и «Хелперы» — соседние вкладки, когда ничего не выделено
        self.no_selection_tabs = QTabWidget()
        self.no_selection_tabs.addTab(self.graph_settings, "График")
        self.helper_tab = HelperTab(session.helper_manager, self)
        self.no_selection_tabs.addTab(self.helper_tab, "Хелперы")

        self.stack.addWidget(self.no_selection_tabs)
        self.stack.addWidget(self.curve_inspector)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.selection_model.selection_changed.connect(self._on_selection_changed)
        self._on_selection_changed(self.selection_model.current())

    # и в _on_selection_changed:
    def _on_selection_changed(self, selected):
        facades = []
        for s in selected:
            f = self._to_facade(s)
            if f is not None and f not in facades:
                facades.append(f)

        if facades:
            self.stack.setCurrentWidget(self.curve_inspector)
            self.curve_inspector.set_curves(facades)
        else:
            self.stack.setCurrentWidget(self.no_selection_tabs)
            self.graph_settings.update_settings()
    def _to_facade(self, item):
        if hasattr(item, "change_name"):  # уже фасад
            return item
        store = getattr(item, "store", None)
        if store is None:
            return None
        rel = getattr(store, "rel_data", None)
        root = getattr(rel, "root_name", None) if rel is not None else None
        if root is None:
            return None
        return self.graph_main.get_curves().get(root)

    def reset_width(self):
        self.setMinimumWidth(240)
        self.setMaximumWidth(16777215)
        self.resize(320, self.height())


# =====================================================================
# Вкладка "График" — когда ничего не выделено
# =====================================================================
class GraphSettingsWidget(QWidget):
    """Вкладка настроек графика (когда ничего не выделено)."""

    AXIS_TITLES = {
        "bottom": "Ось X (нижняя)",
        "left":   "Ось Y1 (левая)",
        "right":  "Ось Y2 (правая)",
    }

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.graph_view = session.graph_main.graphView
        self._suppress = False
        self._axis_widgets = {}
        self._legend_font = QFont("Arial", 10)
        self.setup_ui()
        self.update_settings()

        session.undo_manager.state_changed.connect(self._on_undo_state_changed)

    # ==================================================================
    # Построение UI
    # ==================================================================
    def setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setStyleSheet("""
            QGroupBox {
                border: 1px solid #555;
                border-radius: 4px;
                margin-top: 16px;
                padding: 10px 6px 6px 6px;
                background-color: rgba(255, 255, 255, 8);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 8px;
                padding: 2px 10px;
                background-color: #3a3a3a;
                border: 1px solid #666;
                border-radius: 3px;
                color: #f0f0f0;
                font-weight: bold;
            }
        """)
        main = QVBoxLayout(content)
        main.setContentsMargins(6, 6, 6, 6)
        main.setSpacing(14)

        main.addWidget(self._build_general_group())
        main.addWidget(self._build_grid_group())

        self.axes_container = self._build_axes_container()
        main.addWidget(self.axes_container)

        self.common_axis_group = self._build_common_axis_style_group()
        self.common_axis_group.setVisible(False)
        main.addWidget(self.common_axis_group)

        main.addWidget(self._build_legend_group())
        main.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)
        self._sync_edit_all_axes_visibility(
            self.edit_all_axes_check.isChecked()
        )

    def _on_edit_all_axes_toggled(self, state):
        if self._suppress:
            return
        enabled = state != 0
        self._sync_edit_all_axes_visibility(enabled)
        if enabled:
            self._load_common_axis_style()
        else:
            self.update_settings()

    def _sync_edit_all_axes_visibility(self, enabled: bool) -> None:
        """Показать либо группу «Стиль всех осей», либо отдельные оси.

        Идемпотентна — можно вызывать из init, из update_settings,
        из восстановления проекта. Содержимое полей не перезагружает.
        """
        if self.axes_container is None or self.common_axis_group is None:
            return
        self.axes_container.setVisible(not enabled)
        self.common_axis_group.setVisible(enabled)

    def _make_group(self, title: str, expanded: bool = True):
        box = CollapsibleGroupBox(title, expanded=expanded)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        box.contentLayout().addLayout(form)
        return box, form

    @staticmethod
    def _make_color_btn():
        """Маленькая кнопка-свотч без текста."""
        btn = QPushButton()
        btn.setFixedSize(32, 20)
        btn.setToolTip("Нажмите для выбора цвета")
        return btn

    def _build_general_group(self):
        box, f = self._make_group("График")

        self.title_edit = QLineEdit()
        self.title_edit.editingFinished.connect(self.apply_general)
        f.addRow("Заголовок:", self.title_edit)

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("—")
        for preset in getattr(self.graph_view, "preset_styles", []):
            self.preset_combo.addItem(preset.get("name", "?"))
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        f.addRow("Пресет:", self.preset_combo)

        self.bg_btn = self._make_color_btn()
        self.bg_btn.clicked.connect(self.choose_bg_color)
        f.addRow("Цвет фона:", self.bg_btn)

        self.antialias_check = QCheckBox("Сглаживание линий")
        self.antialias_check.stateChanged.connect(self.apply_general)
        f.addRow(self.antialias_check)

        self.edit_all_axes_check = QCheckBox("Редактировать стиль для всех")
        self.edit_all_axes_check.setToolTip(
            "Редактировать цвет и шрифты осей X, Y1, Y2 одновременно. "
            "Изменение любого параметра применяется ко всем осям только в "
            "момент подтверждения в диалоге."
        )
        self.edit_all_axes_check.setChecked(True)
        self.edit_all_axes_check.stateChanged.connect(self._on_edit_all_axes_toggled)
        f.addRow(self.edit_all_axes_check)

        return box

    def _load_common_axis_style(self):
        controller = self.graph_view.axises.get("bottom")
        if controller is None:
            return

        prev = self._suppress
        self._suppress = True
        try:
            try:
                color = controller.axis.textPen().color().name()
            except Exception:
                color = "#000000"
            self._set_btn_color(self.common_axis_color_btn, color)

            try:
                ps = controller.label.font().pointSize()
                if ps > 0:
                    self.common_axis_font_size.setValue(ps)
            except Exception:
                pass

            try:
                tick_font = controller.axis.style.get("tickFont")
                if tick_font is not None:
                    tps = tick_font.pointSize()
                    if tps > 0:
                        self.common_axis_tick_font_size.setValue(tps)
            except Exception:
                pass
        finally:
            self._suppress = prev

    def apply_preset(self, name):
        if self._suppress or name == "—":
            return
        for preset in getattr(self.graph_view, "preset_styles", []):
            if preset.get("name") == name:
                gv_main = self.graph_view
                def mutate():
                    for gv in self._all_graph_views():
                        try:
                            gv.apply_preset_style(preset)
                        except Exception:
                            logger.exception("apply_preset: %r", gv)
                gv_main.apply_appearance_change(mutate)
                self.update_settings()
                _status(self.session, f"Пресет применён: {name}", 2500)
                return

    def _build_grid_group(self):
        box, f = self._make_group("Сетка")

        self.grid_x_check = QCheckBox("Показывать сетку по X")
        self.grid_x_check.stateChanged.connect(self.apply_grid)
        f.addRow(self.grid_x_check)

        self.grid_y_check = QCheckBox("Показывать сетку по Y")
        self.grid_y_check.stateChanged.connect(self.apply_grid)
        f.addRow(self.grid_y_check)

        self.grid_color_btn = self._make_color_btn()
        self.grid_color_btn.clicked.connect(self.choose_grid_color)
        f.addRow("Цвет сетки:", self.grid_color_btn)

        self.grid_alpha = QSpinBox()
        self.grid_alpha.setRange(0, 100)
        self.grid_alpha.setSuffix(" %")
        self.grid_alpha.setToolTip("Интенсивность линий сетки (0 % — полностью прозрачные)")
        self.grid_alpha.setValue(100)
        self.grid_alpha.valueChanged.connect(self.apply_grid)
        f.addRow("Интенсивность:", self.grid_alpha)

        return box

    def _build_axis_group(self, key: str):
        box, f = self._make_group(self.AXIS_TITLES[key])
        w = {}

        w["label"] = QLineEdit()
        w["label"].editingFinished.connect(lambda k=key: self.apply_axis(k))
        f.addRow("Подпись:", w["label"])

        w["color_btn"] = self._make_color_btn()
        w["color_btn"].clicked.connect(lambda _, k=key: self.choose_axis_color(k))
        f.addRow("Цвет оси и делений:", w["color_btn"])

        w["font_btn"] = QPushButton("Шрифт подписи")
        w["font_btn"].clicked.connect(lambda _, k=key: self.choose_axis_font(k))
        f.addRow(w["font_btn"])

        w["tick_btn"] = QPushButton("Шрифт делений")
        w["tick_btn"].clicked.connect(lambda _, k=key: self.choose_axis_tick_font(k))
        f.addRow(w["tick_btn"])

        w["invert"] = QCheckBox("Инвертировать ось")
        w["invert"].stateChanged.connect(lambda _, k=key: self.apply_axis(k))
        f.addRow(w["invert"])

        w["visible"] = QCheckBox("Показывать ось")
        w["visible"].stateChanged.connect(lambda _, k=key: self.apply_axis(k))
        f.addRow(w["visible"])

        if key in ("bottom", "left"):
            w["log"] = QCheckBox("Логарифмическая шкала")
            w["log"].stateChanged.connect(lambda _, k=key: self.apply_axis(k))
            f.addRow(w["log"])
        else:
            w["log"] = None

        self._axis_widgets[key] = w
        return box

    def _build_legend_group(self):
        box, f = self._make_group("Легенда")

        self.legend_check = QCheckBox("Показывать легенду")
        self.legend_check.stateChanged.connect(self.apply_legend)
        f.addRow(self.legend_check)

        self.legend_color_btn = self._make_color_btn()
        self.legend_color_btn.clicked.connect(self.choose_legend_color)
        f.addRow("Цвет текста:", self.legend_color_btn)

        self.legend_font_btn = QPushButton("Шрифт...")
        self.legend_font_btn.clicked.connect(self.choose_legend_font)
        f.addRow("Шрифт:", self.legend_font_btn)

        self.legend_font_size_spin = QSpinBox()
        self.legend_font_size_spin.setRange(6, 48)
        self.legend_font_size_spin.setValue(10)
        self.legend_font_size_spin.setSuffix(" pt")
        self.legend_font_size_spin.valueChanged.connect(self.apply_legend_font)
        f.addRow("Размер шрифта:", self.legend_font_size_spin)

        return box
    
    
    # ==================================================================
    # Синхронизация UI с текущим состоянием виджета
    # ==================================================================
    def _on_undo_state_changed(self):
        # При undo/redo виджет меняется снаружи — синхронизируем поля.
        self.update_settings()

    def update_settings(self):
        from graphs.hdf5_io.utils import extract_plot_widget_settings
        try:
            settings = extract_plot_widget_settings(self.graph_view)
        except Exception:
            logger.exception("GraphSettingsWidget.update_settings: extract failed")
            return

        self._suppress = True
        try:
            self.title_edit.setText(settings.title or "")
            self.antialias_check.setChecked(bool(settings.antialiasing))
            self._set_btn_color(self.bg_btn, settings.background_color)

            self.grid_x_check.setChecked(bool(getattr(settings, "x_grid_enabled", settings.grid_enabled)))
            self.grid_y_check.setChecked(bool(getattr(settings, "y_grid_enabled", settings.grid_enabled)))
            self._set_btn_color(self.grid_color_btn, settings.grid_color)
            try:
                self.grid_alpha.setValue(int(round(float(settings.grid_alpha) * 100)))
            except Exception:
                self.grid_alpha.setValue(100)

            if hasattr(self.graph_view, "get_legend_font"):
                try:
                    self._legend_font = self.graph_view.get_legend_font()
                    self.legend_font_size_spin.blockSignals(True)
                    try:
                        self.legend_font_size_spin.setValue(self._legend_font.pointSize())
                    finally:
                        self.legend_font_size_spin.blockSignals(False)
                except Exception:
                    pass

            for key, w in self._axis_widgets.items():
                axis_model = settings.axes.get(key)
                if axis_model is None:
                    continue
                w["label"].setText(axis_model.label or "")
                w["invert"].setChecked(bool(axis_model.is_inverted))
                w["visible"].setChecked(bool(axis_model.is_visible))
                if w["log"] is not None:
                    w["log"].setChecked(bool(axis_model.log_mode))

                controller = self.graph_view.axises.get(key)
                if controller is not None:
                    try:
                        color = controller.axis.textPen().color().name()
                    except Exception:
                        color = self._color_from_btn(w["color_btn"])
                    self._set_btn_color(w["color_btn"], color)

            self.legend_check.setChecked(bool(settings.legend_enabled))
            self._set_btn_color(self.legend_color_btn, settings.legend_text_color)

            if self.edit_all_axes_check.isChecked():
                self._load_common_axis_style()

            preset_name = getattr(settings, 'applied_preset_name', '—')
            idx = self.preset_combo.findText(preset_name)
            if idx >= 0:
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentIndex(idx)
                self.preset_combo.blockSignals(False)
        finally:
            self._suppress = False

        self._sync_edit_all_axes_visibility(
            self.edit_all_axes_check.isChecked()
        )
        if self.edit_all_axes_check.isChecked():
            self._load_common_axis_style()

    # ==================================================================
    # Мутации (каждая оборачивается в undo-команду и пишет в статус-бар)
    # ==================================================================

    def apply_general(self, *_):
        if self._suppress:
            return
        title = self.title_edit.text()
        antialias = self.antialias_check.isChecked()
        gv_main = self.graph_view

        def mutate():
            for gv in self._all_graph_views():
                try:
                    gv.setTitle(title)
                    gv.setAntialiasing(antialias)
                except Exception:
                    logger.exception("apply_general: %r", gv)

        gv_main.apply_appearance_change(mutate)
        _status(self.session, "Настройки графика обновлены", 2000)

    def apply_grid(self, *_):
        if self._suppress:
            return
        show_x = self.grid_x_check.isChecked()
        show_y = self.grid_y_check.isChecked()
        alpha = int(round(self.grid_alpha.value() / 100.0 * 255))
        color = QColor(self._color_from_btn(self.grid_color_btn))
        gv_main = self.graph_view

        def mutate():
            for gv in self._all_graph_views():
                try:
                    bottom = gv.plotItem.getAxis("bottom")
                    left = gv.plotItem.getAxis("left")
                    bottom.setPen(color)
                    left.setPen(color)
                    bottom.setGrid(alpha if show_x else False)
                    left.setGrid(alpha if show_y else False)
                    gv.is_grid_shown = bool(show_x or show_y)
                except Exception:
                    logger.exception("apply_grid: %r", gv)

        gv_main.apply_appearance_change(mutate)
        _status(self.session, "Сетка обновлена", 2000)

    def apply_axis(self, key):
        if self._suppress:
            return
        w = self._axis_widgets.get(key)
        if w is None:
            return
        label = w["label"].text()
        visible = w["visible"].isChecked()
        invert = w["invert"].isChecked()
        log_on = w["log"].isChecked() if w["log"] is not None else None
        gv_main = self.graph_view

        def mutate():
            for gv in self._all_graph_views():
                controller = gv.axises.get(key)
                if controller is None:
                    continue
                try:
                    controller.settings.label = label
                    controller.setLabel(label)
                    controller.settings.is_visible = visible
                    if visible:
                        controller.show()
                    else:
                        controller.hide()
                    controller.settings.is_inverted = invert
                    if key == "bottom":
                        gv.invert_x_axis(invert)
                    elif key == "left":
                        gv.invert_y_axis(invert)
                    elif key == "right":
                        gv.invert_y2_axis(invert)
                    if log_on is not None:
                        cur_x = bool(getattr(gv.plotItem, "_log_x_on", False))
                        cur_y = bool(getattr(gv.plotItem, "_log_y_on", False))
                        if key == "bottom":
                            cur_x = log_on
                        elif key == "left":
                            cur_y = log_on
                        gv.plotItem.setLogMode(x=cur_x, y=cur_y)
                        gv.plotItem._log_x_on = cur_x
                        gv.plotItem._log_y_on = cur_y
                        controller.settings.log_mode = bool(log_on)
                except Exception:
                    logger.exception("apply_axis %s: %r", key, gv)

        gv_main.apply_appearance_change(mutate)
        _status(self.session, f"Ось «{self.AXIS_TITLES.get(key, key)}» обновлена", 2000)
    
    def apply_legend(self, *_):
        if self._suppress:
            return
        show = self.legend_check.isChecked()
        gv_main = self.graph_view

        def mutate():
            for gv in self._all_graph_views():
                for legend in (getattr(gv, "legend", None), getattr(gv, "legend2", None)):
                    if legend is not None:
                        legend.setVisible(show)

        gv_main.apply_appearance_change(mutate)
        _status(self.session, "Легенда обновлена", 2000)

    _AXIS_KEYS = ("bottom", "left", "right")

    def _choose_common_axis_color(self):
        c = QColorDialog.getColor(QColor(self._color_from_btn(self.common_axis_color_btn)))
        if not c.isValid():
            return
        self._set_btn_color(self.common_axis_color_btn, c.name())
        gv = self.graph_view
        color_name = c.name()

        def mutate():
            for key in self._AXIS_KEYS:
                ctrl = gv.axises.get(key)
                if ctrl is None:
                    continue
                ctrl.custom_style.color = color_name
                ctrl.set_custom_style(ctrl.custom_style)

        gv.apply_appearance_change(mutate)
        _status(self.session, "Цвет всех осей обновлён", 2000)

    def _choose_common_axis_font(self):
        controller = self.graph_view.axises.get("bottom")
        if controller is None:
            return
        current = controller.label.font()
        font, ok = QFontDialog.getFont(current, self, "Шрифт подписи оси")
        if not ok:
            return
        family = font.family()
        gv = self.graph_view

        def mutate():
            for key in self._AXIS_KEYS:
                ctrl = gv.axises.get(key)
                if ctrl is None:
                    continue
                new_font = QFont(ctrl.label.font())
                new_font.setFamily(family)
                ctrl.custom_style.text_font = new_font
                ctrl.set_custom_style(ctrl.custom_style)

        gv.apply_appearance_change(mutate)
        _status(self.session, "Шрифт подписей осей обновлён", 2000)

    def _apply_common_axis_font_size(self, size):
        if self._suppress:
            return
        size = int(size)
        gv = self.graph_view

        def mutate():
            for key in self._AXIS_KEYS:
                ctrl = gv.axises.get(key)
                if ctrl is None:
                    continue
                new_font = QFont(ctrl.label.font())
                new_font.setPointSize(size)
                ctrl.custom_style.text_font = new_font
                ctrl.set_custom_style(ctrl.custom_style)

        gv.apply_appearance_change(mutate)
        _status(self.session, "Размер шрифта подписей осей обновлён", 2000)

    def _choose_common_axis_tick_font(self):
        controller = self.graph_view.axises.get("bottom")
        if controller is None:
            return
        current = controller.axis.style.get("tickFont") or QFont()
        font, ok = QFontDialog.getFont(current, self, "Шрифт делений оси")
        if not ok:
            return
        family = font.family()
        gv = self.graph_view

        def mutate():
            for key in self._AXIS_KEYS:
                ctrl = gv.axises.get(key)
                if ctrl is None:
                    continue
                cur = ctrl.axis.style.get("tickFont") or QFont()
                new_font = QFont(cur)
                new_font.setFamily(family)
                ctrl.custom_style.tick_font = new_font
                ctrl.set_custom_style(ctrl.custom_style)

        gv.apply_appearance_change(mutate)
        _status(self.session, "Шрифт делений осей обновлён", 2000)

    def _apply_common_axis_tick_font_size(self, size):
        if self._suppress:
            return
        size = int(size)
        gv = self.graph_view

        def mutate():
            for key in self._AXIS_KEYS:
                ctrl = gv.axises.get(key)
                if ctrl is None:
                    continue
                cur = ctrl.axis.style.get("tickFont") or QFont()
                new_font = QFont(cur)
                new_font.setPointSize(size)
                ctrl.custom_style.tick_font = new_font
                ctrl.set_custom_style(ctrl.custom_style)

        gv.apply_appearance_change(mutate)
        _status(self.session, "Размер шрифта делений осей обновлён", 2000)


    # ==================================================================
    # Диалоги выбора цвета / шрифтов (тоже через undo-обёртку)
    # ==================================================================
    def choose_bg_color(self):
        c = QColorDialog.getColor(QColor(self._color_from_btn(self.bg_btn)))
        if not c.isValid():
            return
        self._set_btn_color(self.bg_btn, c.name())
        gv = self.graph_view
        gv.apply_appearance_change(lambda: gv.setCustomBackgroundColor(c))
        _status(self.session, "Цвет фона обновлён", 2000)

    def choose_grid_color(self):
        c = QColorDialog.getColor(QColor(self._color_from_btn(self.grid_color_btn)))
        if not c.isValid():
            return
        self._set_btn_color(self.grid_color_btn, c.name())
        # повторно применяем сетку уже с новым цветом
        self.apply_grid()

    def choose_axis_color(self, key):
        w = self._axis_widgets[key]
        c = QColorDialog.getColor(QColor(self._color_from_btn(w["color_btn"])))
        if not c.isValid():
            return
        self._set_btn_color(w["color_btn"], c.name())
        gv = self.graph_view

        def mutate():
            ctrl = gv.axises.get(key)
            if ctrl is None:
                return
            ctrl.custom_style.color = c.name()
            ctrl.set_custom_style(ctrl.custom_style)

        gv.apply_appearance_change(mutate)
        _status(self.session, f"Цвет оси {key} обновлён", 2000)

    def choose_axis_font(self, key):
        controller = self.graph_view.axises.get(key)
        if controller is None:
            return
        current = controller.label.font()
        font, ok = QFontDialog.getFont(current, self, "Шрифт подписи оси")
        if not ok:
            return
        gv = self.graph_view

        def mutate():
            ctrl = gv.axises.get(key)
            if ctrl is None:
                return
            ctrl.custom_style.text_font = font
            ctrl.set_custom_style(ctrl.custom_style)

        gv.apply_appearance_change(mutate)
        _status(self.session, f"Шрифт подписи оси {key} обновлён", 2000)

    def choose_axis_tick_font(self, key):
        controller = self.graph_view.axises.get(key)
        if controller is None:
            return
        current = controller.axis.style.get("tickFont") or QFont()
        font, ok = QFontDialog.getFont(current, self, "Шрифт делений оси")
        if not ok:
            return
        gv = self.graph_view

        def mutate():
            ctrl = gv.axises.get(key)
            if ctrl is None:
                return
            ctrl.custom_style.tick_font = font
            ctrl.set_custom_style(ctrl.custom_style)

        gv.apply_appearance_change(mutate)
        _status(self.session, f"Шрифт делений оси {key} обновлён", 2000)

    def _build_axes_container(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        for key in ("bottom", "left", "right"):
            layout.addWidget(self._build_axis_group(key))
        return container

    def _build_common_axis_style_group(self):
        box, f = self._make_group("Стиль всех осей")

        self.common_axis_color_btn = self._make_color_btn()
        self.common_axis_color_btn.clicked.connect(self._choose_common_axis_color)
        f.addRow("Цвет оси и делений:", self.common_axis_color_btn)

        self.common_axis_font_btn = QPushButton("Шрифт подписи")
        self.common_axis_font_btn.clicked.connect(self._choose_common_axis_font)
        f.addRow(self.common_axis_font_btn)

        self.common_axis_font_size = QSpinBox()
        self.common_axis_font_size.setRange(6, 72)
        self.common_axis_font_size.setSuffix(" pt")
        self.common_axis_font_size.valueChanged.connect(
            self._apply_common_axis_font_size
        )
        f.addRow("Размер шрифта подписи:", self.common_axis_font_size)

        self.common_axis_tick_font_btn = QPushButton("Шрифт делений")
        self.common_axis_tick_font_btn.clicked.connect(
            self._choose_common_axis_tick_font
        )
        f.addRow(self.common_axis_tick_font_btn)

        self.common_axis_tick_font_size = QSpinBox()
        self.common_axis_tick_font_size.setRange(6, 72)
        self.common_axis_tick_font_size.setSuffix(" pt")
        self.common_axis_tick_font_size.valueChanged.connect(
            self._apply_common_axis_tick_font_size
        )
        f.addRow("Размер шрифта делений:", self.common_axis_tick_font_size)

        return box


    def choose_legend_color(self):
        c = QColorDialog.getColor(QColor(self._color_from_btn(self.legend_color_btn)))
        if not c.isValid():
            return
        self._set_btn_color(self.legend_color_btn, c.name())
        gv = self.graph_view

        def mutate():
            try:
                gv.set_legend_color(c)
            except Exception:
                logger.exception("choose_legend_color failed")

        gv.apply_appearance_change(mutate)
        _status(self.session, "Цвет легенды обновлён", 2000)

    def apply_legend_font(self, *_):
        if self._suppress:
            return
        new_font = QFont(self._legend_font)
        new_font.setPointSize(int(self.legend_font_size_spin.value()))
        self._legend_font = new_font
        self._apply_font_to_all_views(new_font)
        _status(self.session, "Шрифт легенды обновлён", 2000)

    def choose_legend_font(self):
        font, ok = QFontDialog.getFont(self._legend_font, self, "Шрифт легенды")
        if not ok:
            return
        self._legend_font = font
        self._suppress = True
        try:
            self.legend_font_size_spin.setValue(font.pointSize())
        finally:
            self._suppress = False
        self._apply_font_to_all_views(font)
        _status(self.session, "Шрифт легенды обновлён", 2000)

    def _apply_font_to_all_views(self, font):
        for gv in self._all_graph_views():
            if hasattr(gv, "set_legend_font"):
                gv.set_legend_font(font)

    # ==================================================================
    # Утилиты
    # ==================================================================
    @staticmethod
    def _set_btn_color(btn, color: str):
        btn.setStyleSheet(f"background-color: {color};")

    @staticmethod
    def _color_from_btn(btn, fallback="#ffffff") -> str:
        css = btn.styleSheet() or ""
        for token in css.split(";"):
            token = token.strip()
            if token.startswith("background-color"):
                _, _, val = token.partition(":")
                val = val.strip()
                if val:
                    return val
        return fallback

    def _all_graph_views(self):
        """Все PatchedPlotWidget текущей сессии: основной, attached-панели, domain-вкладки."""
        views = []
        main = getattr(self.session, "graph_main", None)
        if main is not None and getattr(main, "graphView", None) is not None:
            views.append(main.graphView)

        ctrl = getattr(self.session, "analysis_controller", None)
        if ctrl is not None:
            renderer = getattr(ctrl, "renderer", None)
            if renderer is not None:
                for info in getattr(renderer._attached, "_panels", {}).values():
                    p = info.get("plot")
                    if p is not None and p not in views:
                        views.append(p)
                for info in getattr(renderer._domain, "_tabs", {}).values():
                    p = info.get("plot")
                    if p is not None and p not in views:
                        views.append(p)
        return views
# =====================================================================
# Контейнер вкладок для кривых
# =====================================================================
class CurveInspectorWidget(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.curves = []
        self.setup_ui()

    def setup_ui(self):
        self.tabs = QTabWidget()
        self.data_tab = DataTab(self.session, self)
        self.note_tab = NoteTab(self.session, self)
        self.style_tab = StyleTab(self.session, self)
        self.filters_tab = FiltersTab(self.session, self)
        self.tools_tab = AnalysisTab(self.session, self)

        self.tabs.addTab(self.data_tab, "Данные")
        self.tabs.addTab(self.note_tab, "Заметка")
        self.tabs.addTab(self.style_tab, "Стиль")
        self.tabs.addTab(self.filters_tab, "Фильтры")
        self.tabs.addTab(self.tools_tab, "Анализ")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)

    def set_curves(self, curves):
        # страховка: пропускаем всё, что не является фасадом
        curves = [c for c in curves if hasattr(c, "change_name")]
        self.curves = curves
        self.data_tab.set_curves(curves)
        self.note_tab.set_curves(curves)
        self.style_tab.set_curves(curves)
        self.filters_tab.set_curves(curves)
        self.tools_tab.set_curves(curves)


# =====================================================================
# Вкладка "Данные"
# =====================================================================
class DataTab(QWidget):
    POINTS_LIMIT = 100

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.curves = []
        self._suppress_item_changed = False
        self.setup_ui()

        # синхронизация таблицы точек с undo/redo и любым изменением кривой
        session.undo_manager.state_changed.connect(self._populate_points)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.name_edit = QLineEdit()
        self.name_edit.editingFinished.connect(self.rename_curve)
        layout.addWidget(QLabel("Название:"))
        layout.addWidget(self.name_edit)

        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        layout.addWidget(QLabel("Статистика:"))
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.stats_table)

        layout.addWidget(QLabel("Точки (двойной клик — редактирование):"))
        self.points_table = QTableWidget()
        self.points_table.setColumnCount(2)
        self.points_table.setHorizontalHeaderLabels(["X", "Y"])
        self.points_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.points_table.itemChanged.connect(self._on_point_item_changed)
        layout.addWidget(self.points_table)

        btn_layout = QHBoxLayout()
        self.show_all_btn = QPushButton("Показать все")
        self.show_all_btn.clicked.connect(lambda: self._populate_points(limit=None))
        self.export_btn = QPushButton("Экспорт в CSV")
        btn_layout.addWidget(self.show_all_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    def set_curves(self, curves):
        # Форсируем актуальность статистики перед чтением
        for c in curves:
            try:
                c.ensure_stats_fresh()
            except Exception:
                logger.exception("DataTab: ensure_stats_fresh failed")

        self.curves = curves
        if not curves:
            self.name_edit.clear()
            self.info_label.clear()
            self.stats_table.setRowCount(0)
            self.points_table.setRowCount(0)
            return

        if len(curves) == 1:
            curve = curves[0]
            self.name_edit.setEnabled(True)
            self.name_edit.setText(curve.curve_name)
            rel = curve.rel_data
            stats = curve.tree_item.parameters
            lines = [
                f"X: {rel.x_current_name}",
                f"Y: {rel.y_current_name}",
                f"Тип: {stats.get('tip', 'linear')}",
                f"ID: {stats.get('id', '')}",
                f"Точек: {len(curve.raw_data_x)}",
            ]
            self.info_label.setText("\n".join(lines))

            self.stats_table.setRowCount(len(stats))
            for i, (k, v) in enumerate(stats.items()):
                self.stats_table.setItem(i, 0, QTableWidgetItem(str(k)))
                self.stats_table.setItem(i, 1, QTableWidgetItem(str(v)))

            self._populate_points()

        else:
            self.name_edit.setEnabled(False)
            self.name_edit.clear()
            self.info_label.setText(f"Выделено кривых: {len(curves)}")
            self.stats_table.setColumnCount(4)
            self.stats_table.setHorizontalHeaderLabels(["Имя", "Тип", "Min Y", "Max Y"])
            self.stats_table.setRowCount(len(curves))
            for i, curve in enumerate(curves):
                stats = curve.tree_item.parameters
                min_y = stats.get("min_y")
                max_y = stats.get("max_y")
                self.stats_table.setItem(i, 0, QTableWidgetItem(curve.curve_name))
                self.stats_table.setItem(i, 1, QTableWidgetItem(str(stats.get("tip") or "linear")))
                self.stats_table.setItem(i, 2, QTableWidgetItem(str(min_y) if min_y is not None else "-"))
                self.stats_table.setItem(i, 3, QTableWidgetItem(str(max_y) if max_y is not None else "-"))
            self.points_table.setRowCount(0)

    # ------------------------------------------------------------------
    def _populate_points(self, limit=POINTS_LIMIT):
        self._suppress_item_changed = True
        try:
            if len(self.curves) != 1:
                self.points_table.setRowCount(0)
                return
            curve = self.curves[0]
            x = curve.store.raw_data_x
            y = curve.store.raw_data_y
            total = len(x)
            n = total if limit is None else min(int(limit), total)

            self.points_table.setRowCount(n)
            for i in range(n):
                self.points_table.setItem(i, 0, QTableWidgetItem(f"{float(x[i]):.6g}"))
                self.points_table.setItem(i, 1, QTableWidgetItem(f"{float(y[i]):.6g}"))
        finally:
            self._suppress_item_changed = False

    # ------------------------------------------------------------------
    def _on_point_item_changed(self, item):
        if self._suppress_item_changed or len(self.curves) != 1:
            return
        curve = self.curves[0]
        row = item.row()
        col = item.column()

        if row >= len(curve.store.raw_data_x):
            self._populate_points()
            return

        try:
            new_val = float(str(item.text()).replace(",", ".").strip())
        except ValueError:
            self._populate_points()
            _status(self.session, "Некорректное значение точки — откат", 3000)
            return

        old_x = float(curve.store.raw_data_x[row])
        old_y = float(curve.store.raw_data_y[row])
        new_x = new_val if col == 0 else old_x
        new_y = new_val if col == 1 else old_y

        if new_x == old_x and new_y == old_y:
            return

        # Форсируем актуальность filtered, чтобы следующее чтение таблицы
        # и статистики увидело свежие данные (важно для «медленного пути» —
        # пересборки фильтров с дебаунсом 200 мс).
        try:
            curve.ensure_stats_fresh()
        except Exception:
            logger.exception("DataTab: ensure_stats_fresh before edit failed")

        cmd = EditPointCommand(curve, row, old_x, old_y, new_x, new_y)
        self.session.undo_manager.push(cmd, execute=True)
        # Перерисовка произойдёт автоматически по state_changed undo_manager;
        # второй ручной вызов _populate_points убран.
        _status(self.session, f"Изменена точка #{row}", 2000)

    # ------------------------------------------------------------------
    def rename_curve(self):
        if len(self.curves) != 1:
            return
        new_name = self.name_edit.text().strip()
        curve = self.curves[0]
        if not new_name or new_name == curve.curve_name:
            return
        cmd = RenameCurveCommand(curve, new_name)
        self.session.undo_manager.push(cmd, execute=True)
        _status(self.session, f"Кривая переименована: {new_name}")

# =====================================================================
# Вкладка "Заметка"
# =====================================================================
class NoteTab(QWidget):
    """
    Пользовательская заметка кривой.

    Хранится в tree_item в блоке «Разное» → «Описание»
    (та же ячейка, что редактируется из контекстного меню дерева).
    Изменения идут через AddNoteCommand → undo/redo, синхронизация
    с деревом происходит автоматически.
    """

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.curves = []
        self.setup_ui()

        # синхронизация с undo/redo
        session.undo_manager.state_changed.connect(self._reload)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Заметка пользователя:"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Введите заметку...")
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self._save)
        self.revert_btn = QPushButton("Отменить изменения")
        self.revert_btn.clicked.connect(self._reload)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.revert_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    # ------------------------------------------------------------------
    def set_curves(self, curves):
        self.curves = curves
        self._reload()

    # ------------------------------------------------------------------
    @staticmethod
    def _get_note(curve) -> str:
        try:
            return curve.tree_item.get_description() or ""
        except Exception:
            return ""

    def _reload(self, *_):
        # при выключенном (ничего не выделено) не мигаем статусом
        if len(self.curves) == 1:
            self.text_edit.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.revert_btn.setEnabled(True)
            self.text_edit.setPlainText(self._get_note(self.curves[0]))
            self.status_label.clear()
        elif len(self.curves) > 1:
            self.text_edit.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.revert_btn.setEnabled(False)
            self.text_edit.clear()
            self.status_label.setText(
                f"Выделено кривых: {len(self.curves)}. "
                f"Заметка редактируется только для одной кривой."
            )
        else:
            self.text_edit.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.revert_btn.setEnabled(False)
            self.text_edit.clear()
            self.status_label.clear()

    # ------------------------------------------------------------------
    def _save(self):
        if len(self.curves) != 1:
            return
        curve = self.curves[0]
        old_text = self._get_note(curve)
        new_text = self.text_edit.toPlainText()

        if old_text == new_text:
            self.status_label.setText("Изменений нет.")
            _status(self.session, "Заметка не изменена", 2000)
            return

        if self.session.undo_manager.is_applying:
            return

        from graphs.core.undo_commands import AddNoteCommand
        block_name = QApplication.translate("GraphWindow", "Разное")
        cmd = AddNoteCommand(
            tree_item=curve.tree_item,
            block_name=block_name,
            old_text=old_text,
            new_text=new_text,
        )
        self.session.undo_manager.push(cmd, execute=True)
        self.status_label.setText("Заметка сохранена.")
        _status(self.session, "Заметка сохранена", 2500)


# =====================================================================
# Вкладка "Стиль"
# =====================================================================
_LINE_STYLE_NAMES = {
    Qt.SolidLine: "Solid",
    Qt.DashLine: "Dash",
    Qt.DotLine: "Dot",
    Qt.DashDotLine: "DashDot",
}
_LINE_STYLE_ENUM = {v: k for k, v in _LINE_STYLE_NAMES.items()}


class StyleTab(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.curves = []
        self._suppress_apply = False
        self._style_form = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._style_form = form

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("—")
        self.preset_combo.addItems(PRESETS_LINE.keys())
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        form.addRow("Пресеты:", self.preset_combo)

        self.color_btn = QPushButton("Цвет линии")
        self.color_btn.clicked.connect(self.choose_color)
        form.addRow(self.color_btn)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10)
        self.width_spin.valueChanged.connect(self.apply_style)
        form.addRow("Толщина:", self.width_spin)

        self.style_combo = QComboBox()
        self.style_combo.addItems(list(_LINE_STYLE_NAMES.values()))
        self.style_combo.currentIndexChanged.connect(self.apply_style)
        form.addRow("Стиль линии:", self.style_combo)

        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems([
            "None", "o", "s", "t", "t1", "t2", "t3", "d", "+", "x",
            "p", "h", "star", "|", "_", "arrow_up", "arrow_right",
            "arrow_down", "arrow_left", "crosshair",
        ])
        self.symbol_combo.currentIndexChanged.connect(self.apply_style)
        form.addRow("Маркер:", self.symbol_combo)

        self.symbol_size = QSpinBox()
        self.symbol_size.setRange(1, 20)
        self.symbol_size.valueChanged.connect(self.apply_style)
        form.addRow("Размер маркера:", self.symbol_size)

        self.sync_symbol_color_check = QCheckBox("Цвет маркера как у линии")
        self.sync_symbol_color_check.setChecked(True)
        self.sync_symbol_color_check.setToolTip(
            "Если включено, цвет маркера и его заливки совпадает с цветом линии "
            "и задаётся одной кнопкой «Цвет линии»."
        )
        self.sync_symbol_color_check.stateChanged.connect(self._on_sync_toggled)
        form.addRow(self.sync_symbol_color_check)

        self.symbol_color_btn = QPushButton("Цвет маркера")
        self.symbol_color_btn.clicked.connect(self.choose_symbol_color)
        form.addRow("Цвет маркера:", self.symbol_color_btn)

        self.fill_color_btn = QPushButton("Цвет заливки")
        self.fill_color_btn.clicked.connect(self.choose_fill_color)
        form.addRow("Цвет заливки:", self.fill_color_btn)

        self.px_mode_check = QCheckBox("Режим пикселей (pxMode)")
        self.px_mode_check.stateChanged.connect(self.apply_style)
        form.addRow(self.px_mode_check)

        layout.addLayout(form)
        layout.addStretch()

        self._apply_sync_visibility()

    # ------------------------------------------------------------------
    def _apply_sync_visibility(self) -> None:
        sync = self.sync_symbol_color_check.isChecked()
        for widget in (self.symbol_color_btn, self.fill_color_btn):
            widget.setVisible(not sync)
            label = self._style_form.labelForField(widget)
            if label is not None:
                label.setVisible(not sync)

    def _on_sync_toggled(self, state: int) -> None:
        self._apply_sync_visibility()
        if self._suppress_apply:
            return
        if state != 0:
            color = self._color_from_btn(self.color_btn)
            self._set_btn_color(self.symbol_color_btn, color)
            self._set_btn_color(self.fill_color_btn, color)
            self.apply_style()

    # ------------------------------------------------------------------
    @staticmethod
    def _color_from_btn(btn, fallback="#ffffff"):
        css = btn.styleSheet()
        for token in css.split(";"):
            token = token.strip()
            if token.startswith("background-color"):
                _, _, val = token.partition(":")
                val = val.strip()
                if val:
                    return val
        return fallback

    def _set_btn_color(self, btn, color: str):
        btn.setStyleSheet(f"background-color: {color};")

    def set_curves(self, curves):
        self.curves = curves
        if not curves:
            return
        self._suppress_apply = True
        try:
            curve = curves[0]
            style = curve.saved_style
            if style is None:
                return
            self.width_spin.setValue(int(style.line_width or 1))
            self.symbol_size.setValue(int(style.symbol_size or 1))
            self._set_btn_color(self.color_btn, str(style.color))
            self._set_btn_color(self.symbol_color_btn, str(style.symbol_color))
            self._set_btn_color(self.fill_color_btn, str(style.fill_color))

            name = _LINE_STYLE_NAMES.get(style.line_style, "Solid")
            self.style_combo.setCurrentText(name)

            sym = style.symbol if style.symbol else "None"
            idx = self.symbol_combo.findText(sym)
            if idx >= 0:
                self.symbol_combo.setCurrentIndex(idx)

            self.px_mode_check.setChecked(bool(style.px_mode))

            sync = (
                str(style.symbol_color) == str(style.color)
                and str(style.fill_color) == str(style.color)
            )
            self.sync_symbol_color_check.setChecked(bool(sync))
        finally:
            self._suppress_apply = False

        self._apply_sync_visibility()

    def _current_style(self) -> LineStyle:
        style = LineStyle()
        style.color = self._color_from_btn(self.color_btn)
        style.line_width = int(self.width_spin.value())
        style.line_style = _LINE_STYLE_ENUM.get(self.style_combo.currentText(), Qt.SolidLine)
        sym = self.symbol_combo.currentText()
        style.symbol = None if sym == "None" else sym
        style.symbol_size = int(self.symbol_size.value())
        if self.sync_symbol_color_check.isChecked():
            style.symbol_color = style.color
            style.fill_color = style.color
        else:
            style.symbol_color = self._color_from_btn(self.symbol_color_btn)
            style.fill_color = self._color_from_btn(self.fill_color_btn)
        style.px_mode = bool(self.px_mode_check.isChecked())
        return style

    def apply_style(self, *_):
        if self._suppress_apply or not self.curves:
            return
        new_style = self._current_style()
        for curve in self.curves:
            cmd = ChangeCurveStyleCommand(curve, new_style.copy())
            self.session.undo_manager.push(cmd, execute=True)
        _status(self.session, "Стиль кривой изменён", 2000)

    def apply_preset(self, name):
        if self._suppress or name == "—":
            return
        for preset in getattr(self.graph_view, "preset_styles", []):
            if preset.get("name") == name:
                gv_main = self.graph_view
                def mutate():
                    for gv in self._all_graph_views():
                        try:
                            gv.apply_preset_style(preset)
                            gv.applied_preset_name = name
                        except Exception:
                            logger.exception("apply_preset: %r", gv)
                gv_main.apply_appearance_change(mutate)
                self.graph_view.applied_preset_name = name
                self.update_settings()
                _status(self.session, f"Пресет применён: {name}", 2500)
                return

    def choose_color(self):
        c = QColorDialog.getColor(QColor(self._color_from_btn(self.color_btn)))
        if c.isValid():
            self._set_btn_color(self.color_btn, c.name())
            if self.sync_symbol_color_check.isChecked():
                self._set_btn_color(self.symbol_color_btn, c.name())
                self._set_btn_color(self.fill_color_btn, c.name())
            self.apply_style()

    def choose_symbol_color(self):
        c = QColorDialog.getColor(QColor(self._color_from_btn(self.symbol_color_btn)))
        if c.isValid():
            self._set_btn_color(self.symbol_color_btn, c.name())
            self.apply_style()

    def choose_fill_color(self):
        c = QColorDialog.getColor(QColor(self._color_from_btn(self.fill_color_btn)))
        if c.isValid():
            self._set_btn_color(self.fill_color_btn, c.name())
            self.apply_style()
# =====================================================================
# Вкладка "Фильтры"
# =====================================================================
# ---------------------------------------------------------------------
# Схема «живых» параметров: какие параметры показывать ползунками.
# Формат: (key, label, kind, min, max, step, decimals, default)
# kind: 'int' | 'float'
# ---------------------------------------------------------------------
_FILTER_PARAM_SCHEMA = {
    "median": [
        ("window", "Окно", "int", 1, 999, 2, 0, 3),
    ],
    "average": [
        ("window", "Окно", "int", 1, 999, 1, 0, 3),
    ],
    "exp_mean": [
        ("alpha", "Коэффициент α", "float", 0.01, 1.0, 0.01, 2, 0.5),
    ],
    "hampel": [
        ("window", "Окно", "int", 3, 999, 2, 0, 5),
        ("n_sigmas", "Порог σ", "float", 0.5, 10.0, 0.1, 2, 3.0),
    ],
    "savitzky_golay": [
        ("window", "Окно", "int", 3, 999, 2, 0, 5),
        ("polyorder", "Степень", "int", 1, 10, 1, 0, 2),
    ],
    "gaussian_smooth": [
        ("window", "Окно", "int", 1, 999, 1, 0, 5),
    ],
    "butterworth": [
        ("cutoff", "Срез, Гц", "float", 0.0, 1e6, 1.0, 4, 10.0),
        ("order", "Порядок", "int", 1, 10, 1, 0, 4),
    ],
    "notch": [
        ("freq", "Частота, Гц", "float", 0.001, 1e6, 1.0, 2, 50.0),
        ("q", "Q", "float", 1.0, 1000.0, 1.0, 1, 30.0),
    ],
    "detrend": [
        ("polyorder", "Степень", "int", 1, 10, 1, 0, 2),
    ],
    "thinning": [
        ("percent", "Процент", "int", 0, 100, 1, 0, 10),
    ],
    "normalize": [],
}

_MIME_FILTER_CARD = "application/x-filter-card"


class FilterDropIndicator(QWidget):
    """Светящаяся полоска-индикатор места вставки при drag-and-drop.

    Рисуется как горизонтальная линия с мягким свечением и круглыми
    маркерами на концах. Не принимает события мыши, поэтому не мешает
    drag'у, идущему над контейнером.
    """

    INDICATOR_HEIGHT = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedHeight(self.INDICATOR_HEIGHT)
        self.setStyleSheet("background: transparent;")
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cy = h / 2.0
        left = 4
        right = w - 4

        # Мягкое свечение вокруг линии
        base_color = QColor(90, 180, 255)
        for i in range(4, 0, -1):
            glow = QColor(base_color)
            glow.setAlpha(max(0, 60 - i * 12))
            painter.setPen(QPen(glow, i * 2.0))
            painter.drawLine(left, int(cy), right, int(cy))

        # Яркая центральная линия
        painter.setPen(QPen(QColor(120, 210, 255), 2))
        painter.drawLine(left, int(cy), right, int(cy))

        # Маркеры на концах
        painter.setBrush(QColor(120, 210, 255))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(left - 3, int(cy) - 3, 6, 6)
        painter.drawEllipse(right - 3, int(cy) - 3, 6, 6)

class FiltersContainer(QWidget):
    """Контейнер карточек фильтров с приёмом drag-and-drop.

    Карточки — обычные дочерние виджеты в QVBoxLayout. Перетаскивание
    инициируется самой карточкой (см. ``AppliedFilterWidget.mouseMoveEvent``),
    а этот контейнер:
      * принимает дроп;
      * во время движения мыши показывает светящуюся полоску
        (``FilterDropIndicator``) между карточками — индикатор того,
        куда именно встанет фильтр;
      * по отпусканию сообщает индекс вставки через ``filter_dropped``.
    """

    filter_dropped = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._indicator = FilterDropIndicator(self)
        self._last_drop_index = -1

    # ------------------------------------------------------------------
    # События drag-and-drop
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(_MIME_FILTER_CARD):
            event.acceptProposedAction()
            self._update_indicator(event.pos())

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(_MIME_FILTER_CARD):
            event.acceptProposedAction()
            self._update_indicator(event.pos())

    def dragLeaveEvent(self, event):
        self._hide_indicator()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(_MIME_FILTER_CARD):
            return
        target_index = self._compute_drop_index(event.pos())
        self._hide_indicator()
        event.acceptProposedAction()
        self.filter_dropped.emit(target_index)

    # ------------------------------------------------------------------
    # Индикатор места вставки
    # ------------------------------------------------------------------
    def _hide_indicator(self) -> None:
        self._indicator.hide()
        self._last_drop_index = -1

    def _update_indicator(self, pos) -> None:
        idx = self._compute_drop_index(pos)
        if idx == self._last_drop_index:
            return
        self._last_drop_index = idx
        self._position_indicator(idx)

    def _position_indicator(self, index: int) -> None:
        """Поставить полоску над карточкой ``index`` или под последней."""
        cards = self._cards()
        n = len(cards)
        if n == 0:
            self._indicator.hide()
            return

        h = self._indicator.height()

        if index < n:
            # Полоска по центру верхней границы карточки index
            y = cards[index].y() - h // 2
        else:
            # После последней карточки
            last = cards[-1]
            y = last.y() + last.height() - h // 2

        if y < 0:
            y = 0
        container_h = self.height()
        if y + h > container_h:
            y = max(0, container_h - h)

        x = 0
        w = max(0, self.width())
        self._indicator.setGeometry(x, int(y), w, h)
        self._indicator.raise_()
        self._indicator.show()

    # ------------------------------------------------------------------
    # Геометрия и вычисление индекса
    # ------------------------------------------------------------------
    def _cards(self) -> list:
        """Дочерние карточки фильтров в порядке layout'а."""
        result = []
        layout = self.layout()
        if layout is None:
            return result
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if isinstance(w, AppliedFilterWidget):
                result.append(w)
        return result

    def _compute_drop_index(self, pos) -> int:
        """Индекс вставки (0..N) по координате Y курсора.

        Идём по карточкам сверху вниз и возвращаем первую, чей центр
        ниже курсора. Если такой нет — вставка в конец.
        """
        for i, card in enumerate(self._cards()):
            center_y = card.y() + card.height() / 2
            if pos.y() < center_y:
                return i
        return len(self._cards())

class AppliedFilterWidget(QGroupBox):
    """Карточка применённого фильтра.

    Содержит:
      * чекбокс включения (выключение исключает фильтр из расчёта, не удаляя);
      * ползунки + спинбоксы для «живых» параметров;
      * кнопку удаления фильтра из истории.

    Карточку можно перетащить мышью, чтобы изменить порядок применения
    фильтров. Drag начинается с любой точки карточки, кроме интерактивных
    контролов (чекбокс, слайдер, спинбокс, кнопки, поля ввода).

    Пока чекбокс снят, фильтр визуально и функционально неактивен:
    контролы параметров выключены, подпись приглушена, отложенные
    изменения сброшены.
    """

    deleted = pyqtSignal(object)         # FilterCommand
    drag_started = pyqtSignal(object)    # FilterCommand

    _DEBOUNCE_MS = 150

    def __init__(self, curve, fc, session, parent=None):
        super().__init__(parent)
        self.curve = curve
        self.fc = fc
        self.session = session
        self._pending_params: dict = {}
        self._param_widgets: list[QWidget] = []
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(self._DEBOUNCE_MS)
        self._debounce.timeout.connect(self._apply_pending)
        self._drag_start_pos = None
        self._build_ui()
        self._apply_enabled_state()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setTitle("")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(3)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        grip = QLabel("⋮⋮")
        grip.setStyleSheet("color: #888; font-weight: bold; padding: 0 4px;")
        grip.setCursor(Qt.OpenHandCursor)
        grip.setToolTip(QApplication.translate(
            "GraphWindow",
            "Перетащите, чтобы изменить порядок применения фильтров"
        ))
        header.addWidget(grip)

        self.enable_check = QCheckBox(self._filter_title())
        self.enable_check.setChecked(bool(getattr(self.fc, "enabled", True)))
        self.enable_check.setToolTip(QApplication.translate(
            "GraphWindow",
            "Снимите галочку, чтобы исключить фильтр из расчёта, не удаляя его."
        ))
        self.enable_check.stateChanged.connect(self._on_enabled_changed)
        header.addWidget(self.enable_check, 1)

        del_btn = QPushButton("×")
        del_btn.setFixedWidth(24)
        del_btn.setToolTip(QApplication.translate("GraphWindow", "Удалить фильтр"))
        del_btn.clicked.connect(self._on_delete)
        header.addWidget(del_btn)

        outer.addLayout(header)

        for entry in _FILTER_PARAM_SCHEMA.get(self.fc.filter_type, []):
            key, label, kind, mn, mx, step, dec, default = entry
            if key == "cutoff" and self.fc.params.get("btype") == "band":
                continue
            current = self.fc.params.get(key, default)
            row = self._make_slider_row(key, label, kind, mn, mx, step, dec, current)
            self._param_widgets.append(row)
            outer.addWidget(row)

    # ------------------------------------------------------------------
    def _apply_enabled_state(self) -> None:
        """Привести вид карточки в соответствие с флагом enabled фильтра.

        Когда фильтр выключен:
          * все контролы параметров становятся недоступны (значения не
            меняются мышью/клавиатурой);
          * подпись фильтра приглушается, чтобы карточка читалась как
            «неактивная»;
          * отложенные изменения сбрасываются и дебаунс останавливается —
            менять параметры выключенного фильтра нельзя даже отложенно.
        """
        enabled = bool(getattr(self.fc, "enabled", True))
        for w in self._param_widgets:
            w.setEnabled(enabled)

        self.enable_check.setStyleSheet("" if enabled else "color: #888;")

        if not enabled:
            self._debounce.stop()
            self._pending_params.clear()

    # ------------------------------------------------------------------
    def _filter_title(self) -> str:
        names = {
            "median": "Медианный",
            "average": "Скользящее среднее",
            "exp_mean": "Экспоненциальное среднее",
            "thinning": "Прореживание",
            "normalize": "Нормировка",
            "hampel": "Hampel",
            "savitzky_golay": "Savitzky-Golay",
            "detrend": "Детренд",
            "butterworth": "Butterworth",
            "notch": "Notch",
            "gaussian_smooth": "Гауссово сглаживание",
        }
        base = names.get(self.fc.filter_type, self.fc.filter_type)
        summary = ", ".join(f"{k}={v}" for k, v in (self.fc.params or {}).items())
        return f"{base} ({summary})" if summary else base

    # ------------------------------------------------------------------
    def _make_slider_row(self, key, label, kind, mn, mx, step, dec, value) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)

        h.addWidget(QLabel(label))

        if kind == "int":
            slider = QSlider(Qt.Horizontal)
            slider.setRange(int(mn), int(mx))
            slider.setSingleStep(max(1, int(step)))
            slider.setValue(int(value))

            spin = QSpinBox()
            spin.setRange(int(mn), int(mx))
            spin.setSingleStep(max(1, int(step)))
            spin.setValue(int(value))

            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            spin.valueChanged.connect(lambda v, k=key: self._schedule_update(k, int(v)))

            h.addWidget(slider, 1)
            h.addWidget(spin)
        else:
            scale = 1000 if dec >= 3 else 100
            slider = QSlider(Qt.Horizontal)
            slider.setRange(int(mn * scale), int(mx * scale))
            slider.setSingleStep(max(1, int(step * scale)))
            slider.setValue(int(value * scale))

            spin = QDoubleSpinBox()
            spin.setRange(float(mn), float(mx))
            spin.setDecimals(int(dec))
            spin.setSingleStep(float(step))
            spin.setValue(float(value))

            slider.valueChanged.connect(lambda v, s=scale: spin.setValue(v / s))
            spin.valueChanged.connect(lambda v, s=scale: slider.setValue(int(v * s)))
            spin.valueChanged.connect(lambda v, k=key: self._schedule_update(k, float(v)))

            h.addWidget(slider, 1)
            h.addWidget(spin)

        return w

    # ------------------------------------------------------------------
    def _schedule_update(self, key: str, value) -> None:
        # Параметры выключенного фильтра не должны меняться.
        if not getattr(self.fc, "enabled", True):
            return
        self._pending_params[key] = value
        self._debounce.start()

    def _apply_pending(self) -> None:
        if not self._pending_params:
            return
        params = dict(self._pending_params)
        self._pending_params.clear()
        self.curve.update_filter_params(self.fc, params)

    def _on_enabled_changed(self, state: int) -> None:
        enabled = state != 0
        # Фиксируем накопленные правки до переключения состояния,
        # чтобы значения слайдеров не разошлись с фактическими params.
        if self._pending_params:
            self._apply_pending()
        self.curve.set_filter_enabled(self.fc, enabled)
        self._apply_enabled_state()

    def _on_delete(self) -> None:
        self._debounce.stop()
        self._pending_params.clear()
        self.deleted.emit(self.fc)

    # ------------------------------------------------------------------
    # Drag-and-drop: инициируется самой карточкой
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            is_interactive = isinstance(
                child,
                (QAbstractButton, QAbstractSlider, QAbstractSpinBox,
                 QComboBox, QLineEdit),
            )
            if not is_interactive:
                self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if self._drag_start_pos is None:
            return
        moved = (event.pos() - self._drag_start_pos).manhattanLength()
        if moved < QApplication.startDragDistance():
            return

        self._drag_start_pos = None

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(_MIME_FILTER_CARD, b"1")
        drag.setMimeData(mime)

        # Полупрозрачный «призрак» карточки под курсором
        pixmap = self.grab()
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.fillRect(pixmap.rect(), QColor(0, 0, 0, 160))
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())

        self.drag_started.emit(self.fc)
        drag.exec_(Qt.MoveAction)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

class FiltersTab(QWidget):
    FILTER_NAMES = [
        "Медианный",
        "Скользящее среднее",
        "Экспоненциальное среднее",
        "Прореживание",
        "Нормировка",
        "Hampel",
        "Savitzky-Golay",
        "Детренд",
        "Butterworth",
        "Notch",
        "Гауссово сглаживание",
    ]

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.curves = []
        self._dragged_fc = None
        self.setup_ui()

    # ------------------------------------------------------------------
    @staticmethod
    def _filter_tooltip(index: int) -> str:
        tips = [
            "Медианный фильтр: удаляет одиночные выбросы, сохраняя форму сигнала. "
            "Окно — нечётное число точек.",
            "Скользящее среднее: сглаживает сигнал, подавляя высокочастотный шум. "
            "Окно — число усредняемых точек.",
            "Экспоненциальное среднее: сглаживание с экспоненциально убывающими "
            "весами. Коэффициент α задаёт скорость забывания старых значений.",
            "Прореживание: удаляет заданный процент точек по выбранному правилу "
            "(равномерно, максимумы, минимумы, с начала или с конца).",
            "Нормировка: приводит значения Y к стандартному диапазону "
            "(0–1, −1–1, Z-score или robust).",
            "Hampel: устойчивый к выбросам фильтр. Заменяет точки, отклоняющиеся "
            "от медианы окна больше заданного порога (в робастных σ).",
            "Savitzky-Golay: сглаживание полиномом в скользящем окне. Сохраняет "
            "форму пиков без sinc-лепестков.",
            "Детренд: вычитает из данных полиномиальный тренд, устраняя дрейф "
            "и низкочастотные «пучности» в спектре.",
            "Butterworth: частотный фильтр (low/high/band) с нулевым сдвигом фазы. "
            "Частота среза задаётся в Гц.",
            "Notch: режекторный фильтр для подавления узкополосной наводки "
            "(обычно 50 Гц). Q задаёт добротность.",
            "Гауссово сглаживание: свёртка с гауссовым ядром. σ оценивается "
            "как window/6.",
        ]
        return tips[index] if 0 <= index < len(tips) else ""

    # ------------------------------------------------------------------
    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Применённые фильтры:"))
        hint = QLabel(QApplication.translate(
            "GraphWindow",
            "Порядок карточек = порядок применения. Перетащите карточку, "
            "чтобы изменить порядок."
        ))
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.filters_scroll = QScrollArea()
        self.filters_scroll.setWidgetResizable(True)
        self.filters_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.filters_container = FiltersContainer()
        self.filters_container.filter_dropped.connect(self._on_filter_dropped)
        self.filters_layout = QVBoxLayout(self.filters_container)
        self.filters_layout.setContentsMargins(0, 0, 0, 0)
        self.filters_layout.setSpacing(4)
        self.filters_scroll.setWidget(self.filters_container)
        layout.addWidget(self.filters_scroll, 1)

        self.reset_all_btn = QPushButton("Сбросить все")
        self.reset_all_btn.setToolTip(QApplication.translate(
            "GraphWindow", "Снять все фильтры с выделенных кривых"))
        self.reset_all_btn.clicked.connect(self.reset_all_filters)
        layout.addWidget(self.reset_all_btn)

        # --- Добавление нового фильтра (без изменений) ---
        group = QGroupBox("Добавить фильтр")
        gl = QVBoxLayout(group)

        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItems(self.FILTER_NAMES)
        for i in range(self.filter_type_combo.count()):
            self.filter_type_combo.setItemData(
                i, self._filter_tooltip(i), Qt.ToolTipRole
            )
        self.filter_type_combo.currentIndexChanged.connect(self._on_type_changed)
        gl.addWidget(self.filter_type_combo)

        self.param_stack = QStackedWidget()
        self.param_stack.addWidget(self._build_median_panel())
        self.param_stack.addWidget(self._build_average_panel())
        self.param_stack.addWidget(self._build_exp_panel())
        self.param_stack.addWidget(self._build_thinning_panel())
        self.param_stack.addWidget(self._build_normalize_panel())
        self.param_stack.addWidget(self._build_hampel_panel())
        self.param_stack.addWidget(self._build_savgol_panel())
        self.param_stack.addWidget(self._build_detrend_panel())
        self.param_stack.addWidget(self._build_butterworth_panel())
        self.param_stack.addWidget(self._build_notch_panel())
        self.param_stack.addWidget(self._build_gaussian_panel())
        gl.addWidget(self.param_stack)

        self.apply_btn = QPushButton("Применить")
        self.apply_btn.setToolTip(QApplication.translate(
            "GraphWindow", "Применить выбранный фильтр к выделенным кривым"))
        self.apply_btn.clicked.connect(self.apply_filter)
        gl.addWidget(self.apply_btn)

        layout.addWidget(group)
    # ------------------------------------------------------------------
    # Панели добавления фильтра (без изменений по существу)
    # ------------------------------------------------------------------
    def _build_median_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.median_window = QSpinBox()
        self.median_window.setRange(1, 999)
        self.median_window.setValue(3)
        f.addRow("Окно:", self.median_window)
        return w

    def _build_average_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.average_window = QSpinBox()
        self.average_window.setRange(1, 999)
        self.average_window.setValue(3)
        f.addRow("Окно:", self.average_window)
        return w

    def _build_exp_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.exp_alpha = QDoubleSpinBox()
        self.exp_alpha.setRange(0.01, 1.0)
        self.exp_alpha.setSingleStep(0.01)
        self.exp_alpha.setValue(0.5)
        f.addRow("Коэффициент α:", self.exp_alpha)
        return w

    def _build_thinning_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.thinning_percent = QSpinBox()
        self.thinning_percent.setRange(0, 100)
        self.thinning_percent.setSuffix(" %")
        f.addRow("Процент удаления:", self.thinning_percent)

        self.thinning_uniform = QCheckBox("Равномерно")
        self.thinning_uniform.setChecked(True)
        f.addRow(self.thinning_uniform)
        self.thinning_max = QCheckBox("Удалить максимальные")
        f.addRow(self.thinning_max)
        self.thinning_min = QCheckBox("Удалить минимальные")
        f.addRow(self.thinning_min)
        self.thinning_first = QCheckBox("Удалить первые %")
        f.addRow(self.thinning_first)
        self.thinning_last = QCheckBox("Удалить последние %")
        f.addRow(self.thinning_last)
        return w

    def _build_normalize_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.norm_type = QComboBox()
        self.norm_type.addItems(["0-1 (Min-Max)", "-1-1", "Z-score", "Robust (медиана/IQR)"])
        f.addRow("Тип:", self.norm_type)
        return w

    def _build_hampel_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.hampel_window = QSpinBox()
        self.hampel_window.setRange(3, 999)
        self.hampel_window.setSingleStep(2)
        self.hampel_window.setValue(5)
        self.hampel_sigmas = QDoubleSpinBox()
        self.hampel_sigmas.setRange(0.5, 10.0)
        self.hampel_sigmas.setSingleStep(0.5)
        self.hampel_sigmas.setDecimals(2)
        self.hampel_sigmas.setValue(3.0)
        f.addRow("Окно:", self.hampel_window)
        f.addRow("Порог (σ):", self.hampel_sigmas)
        return w

    def _build_savgol_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.savgol_window = QSpinBox()
        self.savgol_window.setRange(3, 999)
        self.savgol_window.setSingleStep(2)
        self.savgol_window.setValue(5)
        self.savgol_polyorder = QSpinBox()
        self.savgol_polyorder.setRange(1, 10)
        self.savgol_polyorder.setValue(2)
        f.addRow("Окно:", self.savgol_window)
        f.addRow("Степень полинома:", self.savgol_polyorder)
        return w

    def _build_detrend_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.detrend_type = QComboBox()
        self.detrend_type.addItems(["linear", "poly"])
        self.detrend_type.currentTextChanged.connect(self._on_detrend_type_changed)
        self.detrend_polyorder = QSpinBox()
        self.detrend_polyorder.setRange(1, 10)
        self.detrend_polyorder.setValue(2)
        self.detrend_polyorder.setEnabled(False)
        f.addRow("Тип:", self.detrend_type)
        f.addRow("Степень:", self.detrend_polyorder)
        return w

    def _on_detrend_type_changed(self, text):
        self.detrend_polyorder.setEnabled(text == "poly")

    def _build_butterworth_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.butter_type = QComboBox()
        self.butter_type.addItems(["low", "high", "band"])
        self.butter_cutoff_low = QDoubleSpinBox()
        self.butter_cutoff_low.setRange(0.0, 1e6)
        self.butter_cutoff_low.setDecimals(4)
        self.butter_cutoff_low.setValue(10.0)
        self.butter_cutoff_high = QDoubleSpinBox()
        self.butter_cutoff_high.setRange(0.0, 1e6)
        self.butter_cutoff_high.setDecimals(4)
        self.butter_cutoff_high.setValue(100.0)
        self.butter_cutoff_high.setEnabled(False)
        self.butter_order = QSpinBox()
        self.butter_order.setRange(1, 10)
        self.butter_order.setValue(4)
        self.butter_type.currentTextChanged.connect(
            lambda t: self.butter_cutoff_high.setEnabled(t == "band")
        )
        f.addRow("Тип:", self.butter_type)
        f.addRow("Срез/нижн. (Гц):", self.butter_cutoff_low)
        f.addRow("Верхн. (Гц):", self.butter_cutoff_high)
        f.addRow("Порядок:", self.butter_order)
        return w

    def _build_notch_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.notch_freq = QDoubleSpinBox()
        self.notch_freq.setRange(0.001, 1e6)
        self.notch_freq.setDecimals(2)
        self.notch_freq.setValue(50.0)
        self.notch_q = QDoubleSpinBox()
        self.notch_q.setRange(1.0, 1000.0)
        self.notch_q.setDecimals(1)
        self.notch_q.setValue(30.0)
        f.addRow("Частота (Гц):", self.notch_freq)
        f.addRow("Q:", self.notch_q)
        return w

    def _build_gaussian_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.gaussian_window = QSpinBox()
        self.gaussian_window.setRange(1, 999)
        self.gaussian_window.setValue(5)
        f.addRow("Окно (→ σ):", self.gaussian_window)
        return w

    # ------------------------------------------------------------------
    def _build_filter_command(self):
        idx = self.filter_type_combo.currentIndex()
        if idx == 0:
            return FilterCommand("median", {"window": int(self.median_window.value())},
                                 self.session.filter_class)
        if idx == 1:
            return FilterCommand("average", {"window": int(self.average_window.value())},
                                 self.session.filter_class)
        if idx == 2:
            return FilterCommand("exp_mean", {"alpha": float(self.exp_alpha.value())},
                                 self.session.filter_class)
        if idx == 3:
            params = {
                "percent": int(self.thinning_percent.value()),
                "uniform": bool(self.thinning_uniform.isChecked()),
                "max": bool(self.thinning_max.isChecked()),
                "min": bool(self.thinning_min.isChecked()),
                "first": bool(self.thinning_first.isChecked()),
                "last": bool(self.thinning_last.isChecked()),
            }
            return FilterCommand("thinning", params, self.session.filter_class)
        if idx == 4:
            return FilterCommand("normalize", {"norm_type": self.norm_type.currentText()},
                                 self.session.filter_class)
        if idx == 5:
            return FilterCommand("hampel", {
                "window": int(self.hampel_window.value()),
                "n_sigmas": float(self.hampel_sigmas.value()),
            }, self.session.filter_class)
        if idx == 6:
            return FilterCommand("savitzky_golay", {
                "window": int(self.savgol_window.value()),
                "polyorder": int(self.savgol_polyorder.value()),
            }, self.session.filter_class)
        if idx == 7:
            return FilterCommand("detrend", {
                "detrend_type": self.detrend_type.currentText(),
                "polyorder": int(self.detrend_polyorder.value()),
            }, self.session.filter_class)
        if idx == 8:
            btype = self.butter_type.currentText()
            if btype == "band":
                cutoff = (float(self.butter_cutoff_low.value()),
                          float(self.butter_cutoff_high.value()))
            else:
                cutoff = float(self.butter_cutoff_low.value())
            return FilterCommand("butterworth", {
                "cutoff": cutoff,
                "btype": btype,
                "order": int(self.butter_order.value()),
            }, self.session.filter_class)
        if idx == 9:
            return FilterCommand("notch", {
                "freq": float(self.notch_freq.value()),
                "q": float(self.notch_q.value()),
            }, self.session.filter_class)
        if idx == 10:
            return FilterCommand("gaussian_smooth", {
                "window": int(self.gaussian_window.value()),
                "sigma": None,
            }, self.session.filter_class)
        return None

    def _on_type_changed(self, idx):
        self.param_stack.setCurrentIndex(idx)
        tip = self.filter_type_combo.itemData(idx, Qt.ToolTipRole) or ""
        self.filter_type_combo.setToolTip(tip)

    # ------------------------------------------------------------------
    # Список применённых фильтров
    # ------------------------------------------------------------------
    def set_curves(self, curves):
        self.curves = curves
        self.update_filters_list()

    def update_filters_list(self):
        while self.filters_layout.count():
            item = self.filters_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        if len(self.curves) != 1:
            self.filters_layout.addStretch()
            return

        curve = self.curves[0]
        for fc in list(curve.filters_history):
            card = AppliedFilterWidget(curve, fc, self.session)
            card.deleted.connect(self._on_filter_deleted)
            card.drag_started.connect(self._on_drag_started)
            self.filters_layout.addWidget(card)
        self.filters_layout.addStretch()

    def _on_drag_started(self, fc) -> None:
        self._dragged_fc = fc

    def _on_filter_dropped(self, target_index: int) -> None:
        fc = self._dragged_fc
        self._dragged_fc = None
        if fc is None or len(self.curves) != 1:
            return

        curve = self.curves[0]
        history = curve.filters_history
        if fc not in history:
            return

        old_index = history.index(fc)
        # target_index — позиция «вставить перед элементом i» в исходном
        # списке. После извлечения элемента индексы справа сдвигаются на 1.
        new_index = target_index
        if new_index > old_index:
            new_index -= 1
        if new_index < 0:
            new_index = 0
        if new_index >= len(history):
            new_index = len(history) - 1
        if new_index == old_index:
            return

        cmd = ReorderFiltersCommand(curve, fc, old_index, new_index)
        self.session.undo_manager.push(cmd, execute=True)
        self.update_filters_list()
        _status(
            self.session,
            QApplication.translate(
                "GraphWindow", "Порядок фильтров изменён"
            ),
            2000,
        )

    def _on_filter_deleted(self, fc):
        if len(self.curves) != 1:
            return
        curve = self.curves[0]
        cmd = RemoveFilterCommand(curve, fc)
        self.session.undo_manager.push(cmd, execute=True)
        self.update_filters_list()
        _status(self.session, f"Фильтр удалён: {fc.filter_type}", 2500)

    # ------------------------------------------------------------------
    def apply_filter(self):
        if not self.curves:
            return
        fc = self._build_filter_command()
        if fc is None:
            return
        cmd = ApplyFilterCommand(list(self.curves), fc)
        self.session.undo_manager.push(cmd, execute=True)
        self.update_filters_list()
        _status(self.session, f"Фильтр применён: {fc.filter_type}", 2500)

    def reset_all_filters(self):
        if not self.curves:
            return
        cmd = ResetFiltersCommand(list(self.curves))
        self.session.undo_manager.push(cmd, execute=True)
        self.update_filters_list()
        _status(self.session, "Фильтры сброшены", 2500)


class CollapsibleGroupBox(QWidget):
    def __init__(self, title: str, parent=None, expanded: bool = True):
        super().__init__(parent)
        self._title = title
        self._expanded = bool(expanded)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.header = QToolButton()
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setChecked(self._expanded)
        self.header.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.header.setArrowType(Qt.DownArrow if self._expanded else Qt.RightArrow)
        self.header.setStyleSheet(
            "QToolButton { border: none; font-weight: bold; text-align: left; padding: 4px; }"
        )
        self.header.clicked.connect(self._toggle)
        outer.addWidget(self.header)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        self.content_layout.setSpacing(6)
        outer.addWidget(self.content)

        self.content.setVisible(self._expanded)

    def _toggle(self):
        self.set_expanded(self.header.isChecked())

    def set_expanded(self, expanded: bool):
        self._expanded = bool(expanded)
        self.header.setChecked(self._expanded)
        self.header.setArrowType(Qt.DownArrow if self._expanded else Qt.RightArrow)
        self.content.setVisible(self._expanded)

    def is_expanded(self) -> bool:
        return self._expanded

    def contentLayout(self) -> QVBoxLayout:
        return self.content_layout

