# graph/ui/inspector.py
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox,
                             QDoubleSpinBox, QPushButton, QGroupBox, QFormLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QStackedWidget, QScrollArea, QApplication,
                             QColorDialog, QTextEdit, QFontDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from graph.core.curve_data import LineStyle
from graph.core.filters_instance_class import FilterCommand
from graph.core.undo_commands import (RenameCurveCommand, ChangeCurveStyleCommand,
                                      ApplyFilterCommand, RemoveFilterCommand,
                                      ResetFiltersCommand, EditPointCommand)
from graph.utils.line_styles import PRESETS_LINE
from graph.analysis.ui.analysis_tab import AnalysisTab

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
    """Правая док-панель — единое место для просмотра и настройки выделенного объекта."""

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

        self.stack.addWidget(self.graph_settings)
        self.stack.addWidget(self.curve_inspector)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.selection_model.selection_changed.connect(self._on_selection_changed)
        self._on_selection_changed(self.selection_model.current())

    # --------------------------------------------------------------
    # SelectionModel хранит CurvePresenter (см. CurvePresenter.on_plot_clicked).
    # Приводим каждый элемент к фасаду linearData через graph_main.get_curves().
    # --------------------------------------------------------------
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
            self.stack.setCurrentWidget(self.graph_settings)
            self.graph_settings.update_settings()

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
        self.setup_ui()
        self.update_settings()

        # Undo/redo меняет виджет снаружи — синхронизируем UI.
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
        main = QVBoxLayout(content)

        main.addWidget(self._build_general_group())
        main.addWidget(self._build_grid_group())
        for key in ("bottom", "left", "right"):
            main.addWidget(self._build_axis_group(key))
        main.addWidget(self._build_legend_group())
        main.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    @staticmethod
    def _make_color_btn():
        """Маленькая кнопка-свотч без текста."""
        btn = QPushButton()
        btn.setFixedSize(32, 20)
        btn.setToolTip("Нажмите для выбора цвета")
        return btn

    def _build_general_group(self):
        g = QGroupBox("График")
        f = QFormLayout(g)

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

        return g

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
        g = QGroupBox("Сетка")
        f = QFormLayout(g)

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

        return g

    def _build_axis_group(self, key: str):
        g = QGroupBox(self.AXIS_TITLES[key])
        f = QFormLayout(g)
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
        return g

    def _build_legend_group(self):
        g = QGroupBox("Легенда")
        f = QFormLayout(g)

        self.legend_check = QCheckBox("Показывать легенду")
        self.legend_check.stateChanged.connect(self.apply_legend)
        f.addRow(self.legend_check)

        self.legend_color_btn = self._make_color_btn()
        self.legend_color_btn.clicked.connect(self.choose_legend_color)
        f.addRow("Цвет текста:", self.legend_color_btn)

        return g

    # ==================================================================
    # Синхронизация UI с текущим состоянием виджета
    # ==================================================================
    def _on_undo_state_changed(self):
        # При undo/redo виджет меняется снаружи — синхронизируем поля.
        self.update_settings()

    def update_settings(self):
        from graph.hdf5_io.utils import extract_plot_widget_settings
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
        finally:
            self._suppress = False

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

        controller = self.graph_view.axises.get(key)
        if controller is None:
            return
        gv = self.graph_view

        def mutate():
            try:
                # через custom_style — чтобы undo корректно считывал цвет
                controller.custom_style.color = c.name()
                controller.set_custom_style(controller.custom_style)
            except Exception:
                logger.exception("choose_axis_color failed")

        gv.apply_appearance_change(mutate)
        _status(self.session, f"Цвет оси {key} обновлён", 2000)

    def choose_axis_font(self, key):
        controller = self.graph_view.axises.get(key)
        if controller is None:
            return
        try:
            current = controller.label.font()
        except Exception:
            current = None

        font, ok = QFontDialog.getFont(current, self, "Шрифт подписи оси")
        if not ok:
            return
        gv = self.graph_view

        def mutate():
            try:
                controller.custom_style.text_font = font
                controller.set_custom_style(controller.custom_style)
            except Exception:
                logger.exception("choose_axis_font failed")

        gv.apply_appearance_change(mutate)
        _status(self.session, f"Шрифт подписи оси {key} обновлён", 2000)

    def choose_axis_tick_font(self, key):
        controller = self.graph_view.axises.get(key)
        if controller is None:
            return

        # Прямое обращение к AxisItem, без __getattr__
        axis_item = controller.axis
        current = axis_item.style.get('tickFont')  # может быть None
        if current is None:
            current = QFont()  # безопасный fallback

        font, ok = QFontDialog.getFont(current, self, "Шрифт делений оси")
        if not ok:
            return
        gv = self.graph_view

        def mutate():
            try:
                axis_item.setTickFont(font)
                controller.custom_style.tick_font = font
            except Exception:
                logger.exception("choose_axis_tick_font failed")

        gv.apply_appearance_change(mutate)
        _status(self.session, f"Шрифт делений оси {key} обновлён", 2000)


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

        from graph.core.undo_commands import AddNoteCommand
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
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

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

        self.symbol_color_btn = QPushButton("Цвет маркера")
        self.symbol_color_btn.clicked.connect(self.choose_symbol_color)
        form.addRow(self.symbol_color_btn)

        self.fill_color_btn = QPushButton("Цвет заливки")
        self.fill_color_btn.clicked.connect(self.choose_fill_color)
        form.addRow(self.fill_color_btn)

        self.px_mode_check = QCheckBox("Режим пикселей (pxMode)")
        self.px_mode_check.stateChanged.connect(self.apply_style)
        form.addRow(self.px_mode_check)

        layout.addLayout(form)
        layout.addStretch()

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
            # ВАЖНО: приводим всё к int, т.к. HDF5 сохраняет числа как float
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
        finally:
            self._suppress_apply = False

    def _current_style(self) -> LineStyle:
        style = LineStyle()
        style.color = self._color_from_btn(self.color_btn)
        style.line_width = int(self.width_spin.value())
        style.line_style = _LINE_STYLE_ENUM.get(self.style_combo.currentText(), Qt.SolidLine)
        sym = self.symbol_combo.currentText()
        style.symbol = None if sym == "None" else sym
        style.symbol_size = int(self.symbol_size.value())
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
        if self._suppress_apply:
            return
        if name not in PRESETS_LINE:
            return
        preset = PRESETS_LINE[name]
        self._suppress_apply = True
        try:
            self._set_btn_color(self.color_btn, preset["color"])
            self._set_btn_color(self.symbol_color_btn, preset["symbol_color"])
            self._set_btn_color(self.fill_color_btn, preset["fill_color"])
            self.width_spin.setValue(int(preset["line_width"]))
            self.symbol_size.setValue(int(preset["symbol_size"]))
            self.style_combo.setCurrentText(_LINE_STYLE_NAMES.get(preset["line_style"], "Solid"))
            sym = preset["symbol"] if preset["symbol"] else "None"
            idx = self.symbol_combo.findText(sym)
            if idx >= 0:
                self.symbol_combo.setCurrentIndex(idx)
        finally:
            self._suppress_apply = False
        self.apply_style()
        _status(self.session, f"Применён пресет: {name}", 2500)

    def choose_color(self):
        c = QColorDialog.getColor(QColor(self._color_from_btn(self.color_btn)))
        if c.isValid():
            self._set_btn_color(self.color_btn, c.name())
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
        self.setup_ui()

    @staticmethod
    def _filter_tooltip(index: int) -> str:
        """Локализованный tooltip фильтра по индексу в FILTER_NAMES."""
        tips = [
            QApplication.translate(
                "GraphWindow",
                "Медианный фильтр: удаляет одиночные выбросы, сохраняя форму сигнала. "
                "Окно — нечётное число точек."),
            QApplication.translate(
                "GraphWindow",
                "Скользящее среднее: сглаживает сигнал, подавляя высокочастотный шум. "
                "Окно — число усредняемых точек."),
            QApplication.translate(
                "GraphWindow",
                "Экспоненциальное среднее: сглаживание с экспоненциально убывающими "
                "весами. Коэффициент α задаёт скорость забывания старых значений."),
            QApplication.translate(
                "GraphWindow",
                "Прореживание: удаляет заданный процент точек по выбранному правилу "
                "(равномерно, максимумы, минимумы, с начала или с конца)."),
            QApplication.translate(
                "GraphWindow",
                "Нормировка: приводит значения Y к стандартному диапазону "
                "(0–1, −1–1, Z-score или robust)."),
            QApplication.translate(
                "GraphWindow",
                "Hampel: устойчивый к выбросам фильтр. Заменяет точки, отклоняющиеся "
                "от медианы окна больше заданного порога (в робастных σ)."),
            QApplication.translate(
                "GraphWindow",
                "Savitzky-Golay: сглаживание полиномом в скользящем окне. Сохраняет "
                "форму пиков без sinc-лепестков."),
            QApplication.translate(
                "GraphWindow",
                "Детренд: вычитает из данных полиномиальный тренд, устраняя дрейф "
                "и низкочастотные «пучности» в спектре."),
            QApplication.translate(
                "GraphWindow",
                "Butterworth: частотный фильтр (low/high/band) с нулевым сдвигом фазы. "
                "Частота среза задаётся в Гц."),
            QApplication.translate(
                "GraphWindow",
                "Notch: режекторный фильтр для подавления узкополосной наводки "
                "(обычно 50 Гц). Q задаёт добротность."),
            QApplication.translate(
                "GraphWindow",
                "Гауссово сглаживание: свёртка с гауссовым ядром. σ оценивается "
                "как window/6."),
        ]
        if 0 <= index < len(tips):
            return tips[index]
        return ""

    def setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Применённые фильтры:"))
        self.filters_list = QTableWidget()
        self.filters_list.setColumnCount(3)
        self.filters_list.setHorizontalHeaderLabels(["Фильтр", "Параметры", "Действия"])
        self.filters_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.filters_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.filters_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.filters_list)

        self.reset_all_btn = QPushButton("Сбросить все")
        self.reset_all_btn.setToolTip(QApplication.translate(
            "GraphWindow", "Снять все фильтры с выделенных кривых"))
        self.reset_all_btn.clicked.connect(self.reset_all_filters)
        layout.addWidget(self.reset_all_btn)

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

    def _build_median_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.median_window = QSpinBox()
        self.median_window.setRange(1, 999)
        self.median_window.setValue(3)
        self.median_window.setToolTip(QApplication.translate(
            "GraphWindow",
            "Размер окна медианного фильтра в точках. Обычно 3–7 (нечётное число). "
            "Чем больше окно, тем сильнее подавление одиночных выбросов, но тем больше "
            "сглаживается форма сигнала."
        ))
        f.addRow("Окно:", self.median_window)
        return w

    def _build_average_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.average_window = QSpinBox()
        self.average_window.setRange(1, 999)
        self.average_window.setValue(3)
        self.average_window.setToolTip(QApplication.translate(
            "GraphWindow",
            "Число усредняемых точек. Больше окно — сильнее сглаживание и меньше шума, "
            "но заметнее размытие быстрых изменений сигнала."
        ))
        f.addRow("Окно:", self.average_window)
        return w

    def _build_exp_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.exp_alpha = QDoubleSpinBox()
        self.exp_alpha.setRange(0.01, 1.0)
        self.exp_alpha.setSingleStep(0.01)
        self.exp_alpha.setValue(0.5)
        self.exp_alpha.setToolTip(QApplication.translate(
            "GraphWindow",
            "Коэффициент α экспоненциального сглаживания (0.01–1.0). "
            "Ближе к 1 — больше веса у свежих значений, слабее сглаживание; "
            "ближе к 0 — сильнее сглаживание и запаздывание."
        ))
        f.addRow("Коэффициент α:", self.exp_alpha)
        return w

    def _build_thinning_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.thinning_percent = QSpinBox()
        self.thinning_percent.setRange(0, 100)
        self.thinning_percent.setSuffix(" %")
        self.thinning_percent.setToolTip(QApplication.translate(
            "GraphWindow",
            "Процент точек, которые будут удалены. При нескольких включённых правилах "
            "процент делится между ними поровну."
        ))
        f.addRow("Процент удаления:", self.thinning_percent)

        self.thinning_uniform = QCheckBox("Равномерно")
        self.thinning_uniform.setChecked(True)
        self.thinning_uniform.setToolTip(QApplication.translate(
            "GraphWindow",
            "Равномерное прореживание: удаляет каждую N-ю точку, сохраняя общую форму сигнала."
        ))
        f.addRow(self.thinning_uniform)

        self.thinning_max = QCheckBox("Удалить максимальные")
        self.thinning_max.setToolTip(QApplication.translate(
            "GraphWindow",
            "Удаляет заданный процент точек с наибольшими значениями Y. "
            "Полезно для подавления положительных выбросов."
        ))
        f.addRow(self.thinning_max)

        self.thinning_min = QCheckBox("Удалить минимальные")
        self.thinning_min.setToolTip(QApplication.translate(
            "GraphWindow",
            "Удаляет заданный процент точек с наименьшими значениями Y. "
            "Полезно для подавления отрицательных выбросов."
        ))
        f.addRow(self.thinning_min)

        self.thinning_first = QCheckBox("Удалить первые %")
        self.thinning_first.setToolTip(QApplication.translate(
            "GraphWindow",
            "Удаляет заданный процент точек с начала кривой (по индексу)."
        ))
        f.addRow(self.thinning_first)

        self.thinning_last = QCheckBox("Удалить последние %")
        self.thinning_last.setToolTip(QApplication.translate(
            "GraphWindow",
            "Удаляет заданный процент точек с конца кривой (по индексу)."
        ))
        f.addRow(self.thinning_last)

        return w

    def _build_normalize_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.norm_type = QComboBox()
        self.norm_type.addItems(["0-1 (Min-Max)", "-1-1", "Z-score", "Robust (медиана/IQR)"])
        self.norm_type.setToolTip(QApplication.translate(
            "GraphWindow",
            "Тип нормировки: 0–1 (min-max), −1–1, Z-score (среднее 0, СКО 1) "
            "или robust (медиана и межквартильный размах)."
        ))
        self.norm_type.setItemData(
            0,
            QApplication.translate(
                "GraphWindow",
                "Приводит Y к диапазону [0, 1]. Устойчива к выбросам только по границам."),
            Qt.ToolTipRole,
        )
        self.norm_type.setItemData(
            1,
            QApplication.translate(
                "GraphWindow",
                "Приводит Y к диапазону [−1, 1]. Удобно для симметричных сигналов."),
            Qt.ToolTipRole,
        )
        self.norm_type.setItemData(
            2,
            QApplication.translate(
                "GraphWindow",
                "Стандартизация: (Y − среднее) / СКО. Среднее 0, СКО 1."),
            Qt.ToolTipRole,
        )
        self.norm_type.setItemData(
            3,
            QApplication.translate(
                "GraphWindow",
                "Робастная нормировка: (Y − медиана) / IQR. Устойчива к выбросам."),
            Qt.ToolTipRole,
        )
        f.addRow("Тип:", self.norm_type)
        return w

    def _build_hampel_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.hampel_window = QSpinBox()
        self.hampel_window.setRange(3, 999)
        self.hampel_window.setSingleStep(2)
        self.hampel_window.setValue(5)
        self.hampel_window.setToolTip(QApplication.translate(
            "GraphWindow",
            "Размер окна для оценки локальной медианы и MAD. Нечётное число ≥ 3. "
            "Окно должно быть больше типичной ширины выброса."
        ))
        self.hampel_sigmas = QDoubleSpinBox()
        self.hampel_sigmas.setRange(0.5, 10.0)
        self.hampel_sigmas.setSingleStep(0.5)
        self.hampel_sigmas.setDecimals(2)
        self.hampel_sigmas.setValue(3.0)
        self.hampel_sigmas.setToolTip(QApplication.translate(
            "GraphWindow",
            "Порог в робастных σ (MAD·1.4826). Точки, отклонившиеся от медианы окна "
            "сильнее порога, заменяются медианой. 3σ — стандарт."
        ))
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
        self.savgol_window.setToolTip(QApplication.translate(
            "GraphWindow",
            "Длина окна аппроксимации. Нечётное число ≥ 3 и строго больше степени полинома. "
            "Больше окно — сильнее сглаживание."
        ))
        self.savgol_polyorder = QSpinBox()
        self.savgol_polyorder.setRange(1, 10)
        self.savgol_polyorder.setValue(2)
        self.savgol_polyorder.setToolTip(QApplication.translate(
            "GraphWindow",
            "Степень аппроксимирующего полинома. Должна быть меньше длины окна. "
            "2 — парабола, 3 — кубическая и т.д."
        ))
        f.addRow("Окно:", self.savgol_window)
        f.addRow("Степень полинома:", self.savgol_polyorder)
        return w

    def _build_detrend_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.detrend_type = QComboBox()
        self.detrend_type.addItems(["linear", "poly"])
        self.detrend_type.setToolTip(QApplication.translate(
            "GraphWindow",
            "Тип тренда: linear — прямая, poly — полином заданной степени."
        ))
        self.detrend_type.setItemData(
            0,
            QApplication.translate("GraphWindow", "Вычитает линейный тренд k·x + b."),
            Qt.ToolTipRole,
        )
        self.detrend_type.setItemData(
            1,
            QApplication.translate(
                "GraphWindow",
                "Вычитает полиномиальный тренд степени, указанной ниже."),
            Qt.ToolTipRole,
        )
        self.detrend_type.currentTextChanged.connect(self._on_detrend_type_changed)

        self.detrend_polyorder = QSpinBox()
        self.detrend_polyorder.setRange(1, 10)
        self.detrend_polyorder.setValue(2)
        self.detrend_polyorder.setEnabled(False)
        self.detrend_polyorder.setToolTip(QApplication.translate(
            "GraphWindow",
            "Степень полиномиального тренда. Доступно только при типе «poly»."
        ))
        f.addRow("Тип:", self.detrend_type)
        f.addRow("Степень:", self.detrend_polyorder)
        return w

    def _on_detrend_type_changed(self, text):
        """Активировать степень полинома только для типа «poly»."""
        self.detrend_polyorder.setEnabled(text == "poly")

    def _build_butterworth_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.butter_type = QComboBox()
        self.butter_type.addItems(["low", "high", "band"])
        self.butter_type.setToolTip(QApplication.translate(
            "GraphWindow",
            "Тип фильтра: low — нижних частот, high — верхних, band — полосовой."
        ))
        self.butter_type.setItemData(
            0,
            QApplication.translate(
                "GraphWindow",
                "ФНЧ: пропускает частоты ниже среза."),
            Qt.ToolTipRole,
        )
        self.butter_type.setItemData(
            1,
            QApplication.translate(
                "GraphWindow",
                "ФВЧ: пропускает частоты выше среза."),
            Qt.ToolTipRole,
        )
        self.butter_type.setItemData(
            2,
            QApplication.translate(
                "GraphWindow",
                "Полосовой: пропускает частоты между нижней и верхней границами."),
            Qt.ToolTipRole,
        )

        self.butter_cutoff_low = QDoubleSpinBox()
        self.butter_cutoff_low.setRange(0.0, 1e6)
        self.butter_cutoff_low.setDecimals(4)
        self.butter_cutoff_low.setValue(10.0)
        self.butter_cutoff_low.setToolTip(QApplication.translate(
            "GraphWindow",
            "Частота среза в Гц. Для band — нижняя граница полосы."
        ))

        self.butter_cutoff_high = QDoubleSpinBox()
        self.butter_cutoff_high.setRange(0.0, 1e6)
        self.butter_cutoff_high.setDecimals(4)
        self.butter_cutoff_high.setValue(100.0)
        self.butter_cutoff_high.setEnabled(False)
        self.butter_cutoff_high.setToolTip(QApplication.translate(
            "GraphWindow",
            "Верхняя граница полосы в Гц. Используется только для типа band."
        ))

        self.butter_order = QSpinBox()
        self.butter_order.setRange(1, 10)
        self.butter_order.setValue(4)
        self.butter_order.setToolTip(QApplication.translate(
            "GraphWindow",
            "Порядок фильтра. Больше порядок — круче срез, но выше риск нестабильности. "
            "Типично 2–6."
        ))

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
        self.notch_freq.setToolTip(QApplication.translate(
            "GraphWindow",
            "Частота подавляемой наводки в Гц. Для сети 50 Гц оставьте 50.0."
        ))

        self.notch_q = QDoubleSpinBox()
        self.notch_q.setRange(1.0, 1000.0)
        self.notch_q.setDecimals(1)
        self.notch_q.setValue(30.0)
        self.notch_q.setToolTip(QApplication.translate(
            "GraphWindow",
            "Добротность Q: чем больше, тем уже полоса подавления. "
            "Обычно 20–50."
        ))

        f.addRow("Частота (Гц):", self.notch_freq)
        f.addRow("Q:", self.notch_q)
        return w

    def _build_gaussian_panel(self):
        w = QWidget()
        f = QFormLayout(w)
        self.gaussian_window = QSpinBox()
        self.gaussian_window.setRange(1, 999)
        self.gaussian_window.setValue(5)
        self.gaussian_window.setToolTip(QApplication.translate(
            "GraphWindow",
            "Размер окна для оценки σ (σ = window/6). Больше окно — сильнее сглаживание."
        ))
        f.addRow("Окно (→ σ):", self.gaussian_window)
        return w

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

    # --- список применённых ------------------------------------------
    def set_curves(self, curves):
        self.curves = curves
        self.update_filters_list()

    def update_filters_list(self):
        self.filters_list.setRowCount(0)
        if len(self.curves) != 1:
            return
        curve = self.curves[0]
        for i, fc in enumerate(curve.filters_history):
            self.filters_list.insertRow(i)
            self.filters_list.setItem(i, 0, QTableWidgetItem(str(fc.filter_type)))
            self.filters_list.setItem(i, 1, QTableWidgetItem(str(fc.params)))

            cell = QWidget()
            hl = QHBoxLayout(cell); hl.setContentsMargins(0, 0, 0, 0)
            del_btn = QPushButton("×"); del_btn.setFixedWidth(28)
            del_btn.clicked.connect(lambda _, c=curve, f=fc: self.remove_filter(c, f))
            hl.addWidget(del_btn)
            self.filters_list.setCellWidget(i, 2, cell)

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

    def remove_filter(self, curve, fc):
        cmd = RemoveFilterCommand(curve, fc)
        self.session.undo_manager.push(cmd, execute=True)
        self.update_filters_list()
        _status(self.session, f"Фильтр удалён: {fc.filter_type}", 2500)

    def reset_all_filters(self):
        if not self.curves:
            return
        cmd = ResetFiltersCommand(list(self.curves))
        self.session.undo_manager.push(cmd, execute=True)
        self.update_filters_list()
        _status(self.session, "Фильтры сброшены", 2500)


# =====================================================================
# Вкладка "Инструменты"
# =====================================================================
class ToolsTab(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        layout = QVBoxLayout(self)
        self.label = QLabel("Выберите инструмент в меню «Анализ»")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

    def set_curves(self, curves):
        pass