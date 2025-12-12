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

import numpy as np
import pyqtgraph as pg
from PyQt5.QtGui import QBrush, QColor
import logging
from PyQt5 import QtWidgets, QtCore, QtGui

logger = logging.getLogger(__name__)

from graph.tree_curves import CurveTreeItem
from graph.dataManager import relationData

class legendName():
    def __init__(self, name) -> None:
        self.__name = name
        self.current_name = self.__name

    def set_custom(self, name: str):
        self.__name = name
        self.current_name = self.__name

class LineStyle:
    def __init__(self, color='w', line_style=QtCore.Qt.SolidLine, line_width=1, 
                 symbol=None, symbol_size=5, symbol_color='w', fill_color='w'):
        self.color = color
        self.line_style = line_style
        self.line_width = line_width
        self.symbol = symbol
        self.symbol_size = symbol_size
        self.symbol_color = symbol_color
        self.fill_color = fill_color
        self.px_mode = True
    
    def to_pen(self):
        """Создать QPen из стиля"""
        #print(f"color: {self.color}, line_style: {self.line_style}, line_width: {self.line_width}")
        return pg.mkPen(
            color=self.color,
            width=self.line_width,
            style=self.line_style
        )
    
    def to_symbol_pen(self):
        """Создать QPen для символа"""
        return pg.mkPen(color=self.symbol_color)
    
    
    def to_brush(self):
        """Создать QBrush для заливки"""
        return pg.mkBrush(color=self.fill_color)
    
    def copy(self):
        """Создать копию стиля"""
        return LineStyle(
            color=self.color,
            line_style=self.line_style,
            line_width=self.line_width,
            symbol=self.symbol,
            symbol_size=self.symbol_size,
            symbol_color=self.symbol_color,
            fill_color=self.fill_color
        )
    
    def apply_to_curve(self, plot_data_item):
        """Применить стиль к кривой (PlotDataItem)"""
        # Установка пера для линии
        plot_data_item.setPen(self.to_pen())
        
        # Настройка символов, если они заданы
        if self.symbol is not None:
            plot_data_item.setSymbol(self.symbol)
            plot_data_item.setSymbolSize(self.symbol_size)
            plot_data_item.setSymbolPen(self.to_symbol_pen())
            plot_data_item.setSymbolBrush(self.to_brush())
        else:
            plot_data_item.setSymbol(None)

        plot_data_item.opts['pxMode'] = self.px_mode
        plot_data_item.updateItems()

        #plot_data_item.setData(pxMode=self.px_mode)


    
class graphData:
    def __init__(self, data) -> None:
        """
        Initializes the graphData object with raw data for x and y axes.
        The length of arrays is cut to the minimum

        Parameters:
            raw_x: The raw data for the x-axis.
            raw_y: The raw data for the y-axis.
        """
        raw_x = data.x_result
        raw_y = data.y_result

        min_len = min(len(data.x_result), len(data.y_result))
        raw_x = raw_x[:min_len]
        raw_y = raw_y[:min_len]

        self.raw_data_x = np.array(raw_x)
        self.raw_data_y = np.array(raw_y)

        self.filtered_x_data = np.array(raw_x)
        self.filtered_y_data = np.array(raw_y)

        self.plot_obj = None
        self.data_x = None
        self.data_y = None

        self.device = None
        self.ch = None
        self.name = None
        self.number = None

        self.number_axis = None

        self.saved_style = None

        self.is_draw = False

        self.parent_graph_field = None
        self.legend_field = None

        self.tree_item = CurveTreeItem(curve_data_obj=self)

        self.is_curve_selected = False
        self.preselection_style = None
        self.higlighted_flag = False

        self.clicked_style = LineStyle(color=(180, 150, 150), line_style=QtCore.Qt.DashLine, line_width=4, symbol="+", symbol_size=10, symbol_color=(150, 150, 150), fill_color='w')


    def set_plot_obj(self, plot_obj, style: LineStyle, highlight = False):
        self.plot_obj = plot_obj
        self.plot_obj.setFocus()
        self.plot_obj.setZValue(100)
        self.plot_obj.setCurveClickable( state = True, width = 10)#установить кривую кликабельной с шириной 10 пикселей
        self.plot_obj.sigClicked.connect(self.on_plot_clicked)

        self.is_curve_selected = False

        self.i_am_click_now = False #флаг поднимается в момент, когда по графику кликают мышкой. Сбрасывается в методе, вызванном по сигналу от клика по всей сцене, 
        #в этом методе проверяется. был-ли только то кликнут график, и если да, то выделенные графики не сбрасываются
        self.preselection_style = style #эта пеерменная необходимо для запоминания стиля перед выделением графика через меню дерева
        self.saved_style = style

        self.tree_item.setForeground(1, QBrush(QColor(self.saved_style.color)))

        if highlight:
            self.is_curve_selected = True
            self.clicked_style.apply_to_curve(self.plot_obj)
        else:
            self.saved_style.apply_to_curve(self.plot_obj)

    def change_style(self, new_style: LineStyle):
        self.saved_style = new_style
        self.saved_style.apply_to_curve(self.plot_obj)

    def higlight_curve(self):
        if self.higlighted_flag:
            return
        self.higlighted_flag = True
        if self.is_curve_selected:
            self.preselection_style = self.clicked_style
        else:
            self.preselection_style = self.saved_style
        self.plot_obj.setPen(pg.mkPen(color=(150, 150, 150, 90), width=5))
        self.plot_obj.setSymbolBrush(color=(150, 150, 150, 90))
        self.plot_obj.setSymbolPen(pg.mkPen(color=(150, 150, 150, 90)))

    def unhiglight_curve(self):
        if not self.higlighted_flag:
            return
        self.higlighted_flag = False
        self.preselection_style.apply_to_curve(self.plot_obj)

    def on_plot_clicked(self, obj):
        self.i_am_click_now = True

        if self.is_curve_selected:
            self.is_curve_selected = False
            self.saved_style.apply_to_curve(self.plot_obj)
        else:
            self.is_curve_selected = True
            self.clicked_style.apply_to_curve(self.plot_obj)
    
    def place_curve_on_graph(self, graph_field: pg.ViewBox, legend_field, number_axis):
        """
        Places the curve on the given graph and legend fields. If the given fields
        are different from the current fields, the curve is first removed from the
        current fields before being added to the new fields.

        Parameters
        ----------
        graph_field : pg.ViewBox
            The ViewBox to add the curve to.
        legend_field : pg.LegendItem
            The LegendItem to add the curve to.
        """

        #logger.info(f"placing curve {self.name} on graph {self.plot_obj=}")
        #logger.info(f"{self.filtered_y_data = }, {self.raw_data_y = }")
        #logger.info(f"{self.plot_obj.yData = }")

        if self.parent_graph_field:
            if graph_field is not self.parent_graph_field:
                self.parent_graph_field.removeItem(self.plot_obj)

        if self.legend_field:
            if self.legend_field is not legend_field:
                self.legend_field.removeItem(self.legend.current_name)

        self.parent_graph_field = graph_field
        self.legend_field = legend_field
        self.number_axis = number_axis

        self.parent_graph_field.addItem(self.plot_obj)

        if self.legend_field.getLabel( self.plot_obj ) is None:
            self.legend_field.addItem(self.plot_obj, self.legend.current_name)

        self.is_draw = True

    def delete_curve_from_graph(self):
        if self.is_draw:
            self.is_draw = False
            self.parent_graph_field.removeItem(self.plot_obj)
            self.legend_field.removeItem(self.legend.current_name)
    
    def data_reset(self) -> bool:
        if self.filtered_x_data is self.raw_data_x:
            return False
        self.filtered_x_data = self.raw_data_x
        self.filtered_y_data = self.raw_data_y
        return True
    
    def setData(self, data):
        old_x = self.rel_data.x_current_name
        old_y = self.rel_data.y_current_name
        self.rel_data = data
        self.rel_data.update_names(old_x, old_y)
        self.raw_data_x = np.array(data.x_result)
        self.raw_data_y = np.array(data.y_result)

    def stop_session(self):
        if self.plot_obj is not None:
            self.plot_obj.setData(self.raw_data_x, self.raw_data_y)
            if not self.data_reset():
                logger.info(f"{self.curve_name} data not reseted after experiment stop")

class linearData(graphData):
    def __init__(self, data: relationData, alias_manager) -> None:
        super().__init__(data)
        self.alias_manager = alias_manager
        self.rel_data = data

        x_name = self.alias_manager.get_alias(self.rel_data.x_root_name)
        y_name = self.alias_manager.get_alias(self.rel_data.y_root_name)
        self.rel_data.update_names(x_name,
                                   y_name)

        self.curve_name = self.rel_data.current_name
        self.legend = legendName(self.curve_name)
        self.alias_manager.aliases_updated.connect(self.alias_changed)
        self.is_name_curve_customized = False#флаг, указывающий на то, что название кривой было изменено пользователем

        self.tree_item.change_name(self.rel_data.current_name, reset=True)
        self.recalc_stats_param()

    def alias_changed(self, original_name, old_alias, alias):
        new_x_name = self.rel_data.x_current_name
        new_y_name = self.rel_data.y_current_name
        if original_name == self.rel_data.x_root_name:
            new_x_name = alias
        if original_name == self.rel_data.y_root_name:
            new_y_name = alias
        self.rel_data.update_names(new_x_name, new_y_name)

        self.curve_name = self.rel_data.current_name
        if not self.is_name_curve_customized:
            self.tree_item.change_name(self.rel_data.current_name, reset=True)

    def stop_session(self):
        super().stop_session()
        self.recalc_stats_param()

    def set_legend_name(self, name):
        if self.legend_field:
            if self.is_draw:
                self.legend_field.removeItem(self.legend.current_name)
                self.legend.set_custom(name)
                self.legend_field.addItem(self.plot_obj, self.legend.current_name)
            else:
                self.legend.set_custom(name)
        else:
            self.legend.set_custom(name)

    def recalc_stats_param(self):
        #вычисление моды
        filtered_data = self.filtered_y_data[~np.isnan(self.filtered_y_data)]
        if filtered_data.size == 0:
            mode_value = np.nan
        else:
            unique_values, counts = np.unique(filtered_data, return_counts=True)
            max_count = counts.max()
            modes = unique_values[counts == max_count]
            mode_value = modes.min()
        #------
        self.tree_item.update_parameters(
            {
                "min_x": np.nanmin(self.filtered_x_data),
                "max_x": np.nanmax(self.filtered_x_data),
                "min_y": np.nanmin(self.filtered_y_data),
                "max_y": np.nanmax(self.filtered_y_data),
                "name": self.curve_name,
                "tip": "linear",
                "mean": np.nanmean(self.filtered_y_data),
                "std": np.nanstd(self.filtered_y_data),
                "median": np.nanmedian(self.filtered_y_data),
                "count": np.count_nonzero(~np.isnan(self.filtered_y_data)),
                "mode": mode_value
            }
        )

class oscData(graphData):
    def __init__(self, data: relationData) -> None:
        super().__init__(data)
        self.rel_data = data
        self.curve_name = self.rel_data.root_name
        self.legend = legendName(self.curve_name)

class hystLoop(graphData):
    '''хранит данные о петле и ее исходных параметрах, содержит методы расчета петли'''
    def __init__(self, raw_x, raw_y, time_scale, resistance, wire_square) -> None:
        super().__init__(raw_x, raw_y)
        self.time_raw_data = [i*time_scale for i in range(len(raw_x))]
        self.time_scale = time_scale
        #отфильтрованные данные петли
        self.filtered_time_data = [i*time_scale for i in range(len(raw_x))]
        self.Q2 = 1.67  # сильно влияет на форму петли. уточнить влияние, для чего она введена?
        
        self.resistance = resistance
        self.wire_square = wire_square
            
    def calc_loop(self):
        arr1 = self.filtered_x_data
        arr2 = self.filtered_y_data

        arr1 = np.array(arr1)
        arr2 = np.array(arr2)

        R = 100 + self.resistance
        # d = 14.2
        d = self.wire_square / 2 * (10 ** (-6))
        A = R * (3.1415 * 2 * d * 2)
        C = 16
        X = arr2 / A + C
        Y = self.calculate_results( arr1 )

        size1 = len(X)
        size2 = len(Y)

        if size1 > size2:
            X = X[:size2]
        elif size2 > size1:
            Y = Y[:size1]

        return X, Y

    def calculate_results(self, C):

        noise_level1 = self.threshold_mean_std(C)
        noise_level2 = self.threshold_median(C)
        noise_level = noise_level2
        #TODO: сделать выбор порога ПОЛЬЗОВАТЕЛЕМ

        n = len(C)

        # Вычисление средних значений и сдвигов
        D2 = np.mean(C)
        E2 = C - D2
        F2 = np.where(np.abs(E2) > noise_level, 1, 0)

        G2 = E2 * F2
        H2 = np.mean(G2)

        # Интегрирование
        I2 = G2 - H2
        J2 = np.cumsum(I2)
        K2 = J2 - np.max(J2) / 2
        L2 = K2 + self.Q2

        # Нормировка
        M = np.where(L2 <= 0, L2 / np.nanmin(L2), L2 / -np.nanmax(L2))

        return M

    def threshold_mean_std(self, data):
        """Вычисляет порог на основе среднего значения и стандартного отклонения."""
        mean = np.mean(data)
        std_dev = np.std(data)
        k = 2  # Можно настроить коэффициент
        threshold = mean + k * std_dev
        return threshold

    def threshold_median(self, data):
        """Вычисляет порог на основе медианы и интерквартильного размаха."""
        Q1 = np.percentile(data, 40)
        Q3 = np.percentile(data, 60)
        IQR = Q3 - Q1
        threshold = Q3 + 1.5 * IQR  # Порог устанавливается на уровне Q3 + 1.5 * IQR
        return threshold
    
    def recalc_data(self):
        self.data_x, self.data_y = self.calc_loop()   
        return self.data_x, self.data_y
    
    def get_xy_data(self):
        if self.data_x is None or self.data_y is None:
             self.data_x, self.data_y = self.calc_loop()   
        return self.data_x, self.data_y