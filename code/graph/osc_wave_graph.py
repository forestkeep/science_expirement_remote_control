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
import time

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QSizePolicy,
                             QSplitter, QVBoxLayout, QWidget)

from graph.colors import GColors
from graph.curve_data import hystLoop, oscData
from graph.dataManager import measTimeData
from graph.dataManager import relationData
from graph.toolBarWidget import tool_bar_widget
from graph.custom_inf_line import RemovableInfiniteLine
from graph.customPlotWidget import PatchedPlotWidget

logger = logging.getLogger(__name__)

def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        return result
    return wrapper

class graphOsc:
    def __init__(self, tablet_page, selector_wave, main_class, alias_manager):
        self.alias_manager = alias_manager
        self.page = tablet_page
        self.legend = pg.LegendItem(size=(80, 60), offset=(10, 10))
        self.is_show_warning = True
        self.key_to_update_plot = True
        self.x = []
        self.y = []
        self.selector_wave = selector_wave
        self.dict_param = {}

        self.stack_osc = {}

        self.inf_line_vert = None
        self.inf_line_hor = None

        self.line_counter = 0

        self.main_class = main_class

        self.used_colors = set()
        self.colors_class = GColors()
        self.color_gen = self.colors_class.get_random_color()

        self.y_main_axis_label = ""
        self.x_axis_label = ""

        self.y_second_axis_label = "V"
        self.x_axis_label = "dots"
        self.y_main_axis_label = "V"

        self.key = True  # ключ предназначен для манипулирования данными в виджетах без вызова функций обработчиков, если ключ установлен в False, то обработчик не будет испольняться

        self.vertical_lines = verticals_lines()
        self.ver_curve_left = None
        self.ver_curve_right = None
        self.tooltip = QLabel("X:0,Y:0")
        self.build_hyst_loop_check = QCheckBox()
        self.build_hyst_loop_check.stateChanged.connect(
            lambda: self.hyst_loop_activate()
        )

        self.loops_stack = [] #здесь хранятся петли, которые были рассчитаны и установлены на график

        self.label = QLabel() 
        self.label2 = QLabel() 

        self.list_vert_curve = []
        self.initUI()

    def initUI(self):

        self.tab1Layout = QVBoxLayout()

        self.graphView = self.setupGraphView()

        self.graphView.scene().sigMouseMoved.connect(self.showToolTip_main)
        self.graphView.scene().sigMouseClicked.connect(self.click_scene_main_graph)
        self.graphView.scene().setClickRadius(20)
        self.legend.setParentItem(self.graphView.plotItem)

        self.graphView.setLabel("left", self.y_main_axis_label, color="#ffffff")
        self.graphView.setLabel("bottom", self.x_axis_label, color="#ffffff")
        self.graphView.getAxis("left").setGrid(True)
        self.graphView.getAxis("bottom").setGrid(True)

        splitter_graph_fields = QSplitter()
        splitter_graph_fields.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        splitter_graph_fields.setOrientation(1)

        self.graphView_loop = self.setupGraphView()

        self.graphView_loop.scene().sigMouseMoved.connect(self.showToolTip_loop)
        self.graphView_loop.scene().sigMouseClicked.connect(self.click_scene_loop_graph)

        splitter_graph_fields.addWidget(self.graphView)
        splitter_graph_fields.addWidget(self.graphView_loop)

        splitter_graph_fields.setStretchFactor(0, 5)
        splitter_graph_fields.setStretchFactor(1, 5)  
        self.graphView_loop.hide()

        tool_bar_graph = tool_bar_widget()

        graph_bar_lay = QVBoxLayout()
        graph_bar_lay.addWidget(tool_bar_graph)
        graph_bar_lay.addWidget(splitter_graph_fields)

        tool_bar_wid = QWidget()
        tool_bar_wid.setLayout(graph_bar_lay)

        splitter_graph_selector = QSplitter()
        splitter_graph_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter_graph_selector.setOrientation(0)
        splitter_graph_selector.setStretchFactor(0, 5)
        splitter_graph_selector.setStretchFactor(1, 5)

        self.hyst_loop_layer = self.create_hyst_calc_layer()
        self.hyst_loop_layer.hide()

        splitter_graph_selector.addWidget( self.selector_wave )
        splitter_graph_selector.addWidget( tool_bar_wid )
        splitter_graph_selector.addWidget( self.hyst_loop_layer )

        self.tab1Layout.addWidget(splitter_graph_selector)
        self.tab1Layout.addWidget(self.build_hyst_loop_check)

        self.page.setLayout(self.tab1Layout)

        self.page.subscribe_to_key_press(key = Qt.Key_Delete, callback = self.delete_key_press)

        self.page.subscribe_to_key_press(key = Qt.Key_Escape, callback = self.reset_filters)

        tool_bar_graph.add_tool_button(tooltip = "Вертикальный курсор",is_change_style = False, icon_path = None, callback = self.click_vert_infinite_line)
        tool_bar_graph.add_tool_button(tooltip = "Горизонтальный курсор",is_change_style = False, icon_path = None, callback = self.click_hor_infinite_line)

        self.retranslateUI(self.page)

    def click_vert_infinite_line(self, state):
        self.add_inf_line(0)

    def click_hor_infinite_line(self, state):
        self.add_inf_line(90)

    def add_inf_line(self, angle):
        view_range = self.graphView.viewRange()
        x_center = int((view_range[0][0] + view_range[0][1]) / 2.0)
        y_center = int((view_range[1][0] + view_range[1][1]) / 2.0)
        center_point = QPoint(x_center, y_center)

        self.line_counter += 1
        line_number = self.line_counter

        if angle == 90:
            pos = x_center
        elif angle == 0:
            pos = y_center
        else:
            pos = center_point

        inf_line = RemovableInfiniteLine(
            movable=True,
            angle=angle,
            pen=(0, 0, 200),
            hoverPen=(0, 200, 0),
            label=f'#{line_number}: {{value:0.9f}}',
            labelOpts={
                'color': (200, 0, 0), 
                'movable': True, 
                'fill': (0, 0, 200, 100)
            },
            pos=pos
        )

        self.graphView.addItem(inf_line)
        inf_line.removeRequested.connect(lambda line: self.graphView.removeItem(line))

    def click_scene_main_graph(self, event):
        self.__callback_click_scene(self.stack_osc.values())

    def click_scene_loop_graph(self, event):
        self.__callback_click_scene(self.loops_stack)

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

    def reset_filters(self):
        for loop in self.loops_stack:
            if loop.current_highlight:
                loop.filtered_x_data = loop.raw_data_x
                loop.filtered_y_data = loop.raw_data_y
                x, y = loop.recalc_data()
                loop.plot_obj.setData(x, y)

        for osc in self.stack_osc.values():
            if osc.current_highlight:
                osc.filtered_x_data = osc.raw_data_x
                osc.filtered_y_data = osc.raw_data_y

                osc.plot_obj.setData(osc.filtered_x_data, osc.filtered_y_data)

    def delete_key_press(self):
        self.clear_highlight_loop()

    def setupGraphView(self):
        graphView = PatchedPlotWidget(title="")

        graphView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        graphView.plotItem.getAxis("left").linkToView(graphView.plotItem.getViewBox())
        graphView.plotItem.getAxis("bottom").linkToView(graphView.plotItem.getViewBox())

        my_font = QFont("Times", 13)
        graphView.getAxis("bottom").label.setFont(my_font)
        graphView.getAxis("left").label.setFont(my_font)

        graphView.setMinimumSize(300, 200)

        return graphView

    def create_hyst_calc_layer(self):

        self.button_hyst_loop = QPushButton()
        self.button_hyst_loop.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.button_hyst_loop.setMaximumSize(
            130, 100
        ) 

        self.button_hyst_loop_clear = QPushButton()
        self.button_hyst_loop_clear.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.button_hyst_loop_clear.setMaximumSize(
            130, 100
        )  

        self.name_field = QLabel(QApplication.translate("GraphWindow","Поле"))
        self.field_ch_choice = QComboBox()

        self.name_sig = QLabel(QApplication.translate("GraphWindow","Сигнал"))
        
        self.sig_ch_choice = QComboBox()

        self.sig_ch_choice.setMaximumSize(250, 40)
        self.field_ch_choice.setMaximumSize(250, 40)

        self.sig_ch_choice.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.field_ch_choice.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.auto_button = QPushButton(QApplication.translate("GraphWindow","Авто"))
        self.auto_button.setMaximumSize(130, 100)

        self.avg_loop_button = QPushButton(QApplication.translate("GraphWindow","Усреднить петли"))
        self.avg_loop_button.setMaximumSize(130, 100)
        
        self.left_coord = wheelLineEdit()
        self.left_coord.line_edit.setPlaceholderText(QApplication.translate("GraphWindow","Координата слева"))
        self.left_coord.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.left_coord.setMaximumSize(250, 40)

        self.right_coord = wheelLineEdit()
        self.right_coord.line_edit.setPlaceholderText(QApplication.translate("GraphWindow","Координата справа"))
        self.right_coord.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.right_coord.setMaximumSize(250, 40)

        self.right_coord.set_second_line_widget(line=self.left_coord.line_edit)
        self.left_coord.set_second_line_widget(line=self.right_coord.line_edit)

        self.square = QLineEdit()
        self.square.setPlaceholderText(QApplication.translate("GraphWindow","Площадь провода(мкм)"))

        self.square.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.square.setMaximumSize(250, 40)

        self.resistance = QLineEdit()
        self.resistance.setPlaceholderText(QApplication.translate("GraphWindow","Сопротивление провода(Ом)"))
        self.resistance.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.resistance.setMaximumSize(250, 40)

        self.square.textChanged.connect(lambda: self.is_all_hyst_correct())
        self.resistance.textChanged.connect(lambda: self.is_all_hyst_correct())
        self.right_coord.line_edit.textChanged.connect(
            lambda: self.is_all_hyst_correct()
        )
        self.right_coord.line_edit.textChanged.connect(lambda: self.draw_vert_line())
        self.left_coord.line_edit.textChanged.connect(
            lambda: self.is_all_hyst_correct()
        )
        self.left_coord.line_edit.textChanged.connect(lambda: self.draw_vert_line())
        self.field_ch_choice.currentTextChanged.connect(
            lambda: self.is_all_hyst_correct()
        )
        self.sig_ch_choice.currentTextChanged.connect(
            lambda: self.is_all_hyst_correct()
        )
        self.field_ch_choice.currentTextChanged.connect(
            lambda: self.update_status_vert_line()
        )
        self.button_hyst_loop.clicked.connect(lambda: self.draw_loop())
        self.button_hyst_loop_clear.clicked.connect( lambda: self.clear_all_loops() )
        self.auto_button.clicked.connect(lambda: self.push_auto_button())

        self.avg_loop_button.clicked.connect(lambda: self.avg_loop())

        self.hyst_loop_layer = QFrame()
        main_lay = QHBoxLayout(self.hyst_loop_layer)

        buttons_lay = QVBoxLayout()

        buttons1_lay = QHBoxLayout()
        buttons1_lay.addWidget(self.button_hyst_loop, alignment=Qt.AlignLeft)
        buttons1_lay.addWidget(self.avg_loop_button, alignment=Qt.AlignLeft)
        buttons_lay.addLayout(buttons1_lay)

        buttons2_lay = QHBoxLayout()
        buttons2_lay.addWidget(self.auto_button, alignment=Qt.AlignLeft)

        buttons_lay.addLayout(buttons2_lay)

        buttons3_lay = QHBoxLayout()
        buttons3_lay.addWidget(self.button_hyst_loop_clear, alignment=Qt.AlignLeft)
        buttons_lay.addLayout(buttons3_lay)

        enter_lay = QVBoxLayout()

        field_signal_lay = QHBoxLayout()
        
        lay_field = QVBoxLayout()

        lay_field.addWidget(self.name_field)
        lay_field.addWidget(self.field_ch_choice)
        field_signal_lay.addLayout(lay_field)

        lay_sig = QVBoxLayout()
        lay_sig.addWidget(self.name_sig)
        lay_sig.addWidget(self.sig_ch_choice)
        field_signal_lay.addLayout(lay_sig)

        enter_lay.addLayout(field_signal_lay)

        coords_line_lay = QHBoxLayout()
        coords_line_lay.addWidget(self.left_coord)
        coords_line_lay.addWidget(self.right_coord)
        enter_lay.addLayout(coords_line_lay)

        field_signal_lay2 = QHBoxLayout()
        field_signal_lay2.addWidget(self.square)

        field_signal_lay2.addWidget(self.resistance)
        enter_lay.addLayout(field_signal_lay2)

        main_lay.addLayout(enter_lay)
        main_lay.addLayout(buttons_lay)

        return self.hyst_loop_layer
    
    def avg_loop(self):
        buf = []

        for loop in self.loops_stack:
            buf.append(loop)

        if len(self.loops_stack) > 1:

            new_loop = self.calc_avg_loop(loops_stack=buf)

            if new_loop is not False:
                #self.clear_all_loops()
                x, y = new_loop.get_xy_data()

                new_pen = {
                        "color": next(self.color_gen),
                        "width": 1,
                        "antialias": True,
                        "symbol": "o",
                        }

                self.loops_stack.append(new_loop)
                plot_obj = self.graphView_loop.plot(
                        x,
                        y,
                        pen=new_pen,

                        )
                new_loop.set_plot_obj(plot_obj, new_pen, highlight=True)

    def calc_avg_loop(self, loops_stack):
        '''вернет объект петли, полученный усреднением стека петель'''
        if len(loops_stack) == 0:
            return False
        elif len(loops_stack) == 1:
            return loops_stack[0]
        
        new_loop = loops_stack[0]
        for i in range(1, len(loops_stack)):
            new_loop = self.calc_avg_two_loops(new_loop, loops_stack[i])  
        
        return new_loop
    
    def average_arrays(self, arr1, arr2):

        len1, len2 = len(arr1), len(arr2)
        min_len = min(len1, len2)
        
        average_part = (arr1[:min_len] + arr2[:min_len]) / 2
        
        if len1 > len2:
            result = np.concatenate((average_part, arr1[min_len:]))
        elif len2 > len1:
            result = np.concatenate((average_part, arr2[min_len:]))
        else:
            result = average_part
        
        return result
            
    def calc_avg_two_loops(self, loop1, loop2):
        if loop1.time_scale != loop2.time_scale:
            logger.warning("невозможно вычислить среднее между петлями, временной шаг должен быть одинаковым")
            return False
        
        mean_resistance  = (loop1.resistance + loop2.resistance)/2
        mean_wire_square = (loop1.wire_square + loop2.wire_square)/2
        
        mean_sig = self.average_arrays(loop2.filtered_x_data,
                                       loop1.filtered_x_data)
        
        mean_field = self.average_arrays(loop2.filtered_y_data,
                                         loop1.filtered_y_data)
                               
        new_loop = hystLoop(raw_x        =mean_sig,
                            raw_y        =mean_field,
                            time_scale   =loop1.time_scale,
                            resistance   =mean_resistance,
                            wire_square  =mean_wire_square
                            )
        return new_loop
                     
    def clear_highlight_loop(self):
        if len(self.loops_stack) > 0:
            for index in range(len(self.loops_stack) - 1, -1, -1):
                loop = self.loops_stack[index]
                if loop.current_highlight:
                    self.graphView_loop.removeItem(loop.plot_obj)
                    del self.loops_stack[index]

    def clear_all_loops(self):
        if len(self.loops_stack) > 0:
            for loop in self.loops_stack:
                self.graphView_loop.removeItem(loop.plot_obj)
            self.loops_stack.clear()

    def clear_layout(self, layout, widget_to_keep):
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if (
                    widget and widget != widget_to_keep
                ):
                    layout.removeWidget(widget)
                    widget.deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout(), widget_to_keep)
                    layout.removeItem(item)
                    item.layout().deleteLater()

    def clear_data(self, device, ch_name):
        for key in self.stack_osc.keys():
                if str(device) in key and str(ch_name) in key:
                    self.stack_osc[key].is_draw = False
                    self.stack_osc[key].current_highlight = False

        self.update_draw()

    def set_data(self, osc_data, step_data, index):
        device = osc_data.device
        ch_name = osc_data.ch
        num_wave = index

        key_stack = str(device) + str(ch_name) + str(num_wave)
        
        if self.stack_osc.get(key_stack, None) == None:

            y = np.array(osc_data.par_val[index])
            x = np.array([abs(step_data.par_val[index]*i) for i in range(1, len(y)+1)])

            meas_y_data = measTimeData( 
                                        device = device,
                                        ch = ch_name,
                                        param = 'wave',
                                        par_val = y,
                                        num_or_time = x)
            meas_x_data = measTimeData( 
                                        device = device,
                                        ch = ch_name,
                                        param = 'step',
                                        par_val = x,
                                        num_or_time = x)
            
            relation_data = relationData(meas_x_data, meas_y_data)

            new_osc = oscData(  data = relation_data )
            
            self.stack_osc[key_stack] = new_osc

        for key in self.stack_osc.keys():
            if key != key_stack:
                if str(device) in key and str(ch_name) in key:
                    self.stack_osc[key].is_draw = False
                    self.stack_osc[key].current_highlight = False

        self.stack_osc[key_stack].is_draw = True                

        self.update_draw()

    def set_default(self):
        """привести класс к исходному состоянию"""
        self.graphView.plotItem.clear()
        self.graphView_loop.plotItem.clear()
        self.choice_device.clear()
        self.choice_device.addItems([self.choice_device_default_text])

    def update_draw(self):

        self.legend.clear()
        #===================================================
        for obj in self.stack_osc.values():
            if obj.is_draw:
                if obj.plot_obj == None:

                    if obj.saved_pen == None:
                        buf_pen = {
                            "color": next(self.color_gen),
                            "width": 1,
                            "antialias": True,  
                            "symbol": "o",
                        }
                    else:
                        buf_pen = obj.saved_pen

                    graph = self.graphView.plot(obj.filtered_x_data, 
                                                obj.filtered_y_data, 
                                                pen  = buf_pen
                                                )

                    obj.set_plot_obj(plot_obj = graph,
                                    pen       = buf_pen)
                    
            else:
                if obj.plot_obj != None:
                    self.graphView.removeItem(obj.plot_obj)
                    obj.plot_obj = None
                
    def showToolTip_main(self, event):
        pos = event

        #==============показываются кривые, когда курсор находится в квадрате графика, квадрат очерчен вокруг графика, 
        '''
        from pyqtgraph.graphicsItems.PlotCurveItem import PlotCurveItem
        items = self.graphView.scene().items(pos)  # Получаем все элементы под курсором
        plot_items = [item for item in items if isinstance(item, PlotCurveItem)]
        if plot_items:
            print("PlotItem под курсором:", plot_items)
        else:
            print("Нет PlotItem под курсором")
        '''
        #==================================================================

        x_val = round(
            self.graphView.plotItem.vb.mapSceneToView(pos).x(), 5
        )  # Координата X
        y_val = round(
            self.graphView.plotItem.vb.mapSceneToView(pos).y(), 5
        )  # Координата Y
        text = f'<p style="font-size:{10}pt">X:{x_val} Y:{y_val}</p>'
        try:
            self.tooltip.setText(text)
        except:
            pass  # лейбл удален

    def showToolTip_loop(self, event):
        pos = event  # Получаем позицию курсора

        x_val = round(
            self.graphView_loop.plotItem.vb.mapSceneToView(pos).x(), 5
        )
        y_val = round(
            self.graphView_loop.plotItem.vb.mapSceneToView(pos).y(), 5
        )
        text = f'<p style="font-size:{10}pt">X:{x_val} Y:{y_val}</p>'
        try:
            self.tooltip.setText(text)
        except:
            pass  # лейбл удален

    # hyst section func
    def is_coord_correct(self) -> bool:
        coord1 = self.left_coord.line_edit.text()
        coord2 = self.right_coord.line_edit.text()

        is_coord1_correct = True
        is_coord2_correct = True

        try:
            coord1 = float(coord1)
        except:
            is_coord1_correct = False

        try:
            coord2 = float(coord2)
        except:
            is_coord2_correct = False

        self.left_coord.setStyleSheet(
            "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
        )
        self.right_coord.setStyleSheet(
            "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
        )
        if is_coord1_correct:
            self.left_coord.setStyleSheet(
                "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
            )
        if is_coord2_correct:
            self.right_coord.setStyleSheet(
                "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
            )
        if is_coord1_correct and is_coord2_correct:
            if coord1 > coord2:
                self.left_coord.setStyleSheet(
                    "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
                )
                self.right_coord.setStyleSheet(
                    "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
                )
                is_coord2_correct = False
                is_coord1_correct = False

        return is_coord1_correct and is_coord2_correct

    def is_param_correct(self) -> bool:
        resistance = self.resistance.text()
        square = self.square.text()

        is_res_correct = True
        is_sq_correct = True

        try:
            resistance = float(resistance)
        except:
            is_res_correct = False

        try:
            square = float(square)
        except:
            is_sq_correct = False

        self.resistance.setStyleSheet(
            "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
        )
        self.square.setStyleSheet(
            "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
        )
        if is_res_correct:
            self.resistance.setStyleSheet(
                "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
            )
        if is_sq_correct:
            self.square.setStyleSheet(
                "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
            )

        return is_res_correct and is_sq_correct

    def is_ch_sig_field_correct(self) -> bool:
        self.sig_ch_choice.setStyleSheet(
            "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
        )
        self.field_ch_choice.setStyleSheet(
            "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
        )
        if self.sig_ch_choice.currentText() == self.field_ch_choice.currentText():
            self.sig_ch_choice.setStyleSheet(
                "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
            )
            self.field_ch_choice.setStyleSheet(
                "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
            )
            return False
        return True

    def is_all_hyst_correct(self) -> bool:
        status = self.is_ch_sig_field_correct()
        status2 = self.is_coord_correct()
        status3 = self.is_param_correct()
        return status and status2 and status3

    def find_sign_change(self, derivative):
        sign_changes = []
        for i in range(1, len(derivative)):
            if (
                np.sign(derivative[i]) != np.sign(derivative[i - 1])
                and derivative[i] != 0
            ):
                sign_changes.append(i)

        return sign_changes

    def push_auto_button(self):

        if self.vertical_lines.is_data_setted == False:
            device = self.choice_device.currentText()
            ch_field = self.field_ch_choice.currentText()
            number_field = int(self.channels_wave_choice[ch_field].currentText()) - 1

            key_wave = None
            for key in self.dict_param[device][ch_field].keys():
                if "wavech" in key:
                    key_wave = key
                    break

            if key_wave == None:
                text = " ".join(self.dict_param[device][ch_field].keys())
                logger.error("В выбранном канале нет осциллограммы" + text)
                return

            y_val = self.dict_param[device][ch_field][key_wave][number_field]
            scale_field = self.dict_param[device][ch_field]["scale"][number_field]

            interval_index = np.array(self.find_sign_change(y_val))
            interval_values = interval_index * scale_field

            ans = self.vertical_lines.set_data(
                max_y_val=np.nanmax(y_val),
                min_y_val=np.nanmin(y_val),
                interval_values=interval_values,
            )
            if ans == False:
                logger.info("Нельзя найти точки пересечения с нулем или она всего одна")

        if self.vertical_lines.is_data_setted == True:
            status, x_vert_1, x_vert_2 = self.vertical_lines.get_next_data()
            if status:
                self.right_coord.line_edit.setText(str(x_vert_2))
                self.left_coord.line_edit.setText(str(x_vert_1))
            else:
                self.right_coord.line_edit.setText("---")
                self.left_coord.line_edit.setText("---")

    def update_status_vert_line(self):
        if self.key:
            self.vertical_lines.reset_data()
            current_curves = self.graphView.plotItem.listDataItems()
            for curve in current_curves:
                if curve in self.list_vert_curve:
                    self.graphView.plotItem.removeItem(curve)

    def draw_vert_line(self):
        if self.ver_curve_left in self.graphView.scene().items():
            self.graphView.removeItem(self.ver_curve_left)

        if self.ver_curve_right in self.graphView.scene().items():
            self.graphView.removeItem(self.ver_curve_right)

        device = self.choice_device.currentText()
        ch_field = self.field_ch_choice.currentText()
        number_field = int(self.channels_wave_choice[ch_field].currentText()) - 1
        try:
            key_wave = None
            for key in self.dict_param[device][ch_field].keys():
                if "wavech" in key:
                    key_wave = key
                    break
            y_val = self.dict_param[device][ch_field][key_wave][number_field]
        except:
            y_val = [5]

        x_vert_1_ok = False
        x_vert_2_ok = False
        try:
            x_vert_2 = float(self.right_coord.line_edit.text())
            x_vert_2_ok = True
        except:
            pass
        try:
            x_vert_1 = float(self.left_coord.line_edit.text())
            x_vert_1_ok = True
        except:
            pass

        y_vert = [np.nanmin(y_val), np.nanmax(y_val)]

        if x_vert_1_ok:
            x_vert_1 = [x_vert_1, x_vert_1]
            self.ver_curve_left = self.graphView.plot(
                x_vert_1,
                y_vert,
                pen={
                    "color": next(self.color_gen),
                    "width": 1,
                    "antialias": True,
                    "symbol": "o",
                }
            )

        if x_vert_2_ok:
            x_vert_2 = [x_vert_2, x_vert_2]

            self.ver_curve_right = self.graphView.plot(
                x_vert_2,
                y_vert,
                pen={
                    "color": next(self.color_gen),
                    "width": 1,
                    "antialias": True,
                    "symbol": "o",
                },
            )

        self.list_vert_curve = [self.ver_curve_right, self.ver_curve_left]

    def hyst_loop_activate(self):
        if self.build_hyst_loop_check.isChecked():
            self.hyst_loop_layer.setVisible(True)
            self.graphView_loop.setVisible(True)
        else:
            self.hyst_loop_layer.setVisible(False)
            self.graphView_loop.setVisible(False)

    def draw_loop(self):
        if self.is_all_hyst_correct():
            device = self.choice_device.currentText()
            ch_field = self.field_ch_choice.currentText()
            ch_sig = self.sig_ch_choice.currentText()
            number_field = int(self.channels_wave_choice[ch_field].currentText()) - 1
            status = True

            key_wave_field = None
            for key in self.dict_param[device][ch_field].keys():
                if "wavech" in key:
                    key_wave_field = key
                    break

            key_wave_sig = None
            for key in self.dict_param[device][ch_sig].keys():
                if "wavech" in key:
                    key_wave_sig = key
                    break

            field_arr = self.dict_param[device][ch_field][key_wave_field][number_field]
            sig_arr = self.dict_param[device][ch_sig][key_wave_sig][number_field]
            sig_scale = self.dict_param[device][ch_sig]["scale"][number_field]
            field_scale = self.dict_param[device][ch_field]["scale"][number_field]
            
            if status:
                if field_scale != sig_scale:
                    status = False
                    logger.warning("time scale сигнала и поля должны быть равны")
                    
            if status:
                try:
                    x_vert_2 = float(self.right_coord.line_edit.text())
                    x_vert_1 = float(self.left_coord.line_edit.text())
                except:
                    status = False

            if status:
                left_ind = int(x_vert_1 / sig_scale)
                right_ind = int(x_vert_2 / sig_scale)
                
                raw_x = sig_arr[left_ind:right_ind]
                raw_y = field_arr[left_ind:right_ind]
                  
                if len(raw_y) > len(raw_x):
                    raw_y = raw_y[0: len(raw_x)]
                elif len(raw_y) < len(raw_x):
                    raw_x = raw_x[0: len(raw_y)]
                
                new_loop = hystLoop(raw_x = raw_x,
                                    raw_y =  raw_y,
                                    time_scale=field_scale,
                                    resistance = float( self.resistance.text() ),
                                    wire_square = float( self.square.text())
                                      )
                x, y = new_loop.get_xy_data()

                self.loops_stack.append(new_loop)

                new_pen = {
                        "color": next(self.color_gen),
                        "width": 1,
                        "antialias": True,
                        "symbol": "o",
                        }

                plot_obj = self.graphView_loop.plot(
                    x,
                    y,
                    pen=new_pen,
                )

                new_loop.set_plot_obj( plot_obj, new_pen )

            else:
                logger.warning("неверные данные для построения петли")
        else:
            pass

    def set_filters(self, filter_func):
        for loop in self.loops_stack:
            if loop.current_highlight:
                loop.filtered_x_data, _ = filter_func(loop.filtered_x_data)
                loop.filtered_y_data, _ = filter_func(loop.filtered_y_data)

                self.graphView_loop.removeItem(loop.plot_obj)

                x, y = loop.recalc_data()

                plot_obj = self.graphView_loop.plot(
                    x,
                    y,
                    pen=loop.saved_pen,
                )

                loop.set_plot_obj( plot_obj, loop.saved_pen)

        for osc in self.stack_osc.values():
            if osc.current_highlight:

                osc.filtered_y_data, _ = filter_func(osc.filtered_y_data)
                osc.filtered_x_data = osc.filtered_x_data[-len(osc.filtered_y_data):]

                osc.plot_obj.setData(osc.filtered_x_data, osc.filtered_y_data)

    def retranslateUI(self, GraphWindow):
        _translate = QApplication.translate
        self.build_hyst_loop_check.setText(_translate("GraphWindow", "Построение петель гистерезиса") )
        self.label.setText(_translate("GraphWindow", "Отображаемый канал") )
        self.label2.setText(_translate("GraphWindow", "Номер осциллограммы") )
        self.button_hyst_loop_clear.setText(_translate("GraphWindow", "Очистить все") )
        self.button_hyst_loop.setText(_translate("GraphWindow", "Построить петлю") )
        self.resistance.setPlaceholderText(_translate("GraphWindow", "Сопротивление провода(Ом)") )
        self.square.setPlaceholderText(_translate("GraphWindow", "Площадь провода(мкм)") )
        self.right_coord.line_edit.setPlaceholderText(_translate("GraphWindow", "Координата справа") )
        self.left_coord.line_edit.setPlaceholderText(_translate("GraphWindow", "Координата слева") )
        self.auto_button.setText(_translate("GraphWindow", "Авто") )
        self.name_sig.setText(_translate("GraphWindow", "Сигнал") )
        self.name_field.setText(_translate("GraphWindow", "Поле") )
        
class verticals_lines:

    def __init__(self) -> None:
        self.is_data_setted = False
        self.ind_intervals = 0
        self.interval_values = None
        self.max_y_val = None
        self.min_y_val = None

    def set_data(self, max_y_val, min_y_val, interval_values: list):
        if len(interval_values) > 1:
            self.max_y_val = max_y_val
            self.min_y_val = min_y_val
            self.interval_values = interval_values
            self.ind_intervals = 0
            self.is_data_setted = True
            return True
        else:
            return False

    def get_next_data(self) -> list:
        status = True
        if len(self.interval_values) > 2:
            x_vert_1 = self.interval_values[self.ind_intervals]
            x_vert_2 = self.interval_values[self.ind_intervals + 2]
        elif len(self.interval_values) == 2:
            x_vert_1 = self.interval_values[self.ind_intervals]
            x_vert_2 = self.interval_values[self.ind_intervals + 1]
        elif len(self.interval_values) == 1:
            x_vert_1 = self.interval_values[self.ind_intervals]
            x_vert_2 = x_vert_1
        else:
            status = False

        self.ind_intervals += 1
        if self.ind_intervals + 2 >= len(self.interval_values):
            self.ind_intervals = 0

        return status, x_vert_1, x_vert_2

    def reset_data(self):
        self.is_data_setted = False
        self.ind_intervals = 0
        self.interval_values = None
        self.max_y_val = None
        self.min_y_val = None


class wheelLineEdit(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.line_edit = QLineEdit()
        self.layout.addWidget(self.line_edit)
        self.setLayout(self.layout)
        self.second_line = None

    def wheelEvent(self, event):
        try:
            current_value = float(self.line_edit.text())
            current_sec_value = float(self.second_line.text())
            delta = event.angleDelta().y()

            step = np.abs((current_value - current_sec_value) * 0.01)
            if delta > 0:
                current_value += step
            else:
                current_value -= step

            self.line_edit.setText(str(current_value))
            event.accept()
        except:
            pass

    def set_second_line_widget(self, line):
        """метод принимает ссылку на парный виджет, чтобы иметь возвможность работать в паре, например,
        изменять значение числа в зависимости от разницы текущего числа и числво во втором виджете
        """
        self.second_line = line


    