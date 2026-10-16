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

from typing import Union, Tuple

import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication
from graph.core.filters_instance_class import FilterCommand
import logging

logger = logging.getLogger(__name__)

class filtersClass():
    def __init__(self):
        self.filters_callbacks = []
        self.thinning_callbacks = []

    def set_filter_slot(self, slot_func):
        self.filters_callbacks.append(slot_func)
    
    def set_thinning_slot(self, slot_func):
        self.thinning_callbacks.append(slot_func)

    def prepare_filters(self, filter_type):
        params = {}
        if filter_type == 'median':
            params['window'] = int(self.filt_window.spin_median.value())
        elif filter_type == 'average':
            params['window'] = int(self.filt_window.spin_average.value())
        elif filter_type == 'exp_mean':
            params['alpha'] = float(self.filt_window.spin_exp_mean.value())
        elif filter_type == 'thinning':
            params['percent'] = int(self.filt_window.spin_thinning.value())
            params['uniform'] = self.filt_window.check_uniform.isChecked()
            params['max'] = self.filt_window.check_max.isChecked()
            params['min'] = self.filt_window.check_min.isChecked()
            params['first'] = self.filt_window.check_first.isChecked()
            params['last'] = self.filt_window.check_last.isChecked()
        elif filter_type == 'normalize':
            params['norm_type'] = self.filt_window.combo_norm_type.currentText()
        else:
            logger.error(f"Unknown filter type: {filter_type}")

        filter_command = FilterCommand(filter_type=filter_type, params=params, filters_instance=self)

        for callback in self.filters_callbacks:
            callback(filter_command)
    
    def med_filt(self, x: Union[list, np.ndarray], y: Union[list, np.ndarray], window: int) -> Tuple[np.ndarray, np.ndarray, str]:
        """
        Применяет медианный фильтр к входным данным.
        
        Функция создает скользящее окно размера `window` вокруг каждого элемента 
        входных данных `y` и вычисляет медианное значение в пределах окна. 
        Для обработки границ используется заполнение граничными значениями исходных данных.
        
        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных для фильтрации
            
        Возвращает:
            Кортеж из трех элементов:
            - X-координаты отфильтрованных данных
            - Y-координаты отфильтрованных данных
            - Описание примененного фильтра
        """

        k2 = (window - 1) // 2
        data_y = np.zeros ((len (y), window), dtype=y.dtype)
        data_y[:,k2] = y
        for i in range (k2):
            j = k2 - i
            data_y[j:,i] = y[:-j]
            data_y[:j,i] = y[0]
            data_y[:-j,-(i+1)] = y[j:]
            data_y[-j:,-(i+1)] = y[-1]

        data_y_ret = np.median(data_y, axis=1)
        x_data = x[-len(data_y_ret):]
        return x_data, data_y_ret, QApplication.translate("GraphWindow","Медиана({})").format(window)

    def exp_mean_filt(self, x: Union[list, np.ndarray], y: Union[list, np.ndarray], alpha: float) -> Tuple[np.ndarray, np.ndarray, str]:
        """
        Применяет экспоненциальное скользящее среднее к входным данным.
        
        Использует метод экспоненциального взвешивания, где более свежим данным 
        присваивается больший вес. Коэффициент α определяет скорость забывания 
        старых значений.
        
        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных для фильтрации
            
        Возвращает:
            Кортеж из трех элементов:
            - X-координаты отфильтрованных данных
            - Y-координаты отфильтрованных данных
            - Описание примененного фильтра
        """
        data_y = y
        data_y = pd.Series(data_y)
        ema = data_y.ewm(alpha=alpha, adjust=False).mean()

        ema_array = ema.to_numpy()


        x_data = x[-len(ema_array):]

        return x_data, ema_array, QApplication.translate("GraphWindow", "экспоненциальное среднее(alpha = {})").format( round(alpha, 2) )

    def calman_filt(self, data):
        return data

    def average_filt(self, x: Union[list, np.ndarray], y: Union[list, np.ndarray], window: int) -> Tuple[np.ndarray, np.ndarray, str]:
        """
        Применяет фильтр скользящего среднего к входным данным.
        
        Выполняет свертку данных с ядром усреднения для сглаживания сигнала.
        Режим 'valid' возвращает только те участки, где свертка определена полностью.
        
        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных для фильтрации
            
        Возвращает:
            Кортеж из трех элементов:
            - X-координаты отфильтрованных данных
            - Y-координаты отфильтрованных данных
            - Описание примененного фильтра
        """
        N = window
        y_data = np.convolve(y, np.ones(N)/N, 'valid')
        x_data = x[-len(y_data):]

        return x_data, y_data, QApplication.translate("GraphWindow","Скользящее среднее({})").format(window)
    
    def _apply_uniform_thinning(self, x: np.ndarray, y: np.ndarray, percent: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Равномерное прореживание - удаление каждой N-ой точки.
        
        Сохраняет общую форму сигнала, равномерно распределяя оставшиеся точки.
        
        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных
            percent: процент удаляемых точек
            
        Возвращает:
            Кортеж из X и Y координат после прореживания
        """
        if percent <= 0 or percent >= 100:
            return x.copy(), y.copy()
        
        n_points = len(y)
        if n_points == 0:
            return x.copy(), y.copy()
        
        keep_ratio = (100 - percent) / 100
        n_keep = int(round(n_points * keep_ratio))
        
        if n_keep >= n_points:
            return x.copy(), y.copy()
        if n_keep <= 0:
            return np.array([]), np.array([])
        
        indices = np.linspace(0, n_points - 1, n_keep, dtype=int)
        
        return x[indices], y[indices]
    
    def _apply_max_thinning(self, x: np.ndarray, y: np.ndarray, percent: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Удаление максимальных значений.
        
        Удаляет заданный процент точек с наибольшими значениями Y.
        Полезно для удаления положительных выбросов.
        
        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных
            percent: процент удаляемых точек
            
        Возвращает:
            Кортеж из X и Y координат после прореживания
        """
        if percent <= 0 or percent >= 100:
            return x.copy(), y.copy()
        
        n_to_remove = int(len(y) * percent / 100)
        if n_to_remove == 0:
            return x.copy(), y.copy()
        
        max_indices = np.argsort(-y)[:n_to_remove]
        
        mask = np.ones(len(y), dtype=bool)
        mask[max_indices] = False
        
        return x[mask], y[mask]
    
    def _apply_min_thinning(self, x: np.ndarray, y: np.ndarray, percent: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Удаление минимальных значений.
        
        Удаляет заданный процент точек с наименьшими значениями Y.
        Полезно для удаления отрицательных выбросов.
        
        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных
            percent: процент удаляемых точек
            
        Возвращает:
            Кортеж из X и Y координат после прореживания
        """
        if percent <= 0 or percent >= 100:
            return x.copy(), y.copy()
        
        n_to_remove = int(len(y) * percent / 100)
        if n_to_remove == 0:
            return x.copy(), y.copy()
        
        min_indices = np.argsort(y)[:n_to_remove]
        
        mask = np.ones(len(y), dtype=bool)
        mask[min_indices] = False
        
        return x[mask], y[mask]
    
    def _apply_first_thinning(self, x: np.ndarray, y: np.ndarray, percent: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Удаление первых процентов точек (по индексу).
        percent – процент от текущего размера данных.
        """
        if percent <= 0 or percent >= 100:
            return x.copy(), y.copy()
        n_points = len(y)
        n_to_remove = int(n_points * percent / 100)
        if n_to_remove == 0:
            return x.copy(), y.copy()
        # оставляем все, начиная с индекса n_to_remove
        return x[n_to_remove:], y[n_to_remove:]

    def _apply_last_thinning(self, x: np.ndarray, y: np.ndarray, percent: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Удаление последних процентов точек (по индексу).
        """
        if percent <= 0 or percent >= 100:
            return x.copy(), y.copy()
        n_points = len(y)
        n_to_remove = int(n_points * percent / 100)
        if n_to_remove == 0:
            return x.copy(), y.copy()
        # оставляем все до последних n_to_remove
        return x[:-n_to_remove], y[:-n_to_remove]

    def thinning_filt(self, x: Union[list, np.ndarray], y: Union[list, np.ndarray], percent: float,
                uniform: bool, max: bool, min: bool, first: bool, last: bool) -> Tuple[np.ndarray, np.ndarray, str]:
        """
        Применяет прореживание данных с учётом выбранных методов.
        Порядок применения: равномерно -> макс -> мин -> первые -> последние.
        """
        if percent == 0:
            return np.array(x).copy(), np.array(y).copy(), "Без прореживания"
        
        x_array = np.array(x)
        y_array = np.array(y)
        
        methods = []
        desc_methods = []
        if uniform:
            methods.append('uniform')
            desc_methods.append('равномерное')
        if max:
            methods.append('max')
            desc_methods.append('максимальное')
        if min:
            methods.append('min')
            desc_methods.append('минимальное')
        if first:
            methods.append('first')
            desc_methods.append('первые')
        if last:
            methods.append('last')
            desc_methods.append('последние')

        if not methods:
            return x_array.copy(), y_array.copy(), "Без прореживания"
        
        percent_per_method = percent / len(methods)
        
        current_x, current_y = x_array.copy(), y_array.copy()
        
        for method in methods:
            if len(current_y) == 0:
                break
                
            if method == 'uniform':
                current_x, current_y = self._apply_uniform_thinning(current_x, current_y, percent_per_method)
            elif method == 'max':
                current_x, current_y = self._apply_max_thinning(current_x, current_y, percent_per_method)
            elif method == 'min':
                current_x, current_y = self._apply_min_thinning(current_x, current_y, percent_per_method)
            elif method == 'first':
                current_x, current_y = self._apply_first_thinning(current_x, current_y, percent_per_method)
            elif method == 'last':
                current_x, current_y = self._apply_last_thinning(current_x, current_y, percent_per_method)
        
        description = f"Прореживание {percent}% ({', '.join(desc_methods)})"
        return current_x, current_y, description
    
    def normalize_filt(self, x: Union[list, np.ndarray], y: Union[list, np.ndarray], norm_type: str) -> Tuple[np.ndarray, np.ndarray, str]:
        """
        Применяет нормировку данных к выбранному диапазону.
        
        Доступные типы нормировки:
        1. 0-1 (Min-Max): приведение к диапазону [0, 1]
        2. -1-1: приведение к диапазону [-1, 1]
        3. Z-score: стандартизация (среднее=0, стандартное отклонение=1)
        4. Robust: устойчивая нормировка на основе медианы и межквартильного размаха
        
        Параметры:
            x: X-координаты данных
            y: Y-координаты данных
            
        Возвращает:
            Tuple[np.ndarray, np.ndarray, str]: Нормированные x, y и описание
        """
        x_array = np.array(x)
        y_array = np.array(y)
        
        if len(y_array) == 0:
            return x_array.copy(), y_array.copy(), "Нормировка: нет данных"
        
        
        if norm_type == "0-1 (Min-Max)":
            y_min = np.min(y_array)
            y_max = np.max(y_array)
            
            if y_max == y_min:
                y_norm = np.zeros_like(y_array) if y_min == 0 else np.ones_like(y_array) * 0.5
            else:
                y_norm = (y_array - y_min) / (y_max - y_min)
            
            description = f"Нормировка [0,1] (min={y_min:.3f}, max={y_max:.3f})"
            
        elif norm_type == "-1-1":
            y_min = np.min(y_array)
            y_max = np.max(y_array)
            
            if y_max == y_min:
                y_norm = np.zeros_like(y_array)
            else:
                y_norm = 2 * ((y_array - y_min) / (y_max - y_min)) - 1
            
            description = f"Нормировка [-1,1] (min={y_min:.3f}, max={y_max:.3f})"
            
        elif norm_type == "Z-score":
            y_mean = np.mean(y_array)
            y_std = np.std(y_array)
            
            if y_std == 0:
                y_norm = np.zeros_like(y_array)
            else:
                y_norm = (y_array - y_mean) / y_std
            
            description = f"Z-score (mean={y_mean:.3f}, std={y_std:.3f})"
            
        elif norm_type == "Robust (медиана/IQR)":
            y_median = np.median(y_array)
            q75, q25 = np.percentile(y_array, [75, 25])
            iqr = q75 - q25
            
            if iqr == 0:
                y_std = np.std(y_array)
                if y_std == 0:
                    y_norm = np.zeros_like(y_array)
                else:
                    y_norm = (y_array - y_median) / y_std
                description = f"Robust (медиана={y_median:.3f}, std={y_std:.3f})"
            else:
                y_norm = (y_array - y_median) / iqr
                description = f"Robust (медиана={y_median:.3f}, IQR={iqr:.3f})"
        else:
            y_norm = y_array.copy()
            description = f"Нормировка: неизвестный тип '{norm_type}'"
        
        return x_array, y_norm, description

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    
    widget = filtersClass()
    widget.filt_window.setWindowTitle("Фильтры данных")
    widget.filt_window.show()
    sys.exit(app.exec_())