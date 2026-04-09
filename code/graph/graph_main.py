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

import time

import pyqtgraph as pg
import logging
import numpy as np
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QFontMetrics, QIcon, QColor
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QSizePolicy, QVBoxLayout, QComboBox, QLineEdit, QMenu, QAction, QColorDialog, QPushButton, QWidget
from PyQt5 import QtWidgets, QtGui, QtCore
from graph.colors import GColors
from graph.curve_data import linearData, LineStyle
from graph.dataManager import relationData
from graph.customPlotWidget import PatchedPlotWidget
from graph.filters_instance_class import FilterCommand

logger = logging.getLogger(__name__)

def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        logger.debug(f"Метод  {func.__name__} выполнялся {end_time - start_time} с")
        return result
    return wrapper

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

    def __init__(self, tablet_page, main_class, select_data_wid, alias_manager):
        super().__init__()
        self.alias_manager = alias_manager
        self.page = tablet_page

        self.select_win = select_data_wid

        self.__is_multiple = False
    
        self.main_class = main_class

        self.axislabel_line_edit = QLineEdit()
        self.axislabel_line_edit.setVisible( False )

        self.focus_axis = None

        self.legends_main = []
        self.legends_second = []

        self.num_showing_points = 10
        self.is_all_points_showing = True

        self.__stack_curve = {}

        self.inf_lines = []

        self.colors_class = GColors()
        self.color_warm_gen = self.colors_class.get_random_warm_color()
        self.color_cold_gen = self.colors_class.get_random_cold_color()

        self.alias_manager.aliases_updated.connect(self.alias_changed)

        self.initUI()

    def alias_changed(self, original_name, old_alias, alias):
        pass

    def set_num_points(self, value):
        self.num_showing_points = value

    def show_all_points(self, state):
        self.is_all_points_showing = state

    def initUI(self):
        self.tab1Layout = QVBoxLayout()
        # Add all data source selectors and graph area to tab1Layout
        
        self.graphView = PatchedPlotWidget()
        #self.graphView.setAntialiasing(False)
        self.graphView.scene().sigMouseClicked.connect(self.click_scene_main_graph)

        #--------------------------------------------------------TESTS
        '''
        self.inf2 = pg.InfiniteLine(movable=True, angle=0, pen=(0, 0, 200), bounds = [-20, 20], hoverPen=(0,200,0), label='y={value:0.2f}mm', 
                       labelOpts={'color': (200,0,0), 'movable': True, 'fill': (0, 0, 200, 100)})
        
        self.targetItem2 = pg.TargetItem(
            pos=(0, 0),
            size=20,
            symbol="star",
            pen="#F4511E",
            label="vert={1:0.2f}"
        )
        self.targetItem2.label().setAngle(45)
        

        self.lr = pg.LinearRegionItem(values=[70, 80])
        label = pg.InfLineLabel(self.lr.lines[1], "region 1", position=0.95, rotateAxis=(1,0), anchor=(1, 1))

        self.x = np.arange(10)
        self.y = np.arange(10) %3
        top = np.linspace(1.0, 1, 10)


        self.err = pg.ErrorBarItem(x=self.x, y=self.y, top=top, bottom=top, beam=0.5)
        #self.graphView.addItem(self.err)
        self.graphView.plot(self.x, self.y, symbol='o', pen={'color': 0.8, 'width': 2})


        self.graphView.addItem(self.lr)
        self.graphView.addItem(self.inf2)
        #self.graphView.addItem(self.targetItem2)
        '''
        #--------------------------------------------------------------------
        
        self.graphView.plotItem.getAxis("left").linkToView(
            self.graphView.plotItem.getViewBox()
        )
        self.graphView.plotItem.getAxis("bottom").linkToView(
            self.graphView.plotItem.getViewBox()
        )

        self.axislabel_line_edit.setParent(self.graphView)

        self.buttons_layout = QHBoxLayout()
        
        self.add_vertical_line_btn = QPushButton("Добавить вертикальную линию")
        self.add_vertical_line_btn.clicked.connect(self.graphView.add_vertical_line)
        self.buttons_layout.addWidget(self.add_vertical_line_btn)
        
        self.add_horizontal_line_btn = QPushButton("Добавить горизонтальную линию")
        self.add_horizontal_line_btn.clicked.connect(self.graphView.add_horizontal_line)
        self.buttons_layout.addWidget(self.add_horizontal_line_btn)
        
        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(self.buttons_layout)
        if self.select_win is not None:
            self.tab1Layout.addWidget( self.select_win )
        self.tab1Layout.addWidget(self.graphView)
        self.tab1Layout.addWidget(self.buttons_widget)
        self.page.setLayout(self.tab1Layout)

        self.page.subscribe_to_key_press(key = Qt.Key_Delete, callback = self.delete_key_press)
        self.page.subscribe_to_key_press(key = Qt.Key_Escape, callback = self.reset_filters)
        self.page.subscribe_to_key_press(key = Qt.Key_Enter, callback = self.click_enter_key)
        self.page.subscribe_to_key_press(key = Qt.Key_Return, callback = self.click_enter_key)

        self.retranslateUi(self.page)
    def set_second_axis(self, state: bool):
        self.graphView.set_second_axis(state)

    def set_default(self):
        self.x = []
        self.old_params = []
        self.y.clear()
        self.y2.clear()
        for item in self.graphView.items():
            if isinstance(item, pg.PlotDataItem):
                self.graphView.removeItem(item)
        self.graphView.second_graphView.clear()

    def get_list_curves(self):
        return list(self.__stack_curve.values())

    def set_filters(self, filter_comand: FilterCommand):
        for curve in self.__stack_curve.values():
            if curve.is_curve_selected:
                curve.set_filter(filter_comand)

    def reset_filters(self, curve = None):
        if self.main_class.data_manager.is_session_running():
            self.main_class.show_tooltip(message = QApplication.translate( "GraphWindow", "Дождитесь окончания эксперимента" ) )
            return
        
        if curve:
            if not curve.data_reset():
                self.main_class.show_tooltip(message = QApplication.translate( "GraphWindow", "Все фильтры уже сброшены, сбрасывать больше нечего." ) )
            for curves in curve.plot_items.values():
                curves['item'].setData(curve.filtered_x_data, curve.filtered_y_data)
            curve.recalc_stats_param()
            if hasattr(curve, "tree_item"):
                name_block = QApplication.translate("GraphWindow","История изменения")
                curve.tree_item.delete_block(name_block)
        else:
            for curve in self.__stack_curve.values():
                if curve.is_curve_selected:
                    curve.data_reset()
                    for curves in curve.plot_items.values():
                        curves['item'].setData(curve.filtered_x_data, curve.filtered_y_data)
                    curve.recalc_stats_param()
                    if hasattr(curve, "tree_item"):
                        name_block = QApplication.translate("GraphWindow","История изменения")
                        curve.tree_item.delete_block(name_block)

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
        is_click_plot = True
        for curve in focus_objects:
            if curve.i_am_click_now:
                curve.i_am_click_now = False
                is_click_plot = False

        if is_click_plot:
            for curve in focus_objects:
                if curve.is_curve_selected:
                        curve.change_style(curve.saved_style)
                        curve.is_curve_selected = False

    def delete_key_press(self):
        curv_for_del = []
        for curve in self.__stack_curve.values():
            if curve.is_curve_selected:
                if curve.is_draw:
                    curv_for_del.append(curve)

        for curve in curv_for_del:
            self.main_class.tree_class.delete_curve(curve.tree_item)

    def handle_skip_draw(self, selector, second_selector,  graph_field, string_x, string_y, is_multiple):
        if is_multiple:
            current_items = list(item.text() for item in selector.selectedItems())
            if string_y not in current_items and string_y != "Select parameter":
                curve_key = string_y + string_x
                if self.__stack_curve.get(curve_key) is not None:
                    self.__stack_curve[curve_key].delete_curve_from_graph()
                    second_selector.addItem(self.__stack_curve[curve_key].y_name)
                    return True
        else:
            #отменить отрисовку всех кривых в блоке
            for data_curve in self.__stack_curve.values():
                if data_curve.is_draw:
                    data_curve.delete_curve_from_graph()
                    second_selector.addItem(data_curve.y_name)
        return False
    
    def hide_second_line_grid(self):
        self.graphView.hide_second_line_grid()

    #@time_decorator
    def update_data(self, data_first_axis:list[relationData], data_second_axis:list[relationData], is_updated = False):
        self.hide_second_line_grid()

        if not is_updated:
            for key, curve in self.__stack_curve.items():    
                if curve.is_draw:
                    if key not in [data.root_name for data in data_first_axis] and key not in [data.root_name for data in data_second_axis]:
                            curve.delete_curve_from_graph()

        self._process_axis_curves(data_first_axis, self.graphView, self.graphView.legend, 1, is_updated)
        self._process_axis_curves(data_second_axis, self.graphView.second_graphView, self.graphView.legend2, 2, is_updated)

    def _process_axis_curves(self, data_list: list[relationData], graph, legend, axis_num, is_updated):
        """Обработка кривых для конкретной оси"""
        for data in data_list:
            self._handle_curve(data, graph, legend, axis_num, is_updated)

    def _handle_curve(self, data : relationData, graph, legend, axis_num, is_updated):
        """Обработка отдельной кривой"""
        curve = self.__stack_curve.get(data.root_name)
        
        if curve is None:
            self.create_and_place_curve(data, graph, legend, axis_num)
        elif not curve.is_draw:
            curve.number_axis = axis_num
            curve.add_to_graph(graph, legend, axis_num)
        elif is_updated:
            self._refresh_curve_data(curve, data)

    def _refresh_curve_data(self, curve, data):
        """Обновление данных существующей кривой"""
        x_data, y_data = self._get_visible_data(data)
        for curves in curve.plot_items.values():
                curves['item'].setData(x_data, y_data)
        curve.setData(data)

    def _get_visible_data(self, data):
        """Получение данных для отображения с учетом настроек видимости"""
        if self.is_all_points_showing:
            return data.x_result, data.y_result
        return (
            data.x_result[-self.num_showing_points:],
            data.y_result[-self.num_showing_points:]
        )

    def destroy_curve(self, curve_data_obj):
        curve_data_obj.delete_curve_from_graph()
        curve_data_obj.is_draw = False
        key = curve_data_obj.curve_name
        if self.__stack_curve.get(key) is not None:
            self.__stack_curve.pop(key)

    def destroy_all_curves(self):
        for curve in self.__stack_curve.values():
            curve.delete_curve_from_graph()
            curve.is_draw = False

        self.__stack_curve.clear()

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
        new_data = linearData(data=data, alias_manager=self.alias_manager)
        buf_color = next(self.color_warm_gen)

        if new_data.saved_style is None:
            style = LineStyle(color=buf_color, line_style=Qt.SolidLine, line_width=1,
                            symbol="o", symbol_size=3, symbol_color=buf_color, fill_color=buf_color)
            new_data.saved_style = style
        else:
            pass
        return new_data

    def create_and_place_curve(self, data: relationData,
                                    graph_field = None,
                                    legend_field = None,
                                    number_axis = None):
        if self.__stack_curve.get(data.root_name):
            return False
        
        if not graph_field:
            graph_field = self.graphView
        if not legend_field:
            legend_field = self.graphView.legend
        if not number_axis:
            number_axis=1
        new_data = self.create_curve(data = data) 
        self.main_class.tree_class.add_curve(new_data.tree_item)
        self.__stack_curve[data.root_name] = new_data
            
        self.__stack_curve[data.root_name].number_axis = number_axis
        self.__stack_curve[data.root_name].add_to_graph(graph_field  = graph_field,
                                                             legend_field  = legend_field,
                                                             number_axis = number_axis
                                                            )
        
        return True
        
    def add_curve(self, curve_data_obj: linearData, type_axis: str = "left"):
        logger.debug(f"add curve {curve_data_obj.curve_name} root name {curve_data_obj.rel_data.root_name}")
        self.__stack_curve[curve_data_obj.rel_data.root_name] = curve_data_obj
        if type_axis == "left":
            curve_data_obj.number_axis = 1#костыль на время, пока нет сохранения для всех графиков. данный график главный и именно он назвачает главную ось, она используется в селекторе параметров
            curve_data_obj.add_to_graph(graph_field  = self.graphView,
                                                legend_field  = self.graphView.legend,
                                                number_axis = 1
                                                )
        else:
            curve_data_obj.number_axis = 2
            curve_data_obj.add_to_graph(graph_field  = self.graphView.second_graphView,
                                                legend_field  = self.graphView.legend2,
                                                number_axis = 2
                                                )
        self.main_class.tree_class.add_curve(curve_data_obj.tree_item)

    def closeEvent(self, event):  # эта функция вызывается при закрытии окна
        self.graph_win_close_signal.emit(1)

    def retranslateUi(self, GraphWindow):
        _translate = QApplication.translate

        