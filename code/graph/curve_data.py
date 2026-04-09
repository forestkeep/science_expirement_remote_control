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
from PyQt5.QtWidgets import QApplication
import logging
from PyQt5 import QtWidgets, QtCore, QtGui

logger = logging.getLogger(__name__)

from graph.tree_curves import CurveTreeItem
from graph.dataManager import relationData
from graph.filters_instance_class import FilterCommand
from datetime import datetime

class legendName():
    def __init__(self, name) -> None:
        self.__name = name
        self.current_name = self.__name
        self.previous_name = ""

    def set_custom(self, name: str):
        self.previous_name = self.__name
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
        plot_data_item.setPen(self.to_pen())
        
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

        self.plot_items = {}
        self.data_x = None
        self.data_y = None

        self.device = None
        self.ch = None
        self.name = None
        self.number = None

        self.is_curve_selected = False

        self.i_am_click_now = False 

        self.number_axis = None

        self.saved_style = None

        self.is_draw = False

        self.main_plot_obj = None

        self.tree_item = CurveTreeItem(curve_data_obj=self)

        self.is_curve_selected = False
        self.preselection_style = None
        self.higlighted_flag = False

        self.filters_history = []

        self.clicked_style = LineStyle(color=(180, 150, 150), line_style=QtCore.Qt.DashLine, line_width=4, symbol="+", symbol_size=10, symbol_color=(150, 150, 150), fill_color='w')

    def create_plot_item(self):
        """
        Создаёт новый PlotDataItem на основе текущих данных и стиля.
        Возвращает созданный item.
        """
        x = self.filtered_x_data
        y = self.filtered_y_data

        pen = self.saved_style.to_pen()
        symbol = self.saved_style.symbol
        symbol_pen = self.saved_style.to_symbol_pen()
        symbol_brush = self.saved_style.to_brush()

        plot_item = pg.PlotDataItem(
            x, y,
            pen=pen,
            name=self.legend.current_name,
            symbol=symbol,
            symbolPen=symbol_pen,
            symbolBrush=symbol_brush,
        )
        plot_item.setClipToView(True)
        plot_item.setDownsampling(auto=True, method='peak')
        plot_item.setFocus()
        plot_item.setZValue(100)
        plot_item.setCurveClickable(state=True, width=10)
        plot_item.sigClicked.connect(self.on_plot_clicked)

        return plot_item

    def add_to_graph(self, graph_field, legend_field, number_axis):
        """
        Добавляет копию кривой на указанный график.
        Если для этого viewbox уже есть копия, ничего не делает (или обновляет).
        """
        if self.plot_items.get(graph_field) is not None:  
            logger.info(f"Curve {self.curve_name} already exists on graph {graph_field} change link")

        new_item = self.create_plot_item()
        graph_field.addItem(new_item)
        if legend_field.getLabel(new_item) is None:
            legend_field.addItem(new_item, self.legend.current_name)

        self.plot_items[graph_field] = {
            'item': new_item,
            'legend': legend_field,
            'axis': number_axis
        }

        if self.is_curve_selected:
            self.clicked_style.apply_to_curve(new_item)
        else:
            self.saved_style.apply_to_curve(new_item)

        self.is_draw = True

    def remove_from_graph(self, viewbox):
        """Удаляет копию кривой с конкретного графика."""
        if viewbox in self.plot_items:
            info = self.plot_items.pop(viewbox)
            viewbox.removeItem(info['item'])
            info['legend'].removeItem(self.legend.current_name)

    def remove_all_from_graphs(self):
        """Удаляет со всех графиков."""
        for viewbox in list(self.plot_items.keys()):
            self.remove_from_graph(viewbox)

    def update_all_plots_data(self):
        """Обновляет данные во всех копиях PlotDataItem."""
        for info in self.plot_items.values():
            info['item'].setData(self.filtered_x_data, self.filtered_y_data)

    def change_name(self, name):
        """
        Изменяет пользовательское имя кривой и обновляет имя в легенде для всех графиков.
        :param name: Новое имя кривой
        :type name: str
        """
        
        self.is_name_curve_customized = True
        self.curve_name = name
        self.set_legend_name(self.curve_name)
        self.tree_item.set_name(self.curve_name)
    
    def reset_name(self):
        self.is_name_curve_customized = False
        self.curve_name = self.rel_data.current_name
        self.set_legend_name(self.curve_name)
        self.tree_item.set_name(self.curve_name)

    def apply_style_to_all(self, style):
        """Применяет стиль (например, LineStyle) ко всем копиям."""
        for info in self.plot_items.values():
            style.apply_to_curve(info['item'])

    def on_plot_clicked(self, obj):
        """Обработчик клика по любой копии кривой."""
        self.i_am_click_now = True
        if self.is_curve_selected:
            self.is_curve_selected = False
            self.apply_style_to_all(self.saved_style)
        else:
            self.is_curve_selected = True
            self.apply_style_to_all(self.clicked_style)

    def higlight_curve(self):
        if self.higlighted_flag:
            return
        self.higlighted_flag = True
        self.preselection_style = self.clicked_style if self.is_curve_selected else self.saved_style
        for info in self.plot_items.values():
            info['item'].setPen(pg.mkPen(color=(150,150,150,90), width=5))
            info['item'].setSymbolBrush(color=(150,150,150,90))
            info['item'].setSymbolPen(pg.mkPen(color=(150,150,150,90)))

    def unhiglight_curve(self):
        if not self.higlighted_flag:
            return
        self.higlighted_flag = False
        self.apply_style_to_all(self.preselection_style)

    # В методе stop_session нужно обновить данные во всех копиях
    def stop_session(self):
        if self.plot_items:
            self.update_all_plots_data()
        if not self.data_reset():
            logger.warning(...)

    def change_style(self, new_style: LineStyle):
        self.saved_style = new_style

        for curves in self.plot_items.values():
                self.saved_style.apply_to_curve(curves['item'])

    def delete_curve_from_graph(self):
        if self.is_draw:
            self.is_draw = False
            for graph_field, data_item in self.plot_items.items():
                graph_field.removeItem(data_item['item'])
                data_item['legend'].removeItem(self.legend.current_name)
    
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

    def set_filter(self, filter_command: FilterCommand):
        self.filtered_x_data, self.filtered_y_data, message = filter_command.apply(self.filtered_x_data, self.filtered_y_data)
        for curves in self.plot_items.values():
            curves['item'].setData(self.filtered_x_data, self.filtered_y_data)

        self.recalc_stats_param()

        self.filters_history.append(filter_command)

        self.tree_item.update_history_block(data={str(datetime.now().strftime("%H:%M:%S")): message,},
                                            filter_command = filter_command,)
    def delete_filter(self, filter_command: FilterCommand):
        if filter_command not in self.filters_history:
            return
        self.filters_history.remove(filter_command)
        self.data_reset()
        self.update_filters_after_delete(self.filters_history)

    def clear_filters(self):
        self.filters_history = []
        self.data_reset()
        self.update_filters_after_delete(self.filters_history)
        self.tree_item.clear_history_block()

    def update_filters_after_delete(self, filters: list):
        for filter in filters:
            self.filtered_x_data, self.filtered_y_data, message = filter.apply(self.filtered_x_data, self.filtered_y_data)
        for curves in self.plot_items.values():
            curves['item'].setData(self.filtered_x_data, self.filtered_y_data)
        self.recalc_stats_param()

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

        self.tree_item.set_name(self.curve_name)
        self.recalc_stats_param()

    def alias_changed(self, original_name, old_alias, alias):
        new_x_name = self.rel_data.x_current_name
        new_y_name = self.rel_data.y_current_name
        if original_name == self.rel_data.x_root_name:
            new_x_name = alias
        if original_name == self.rel_data.y_root_name:
            new_y_name = alias
        self.rel_data.update_names(new_x_name, new_y_name)

        if not self.is_name_curve_customized:
            self.curve_name = self.rel_data.current_name
            self.tree_item.set_name(self.curve_name)
            self.set_legend_name(self.curve_name)

    def stop_session(self):
        super().stop_session()
        self.recalc_stats_param()

    def set_legend_name(self, name):
        """Изменяет имя в легенде для всех графиков."""
        self.legend.set_custom(name)
        for info in self.plot_items.values():
            # Удаляем старую запись в легенде и добавляем новую
            info['legend'].removeItem(self.legend.previous_name)  # нужно хранить предыдущее имя
            info['legend'].addItem(info['item'], self.legend.current_name)

    def recalc_stats_param(self):
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

