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
from graph.utils.colors import GColors
from graph.core.curve_data import linearData, LineStyle
from graph.core.dataManager import relationData
from graph.ui.customPlotWidget import PatchedPlotWidget
from graph.core.filters_instance_class import FilterCommand

logger = logging.getLogger(__name__)

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

    DEFAULT_NUM_POINTS   = 10
    DEFAULT_SHOW_ALL     = True

    def __init__(self, tablet_page, main_class, select_data_wid, alias_manager, selection_model=None):
        super().__init__()
        self.alias_manager = alias_manager
        self.selection_model = selection_model
        self.page = tablet_page

        self.select_win = select_data_wid
        self.main_class = main_class

        self._num_showing_points: int  = self.DEFAULT_NUM_POINTS
        self._is_all_points_showing: bool = self.DEFAULT_SHOW_ALL

        self.axislabel_line_edit = QLineEdit()
        self.axislabel_line_edit.setVisible( False )

        self.focus_axis = None

        self.legends_main = []
        self.legends_second = []

        self.__stack_curve = {}

        self.inf_lines = []

        self.colors_class = GColors()
        self.color_warm_gen = self.colors_class.get_random_warm_color()
        self.color_cold_gen = self.colors_class.get_random_cold_color()

        self.alias_manager.aliases_updated.connect(self.alias_changed)

        self.initUI()

    def alias_changed(self, original_name, old_alias, alias):
        pass

    def set_num_points(self, value: int) -> None:
        self._num_showing_points = max(1, int(value))
        for curve in self.__stack_curve.values():
            curve.set_num_points(self._num_showing_points)

    def show_all_points(self, state: bool) -> None:
        self._is_all_points_showing = bool(state)
        for curve in self.__stack_curve.values():
            curve.show_all_points(self._is_all_points_showing)

    def _apply_window_state_to_curve(self, curve) -> None:
        """Применить текущее окно к только что созданной/восстановленной кривой."""
        curve.set_num_points(self._num_showing_points)
        curve.show_all_points(self._is_all_points_showing)

    def initUI(self):
        self.tab1Layout = QVBoxLayout()
        # Add all data source selectors and graph area to tab1Layout
        
        self.graphView = PatchedPlotWidget()
        #self.graphView.setAntialiasing(False)
        self.graphView.scene().sigMouseClicked.connect(self.click_scene_main_graph)

        self.graphView.inf_line_added.connect(self._on_inf_line_added)
        self.graphView.inf_line_removed.connect(self._on_inf_line_removed)

        self.graphView.appearance_undo_callback = self._on_appearance_changed
        
        self.graphView.plotItem.getAxis("left").linkToView(
            self.graphView.plotItem.getViewBox()
        )
        self.graphView.plotItem.getAxis("bottom").linkToView(
            self.graphView.plotItem.getViewBox()
        )

        self.axislabel_line_edit.setParent(self.graphView)

        # Вертикальный сплиттер: секция выбора параметров над графиком.
        # Позволяет пользователю перетаскивать границу и сворачивать
        # панель выбора, если она не нужна в данный момент.
        self.graph_splitter = QSplitter(Qt.Vertical)
        self.graph_splitter.setChildrenCollapsible(True)
        if self.select_win is not None:
            self.graph_splitter.addWidget(self.select_win)
        self.graph_splitter.addWidget(self.graphView)
        if self.select_win is not None:
            self.graph_splitter.setStretchFactor(0, 0)   # верх не растягивается
        self.graph_splitter.setStretchFactor(1, 1)        # график растягивается
        self.graph_splitter.setSizes([220, 400])

        self.tab1Layout.addWidget(self.graph_splitter)
        self.page.setLayout(self.tab1Layout)

        self.page.subscribe_to_key_press(key = Qt.Key_Delete, callback = self.delete_key_press)
        self.page.subscribe_to_key_press(key = Qt.Key_Escape, callback = self.reset_filters)
        self.page.subscribe_to_key_press(key = Qt.Key_Enter, callback = self.click_enter_key)
        self.page.subscribe_to_key_press(key = Qt.Key_Return, callback = self.click_enter_key)

        self.retranslateUi(self.page)
    def set_second_axis(self, state: bool):
        self.graphView.set_second_axis(state)

    def _add_vertical_line_undoable(self):
        self.graphView.apply_appearance_change(self.graphView.add_vertical_line)

    def _add_horizontal_line_undoable(self):
        self.graphView.apply_appearance_change(self.graphView.add_horizontal_line)

    def get_list_curves(self):
        return list(self.__stack_curve.values())

    def _refresh_tree_visibility(self) -> None:
        """Переприменить режим видимости дерева после смены is_draw().

        Вызывается в конце операций, которые меняют состав нарисованного
        (создание/показ/скрытие/удаление кривых), — иначе в режиме
        «только активные» дерево останется несинхронизированным.
        """
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
        from graph.core.undo_commands import AddInfiniteLineCommand
        session.undo_manager.push(AddInfiniteLineCommand(self.graphView, line))

    def _on_inf_line_removed(self, line):
        session = self.main_class
        if session is None or not hasattr(session, "undo_manager"):
            return
        if session.undo_manager.is_applying:
            return
        from graph.core.undo_commands import RemoveInfiniteLineCommand
        session.undo_manager.push(RemoveInfiniteLineCommand(self.graphView, line))

    def _on_appearance_changed(self, widget, before_settings, after_settings):
        session = self.main_class
        if session is None or not hasattr(session, "undo_manager"):
            return
        if session.undo_manager.is_applying:
            return
        from graph.core.undo_commands import GraphAppearanceCommand
        session.undo_manager.push(
            GraphAppearanceCommand(widget, before_settings, after_settings)
        )

    def set_default(self):
        self.graphView.clear()
        self.graphView.second_graphView.clear()
        self.__stack_curve.clear()
        self._num_showing_points    = self.DEFAULT_NUM_POINTS
        self._is_all_points_showing = self.DEFAULT_SHOW_ALL
        if self.selection_model is not None:
            self.selection_model.clear()

    def destroy_curve(self, curve_data_obj):
        """
        Удаление кривой из графа БЕЗ detach() — чтобы её можно было
        вернуть по undo. Реальный detach делается в destroy_all_curves().
        """
        curve_data_obj.delete_curve_from_graph()
        curve_data_obj.is_draw = False
        if self.selection_model is not None:
            self.selection_model.remove(curve_data_obj)
        root_name = curve_data_obj.rel_data.root_name
        self.__stack_curve.pop(root_name, None)

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
        # Нет собственного сигнала; закрытие окна сессии обрабатывается её владельцем.
        event.accept()

    def set_filters(self, filter_comand: FilterCommand) -> list:
        """Применить фильтр ко всем выделенным кривым. Возвращает список затронутых."""
        affected = []
        for curve in self.__stack_curve.values():
            if curve.is_curve_selected:
                curve.set_filter(filter_comand)
                affected.append(curve)
        return affected

    def reset_filters(self, curve=None):
        if not self.main_class.can(modify=True):
            self.main_class.show_tooltip(
                message=QApplication.translate("GraphWindow", "Дождитесь окончания эксперимента")
            )
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
            from graph.core.undo_commands import ResetFiltersCommand
            cmd = ResetFiltersCommand(targets)

        name_block = QApplication.translate("GraphWindow", "История изменения")
        for c in targets:
            c.clear_filters()
            if hasattr(c, "tree_item"):
                c.tree_item.delete_block(name_block)

        if cmd is not None and not session.undo_manager.is_applying:
            session.undo_manager.push(cmd)

    def click_enter_key(self):

        if self.axislabel_line_edit.isVisible() and self.focus_axis:
            self.focus_axis.setLabel(self.axislabel_line_edit.text())
            self.axislabel_line_edit.setVisible(False)
            self.focus_axis = None

    def click_scene_main_graph(self, event):
        if event.double():
            is_checked_axis = False
            for item in self.graphView.scene().itemsNearEvent(event):
                if item is self.graphView.plotItem.getAxis("left"):
                    axis = self.graphView.plotItem.getAxis("left")
                    self.focus_axis = axis
                    shift_x = 50
                    shift_y = 0
                    is_checked_axis = True
                    break
                    
                elif item is self.graphView.plotItem.getAxis("bottom"):
                    axis = self.graphView.plotItem.getAxis("bottom")
                    self.focus_axis = axis
                    shift_x = 0
                    shift_y = -50
                    is_checked_axis = True
                    break

                elif item is self.graphView.plotItem.getAxis("right"):
                    if event.scenePos().x() - event.pos().x() > self.graphView.size().width()*0.9:
                        axis = self.graphView.plotItem.getAxis("right")
                        self.focus_axis = axis
                        shift_x = -100
                        shift_y = 0
                        is_checked_axis = True
                        break

            if is_checked_axis:
                text = self.focus_axis.label.toPlainText()
                self.axislabel_line_edit.setText(text)
                self.axislabel_line_edit.setGeometry(int(event.scenePos().x() + shift_x), int(event.scenePos().y() + shift_y), 100, 20)
                self.axislabel_line_edit.setFocus()
                self.axislabel_line_edit.setVisible(True)
            else:
                self.focus_axis = None
                self.axislabel_line_edit.setVisible(False)
        else:
            self.__callback_click_scene( self.__stack_curve.values() )

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

    def update_data(self, data_first_axis: list[relationData],
                data_second_axis: list[relationData], is_updated=False):
        self.hide_second_line_grid()
        logger.info(f"update_data {data_first_axis} {data_second_axis} {is_updated=}")

        if not is_updated:
            first_roots  = {d.root_name for d in data_first_axis}
            second_roots = {d.root_name for d in data_second_axis}
            for key, curve in self.__stack_curve.items():
                if not curve.is_draw:
                    continue
                # Генерируемые кривые (автокорреляция, формулы) не приходят из data_manager,
                # поэтому их нельзя снимать по «отсутствию в новом списке».
                if getattr(curve.rel_data, "is_gen", False):
                    continue
                if key not in first_roots and key not in second_roots:
                    logger.info(f"Удаление кривой {curve.curve_name} из графика")
                    curve.delete_curve_from_graph()

        self._process_axis_curves(data_first_axis, self.graphView, self.graphView.legend, 1, is_updated)
        self._process_axis_curves(data_second_axis, self.graphView.second_graphView, self.graphView.legend2, 2, is_updated)
        self._refresh_tree_visibility()

    def _process_axis_curves(self, data_list: list[relationData], graph, legend, axis_num, is_updated):
        """Обработка кривых для конкретной оси"""
        for data in data_list:
            self._handle_curve(data, graph, legend, axis_num, is_updated)

    def _handle_curve(self, data: relationData, graph, legend, axis_num, is_updated):
        """Обработка отдельной кривой."""
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

    def hide_curve(self, curve_data_obj:linearData):
        curve_data_obj.delete_curve_from_graph()
        
    def set_multiple_mode(self, is_multiple):
        self.__is_multiple = is_multiple

    def get_curve(self, name):
        return self.__stack_curve.get(name)

    def create_curve(self, data: relationData) -> linearData:
        new_data = linearData(
            data=data,
            alias_manager=self.alias_manager,
            selection_model=self.selection_model,
        )
        new_data.set_main_class(self.main_class)

        buf_color = next(self.color_warm_gen)
        if new_data.saved_style is None:
            style = LineStyle(
                color=buf_color, line_style=Qt.SolidLine, line_width=1,
                symbol="o", symbol_size=3,
                symbol_color=buf_color, fill_color=buf_color,
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

    # ------------------------------------------------------------------
    # Создание / добавление кривой
    # ------------------------------------------------------------------
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
        new_data.add_to_graph(graph_field=graph_field,
                              legend_field=legend_field,
                              number_axis=number_axis)

        self._apply_window_state_to_curve(new_data)
        self._refresh_tree_visibility()
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
                graph_field=self.graphView,
                legend_field=self.graphView.legend,
                number_axis=1,
            )
        else:
            curve_data_obj.number_axis = 2
            curve_data_obj.add_to_graph(
                graph_field=self.graphView.second_graphView,
                legend_field=self.graphView.legend2,
                number_axis=2,
            )
        self.main_class.tree_class.add_curve(curve_data_obj.tree_item)

        self._apply_window_state_to_curve(curve_data_obj)

    def retranslateUi(self, GraphWindow):
        _translate = QApplication.translate

        