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
from datetime import datetime

import pyqtgraph as pg
import logging
from PyQt5.QtCore import QObject, Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import (QApplication, QHBoxLayout,
                             QSizePolicy, QSpacerItem, QVBoxLayout, QComboBox, QLineEdit)

try:
    from colors import GColors
    from curve_data import linearData
    from dataManager import relationData
except:
    from graph.colors import GColors
    from graph.curve_data import linearData
    from graph.dataManager import relationData

logger = logging.getLogger(__name__)

def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        logger.info(f"Метод  {func.__name__} выполнялся {end_time - start_time} с")
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
            
class graphMain(QObject):
    new_curve_selected = pyqtSignal()

    def __init__(self, tablet_page, main_class, select_data_wid):
        super().__init__()
        self.page = tablet_page
        #++++++++++++++++++++++++++++++++++++++++
        #self.import_data_widget = import_data_widget
        self.select_win = select_data_wid

        #++++++++++++++++++++++++++++++++++++++++++
        self.is_show_warning = True

        self.is_second_axis = False
        self.is_multiple = False
    
        self.main_class = main_class

        self.legend = pg.LegendItem(size=(80, 60), offset=(10, 10))
        self.legend2 = pg.LegendItem(size=(80, 60), offset=(50, 10))

        self.tooltip = pg.TextItem("X:0,Y:0", color=(255, 255, 255), anchor=(0, 0))

        self.axislabel_line_edit = QLineEdit()
        self.axislabel_line_edit.setVisible( False )

        self.focus_axis = None

        self.legends_main = []
        self.legends_second = []

        self.y_main_axis_label = ""
        self.x_axis_label = ""
        self.y_second_axis_label = ""


        self.num_showing_points = 10
        self.is_all_points_showing = True

        self.stack_curve = {}

        self.colors_class = GColors()
        self.color_warm_gen = self.colors_class.get_random_warm_color()
        self.color_cold_gen = self.colors_class.get_random_cold_color()

        self.initUI()

    def set_num_points(self, value):
        self.num_showing_points = value

    def show_all_points(self, state):
        self.is_all_points_showing = state

    def initUI(self):
        self.tab1Layout = QVBoxLayout()
        # Add all data source selectors and graph area to tab1Layout
        
        self.graphView = self.setupGraphView()
        self.graphView.setAntialiasing(False)
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
            label="vert={1:0.2f}",
            labelOpts={
                "offset": QPoint(15, 15)
            }
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
        
        self.selector = QSpacerItem(15, 15, QSizePolicy.Expanding, QSizePolicy.Minimum)

        data_name_layout = QHBoxLayout()
        data_name_layout.addItem(self.selector)
        # Add the layouts to the first tab
        self.tab1Layout.addLayout(data_name_layout)
        self.tab1Layout.addWidget( self.select_win )
        self.tab1Layout.addWidget(self.graphView)
        #self.tab1Layout.addWidget(self.import_data_widget)
        self.page.setLayout(self.tab1Layout)

        self.set_second_axis(state = False)
        

        self.page.subscribe_to_key_press(key = Qt.Key_Delete, callback = self.delete_key_press)
        self.page.subscribe_to_key_press(key = Qt.Key_Escape, callback = self.reset_filters)
        self.page.subscribe_to_key_press(key = Qt.Key_Enter, callback = self.click_enter_key)
        self.page.subscribe_to_key_press(key = Qt.Key_Return, callback = self.click_enter_key)

        self.retranslateUi(self.page)
    def set_second_axis(self, state: bool):
        self.is_second_axis = state

        if not state:
            self.plots_lay.getAxis("right").hide()
            for curve in self.stack_curve.values():
                if curve.parent_graph_field is self.second_graphView and curve.is_draw:
                    curve.delete_curve_from_graph()
        else:
            self.plots_lay.getAxis("right").show()

    def setupGraphView(self):
        graphView = pg.PlotWidget(title="")

        self.color_line_main = "#55aa00"
        self.color_line_second = "#ff0000"

        graphView.scene().sigMouseMoved.connect(self.showToolTip)
        graphView.plotItem.getAxis("left").linkToView(graphView.plotItem.getViewBox())
        graphView.plotItem.getAxis("bottom").linkToView(graphView.plotItem.getViewBox())

        self.plots_lay = graphView.plotItem
        
        self.second_graphView = pg.ViewBox(parent=None,
                border=None,
                lockAspect=False,
                enableMouse=False,
                invertY=False,
                enableMenu=False,
                name=None,
                invertX=False,
                defaultPadding=0.02
                )
        
        self.plots_lay.showAxis("right")
        self.plots_lay.scene().addItem(self.second_graphView)
        self.plots_lay.getAxis("right").linkToView(self.second_graphView)
        self.second_graphView.setXLink(self.plots_lay)
        self.plots_lay.getAxis("right").setLabel("axis2", color="#000fff")

        self.plots_lay.vb.sigResized.connect(self.updateViews)
        
        self.legend.setParentItem(self.plots_lay)
        self.legend2.setParentItem(self.second_graphView)
        self.tooltip.setParentItem(self.plots_lay)

        my_font = QFont("Times", 13)
        self.plots_lay.getAxis("right").label.setFont(my_font)
        graphView.getAxis("bottom").label.setFont(my_font)
        graphView.getAxis("left").label.setFont(my_font)

        return graphView

    def showToolTip(self, event):
        pos = event 
        x_val = round(
            self.graphView.plotItem.vb.mapSceneToView(pos).x(), 1
        ) 
        y_val = round(
            self.graphView.plotItem.vb.mapSceneToView(pos).y(), 1
        ) 
        text = f'X:{x_val} Y:{y_val}'
        self.tooltip.setPlainText(text)

    def set_default(self):
        self.x = []
        self.old_params = []
        self.y.clear()
        self.y2.clear()
        for item in self.graphView.items():
            if isinstance(item, pg.PlotDataItem):
                self.graphView.removeItem(item)
        self.second_graphView.clear()

    def updateViews(self):
        self.second_graphView.setGeometry(self.plots_lay.vb.sceneBoundingRect())
        self.second_graphView.linkedViewChanged(self.plots_lay.vb, self.second_graphView.XAxis)

    def set_filters(self, filter_func):
        for curve in self.stack_curve.values():
            if curve.current_highlight:
                curve.filtered_y_data, message = filter_func(curve.filtered_y_data)
                curve.filtered_x_data = curve.filtered_x_data[-len(curve.filtered_y_data):]
                curve.plot_obj.setData(curve.filtered_x_data, curve.filtered_y_data)

                curve.recalc_stats_param()

                name_block = QApplication.translate("GraphWindow","История изменения")

                status = curve.tree_item.update_block_data( 
                        block_name   = name_block,
                        data         = {str(datetime.now().strftime("%H:%M:%S")): message,},
                        is_add_force = True
                                                    )

                if not status:
                    curve.tree_item.add_new_block(
                    block_name   = name_block,
                    data         = {str(datetime.now().strftime("%H:%M:%S")): message,},
                                                 )

    def reset_filters(self, curve = None):
        if self.main_class.data_manager.is_session_running():
            self.main_class.show_tooltip(message = QApplication.translate( "GraphWindow", "Дождитесь окончания эксперимента" ) )
            return
        
        if curve:
            if not curve.data_reset():
                self.main_class.show_tooltip(message = QApplication.translate( "GraphWindow", "Все фильтры уже сброшены, сбрасывать больше нечего." ) )
            curve.plot_obj.setData(curve.filtered_x_data, curve.filtered_y_data)
            curve.recalc_stats_param()
            if hasattr(curve, "tree_item"):
                name_block = QApplication.translate("GraphWindow","История изменения")
                curve.tree_item.delete_block(name_block)
        else:
            for curve in self.stack_curve.values():
                if curve.current_highlight:
                    curve.data_reset()
                    curve.plot_obj.setData(curve.filtered_x_data, curve.filtered_y_data)
                    curve.recalc_stats_param()
                    if hasattr(curve, "tree_item"):
                        name_block = QApplication.translate("GraphWindow","История изменения")
                        curve.tree_item.delete_block(name_block)

    def click_enter_key(self):

        if self.axislabel_line_edit.isVisible() and self.focus_axis:
            self.focus_axis.setLabel(self.axislabel_line_edit.text(), color=self.focus_axis.pen().color())
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
            self.__callback_click_scene( self.stack_curve.values() )

            if self.axislabel_line_edit.isVisible():
                self.axislabel_line_edit.setVisible(False)
                self.focus_axis = None

        self.hide_second_line_grid()

    def __callback_click_scene(self, focus_objects: list):
        is_click_plot = True
        for graph in focus_objects:
            if graph.i_am_click_now:
                graph.i_am_click_now = False
                is_click_plot = False

        if is_click_plot:
            for graph in focus_objects:
                if graph.current_highlight:
                        graph.current_highlight = False
                        graph.plot_obj.setPen(graph.saved_pen)
                        graph.plot_obj.setSymbolBrush(color = graph.saved_pen['color'])

    def delete_key_press(self):
        curv_for_del = []
        for curve in self.stack_curve.values():
            if curve.current_highlight:
                if curve.is_draw:
                    curv_for_del.append(curve)

        for curve in curv_for_del:
            self.main_class.tree_class.delete_curve(curve.tree_item)

    def handle_skip_draw(self, selector, second_selector,  graph_field, string_x, string_y, is_multiple):
        if is_multiple:
            current_items = list(item.text() for item in selector.selectedItems())
            if string_y not in current_items and string_y != "Select parameter":
                curve_key = string_y + string_x
                if self.stack_curve.get(curve_key) is not None:
                    self.stack_curve[curve_key].delete_curve_from_graph()
                    second_selector.addItem(self.stack_curve[curve_key].y_name)
                    return True
        else:
            #отменить отрисовку всех кривых в блоке
            for data_curve in self.stack_curve.values():
                if data_curve.is_draw and data_curve.parent_graph_field is graph_field:
                    data_curve.delete_curve_from_graph()
                    second_selector.addItem(data_curve.y_name)
        return False
    
    def hide_second_line_grid(self):
        self.plots_lay.getAxis("right").setGrid(0)#костыль, который необходим для того, чтобы сетка по вспомогательной оси не отображалась. При вызове меню сетки отрисоываются на всех осях

    #@time_decorator
    def update_data(self, data_first_axis, data_second_axis, is_updated = False):

        self.hide_second_line_grid()

        if not is_updated:
            for key, curve in self.stack_curve.items():    
                if curve.is_draw:
                    if key not in [data.name for data in data_first_axis] and key not in [data.name for data in data_second_axis]:
                            curve.delete_curve_from_graph()

        for data in data_first_axis:
            if self.stack_curve.get(data.name) is None:
                self.create_and_place_curve(
                                            data = data,
                                            graph_field = self.graphView,
                                            legend_field = self.legend,
                                            number_axis=1
                                            )
            else:
                if not self.stack_curve[data.name].is_draw:
                    self.stack_curve[data.name].place_curve_on_graph(graph_field  = self.graphView,
                                                                    legend_field  = self.legend,
                                                                    number_axis=1
                                                                    )
                else:
                    if is_updated:
                        if self.is_all_points_showing:
                            x = data.x_result
                            y = data.y_result
                        else:
                            x = data.x_result[-1*self.num_showing_points:]
                            y = data.y_result[-1*self.num_showing_points:]
                        self.stack_curve[data.name].plot_obj.setData(x, y)
                        self.stack_curve[data.name].setData(data)
                
        for data in data_second_axis:
            if self.stack_curve.get(data.name) is None:
                self.create_and_place_curve(
                                            data = data,
                                            graph_field = self.second_graphView,
                                            legend_field = self.legend2,
                                            number_axis=2
                                            )
            else:
                if not self.stack_curve[data.name].is_draw:
                    self.stack_curve[data.name].place_curve_on_graph(graph_field  = self.second_graphView,
                                                                    legend_field  = self.legend2,
                                                                    number_axis=2)
                else:
                    if is_updated:
                        if self.is_all_points_showing:
                            x = data.x_result
                            y = data.y_result
                        else:
                            x = data.x_result[-1*self.num_showing_points:]
                            y = data.y_result[-1*self.num_showing_points:]
                        self.stack_curve[data.name].plot_obj.setData(x, y)
                        self.stack_curve[data.name].rel_data = data

    def destroy_curve(self, curve_data_obj):
        curve_data_obj.delete_curve_from_graph()
        curve_data_obj.is_draw = False
        key = curve_data_obj.curve_name
        if self.stack_curve.get(key) is not None:
            self.stack_curve.pop(key)

    def stop_session(self):
        i = 0
        for curve in self.stack_curve.values():
            curve.stop_session()
            i+=1

    def hide_curve(self, curve_data_obj:linearData):
        curve_data_obj.delete_curve_from_graph()
        
    def set_multiple_mode(self, is_multiple):
        self.is_multiple = is_multiple

    def get_curve(self, name):
        return self.stack_curve.get(name)

    def create_curve(self, data: relationData) -> linearData:
            new_data = linearData(data=data)
            buf_color = next(self.color_warm_gen)

            if new_data.saved_pen == None:
                buf_pen = {
                            "color": buf_color,
                            "width": 1,
                            "antialias": True,  
                            "symbol": "o",
                }
            else:
                buf_pen = new_data.saved_pen

            graph = pg.PlotDataItem(new_data.filtered_x_data, 
                                            new_data.filtered_y_data, 
                                            pen  = buf_pen,
                                            name = new_data.legend,
                                            symbolPen=buf_pen,
                                            symbolBrush=buf_color,
                                            symbol='o',
                                            )
            graph.setClipToView(True)
            graph.setDownsampling(auto=True, method='peak')

            new_data.set_plot_obj(plot_obj = graph,
                                  pen      = buf_pen)
            
            return new_data
    @time_decorator
    def create_and_place_curve(self, data,
                                    graph_field = None,
                                    legend_field = None,
                                    number_axis = None):
        if self.stack_curve.get(data.name):
            return False
        
        if not graph_field:
            graph_field = self.graphView
        if not legend_field:
            legend_field = self.legend
        if not number_axis:
            number_axis=1
        new_data = self.create_curve(data = data)
        self.main_class.tree_class.add_curve(new_data.tree_item)
        self.stack_curve[data.name] = new_data
            
        self.stack_curve[data.name].place_curve_on_graph(graph_field  = graph_field,
                                                             legend_field  = legend_field,
                                                             number_axis = number_axis
                                                            )
        return True
        
    def add_curve_to_stack(self, curve_data_obj):   
        self.stack_curve[curve_data_obj.y_name + curve_data_obj.x_name] = curve_data_obj

    def closeEvent(self, event):  # эта функция вызывается при закрытии окна
        self.graph_win_close_signal.emit(1)

    def retranslateUi(self, GraphWindow):
        _translate = QApplication.translate

        