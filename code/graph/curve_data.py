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
from scipy import stats

try:
    from tree_curves import CurveTreeItem
except:
    from graph.tree_curves import CurveTreeItem
    
class graphData:
    def __init__(self, raw_x, raw_y) -> None:
        """
        Initializes the graphData object with raw data for x and y axes.

        Parameters:
            raw_x: The raw data for the x-axis.
            raw_y: The raw data for the y-axis.
        """
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
        self.legend_name = None

        self.mother_data = None

        self.saved_pen = None

        self.is_draw = False

        self.parent_graph_field = None
        self.legend_field = None

        self.tree_item = CurveTreeItem(curve_data_obj=self)

    def set_plot_obj(self, plot_obj, pen, highlight=False):
        self.plot_obj = plot_obj
        self.plot_obj.setFocus()
        self.plot_obj.setZValue(100)
        self.plot_obj.setCurveClickable( state = True, width = 10)#установить кривую кликабельной с шириной 10 пикселей
        self.plot_obj.sigClicked.connect(self.on_plot_clicked)

        self.current_highlight = False

        self.i_am_click_now = False #флаг поднимается в момент, когда по графику кликают мышкой. Сбрасывается в методе, вызванном по сигналу от клика по всей сцене, 
        #в этом методе проверяется. был-ли только то кликнут график, и если да, то выделенные графики не сбрасываются
        self.preselection_pen = pen #эта пеерменная необходимо для запоминания стиля перед выделением графика через меню дерева
        self.saved_pen = pen

        self.tree_item.setForeground(1, QBrush(QColor(self.saved_pen['color'])))

        if highlight:
            self.current_highlight = True
            self.plot_obj.setPen(pg.mkPen('w', width=2))
            self.plot_obj.setSymbolBrush(color = 'w')

    def change_color(self, color):
        self.saved_pen['color'] = color
        self.plot_obj.setPen(self.saved_pen)
        self.plot_obj.setSymbolBrush(self.saved_pen['color'])

    def higlight_curve(self):
        if self.current_highlight:
            self.preselection_pen = pg.mkPen('w', width=2)
        else:
            self.preselection_pen = self.saved_pen
        self.plot_obj.setPen(pg.mkPen(color=(150, 150, 150, 90), width=5))
        self.plot_obj.setSymbolBrush(color=(150, 150, 150, 90))

    def unhiglight_curve(self):
        self.plot_obj.setPen(self.preselection_pen)
        if self.preselection_pen is not self.saved_pen:
            self.plot_obj.setSymbolBrush(color = 'w')
        else:
            self.plot_obj.setSymbolBrush(color = self.saved_pen['color'])

    def on_plot_clicked(self, obj):

        self.i_am_click_now = True

        if self.current_highlight:
            self.current_highlight = False
            self.plot_obj.setPen(self.saved_pen)
            self.plot_obj.setSymbolBrush(self.saved_pen['color'])
        else:
            self.current_highlight = True
            self.plot_obj.setPen(pg.mkPen('w', width=2))
            self.plot_obj.setSymbolBrush(color = 'w')
    def place_curve_on_graph(self, graph_field: pg.ViewBox, legend_field):
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
        if self.parent_graph_field:
            if graph_field is not self.parent_graph_field:
                self.parent_graph_field.removeItem(self.plot_obj)

        if self.legend_field:
            if self.legend_field is not legend_field:
                self.legend_field.removeItem(self.legend_name)

        self.parent_graph_field = graph_field
        self.legend_field = legend_field
        
        self.parent_graph_field.addItem(self.plot_obj)

        if self.legend_field.getLabel( self.plot_obj ) is None:
            self.legend_field.addItem(self.plot_obj, self.legend_name)

        self.is_draw = True

    def delete_curve_from_graph(self):
        if self.is_draw:
            self.is_draw = False
            self.parent_graph_field.removeItem(self.plot_obj)
            self.legend_field.removeItem(self.legend_name)
    
    def data_reset(self) -> bool:
        if self.filtered_x_data is self.raw_data_x:
            return False
        self.filtered_x_data = self.raw_data_x
        self.filtered_y_data = self.raw_data_y
        return True

class linearData(graphData):
    def __init__(self, raw_x, raw_y, device, ch, y_name, x_name, y_param_name, x_param_name) -> None:
        super().__init__(raw_x, raw_y)
        self.device = device
        self.ch = ch
        self.y_name = y_name
        self.x_name = x_name
        self.legend_name = " ".join([device, ch])

        self.y_param_name = y_param_name
        self.x_param_name = x_param_name

        self.recalc_stats_param()

    def set_full_legend_name(self):
        if self.legend_field:
            self.legend_field.removeItem(self.legend_name)

        self.legend_name = " ".join([self.device, self.ch, self.y_param_name])

        if self.legend_field:
            self.legend_field.addItem(self.plot_obj, self.legend_name)

    def set_short_legend_name(self):
        if self.legend_field:
            self.legend_field.removeItem(self.legend_name)

        self.legend_name = " ".join([self.device, self.ch])

        if self.legend_field:
            self.legend_field.addItem(self.plot_obj, self.legend_name)

    def recalc_stats_param(self):
        self.tree_item.update_parameters(
            {
                "min_x": np.nanmin(self.filtered_x_data),
                "max_x": np.nanmax(self.filtered_x_data),
                "min_y": np.nanmin(self.filtered_y_data),
                "max_y": np.nanmax(self.filtered_y_data),
                "name": "-".join([self.y_name, self.x_name]),
                "tip": "linear",
                "mean": round(np.nanmean(self.filtered_y_data), 3),
                "std": round(np.nanstd(self.filtered_y_data), 3),
                "median": np.nanmedian(self.filtered_y_data),
                "count": np.count_nonzero(~np.isnan(self.filtered_y_data)),  #Колиество ненулевых значений
                "mode": stats.mode(self.filtered_y_data[~np.isnan(self.filtered_y_data)])[0]  #только ненулевые значения
            }
        )

class oscData(graphData):
    def __init__(self, raw_x, raw_y, device, ch, name, number) -> None:
        super().__init__(raw_x, raw_y)
        self.device = device
        self.ch = ch
        self.name = name
        self.number = number
        self.legend_name = ch

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