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
class graphData:
    def __init__(self, raw_x, raw_y) -> None:
        """
        Initializes the graphData object with raw data for x and y axes.

        Parameters:
            raw_x: The raw data for the x-axis.
            raw_y: The raw data for the y-axis.
        """
        self.raw_data = raw_x 
        self.raw_data = raw_y 

        self.filtered_x_data = raw_x
        self.filtered_y_data = raw_y

        self.plot_obj = None
        self.data_x = None
        self.data_y = None

    def set_plot_obj(self, plot_obj, pen, highlight=False):
        self.plot_obj = plot_obj
        self.plot_obj.setFocus()
        self.plot_obj.setZValue(100)
        self.plot_obj.setCurveClickable( state = True, width = 10)#установить кривую кликабельной с шириной 10 пикселей
        self.plot_obj.sigPointsClicked.connect(self.on_points_clicked)
        self.plot_obj.sigClicked.connect(self.on_plot_clicked)

        self.line_color = (0, 0, 255)
        self.current_highlight = False

        self.saved_pen = pen

        if highlight:
            self.current_highlight = True
            self.plot_obj.setPen(pg.mkPen('w', width=2))
    
    def on_points_clicked(self, points):
        print("clicked point",points)
     
    def on_plot_clicked(self, pos):
        print("clicked plot", pos)
        if self.current_highlight:
            self.current_highlight = False
            self.plot_obj.setPen(self.saved_pen)
        else:
            self.current_highlight = True
            self.plot_obj.setPen(pg.mkPen('w', width=2))

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
            
    def set_plot_obj(self, plot_obj, pen, highlight=False):
        self.plot_obj = plot_obj
        self.plot_obj.setFocus()
        self.plot_obj.setZValue(100)
        self.plot_obj.setCurveClickable( state = True, width = 10)#установить кривую кликабельной с шириной 10 пикселей
        #self.plot_obj.setShadowPen(pen=None)#перо для выделения графика, если нажали, то задать это
        self.plot_obj.sigPointsClicked.connect(self.on_points_clicked)
        self.plot_obj.sigClicked.connect(self.on_plot_clicked)
        #self.plot_obj.sigPlotChanged.connect(self.on_plot_changed)

        self.line_color = (0, 0, 255)
        self.current_highlight = False

        self.saved_pen = pen

        if highlight:
            self.current_highlight = True
            self.plot_obj.setPen(pg.mkPen('w', width=2))
    
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
        J2 = np.cumsum(I2)  # Кусковая сумма
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