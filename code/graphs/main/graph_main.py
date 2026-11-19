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

import logging
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QVBoxLayout, QComboBox, QLineEdit,
    QPushButton, QWidget, QSplitter, QStackedWidget
)
from graphs.utils.colors import GColors
from graphs.core.curve_data import linearData, LineStyle
from graphs.core.dataManager import relationData
from graphs.ui.customPlotWidget import PatchedPlotWidget
from graphs.core.filters_instance_class import FilterCommand

logger = logging.getLogger(__name__)

DEFAULT_AXIS_LABELS = {"bottom": "X", "left": "Y", "right": "Y2"}

class CustomComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.minimum_w = None

    def addItem(self, text):
        super().addItem(text)
        fm = QFontMetrics(self.font())
        self.minimum_w = max(fm.width(self.itemText(i)) for i in range(self.count()))

    def showPopup(self):
        super().showPopup()
        if self.minimum_w:
            self.view().setMinimumWidth(self.minimum_w)

class manageGraph(QObject):
    new_curve_selected = pyqtSignal()
    curve_added = pyqtSignal(object)
    curve_removed = pyqtSignal(object)
    DEFAULT_NUM_POINTS = 10
    DEFAULT_SHOW_ALL = True
    DEFAULT_CONNECT_LINES = True
    DEFAULT_SHOW_MARKERS = False

    def __init__(self, tablet_page, main_class, select_data_wid, alias_manager, selection_model=None):
        super().__init__()
        self.alias_manager = alias_manager
        self.selection_model = selection_model
        self.page = tablet_page
        self.select_win = select_data_wid
        self.main_class = main_class
        self._num_showing_points: int = self.DEFAULT_NUM_POINTS
        self._is_all_points_showing: bool = self.DEFAULT_SHOW_ALL
        self._is_connect_lines: bool = self.DEFAULT_CONNECT_LINES
        self._is_show_markers: bool = self.DEFAULT_SHOW_MARKERS
        self._axis_param_names = {key: [] for key in DEFAULT_AXIS_LABELS}
        self.axislabel_line_edit = QLineEdit()
        self.axislabel_line_edit.setVisible(False)
        self.focus_axis = None
        self.__stack_curve = {}
        self.inf_lines = []
        self.colors_class = GColors()
        self.color_warm_gen = self.colors_class.get_random_warm_color()
        self.color_cold_gen = self.colors_class.get_random_cold_color()
        self.initUI()

    def set_axis_auto_labels(self, x_name, y1_names, y2_names) -> None:
        self._axis_param_names = {
            "bottom": [x_name] if x_name else [],
            "left": list(y1_names or []),
            "right": list(y2_names or []),
        }
        self.refresh_axis_auto_labels()

    def refresh_axis_auto_labels(self) -> None:
        for key, default_label in DEFAULT_AXIS_LABELS.items():
            controller = self.graphView.axises.get(key)
            if controller is None:
                continue
            names = [n for n in self._axis_param_names.get(key, []) if n]
            controller.apply_auto_label(names[0] if len(names) == 1 else default_label)

    def set_num_points(self, value: int) -> None:
        self._num_showing_points = max(1, int(value))
        for curve in self.__stack_curve.values():
            curve.set_num_points(self._num_showing_points)

    def show_all_points(self, state: bool) -> None:
        self._is_all_points_showing = bool(state)
        for curve in self.__stack_curve.values():
            curve.show_all_points(self._is_all_points_showing)

    def _on_scene_mouse_moved(self,pos):
        try:
            view=self.graphView.plotItem.vb
            p=view.mapSceneToView(pos)
            self.main_class.update_cursor_position(p.x(),p.y())
        except Exception:
            logger.debug("_on_scene_mouse_moved failed",exc_info=True)

    def eventFilter(self,watched,event):
        from PyQt5.QtCore import QEvent
        if watched is self.graphView.viewport() and event.type()==QEvent.Leave:
            try:
                self.main_class.clear_cursor_position()
            except Exception:
                logger.debug("eventFilter clear cursor failed",exc_info=True)
        return super().eventFilter(watched,event) if hasattr(super(),"eventFilter") else False


    def set_connect_lines(self, state: bool) -> None:
        self._is_connect_lines = bool(state)
        for curve in self.__stack_curve.values():
            curve.set_connect_lines(self._is_connect_lines)

    def set_show_markers(self, state: bool) -> None:
        self._is_show_markers = bool(state)
        for curve in self.__stack_curve.values():
            curve.set_show_markers(self._is_show_markers)

    def _apply_window_state_to_curve(self, curve) -> None:
        curve.set_num_points(self._num_showing_points)
        curve.show_all_points(self._is_all_points_showing)
        curve.set_connect_lines(self._is_connect_lines)
        curve.set_show_markers(self._is_show_markers)

    def initUI(self):
        self.tab1Layout=QVBoxLayout()
        self.graphView=PatchedPlotWidget()
        self.graphView.scene().sigMouseClicked.connect(self.click_scene_main_graph)
        self.graphView.scene().sigMouseMoved.connect(self._on_scene_mouse_moved)
        self.graphView.viewport().installEventFilter(self)
        self.graphView.inf_line_added.connect(self._on_inf_line_added)
        self.graphView.inf_line_removed.connect(self._on_inf_line_removed)
        self.graphView.appearance_undo_callback=self._on_appearance_changed
        self.graphView.legend_recreated.connect(self._on_legend_recreated)
        self.graphView.plotItem.getAxis("left").linkToView(self.graphView.plotItem.getViewBox())
        self.graphView.plotItem.getAxis("bottom").linkToView(self.graphView.plotItem.getViewBox())
        self.axislabel_line_edit.setParent(self.graphView)
        self.graph_splitter=QSplitter(Qt.Vertical)
        self.graph_splitter.setChildrenCollapsible(True)
        if self.select_win is not None:
            self.graph_splitter.addWidget(self.select_win)
        self.graph_splitter.addWidget(self.graphView)
        if self.select_win is not None:
            self.graph_splitter.setStretchFactor(0,0)
            self.graph_splitter.setStretchFactor(1,1)
            self.graph_splitter.setSizes([220,400])
        self.tab1Layout.addWidget(self.graph_splitter)
        self.page.setLayout(self.tab1Layout)
        self.page.subscribe_to_key_press(key=Qt.Key_Delete,callback=self.delete_key_press)
        self.page.subscribe_to_key_press(key=Qt.Key_Escape,callback=self.reset_filters)
        self.page.subscribe_to_key_press(key=Qt.Key_Enter,callback=self.click_enter_key)
        self.page.subscribe_to_key_press(key=Qt.Key_Return,callback=self.click_enter_key)

    def set_second_axis(self, state: bool):
        self.graphView.set_second_axis(state)

    def get_list_curves(self):
        return list(self.__stack_curve.values())

    def _refresh_tree_visibility(self) -> None:
        tree = getattr(self.main_class, "tree_class", None)
        if tree is not None:
            try:
                tree.update_visible()
            except Exception:
                logger.exception("_refresh_tree_visibility failed")

    def _on_inf_line_added(self, line):
        session = self.main_class
        if session is None or not hasattr(session, "undo_manager"):
            return
        if session.undo_manager.is_applying:
            return
        from graphs.core.undo_commands import AddInfiniteLineCommand
        session.undo_manager.push(AddInfiniteLineCommand(self.graphView, line))

    def _on_inf_line_removed(self, line):
        session = self.main_class
        if session is None or not hasattr(session, "undo_manager"):
            return
        if session.undo_manager.is_applying:
            return
        from graphs.core.undo_commands import RemoveInfiniteLineCommand
        session.undo_manager.push(RemoveInfiniteLineCommand(self.graphView, line))

    def _on_legend_recreated(self, old_legend, new_legend):
        for curve in self.__stack_curve.values():
            curve.presenter.replace_legend(old_legend, new_legend)

    def _on_appearance_changed(self, widget, before_settings, after_settings):
        session = self.main_class
        if session is None or not hasattr(session, "undo_manager"):
            return
        if session.undo_manager.is_applying:
            return
        from graphs.core.undo_commands import GraphAppearanceCommand
        session.undo_manager.push(GraphAppearanceCommand(widget, before_settings, after_settings))

    def set_default(self):
        self.graphView.clear()
        self.graphView.second_graphView.clear()
        self.__stack_curve.clear()
        self._num_showing_points = self.DEFAULT_NUM_POINTS
        self._is_all_points_showing = self.DEFAULT_SHOW_ALL
        self._is_connect_lines = self.DEFAULT_CONNECT_LINES
        self._is_show_markers = self.DEFAULT_SHOW_MARKERS
        if self.selection_model is not None:
            self.selection_model.clear()

    def destroy_curve(self, curve_data_obj):
        curve_data_obj.delete_curve_from_graph()
        curve_data_obj.is_draw = False
        if self.selection_model is not None:
            self.selection_model.remove(curve_data_obj)
        root_name = curve_data_obj.rel_data.root_name
        self.__stack_curve.pop(root_name, None)
        self.curve_removed.emit(curve_data_obj)

    def destroy_all_curves(self):
        for curve in list(self.__stack_curve.values()):
            curve.delete_curve_from_graph()
            curve.is_draw = False
            try:
                curve.detach()
            except Exception:
                logger.exception("destroy_all_curves: detach failed")
        self.__stack_curve.clear()
        if self.selection_model is not None:
            self.selection_model.clear()

    def closeEvent(self, event):
        event.accept()

    def set_filters(self, filter_comand: FilterCommand) -> list:
        affected = []
        for curve in self.__stack_curve.values():
            if curve.is_curve_selected:
                curve.set_filter(filter_comand)
                affected.append(curve)
        return affected

    def reset_filters(self, curve=None):
        if not self.main_class.can(modify=True):
            self.main_class.show_tooltip(message=QApplication.translate("GraphWindow", "Дождитесь окончания эксперимента"))
            return
        if curve:
            targets = [curve]
        else:
            targets = [c for c in self.__stack_curve.values() if c.is_curve_selected]
        if not targets:
            return
        session = self.main_class
        cmd = None
        if session is not None and hasattr(session, "undo_manager"):
            from graphs.core.undo_commands import ResetFiltersCommand
            cmd = ResetFiltersCommand(targets)
        name_block = QApplication.translate("GraphWindow", "История изменения")
        for c in targets:
            c.clear_filters()
            if hasattr(c, "tree_item"):
                c.tree_item.delete_block(name_block)
        if cmd is not None and not session.undo_manager.is_applying:
            session.undo_manager.push(cmd)

    def click_enter_key(self):
        if not (self.axislabel_line_edit.isVisible() and self.focus_axis):
            return
        text = self.axislabel_line_edit.text()
        setter = getattr(self.focus_axis, "set_label", None)
        if callable(setter):
            setter(text, customized=bool(text))
        if not text:
            self.refresh_axis_auto_labels()
        else:
            self.focus_axis.setLabel(text)
        self.axislabel_line_edit.setVisible(False)
        self.focus_axis = None

    def click_scene_main_graph(self, event):
        if event.double():
            return
        self.__callback_click_scene(self.__stack_curve.values())
        if self.axislabel_line_edit.isVisible():
            self.axislabel_line_edit.setVisible(False)
            self.focus_axis = None
        self.hide_second_line_grid()

    def get_curves(self):
        return self.__stack_curve

    def __callback_click_scene(self, focus_objects: list):
        clicked_any = False
        for curve in focus_objects:
            if curve.i_am_click_now:
                curve.i_am_click_now = False
                clicked_any = True
        if clicked_any:
            return
        if self.selection_model is not None:
            self.selection_model.clear()
        else:
            for curve in focus_objects:
                if curve.is_curve_selected:
                    curve.is_curve_selected = False

    def delete_key_press(self):
        curv_for_del = []
        for curve in self.__stack_curve.values():
            if curve.is_curve_selected:
                if curve.is_draw:
                    curv_for_del.append(curve)
        for curve in curv_for_del:
            self.main_class.tree_class.delete_curve(curve.tree_item)

    def hide_second_line_grid(self):
        self.graphView.hide_second_line_grid()

    def update_data(self, data_first_axis: list[relationData], data_second_axis: list[relationData], is_updated=False):
        self.hide_second_line_grid()
        logger.info(f"update_data {data_first_axis} {data_second_axis} {is_updated=}")
        if not is_updated:
            first_roots = {d.root_name for d in data_first_axis}
            second_roots = {d.root_name for d in data_second_axis}
            for key, curve in self.__stack_curve.items():
                if not curve.is_draw:
                    continue
                if getattr(curve.rel_data, "is_gen", False):
                    continue
                if key not in first_roots and key not in second_roots:
                    logger.info(f"Удаление кривой {curve.curve_name} из графика")
                    curve.delete_curve_from_graph()
        self._process_axis_curves(data_first_axis, self.graphView, self.graphView.legend, 1, is_updated)
        self._process_axis_curves(data_second_axis, self.graphView.second_graphView, self.graphView.legend2, 2, is_updated)
        self._refresh_tree_visibility()

    def _process_axis_curves(self, data_list: list[relationData], graph, legend, axis_num, is_updated):
        for data in data_list:
            self._handle_curve(data, graph, legend, axis_num, is_updated)

    def _handle_curve(self, data: relationData, graph, legend, axis_num, is_updated):
        curve = self.__stack_curve.get(data.root_name)
        if curve is None:
            self.create_and_place_curve(data, graph, legend, axis_num)
        elif not curve.is_draw:
            curve.number_axis = axis_num
            curve.add_to_graph(graph, legend, axis_num)
            if self.main_class.is_live():
                curve.setData(data)
        elif is_updated:
            curve.setData(data)

    def stop_session(self):
        for curve in self.__stack_curve.values():
            curve.stop_session()

    def hide_curve(self, curve_data_obj: linearData):
        curve_data_obj.delete_curve_from_graph()

    def get_curve(self, name):
        return self.__stack_curve.get(name)

    def create_curve(self, data: relationData) -> linearData:
        new_data = linearData(data=data, alias_manager=self.alias_manager, selection_model=self.selection_model)
        new_data.set_main_class(self.main_class)
        buf_color = next(self.color_warm_gen)
        if new_data.saved_style is None:
            style = LineStyle(
                color=buf_color,
                line_style=Qt.SolidLine,
                line_width=1,
                symbol="o",
                symbol_size=3,
                symbol_color=buf_color,
                fill_color=buf_color,
            )
            ctrl = getattr(self.main_class, "analysis_controller", None)
            if ctrl is not None:
                try:
                    new_data.change_style(style)
                except Exception:
                    logger.exception("create_curve: initial style failed")
            else:
                new_data.change_style(style)
        return new_data

    def create_and_place_curve(self, data, graph_field=None, legend_field=None, number_axis=None):
        if self.__stack_curve.get(data.root_name):
            return False
        if not graph_field:
            graph_field = self.graphView
        if not legend_field:
            legend_field = self.graphView.legend
        if not number_axis:
            number_axis = 1
        new_data = self.create_curve(data=data)
        self.main_class.tree_class.add_curve(new_data.tree_item)
        self.__stack_curve[data.root_name] = new_data
        new_data.number_axis = number_axis
        new_data.add_to_graph(graph_field=graph_field, legend_field=legend_field, number_axis=number_axis)
        self._apply_window_state_to_curve(new_data)
        self._refresh_tree_visibility()
        self.curve_added.emit(new_data)
        return True

    def add_curve(self, curve_data_obj: linearData, type_axis: str = "left"):
        curve_data_obj._main_class = self.main_class
        if self.selection_model is not None:
            curve_data_obj.attach_selection_model(self.selection_model)
        logger.debug(f"add curve {curve_data_obj.curve_name} root {curve_data_obj.rel_data.root_name}")
        self.__stack_curve[curve_data_obj.rel_data.root_name] = curve_data_obj
        if type_axis == "left":
            curve_data_obj.number_axis = 1
            curve_data_obj.add_to_graph(
                graph_field=self.graphView, legend_field=self.graphView.legend, number_axis=1
            )
        else:
            curve_data_obj.number_axis = 2
            curve_data_obj.add_to_graph(
                graph_field=self.graphView.second_graphView, legend_field=self.graphView.legend2, number_axis=2
            )
        self.main_class.tree_class.add_curve(curve_data_obj.tree_item)
        self._apply_window_state_to_curve(curve_data_obj)