# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
#
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
#
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

# --- Стандартная библиотека ---
import copy
import logging
import os
import random
import uuid

# --- Сторонние библиотеки ---
import numpy as np
from PyQt5.QtCore import QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from graphs.ui.empty_state import EmptyStateWidget
from graphs.main.demo_session import LiveDemoController, StaticDemoLoader
from graphs.helpers import HelperManager, HelperTab

# --- Локальные модули проекта ---
from functions import open_log_file

from graphs.adapters.graphSelectAdapter import graphSelectAdapter
from graphs.adapters.waveSelectAdapter import waveSelectAdapter
from graphs.animation_graph.animation_widget import AnimationWindow
from graphs.api.experiment_port import ExperimentPort
from graphs.comparison.compare_sessions_graph import CompareWindowMediator
from graphs.core.dataManager import graphDataManager
from graphs.core.filters_instance_class import FilterCommand
from graphs.core.parameter_alias_manager import ParameterAliasDialog, ParameterAliasManager
from graphs.core.selection_model import SelectionModel
from graphs.core.session_mode import SessionMode
from graphs.core.undo_commands import (
    ApplyFilterCommand,
    ChangeDescriptionCommand,
    RenameSessionCommand,
)
from common.undo.manager import SessionUndoManager
from graphs.hdf5_io.adapters import HDF5ToProjectAdapter
from graphs.hdf5_io.facade import HDF5Facade
from graphs.hdf5_io.models import FieldSettings
from graphs.hdf5_io.utils import extract_plot_widget_settings
from graphs.main.graph_main import manageGraph
from graphs.main.test_main_graph import test_graph
from common.actions.registry import ActionRegistry
from graphs.ui.buttons_panel import ButtonsControl
from graphs.ui.notification import NotificationWidget
from graphs.ui.osc_selector import OscilloscopeSelector
from graphs.ui.osc_wave_graph import graphOsc
from graphs.ui.paramSelectors import paramController, paramSelector
from graphs.ui.select_session import SessionSelectControl
from graphs.ui.status_line import StatusBar
from graphs.ui.tabPage_win import tabPage
from graphs.ui.tree_curves import treeWin
from graphs.ui.inspector import Inspector
from graphs.analysis.registry import AnalysisToolRegistry
from graphs.analysis.models import tr_analysis

from graphs.analysis import AnalysisController
from graphs.analysis.io.serializer import save_artifacts, load_artifacts

logger = logging.getLogger(__name__)


class GraphWindow(QMainWindow):
    graph_win_close_signal = pyqtSignal(int)

    def __init__(self, session_selector, buttons_controller=None, version=None,
                 action_registry=None, session_controller=None):
        super().__init__()
        self.setWindowTitle(("Online Graph " + version) if version else "Online Graph")
        self.action_registry = action_registry
        self.buttons_controller = buttons_controller
        self.session_controller = session_controller 

        self._apply_adaptive_geometry()
        self.notification = None
        self.initUI(session_selector=session_selector,
                    buttons_controller=buttons_controller)

    def _apply_adaptive_geometry(self):
        """Подгоняем окно под текущий экран: 90% от доступной области,
        с ограничениями по минимуму/максимуму и центрированием."""

        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(1280, 720)
            return

        avail: QRect = screen.availableGeometry()
        avail_w, avail_h = avail.width(), avail.height()

        target_w = int(avail_w * 0.90)
        target_h = int(avail_h * 0.90)

        MIN_W, MIN_H = 800, 500
        MAX_W, MAX_H = 1900, 1100

        target_w = max(MIN_W, min(target_w, MAX_W, avail_w))
        target_h = max(MIN_H, min(target_h, MAX_H, avail_h))

        self.setMinimumSize(MIN_W, MIN_H)

        x = avail.x() + (avail_w - target_w) // 2
        y = avail.y() + (avail_h - target_h) // 2

        self.setGeometry(x, y, target_w, target_h)

    def showEvent(self, event):
        super().showEvent(event)
        scr = self.screen()
        if scr is not None:
            avail = scr.availableGeometry()
            if self.width() > avail.width() or self.height() > avail.height():
                self._apply_adaptive_geometry()

    def initUI(self, session_selector, buttons_controller):
        self.__add_menu()

        self.mainWidget = QWidget(self)
        self.main_lay = QVBoxLayout(self.mainWidget)
        self.main_lay.setContentsMargins(4, 4, 4, 4)
        self.main_lay.setSpacing(4)
        self.setWindowIcon(QIcon('picture/graph.png'))
        self.setCentralWidget(self.mainWidget)

        self.session_selector = session_selector

        self.stack = QStackedWidget(self)
        self.stack.setMinimumWidth(0)
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.main_lay.addWidget(self.session_selector)
        self.main_lay.addWidget(self.stack, 1)

    def __add_menu(self):
        menubar = self.menuBar()

        self.file_menu = menubar.addMenu(QApplication.translate('graph', "Файл"))
        self.edit_menu = menubar.addMenu(QApplication.translate('graph', "Правка"))
        data_menu = menubar.addMenu(QApplication.translate('graph', "Данные"))

        self.rename_param_action = QAction(
            QApplication.translate('graph', "Изменить имена параметров"), self)
        self.log_path_open = QtWidgets.QAction(
            QApplication.translate('graph', "Открыть лог файл"), self)

        self.save_action = QAction(QApplication.translate('graph', "Сохранить"), self)
        self.save_action.setShortcut("Ctrl + S")
        self.save_action_as = QAction(QApplication.translate('graph', "Сохранить как..."), self)
        self.save_action_as.setShortcut("Ctrl + Shift + S")
        self.load_action = QAction(QApplication.translate('graph', "Загрузить"), self)
        self.load_action.setShortcut("Ctrl + O")

        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.save_action_as)
        self.file_menu.addAction(self.load_action)
        self.file_menu.addAction(self.log_path_open)

        # --- Импорт данных и осциллограмм перенесён в меню «Файл» ---
        if self.buttons_controller is not None:
            self.file_menu.addSeparator()

            self.import_data_action = QAction(
                QApplication.translate('graph', "Импортировать данные"), self
            )
            self.import_data_action.triggered.connect(
                self.buttons_controller.handle_import_data
            )
            self.file_menu.addAction(self.import_data_action)

            self.import_osc_action = QAction(
                QApplication.translate('graph', "Импортировать осциллограммы"), self
            )
            self.import_osc_action.triggered.connect(
                self.buttons_controller.handle_import_osc
            )
            self.file_menu.addAction(self.import_osc_action)

        if self.session_controller is not None:
            self.file_menu.addSeparator()

            self.live_demo_action = QAction(
                QApplication.translate('graph', "Демо: live-сессия"), self)
            self.live_demo_action.setToolTip(QApplication.translate(
                'graph',
                "2 прибора × 3 канала, по 100 точек каждую секунду"))
            self.live_demo_action.triggered.connect(
                self.session_controller.start_live_demo_session)
            self.file_menu.addAction(self.live_demo_action)

            self.static_demo_action = QAction(
                QApplication.translate('graph', "Демо: готовые данные"), self)
            self.static_demo_action.setToolTip(QApplication.translate(
                'graph',
                "2 прибора × 3 канала, 10 000 точек сразу"))
            self.static_demo_action.triggered.connect(
                self.session_controller.load_static_demo_session)
            self.file_menu.addAction(self.static_demo_action)

        data_menu.addAction(self.rename_param_action)

        if self.action_registry is not None:
            self.action_registry.add_actions_to_menu(self.edit_menu, "edit")

    def closeEvent(self, event):
        self.graph_win_close_signal.emit(1)
        event.accept()


class GraphSession(QWidget):
    graph_win_close_signal = pyqtSignal(int)

    def __init__(self, id, name, alias_manager, session_controller, simple_mode=False, ses_uuid=None):
        super().__init__()
        self.alias_manager = alias_manager
        self.notification = None
        self.session_id = id
        self.session_controller = session_controller
        self._session_name = name
        self.description = None
        self.uuid = uuid.uuid4().hex if ses_uuid is None else ses_uuid
        logger.info(f"Session {self.uuid=} created")
        self._simple_mode = simple_mode
        self.selection_model = SelectionModel(parent=self)

        # per-session undo manager
        self.undo_manager = SessionUndoManager(parent=self)
        self.analysis_controller = AnalysisController(self, parent=self)
        self.analysis_controller.artifacts_changed.connect(self._sync_analysis_tree)

        self.initUI()

    @property
    def mode(self) -> SessionMode:
        """Режим сессии: LIVE — эксперимент идёт, REVIEW — остановлен/импорт."""
        if not hasattr(self, "data_manager") or self.data_manager is None:
            return SessionMode.REVIEW
        if self.data_manager.is_session_running():
            return SessionMode.LIVE
        return SessionMode.REVIEW

    def is_live(self) -> bool:
        return self.mode == SessionMode.LIVE

    def can(self, modify: bool = False) -> bool:
        """Можно ли что-то менять. В LIVE тяжёлые операции запрещены."""
        if modify:
            return self.mode != SessionMode.LIVE
        return True

    @property
    def session_name(self):
        return self._session_name

    @session_name.setter
    def session_name(self, value):
        self._session_name = value

    def get_compare_graph(self):
        return self.session_controller.get_compare_graph()

    def animation_start(self, animator):
        self.session_controller.animation_start(animator)

    def _sync_analysis_tree(self) -> None:
        """Синхронизирует AnalysisTreeItem'ы в дереве под источниками."""
        from graphs.ui.tree_curves import AnalysisTreeItem, CurveTreeItem
        for curve_item in self.tree_class.curves:
            if not isinstance(curve_item, CurveTreeItem):
                continue
            root_name = curve_item.curve_data_obj.rel_data.root_name
            wanted = {a.id: a for a in self.analysis_controller.get_artifacts_for_curve(root_name)}
            existing = {it.artifact_id: it for it in curve_item.get_analysis_items()}
            # Удалить отсутствующие
            for aid, item in existing.items():
                if aid not in wanted:
                    curve_item.remove_analysis_item(item)
            # Добавить новые
            for aid, art in wanted.items():
                if aid not in existing:
                    desc = AnalysisToolRegistry.instance().get(art.tool_id)
                    human = tr_analysis(desc.title_key) if desc else art.tool_id
                    text = f"{root_name} → {human}"
                    if art.description:
                        text += f" ({art.description})"
                    new_item = AnalysisTreeItem(aid, text, tool_id=art.tool_id)
                    if not art.visibility:
                        f = new_item.font(0)
                        f.setItalic(True)
                        new_item.setFont(0, f)
                    curve_item.add_analysis_item(new_item, art.order_index)

    def initUI(self):
        simple = self._simple_mode
        self.up_lay = QHBoxLayout(self)

        if not simple:
            from graphs.ui.filters_win import filtersClass
            self.filter_class = filtersClass()
            self.tree_class = treeWin(
                main_class=self,
                action_registry=getattr(self.session_controller, "action_registry", None),
            )
            # Клик/выбор в дереве синхронизируется с SelectionModel,
            # чтобы артефакты анализа подсвечивались на всех графиках.
            self.tree_class.tree_widget.itemSelectionChanged.connect(
                self._on_tree_selection_changed
            )

        if not simple:
            self.tree_class.analysis_item_removed.connect(self._on_analysis_item_removed)
            self.tree_class.analysis_item_visibility_toggled.connect(
                self._on_analysis_item_visibility_toggled)
            self.tree_class.analysis_item_properties_requested.connect(
                self._on_analysis_item_properties_requested)

        self.tabWidget = QTabWidget()

        splitter = QSplitter()
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        splitter.setOrientation(1)

        if not simple:
            splitter.addWidget(self.tree_class)
        splitter.addWidget(self.tabWidget)

        if not simple:
            pass
            #splitter.addWidget(self.filter_class.filt_window)

        splitter.setHandleWidth(1)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 10)
        splitter.setStretchFactor(2, 1)

        one_deca_part = self.width() // 10
        splitter.setSizes([one_deca_part, one_deca_part * 9, 0])

        self.select_win = None

        if not simple:
            self.data_manager = graphDataManager(alias_manager=self.alias_manager)
            self.select_win = paramSelector(alias_manager=self.alias_manager)
            self.select_controller = paramController(self.select_win, alias_manager=self.alias_manager)
            self.filter_class.set_filter_slot(self.filters_callback)
            self.data_manager.stop_current_session.connect(self._on_session_stopped)

        self.tab1 = tabPage(1)
        self.tab2 = tabPage(2)

        self.tabWidget.addTab(self.tab1, QApplication.translate("GraphWindow", "Графики"))
        self.tabWidget.addTab(self.tab2, QApplication.translate("GraphWindow", "Осциллограммы"))

        self.selector_osc = OscilloscopeSelector()

        self.graph_main = manageGraph(
            tablet_page=self.tab1,
            main_class=self,
            select_data_wid=self.select_win,
            alias_manager=self.alias_manager,
            selection_model=self.selection_model,
        )
        self.graph_wave = graphOsc(
            self.tab2,
            self.selector_osc,
            self,
            alias_manager=self.alias_manager
        )

        self.helper_manager = HelperManager(self, parent=self)


        # При смене внешнего вида основного графика — обновить все дочерние
        # (attached-панели и domain-вкладки анализа).
        self.graph_main.graphView.style_changed.connect(self._on_main_style_changed)

        if not simple:
            self.adapter_main_graph = graphSelectAdapter(
                self.graph_main,
                self.select_controller,
                self.data_manager,
                self.tree_class,
                'main',
                self
            )
            self.adapter_osc_graph = waveSelectAdapter(
                self.graph_wave,
                self.selector_osc,
                self.data_manager,
                'osc',
                self
            )

        # Горизонтальный сплиттер: слева — графики, справа — инспектор
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(splitter)

        self.inspector = Inspector(self)
        self.main_splitter.addWidget(self.inspector)

        self.main_splitter.setSizes([self.width() - 320, 320])
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)

        self.up_lay.addWidget(self.main_splitter)


        # подключение undo для инфинитных линий обеих вкладок
        for gv in (self.graph_main.graphView,
                   self.graph_wave.graphView,
                   self.graph_wave.graphView_loop):
            if gv is None:
                continue
            gv.inf_line_added.connect(self._on_inf_line_added)
            gv.inf_line_removed.connect(self._on_inf_line_removed)
            gv.appearance_undo_callback = self._on_appearance_changed

        self.tabWidget.setCurrentIndex(0)

    def _on_tree_selection_changed(self) -> None:
        """Синхронизировать выделение дерева с SelectionModel."""
        try:
            from graphs.ui.tree_curves import CurveTreeItem
            selected_curves = []
            for item in self.tree_class.tree_widget.selectedItems():
                root = item
                while root.parent() is not None:
                    root = root.parent()
                if isinstance(root, CurveTreeItem) and root in self.tree_class.curves:
                    facade = root.curve_data_obj
                    if facade not in selected_curves:
                        selected_curves.append(facade)
            self.selection_model.select(selected_curves)
        except Exception:
            logger.exception("_on_tree_selection_changed failed")

    def _on_main_style_changed(self) -> None:
        """Скопировать стиль основного графика во все дочерние поля анализа."""
        if self.sender() is not self.graph_main.graphView:
            return

        from graphs.analysis.renderers.base import apply_main_graph_style
        ctrl = getattr(self, "analysis_controller", None)
        if ctrl is None:
            return
        renderer = getattr(ctrl, "renderer", None)
        if renderer is None:
            return

        failed: list[str] = []
        for kind, items in (
            ("attached", getattr(renderer._attached, "_panels", {})),
            ("domain", getattr(renderer._domain, "_tabs", {})),
        ):
            for key, info in items.items():
                plot = info.get("plot")
                if plot is None:
                    continue
                try:
                    apply_main_graph_style(self, plot)
                except (AttributeError, RuntimeError, KeyError) as exc:
                    failed.append(f"{kind}:{key} ({type(exc).__name__}: {exc})")

        try:
            renderer._domain.reapply_labels()
        except (AttributeError, RuntimeError, KeyError) as exc:
            failed.append(f"domain labels: {type(exc).__name__}: {exc}")

        if failed:
            logger.warning(
                "_on_main_style_changed: %d sub-graph(s) failed: %s",
                len(failed), ", ".join(failed),
            )

    def show_tooltip(self, message, show_while_not_click=False, timeout=3000):
        if self.notification is None:
            self.notification = NotificationWidget(parent=self)

        self.notification.set_message(message)

        note_size = self.notification.sizeHint()
        pos = QPoint(self.width() - note_size.width(), self.height() - note_size.height())

        self.notification.move(pos)

        if show_while_not_click:
            self.notification.show()
        else:
            self.notification.show_with_animation(timeout=timeout)

    # ------------------------------------------------------------------
    # Undo/redo: обработчики сигналов от виджетов
    # ------------------------------------------------------------------
    def _on_inf_line_added(self, line):
        if self.undo_manager.is_applying:
            return
        from graphs.core.undo_commands import AddInfiniteLineCommand
        target = None
        for gv in (self.graph_main.graphView,
                   self.graph_wave.graphView,
                   self.graph_wave.graphView_loop):
            if gv is not None and line in gv.inf_lines:
                target = gv
                break
        if target is None:
            return
        self.undo_manager.push(AddInfiniteLineCommand(target, line))

    def _on_session_stopped(self):
        """При остановке эксперимента переходим в REVIEW-режим."""
        self.inspector.setVisible(True)
        # Скрыть секцию видимого окна точек: в REVIEW данные не растут.
        if getattr(self, "select_controller", None) is not None:
            self.select_controller.set_live_mode(False)

    def _on_analysis_item_removed(self, artifact_id: str) -> None:
        self.analysis_controller.remove_artifact(artifact_id)

    def _on_analysis_item_visibility_toggled(self, artifact_id: str, visible: bool) -> None:
        self.analysis_controller.set_artifact_visibility(artifact_id, visible)

    def _on_analysis_item_properties_requested(self, artifact_id: str) -> None:
        # Открыть вкладку «Анализ» с параметрами артефакта
        if hasattr(self, "inspector"):
            self.inspector.curve_inspector.tabs.setCurrentWidget(
                self.inspector.curve_inspector.tools_tab)

    def _on_inf_line_removed(self, line):
        if self.undo_manager.is_applying:
            return
        from graphs.core.undo_commands import RemoveInfiniteLineCommand
        sender = self.sender()
        if sender is None:
            return
        self.undo_manager.push(RemoveInfiniteLineCommand(sender, line))

    def _on_appearance_changed(self, widget, before_settings, after_settings):
        if self.undo_manager.is_applying:
            return
        from graphs.core.undo_commands import GraphAppearanceCommand
        self.undo_manager.push(
            GraphAppearanceCommand(widget, before_settings, after_settings)
        )

    # ------------------------------------------------------------------
    # Фильтры
    # ------------------------------------------------------------------
    def filters_callback(self, filter_comand: FilterCommand):
        is_apply = True
        if self.data_manager is not None:
            if not self.can(modify=True):
                is_apply = False

        if not is_apply:
            self.show_tooltip(
                QApplication.translate("GraphWindow", "Дождитесь окончания эксперимента"),
                timeout=3000,
            )
            return

        active_tab_index = self.tabWidget.currentIndex()
        if active_tab_index == 0:
            affected = self.graph_main.set_filters(filter_comand)
            if affected and not self.undo_manager.is_applying:
                self.undo_manager.push(ApplyFilterCommand(affected, filter_comand))
        elif active_tab_index == 1:
            self.graph_wave.set_filters(filter_comand)

        self.show_tooltip(
            QApplication.translate(
                "GraphWindow",
                "Фильтры применены к выделенным графикам. \n "
                "Для сброса фильтров выделите графики и нажмите кнопку esc.",
            ),
            timeout=5000,
        )

    def update_graphics(self, new_data: dict, is_exp_stop=False):
        '''is_exp_stop - флаг остановки эксперимента, передается, когда эксперимент завершается, принудительно переводит окно графиков в расщиренный режим просмотра'''
        if new_data:
            self.data_manager.add_measurement_data(new_data)

    def set_default(self):
        self.graph_main.set_default()
        self.graph_wave.set_default()

    def closeEvent(self, event):
        self.graph_win_close_signal.emit(1)

    def get_field_settings(self) -> FieldSettings:
        """Возвращает настройки графика и осциллограмм для сохранения."""
        fs = FieldSettings()
        fs.graph_field = extract_plot_widget_settings(self.graph_main.graphView)
        fs.oscilloscope_field = extract_plot_widget_settings(self.graph_wave.graphView)
        fs.graph_field.is_second_axis_enabled = self.select_win.second_check_box.isChecked()

        y1_mult = self.select_win.y1_group.multiple_check.isChecked()
        y2_mult = self.select_win.y2_group.multiple_check.isChecked()
        fs.graph_field.is_multiple_y1_enabled = y1_mult
        fs.graph_field.is_multiple_y2_enabled = y2_mult
        # legacy: пишем Y1, чтобы старый софт видел хоть что-то осмысленное
        fs.graph_field.is_multiple_selection_enabled = y1_mult
        return fs

    def apply_field_settings(self, settings: FieldSettings) -> None:
        """Применяет настройки к UI."""
        adapter = HDF5ToProjectAdapter()
        adapter.apply_graph_settings(self.graph_main.graphView, settings)
        # аналогично для осциллограмм, если нужно
        self.select_win.set_second_check_box(settings.graph_field.is_second_axis_enabled)

        gf = settings.graph_field
        y1_mult = getattr(
            gf, 'is_multiple_y1_enabled', gf.is_multiple_selection_enabled
        )
        y2_mult = getattr(gf, 'is_multiple_y2_enabled', False)
        self.select_win.set_multiple_mode_y1(y1_mult)
        self.select_win.set_multiple_mode_y2(y2_mult)

class running_exp_test(QWidget):

    def __init__(self, graph_class, max_points, periodsec):
        super().__init__()
        self.test1 = test_graph(is_sine_wave=True)
        self.test2 = test_graph()
        self.gen1 = self.test1.append_values()
        self.gen2 = self.test2.append_values()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.gen_new_data)
        self.counter_test = 0
        self.max_points = max_points
        self.periodsec = periodsec
        self.graph_class = graph_class

    def run(self):
        self.id = self.graph_class.start_new_session("test", is_experiment_running=True, use_timestamps=True)
        self.timer.start(int(self.periodsec * 1000))

    def gen_new_data(self):
        """функция раз в n секунд генерирует словарь и обновляет данные"""
        if random.random() < 0.5:
            gen = self.gen1
        else:
            gen = self.gen2
        self.graph_class.update_session_data(self.id, (next(gen)))
        self.counter_test += 1

        if self.counter_test >= self.max_points:
            self.counter_test = 0
            self.timer.stop()
            self.graph_class.stop_session_running(self.id)


class sessionController():
    def __init__(self, current_version=None):
        self.version_app = "1.0.0" if not current_version else str(current_version)
        self.experiment_port = ExperimentPort(self)
        self.alias_manager = ParameterAliasManager()
        self.action_registry = ActionRegistry(parent=self.alias_manager)

        self._pub_win = None

        # --- undo/redo через реестр ---
        self.undo_action = self.action_registry.register(
            "edit.undo",
            QApplication.translate("GraphWindow", "Отменить"),
            self._undo_current_session,
            shortcut="Ctrl+Z",
            context="edit",
            tooltip=QApplication.translate("GraphWindow", "Отменить последнее действие"),
        )
        self.redo_action = self.action_registry.register(
            "edit.redo",
            QApplication.translate("GraphWindow", "Повторить"),
            self._redo_current_session,
            shortcut="Ctrl+Y",
            context="edit",
            tooltip=QApplication.translate("GraphWindow", "Повторить отменённое действие"),
        )
        # Второй shortcut для redo
        self.redo_action.setShortcuts(["Ctrl+Y", "Ctrl+Shift+Z"])
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)

        self.session_selector = SessionSelectControl()
        self.buttons_controller = ButtonsControl(self.session_selector)
        self.status_bar = StatusBar()
        self.button_ctrl_win = self.buttons_controller.widget
        self.controll_sessions_win = self.session_selector.widget

        self.session_selector.current_session_changed.connect(self.change_session)
        self.session_selector.session_deleted.connect(self.delete_session)
        self.session_selector.session_name_changed.connect(self._session_renamed)
        self.session_selector.session_description_changed.connect(self._session_description_changed)

        self.buttons_controller.new_data_imported.connect(self.data_imported)


        self.graphics_win = GraphWindow(
            self.controll_sessions_win,
            self.buttons_controller,
            version=self.version_app,
            action_registry=self.action_registry,
            session_controller=self
        )
        self.graphics_win.setStatusBar(self.status_bar)
        self.graphics_win.graph_win_close_signal.connect(self.close_graph_window)
        self.graphics_win.save_action.triggered.connect(self.push_button_save_graph)
        self.graphics_win.load_action.triggered.connect(self.push_button_open_graph)
        self.graphics_win.log_path_open.triggered.connect(open_log_file)
        self.graphics_win.save_action_as.triggered.connect(self.push_button_save_graph_as)
        self.graphics_win.rename_param_action.triggered.connect(self.show_alias_dialog)

        # --- Empty state: показывается, когда в проекте нет ни одной сессии ---
        self._empty_state_page = EmptyStateWidget(self.graphics_win)
        self.graphics_win.stack.addWidget(self._empty_state_page)

        self._empty_state_page.load_hdf5_requested.connect(
            self.push_button_open_graph)
        self._empty_state_page.import_excel_requested.connect(
            self.buttons_controller.handle_import_data)
        self._empty_state_page.start_live_demo_requested.connect(
            self.start_live_demo_session)
        self._empty_state_page.start_static_demo_requested.connect(
            self.load_static_demo_session)

        self.way_to_save_file = None
        self.way_to_save_excel = None
        self.way_to_save_project = None

        self.graph_sessions = {}
        self.compare_graph = None
        self.animation_win = None
        self.dot_counter = 0
        self._live_demo = None

        self._update_undo_actions()

        self.status_bar.set_permanent("Готово")

        self._refresh_empty_state()

    def get_publication_window(self):
        if self._pub_win is None:
            from publication.ui.publication_window import PublicationWindow
            self._pub_win = PublicationWindow(self)
        return self._pub_win

    # ------------------------------------------------------------------
    # Undo/redo: центральные слоты
    # ------------------------------------------------------------------
    def _current_session(self):
        """Активная GraphSession или None."""
        if not hasattr(self, "graphics_win") or self.graphics_win is None:
            return None
        current_widget = self.graphics_win.stack.currentWidget()
        for session in self.graph_sessions.values():
            if session is current_widget:
                return session
        return None

    def _refresh_empty_state(self) -> None:
        """Показать заглушку с кнопками, когда сессий нет вообще,
        и переключиться на первую сессию, если она появилась."""
        if not self.graph_sessions:
            self.graphics_win.stack.setCurrentWidget(self._empty_state_page)
            return
        if self.graphics_win.stack.currentWidget() is self._empty_state_page:
            first_session = next(iter(self.graph_sessions.values()))
            self.graphics_win.stack.setCurrentWidget(first_session)

    def _undo_current_session(self):
        session = self._current_session()
        if session is not None and hasattr(session, "undo_manager"):
            session.undo_manager.undo()

    def _redo_current_session(self):
        session = self._current_session()
        if session is not None and hasattr(session, "undo_manager"):
            session.undo_manager.redo()

    def _update_undo_actions(self):
        tr = QApplication.translate
        base_u = tr('graph', "Отменить")
        base_r = tr('graph', "Повторить")

        session = self._current_session()
        if session is None or not hasattr(session, "undo_manager"):
            self.undo_action.setEnabled(False)
            self.redo_action.setEnabled(False)
            self.undo_action.setText(base_u)
            self.redo_action.setText(base_r)
            return

        mgr = session.undo_manager
        self.undo_action.setEnabled(mgr.can_undo())
        self.redo_action.setEnabled(mgr.can_redo())

        ut = mgr.undo_text()
        rt = mgr.redo_text()
        self.undo_action.setText(f"{base_u}: {ut}" if ut else base_u)
        self.redo_action.setText(f"{base_r}: {rt}" if rt else base_r)

    # ------------------------------------------------------------------
    # Окно
    # ------------------------------------------------------------------
    def close_graph_window(self):
        if self.compare_graph is not None:
            self.compare_graph.close()
            self.compare_graph = None
        self.graphics_win.close()

    def close(self):
        if self.compare_graph is not None:
            self.compare_graph.close()
        self.graphics_win.close()

    def animation_start(self, animator):
        if self.animation_win is not None:
            if self.animation_win.animator.is_playing:
                self.animation_win.animator.stop()
            self.animation_win.close()
        self.animation_win = AnimationWindow(animator=animator)
        self.animation_win.show()

    def get_compare_graph(self):
        if self.compare_graph is None:
            graph_compare = GraphSession(
                id=125,
                name="compare",
                alias_manager=self.alias_manager,
                session_controller=self,
                simple_mode=True,
                ses_uuid=125
            )
            self.compare_graph = CompareWindowMediator(1,
                                                       "test",
                                                       self.alias_manager,
                                                       graph_compare,
                                                       )
        self.compare_graph.window.show()
        return self.compare_graph

    def show_alias_dialog(self):
        """Показывает диалог управления псевдонимами"""
        # available_params = self.get_name_params()
        dialog = ParameterAliasDialog(self.alias_manager, self.graphics_win)
        dialog.exec_()

    def push_button_save_graph(self):
        """Быстрое сохранение проекта – всегда в HDF5, независимо от последнего Save As."""

        for session in self.graph_sessions.values():
            for curve in session.graph_main.get_curves().values():
                try:
                    curve.ensure_stats_fresh()
                except Exception:
                    logger.exception("push_button_save_graph: ensure_stats_fresh failed")
        if self.way_to_save_project is not None:
            # Сохраняем по известному пути проекта
            HDF5Facade().save_project(self, self.way_to_save_project)
            self.graphics_win.setWindowTitle(self.way_to_save_project)
        else:
            # Путь проекта ещё не задан – открываем диалог только для HDF5
            options = QtWidgets.QFileDialog.Options()
            options |= QtWidgets.QFileDialog.DontUseNativeDialog
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.graphics_win,
                "Сохранить проект",
                "",
                "Installation (*.hdf5)",
                options=options,
            )
            if fileName:
                if not fileName.endswith('.hdf5'):
                    fileName += '.hdf5'
                self.way_to_save_project = fileName
                HDF5Facade().save_project(self, fileName)
                self.graphics_win.setWindowTitle(fileName)

    def push_button_save_graph_as(self):
        for session in self.graph_sessions.values():
            for curve in session.graph_main.get_curves().values():
                try:
                    curve.ensure_stats_fresh()
                except Exception:
                    logger.exception("push_button_save_graph_as: ensure_stats_fresh failed")
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog

        initial_path = self.way_to_save_project or self.way_to_save_excel or ""
        fileName, selectedFilter = QtWidgets.QFileDialog.getSaveFileName(
            self.graphics_win, "Сохранить как", initial_path,
            "Installation (*.hdf5);; Книга Excel (*.xlsx)",
            options=options,
        )
        if not fileName:
            return

        if selectedFilter == "Installation (*.hdf5)":
            if not fileName.endswith('.hdf5'):
                fileName += '.hdf5'
            self.way_to_save_project = fileName
            HDF5Facade().save_project(self, fileName)
            self.graphics_win.setWindowTitle(fileName)
        elif selectedFilter == "Книга Excel (*.xlsx)":
            if not fileName.endswith('.xlsx'):
                fileName += '.xlsx'
            self.way_to_save_excel = fileName
            try:
                self._save_excel(fileName)
            except Exception as e:
                self.status_bar.set_status(f"Ошибка сохранения: {e}", timeout=5000)
                logger.error(f"Ошибка при сохранении Excel файла: {e}")
            finally:
                self.status_bar.hide_progress()
        else:
            logger.warning(f"Неизвестный фильтр при сохранении: {selectedFilter}")

    def _save_excel(self, filepath: str):
        from graphs.export.save_excell import ExcelSaver

        self.temp_excell_file_path = filepath
        self.excel_saver = ExcelSaver()
        sessions = list(self.graph_sessions.values())
        if not sessions:
            self.status_bar.set_status("Нет данных для сохранения.", timeout=3000)
            return

        for session in sessions:
            sheet_dict = {}
            parameters = session.data_manager.get_all_data()
            for type_param in parameters.keys():
                for param_name in parameters[type_param].data.keys():
                    alias_param = self.alias_manager.get_alias(param_name)
                    sheet_dict[alias_param] = parameters[type_param].data[param_name]
            self.excel_saver.add_sheet(
                sheet_name=session.session_name,
                sheet_data=sheet_dict,
                description=session.description,
            )

        self.excel_saver.enable_statistics()

        self.progress_save_excell = self.status_bar.show_progress(0, 100)
        self.status_bar.set_status("Сохранение...")

        self.excel_saver.save(filepath)

        self.saving_excell_timer = QTimer()
        self.saving_excell_timer.setInterval(1000)
        self.saving_excell_timer.timeout.connect(self.update_progress_saver)
        self.saving_excell_timer.start()

    def update_progress_saver(self):
        processed, total, status = self.excel_saver.get_progress()
        if total > 0:
            percent = int((processed / total) * 100)
            self.progress_save_excell.setValue(percent)

            self.dot_counter = (self.dot_counter + 1) % 4
            dots = '.' * (self.dot_counter + 1)
            base_status = status.rstrip('.')
            self.status_bar.set_status(base_status + dots)
        else:
            self.status_bar.set_status("Подготовка...")

        if not self.excel_saver.is_saving:
            self.saving_excell_timer.stop()
            self.status_bar.hide_progress()
            self.status_bar.set_permanent(f"Файл эксель сохранён: {self.temp_excell_file_path}")

    def push_button_open_graph(self):
        logger.debug("нажата кнопка открыть график")
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, ans = QtWidgets.QFileDialog.getOpenFileName(
            self.graphics_win,
            "Open File",
            "",
            "Installation(*.hdf5)",
            options=options,
        )
        if ans == "Installation(*.hdf5)":
            self.load_project(fileName)

    def load_project(self, file_path: str):
        HDF5Facade().load_project(file_path, self)
        self.way_to_save_project = file_path
        self.graphics_win.setWindowTitle(self.way_to_save_project)

    def show(self):
        self.graphics_win.show()

    def start_live_demo_session(self):
        """Live-демо: 2 прибора × 3 канала × 100 точек/с."""
        if self._live_demo is not None:
            self._live_demo.stop()
        self._live_demo = LiveDemoController(self)
        if not self._live_demo.start():
            self._live_demo = None
            self.status_bar.set_status(
                QApplication.translate("graph", "Не удалось запустить live-демо"), 5000)

    def load_static_demo_session(self):
        """Демо: 10 000 точек сразу, обычная остановленная сессия."""
        sid = StaticDemoLoader(self).load()
        if sid is None:
            self.status_bar.set_status(
                QApplication.translate("graph", "Не удалось загрузить демо-данные"), 5000)
        else:
            self.status_bar.set_status(
                QApplication.translate("graph", "Демо-данные загружены"), 3000)

    def stop_session_running(self, session_id):
        if self.graph_sessions.get(session_id):
            self.graph_sessions[session_id].data_manager.stop_session_running()
            self.session_selector.set_session_status(session_id=session_id, status="Exp completed")

    def start_new_session(self, session_name: str, use_timestamps: bool = False,
                          is_experiment_running: bool = False, new_data=None, uuid=None) -> str | bool:
        session_id = self.session_selector.get_free_id()
        is_session_created = self.__create_session(session_name, session_id, use_timestamps,
                                                   is_experiment_running, new_data, uuid)

        if is_session_created:
            if is_experiment_running:
                status = "running"
            else:
                status = "downloaded"
            self.session_selector.add_session({'id': session_id, 'name': session_name, 'status': status})

            self.change_session(session_id)

        return session_id if is_session_created else False

    def __create_session(self, session_name: str, session_id: str, use_timestamps: bool = False,
                         is_experiment_running: bool = False, new_data=None, uuid=None) -> bool:
        new_session_graph = GraphSession(session_id, copy.copy(session_name),
                                         alias_manager=self.alias_manager,
                                         ses_uuid=uuid, session_controller=self)
        try:
            new_session_graph.data_manager.start_new_session(session_id, use_timestamps,
                                                             is_experiment_running, new_data)
            logger.info(f"Session {session_id} {new_session_graph.uuid=} {new_session_graph.session_name=} created")
        except Exception as e:
            logger.warning(f"Failed to start session {session_id} {e}")
            return False

        if is_experiment_running:
            new_session_graph.inspector.setVisible(False)
        else:
            new_session_graph.inspector.setVisible(True)

        # «Отображение точек» показываем только в LIVE-режиме.
        # В simple_mode (окно сравнения) select_controller отсутствует —
        # защищаемся через hasattr, хотя __create_session для него и не
        # вызывается.
        if hasattr(new_session_graph, "select_controller"):
            new_session_graph.select_controller.set_live_mode(
                bool(is_experiment_running)
            )

        self.graph_sessions[session_id] = new_session_graph
        self.graphics_win.stack.addWidget(new_session_graph)

        # подключаем сигнал изменения истории — обновит состояние undo/redo-кнопок
        new_session_graph.undo_manager.state_changed.connect(self._update_undo_actions)

        self._refresh_empty_state()

        return True

    def change_session(self, session_id: str):
        session = self.graph_sessions.get(session_id)
        if session is not None:
            self.graphics_win.stack.setCurrentWidget(session)
            self.session_selector.set_current_session(session_id)
        else:
            logger.warning(f"Session {session_id} not found")
        # обновляем состояние undo/redo-кнопок под новую сессию
        self._update_undo_actions()

    def data_imported(self, session_name: str, session_id: str, data: dict):
        status = self.__create_session(session_name, session_id, new_data=data)
        if status:
            self.graph_sessions[session_id].data_manager.stop_session_running()
            self.session_selector.add_session({'id': session_id, 'name': session_name, 'status': 'imported'})
            self.status_bar.set_status(QApplication.translate("graph", "Данные импортированы"), 10000)

    def delete_session(self, session_id: str):
        session = self.graph_sessions.get(session_id)
        if session is None:
            return
        if not session.can(modify=True):
            session.show_tooltip(
                QApplication.translate("graph", "Сессию можно удалить только после остановки.")
            )
            logger.warning(f"Session {session_id} is running. Broke session deletion.")
            return

        ans = QMessageBox.question(
            self.graphics_win,
            QApplication.translate("graph", "Удаление сессии"),
            QApplication.translate(
                "graph",
                f"Удалить сессию «{session.session_name}»?\n\n"
                "Действие необратимо. При необходимости сохраните её через "
                "Файл → Сохранить как.",
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return

        was_current = self.graphics_win.stack.currentWidget() is session

        self.graphics_win.stack.removeWidget(session)
        session.graph_main.destroy_all_curves()
        session.deleteLater()
        del self.graph_sessions[session_id]
        self.session_selector.delete_session(session_id)

        if was_current and self.graph_sessions:
            new_cur = self.graphics_win.stack.currentWidget()
            for sid, s in self.graph_sessions.items():
                if s is new_cur:
                    self.change_session(sid)
                    break

        self._refresh_empty_state()

    def _session_renamed(self, session_id: str, new_session_name: str):
        logger.info(f"_session_renamed {session_id=} {new_session_name=}")
        session = self.graph_sessions.get(session_id)
        if session is None:
            logger.warning(f"Session {session_id} not found")
            return

        old_name = session.session_name
        if old_name == new_session_name:
            return

        session.session_name = copy.copy(new_session_name)

        if hasattr(session, "undo_manager") and not session.undo_manager.is_applying:
            session.undo_manager.push(
                RenameSessionCommand(self, session_id, old_name, new_session_name)
            )

    def _session_description_changed(self, session_id: str, new_description: str):
        session = self.graph_sessions.get(session_id)
        if session is None:
            logger.warning(f"Session {session_id} not found")
            return

        old_description = session.description or ""
        new_description = new_description or ""
        if old_description == new_description:
            return

        session.description = new_description

        if hasattr(session, "undo_manager") and not session.undo_manager.is_applying:
            session.undo_manager.push(
                ChangeDescriptionCommand(self, session_id, old_description, new_description)
            )

    def update_session_description(self, session_id: str, new_description: str):
        logger.info(f"update_session_description {session_id} {new_description}")
        if self.graph_sessions.get(session_id) is None:
            logger.warning(f"Session {session_id} not found")
            return
        else:
            self.graph_sessions[session_id].description = new_description
            self.session_selector.update_session_description(session_id, new_description)

    def change_session_name(self, session_id: str, new_session_name: str) -> bool:
        logger.info(f"change_session_name {session_id} {new_session_name}")
        if self.graph_sessions.get(session_id) is None:
            logger.warning(f"change_session_name Session {session_id=} not found skip new name {new_session_name=}")
            return False
        self._session_renamed(session_id, new_session_name)
        self.session_selector.set_session_name(session_id, new_session_name)
        return True

    def update_session_data(self, session_id: str, data: dict) -> bool:
        session = self.graph_sessions.get(session_id)
        if session is None:
            return False
        try:
            session.data_manager.add_measurement_data(data)
            return True
        except Exception as e:
            logger.exception(f"update_session_data failed for {session_id}: {e}")
            return False

    def get_session_name(self, session_id: str) -> str:
        logger.info(f"get_session_name {session_id} list: {self.graph_sessions}")
        if self.graph_sessions.get(session_id) is None:
            logger.warning(f"Session {session_id} not found")
            return None
        return self.graph_sessions[session_id].session_name

    def decode_add_exp_parameters(self, session_id, entry, time) -> bool:
        if self.graph_sessions.get(session_id) is None:
            return False
        return self.graph_sessions[session_id].data_manager.decode_add_exp_parameters(entry, time)


def run_graph_process(queue):
    app = QApplication([])
    controller = sessionController(current_version="test")
    controller.controll_sessions_win.show()
    app.exec_()