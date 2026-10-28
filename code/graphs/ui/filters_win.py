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
from graphs.core.filters_instance_class import FilterCommand
import logging
from scipy.signal import iirnotch, filtfilt, savgol_filter, butter
from scipy.ndimage import gaussian_filter1d

logger = logging.getLogger(__name__)

class filtersClass():
    def __init__(self):
        self.filters_callbacks = []

    def set_filter_slot(self, slot_func):
        self.filters_callbacks.append(slot_func)
    
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

    def hampel_filt(self, x, y, window, n_sigmas=3.0):
        """
        Фильтр Хампеля для удаления выбросов.

        Заменяет точки, отклоняющиеся от медианы окна более чем на
        n_sigmas робастных стандартных отклонений (MAD * 1.4826),
        на медиану окна. Не искажает остальной сигнал.

        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных
            window: размер окна (нечётное число >= 3)
            n_sigmas: порог в робастных сигмах

        Возвращает:
            Кортеж (x, y_filtered, описание)
        """
        x_arr = np.asarray(x)
        y_arr = np.asarray(y, dtype=float)
        window = int(window)
        if window < 3:
            window = 3
        if window % 2 == 0:
            window += 1
        n = len(y_arr)
        if n < window:
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Hampel: мало данных")
        half = window // 2
        k = 1.4826
        y_out = y_arr.copy()
        for i in range(n):
            lo = max(0, i - half)
            hi = min(n, i + half + 1)
            seg = y_arr[lo:hi]
            med = np.median(seg)
            mad = np.median(np.abs(seg - med))
            if mad == 0:
                continue
            threshold = float(n_sigmas) * k * mad
            if abs(y_arr[i] - med) > threshold:
                y_out[i] = med
        return x_arr, y_out, QApplication.translate("GraphWindow", "Hampel({}, {}σ)").format(window, n_sigmas)

    def savitzky_golay_filt(self, x, y, window, polyorder):
        """
        Сглаживание Савицкого-Голея.

        Аппроксимирует данные полиномом заданной степени в скользящем
        окне. Не даёт sinc-лепестков и сохраняет форму пиков.

        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных
            window: длина окна (нечётное число >= 3)
            polyorder: степень полинома

        Возвращает:
            Кортеж (x, y_filtered, описание)
        """
        x_arr = np.asarray(x)
        y_arr = np.asarray(y, dtype=float)
        window = int(window)
        polyorder = int(polyorder)
        if window < 3:
            window = 3
        if window % 2 == 0:
            window += 1
        n = len(y_arr)
        if n < window:
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Savitzky-Golay: мало данных")
        if polyorder >= window:
            polyorder = window - 1
        if polyorder < 1:
            polyorder = 1
        try:
            y_out = savgol_filter(y_arr, window, polyorder)
            return x_arr, y_out, QApplication.translate("GraphWindow", "Savitzky-Golay({}, {})").format(window, polyorder)
        except Exception as e:
            logger.error(f"savitzky_golay_filt failed: {e}")
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Savitzky-Golay: ошибка")

    def detrend_filt(self, x, y, detrend_type='linear', polyorder=1):
        """
        Удаление тренда (детрендинг).

        Вычитает из данных полиномиальный тренд заданной степени.
        Устраняет дрейф и низкочастотные «пучности» в спектре.

        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных
            detrend_type: 'linear' или 'poly'
            polyorder: степень полинома для 'poly'

        Возвращает:
            Кортеж (x, y_detrended, описание)
        """
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        n = len(y_arr)
        if n < 2:
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Детренд: мало данных")
        if detrend_type == 'linear':
            order = 1
        else:
            order = max(1, int(polyorder))
        if order >= n:
            order = n - 1
        coeffs = np.polyfit(x_arr, y_arr, order)
        trend = np.polyval(coeffs, x_arr)
        y_out = y_arr - trend
        return x_arr, y_out, QApplication.translate("GraphWindow", "Детренд(order={})").format(order)

    def butterworth_filt(self, x, y, cutoff, btype='low', order=4):
        """
        Фильтр Баттерворта (low/high/band) с zero-phase через filtfilt.

        Даёт гладкую АЧХ без лепестков; фаза не искажается.

        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных
            cutoff: частота среза в Гц (или кортеж (low, high) для band)
            btype: 'low', 'high' или 'band'
            order: порядок фильтра

        Возвращает:
            Кортеж (x, y_filtered, описание)
        """
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        n = len(y_arr)
        if n < 16:
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Butterworth: мало данных")
        dx = float(np.mean(np.diff(x_arr)))
        if dx <= 0:
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Butterworth: некорректный шаг X")
        fs = 1.0 / dx
        nyq = 0.5 * fs
        try:
            order = max(1, int(order))
            if btype == 'band':
                if isinstance(cutoff, (tuple, list)) and len(cutoff) == 2:
                    low, high = float(cutoff[0]), float(cutoff[1])
                    wn = [low / nyq, high / nyq]
                    if wn[0] <= 0 or wn[1] >= 1 or wn[0] >= wn[1]:
                        return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Butterworth: диапазон вне допустимого")
                else:
                    return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Butterworth: нужен диапазон")
            else:
                wn = float(cutoff) / nyq
                if wn <= 0 or wn >= 1:
                    return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Butterworth: частота среза вне диапазона")
            b, a = butter(order, wn, btype=btype)
            y_out = filtfilt(b, a, y_arr)
            return x_arr, y_out, QApplication.translate("GraphWindow", "Butterworth({}, {})").format(btype, order)
        except Exception as e:
            logger.error(f"butterworth_filt failed: {e}")
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Butterworth: ошибка")

    def notch_filt(self, x, y, freq=50.0, q=30.0):
        """
        Режекторный фильтр (notch) для подавления сетевой наводки.

        Вырожденный Butterworth bandstop с zero-phase.

        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных
            freq: подавляемая частота, Гц
            q: добротность (обычно 20–50)

        Возвращает:
            Кортеж (x, y_filtered, описание)
        """
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        n = len(y_arr)
        if n < 16:
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Notch: мало данных")
        dx = float(np.mean(np.diff(x_arr)))
        if dx <= 0:
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Notch: некорректный шаг X")
        fs = 1.0 / dx
        nyq = 0.5 * fs
        w0 = float(freq) / nyq
        if w0 <= 0 or w0 >= 1:
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Notch: частота вне диапазона")
        try:
            b, a = iirnotch(w0, float(q))
            y_out = filtfilt(b, a, y_arr)
            return x_arr, y_out, QApplication.translate("GraphWindow", "Notch({} Гц, Q={})").format(freq, q)
        except Exception as e:
            logger.error(f"notch_filt failed: {e}")
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Notch: ошибка")

    def gaussian_smooth_filt(self, x, y, window, sigma=None):
        """
        Гауссово сглаживание.

        То же, что скользящее среднее, но с гладкой АЧХ без боковых
        лепестков.

        Параметры:
            x: массив X-координат данных
            y: массив Y-координат данных
            window: размер окна (используется для оценки sigma)
            sigma: явное значение sigma (если None, берётся window/6)

        Возвращает:
            Кортеж (x, y_filtered, описание)
        """
        x_arr = np.asarray(x)
        y_arr = np.asarray(y, dtype=float)
        window = int(window)
        if window < 1:
            window = 1
        if sigma is None:
            sigma = window / 6.0
        sigma = float(sigma)
        if sigma <= 0:
            sigma = 1.0
        try:
            y_out = gaussian_filter1d(y_arr, sigma=sigma)
            return x_arr, y_out, QApplication.translate("GraphWindow", "Gaussian(σ={})").format(sigma)
        except Exception as e:
            logger.error(f"gaussian_smooth_filt failed: {e}")
            return x_arr.copy(), y_arr.copy(), QApplication.translate("GraphWindow", "Gaussian: ошибка")
        