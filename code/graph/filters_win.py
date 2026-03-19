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
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QApplication, QDoubleSpinBox, QHBoxLayout, QLabel,
                             QPushButton, QSpinBox, QVBoxLayout, QWidget,
                             QCheckBox, QGroupBox, QToolTip, QComboBox)

class filterWin(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()

        self.median_button   = QPushButton("Применить")
        self.average_button  = QPushButton("Применить")
        self.calman_button   = QPushButton("Применить")
        self.exp_mean_button = QPushButton("Применить")
        self.thinning_button = QPushButton("Применить прореживание")
        self.normalize_button = QPushButton("Применить нормировку")

        self.median_button.setToolTip(self.get_median_description())
        self.average_button.setToolTip(self.get_average_description())
        self.exp_mean_button.setToolTip(self.get_exp_mean_description())
        self.thinning_button.setToolTip(self.get_thinning_description())
        self.normalize_button.setToolTip(self.get_normalize_description())

        self.median_button.setMinimumSize(30, 20)
        self.average_button.setMinimumSize(30, 20)
        self.calman_button.setMinimumSize(30, 20)
        self.exp_mean_button.setMinimumSize(30, 20)
        self.thinning_button.setMinimumSize(30, 20)
        self.normalize_button.setMinimumSize(30, 20)

        self.spin_median   = QSpinBox() 
        self.spin_average  = QSpinBox()
        self.spin_calman   = QSpinBox()
        self.spin_calman2  = QSpinBox()
        self.spin_exp_mean = QDoubleSpinBox()
        self.spin_thinning = QSpinBox()

        self.spin_calman.setMaximum(10)
        self.spin_calman2.setMaximum(10)
        self.spin_exp_mean.setMaximum(1)
        self.spin_thinning.setRange(0, 100)
        self.spin_thinning.setSuffix("%")

        self.spin_exp_mean.setSingleStep(0.01)

        self.check_uniform = QCheckBox("Равномерно")
        self.check_max = QCheckBox("Удалить максимальные")
        self.check_min = QCheckBox("Удалить минимальные")
        # NEW: чекбоксы для удаления первых и последних процентов по индексу
        self.check_first = QCheckBox("Удалить первые %")
        self.check_last  = QCheckBox("Удалить последние %")

        self.combo_norm_type = QComboBox()
        self.combo_norm_type.addItem("0-1 (Min-Max)")
        self.combo_norm_type.addItem("-1-1")
        self.combo_norm_type.addItem("Z-score")
        self.combo_norm_type.addItem("Robust (медиана/IQR)")
        
        self.check_uniform.setToolTip(self.get_uniform_thinning_description())
        self.check_max.setToolTip(self.get_max_thinning_description())
        self.check_min.setToolTip(self.get_min_thinning_description())
        # NEW: тултипы для новых чекбоксов
        self.check_first.setToolTip(self.get_first_thinning_description())
        self.check_last.setToolTip(self.get_last_thinning_description())
        self.combo_norm_type.setToolTip(self.get_norm_type_description())

        main_layout.addLayout(self.create_layer_filter(
            QApplication.translate("filters", "Медианный фильтр"), 
            [self.create_spin_box("Окно", self.spin_median)],
            self.median_button,
            self.get_median_description()
        ))
        
        main_layout.addLayout(self.create_layer_filter(
            QApplication.translate("filters", "Бегущее среднее"), 
            [self.create_spin_box("Окно", self.spin_average)],
            self.average_button,
            self.get_average_description()
        ))
        
        main_layout.addLayout(self.create_layer_filter(
            QApplication.translate("filters", "Экспоненциальное \n среднее"),
            [self.create_spin_box("Коэфф", self.spin_exp_mean)],
            self.exp_mean_button,
            self.get_exp_mean_description()
        ))
        
        thinning_group = QGroupBox("Прореживание данных")
        thinning_group.setToolTip(self.get_thinning_group_description())
        thinning_layout = QVBoxLayout()
        
        percent_layout = QHBoxLayout()
        percent_label = QLabel("Процент удаления:")
        percent_layout.addWidget(percent_label)
        percent_layout.addWidget(self.spin_thinning)
        percent_layout.addStretch()
        thinning_layout.addLayout(percent_layout)
        
        thinning_layout.addWidget(self.check_uniform)
        thinning_layout.addWidget(self.check_max)
        thinning_layout.addWidget(self.check_min)
        # NEW: добавляем новые чекбоксы
        thinning_layout.addWidget(self.check_first)
        thinning_layout.addWidget(self.check_last)
        self.check_uniform.setChecked(True)
        
        thinning_layout.addWidget(self.thinning_button)
        thinning_group.setLayout(thinning_layout)
        main_layout.addWidget(thinning_group)
        
        norm_group = QGroupBox("Нормировка данных")
        norm_group.setToolTip(self.get_normalize_group_description())
        norm_layout = QVBoxLayout()
        
        type_layout = QHBoxLayout()
        type_label = QLabel("Тип нормировки:")
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.combo_norm_type)
        type_layout.addStretch()
        norm_layout.addLayout(type_layout)
        
        norm_layout.addWidget(self.normalize_button)
        norm_group.setLayout(norm_layout)
        main_layout.addWidget(norm_group)

        self.setLayout(main_layout)

        self.setStyleSheet("""
                            QToolTip {
                            color: #000000;
                            background-color: #f0f0f0;
                            border: 2px solid #cccccc;
                            padding: 5px;
                            border-radius: 3px;
                            opacity: 240;
                            }
                            """)

    def create_spin_box(self, label, spinbox):
        spin_widget = QWidget()
        lay = QVBoxLayout(spin_widget)
        lay.setContentsMargins(0, 0, 0, 0)
        spinbox.setMaximumSize(50, 20)
        label_widget = QLabel(label)
        lay.addWidget(label_widget)
        lay.addWidget(spinbox)
        return spin_widget

    def create_layer_filter(self, filter_name, spinboxes, button, description):
        filter_layout = QVBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_label = QLabel(filter_name)
        filter_label.setAlignment(Qt.AlignCenter)
        filter_label.setToolTip(description)
        filter_layout.addWidget(filter_label)
        font = QFont('Arial', 10, QFont.Bold)
        filter_label.setFont(font)
        parameter_layout = QHBoxLayout()
        parameter_layout.setContentsMargins(0, 0, 0, 0)
        parameter_layout.setSpacing(0)
        for spin in spinboxes:
            parameter_layout.addWidget(spin)
        filter_layout.addLayout(parameter_layout)
        filter_layout.addWidget(button)
        return filter_layout

    def get_median_description(self):
        return QApplication.translate("filters",
            "Медианный фильтр - нелинейный метод фильтрации, который заменяет каждое значение в сигнале медианой значений в скользящем окне заданного размера.\n\n"
            "Принцип работы:\n"
            "1. Для каждой точки данных создается окно из соседних значений\n"
            "2. Все значения в окне сортируются по возрастанию\n"
            "3. В качестве отфильтрованного значения берется медиана (среднее значение в отсортированном списке)\n\n"
            "Преимущества:\n"
            "• Эффективно удаляет импульсные шумы (выбросы)\n"
            "• Сохраняет резкие перепады сигнала (ступенчатые изменения)\n"
            "• Устойчив к экстремальным значениям\n\n"
            "Рекомендуется для: удаления одиночных выбросов, обработки сигналов с импульсными помехами"
        )
    
    def get_first_thinning_description(self):
        return QApplication.translate("filters",
            "Удаление первых процентов данных – удаляет указанный процент точек с начала массива.\n\n"
            "Точки удаляются по индексу, независимо от их значений.\n"
            "Полезно, например, для отбрасывания начальных нестационарных участков сигнала."
        )

    def get_last_thinning_description(self):
        return QApplication.translate("filters",
            "Удаление последних процентов данных – удаляет указанный процент точек с конца массива.\n\n"
            "Точки удаляются по индексу, независимо от их значений.\n"
            "Может использоваться для обрезания хвоста записи."
        )
    
    def get_average_description(self):
        return QApplication.translate("filters",
            "Фильтр скользящего среднего (бегущее среднее) - линейный метод сглаживания данных путем усреднения значений в скользящем окне.\n\n"
            "Принцип работы:\n"
            "1. Для каждой точки данных создается окно из соседних значений\n"
            "2. Вычисляется среднее арифметическое всех значений в окне\n"
            "3. Это среднее становится новым значением для центральной точки окна\n\n"
            "Характеристики:\n"
            "• Размер окна определяет степень сглаживания (большее окно = большее сглаживание)\n"
            "• Уменьшает высокочастотный шум\n"
            "• Может вызывать фазовые задержки и сглаживание резких изменений\n"
            "• Простота реализации и низкие вычислительные затраты\n\n"
            "Рекомендуется для: плавного сглаживания данных, удаления высокочастотного шума"
        )
    
    def get_exp_mean_description(self):
        return QApplication.translate("filters",
            "Экспоненциальное скользящее среднее (EMA) - рекурсивный фильтр, который присваивает больший вес последним наблюдениям.\n\n"
            "Принцип работы:\n"
            "• Новое значение = α * текущее_измерение + (1-α) * предыдущее_отфильтрованное_значение\n"
            "• Коэффициент α (0 < α ≤ 1) определяет скорость забывания старых значений\n"
            "• Большее α = больше вес текущих измерений, меньшее сглаживание\n"
            "• Меньшее α = больше сглаживание, но больше задержка\n\n"
            "Особенности:\n"
            "• Требует меньше памяти (хранит только предыдущее значение)\n"
            "• Более чувствителен к последним изменениям\n"
            "• Эффективно для онлайн-обработки данных в реальном времени\n"
            "• Не требует буферизации данных\n\n"
            "Рекомендуется для: потоковой обработки данных, адаптивного сглаживания"
        )
    
    def get_thinning_description(self):
        return QApplication.translate("filters",
            "Прореживание данных - метод уменьшения количества точек данных путем выборочного удаления части из них.\n\n"
            "Применение:\n"
            "• Уменьшение объема данных для хранения или передачи\n"
            "• Ускорение обработки и визуализации\n"
            "• Удаление выбросов и аномальных значений\n\n"
            "Доступные методы:\n"
            "1. Равномерное прореживание - удаление точек с постоянным шагом\n"
            "2. Удаление максимальных - удаление точек с наибольшими значениями\n"
            "3. Удаление минимальных - удаление точек с наименьшими значениями\n\n"
            "Методы можно комбинировать. Приоритет выполнения: равномерно → максимальные → минимальные."
        )
    
    def get_thinning_group_description(self):
        return QApplication.translate("filters",
            "Группа параметров для прореживания данных\n\n"
            "Прореживание позволяет уменьшить количество точек данных путем выборочного удаления.\n"
            "Это полезно для:\n"
            "• Уменьшения объема данных\n"
            "• Снижения вычислительной нагрузки\n"
            "• Уменьшения времени отрисовки графиков\n"
            "• Удаления статистических выбросов\n\n"
            "Выберите метод(ы) прореживания и укажите процент удаляемых точек."
        )
    
    def get_uniform_thinning_description(self):
        return QApplication.translate("filters",
            "Равномерное прореживание - удаление точек данных через равные интервалы.\n\n"
            "Пример:\n"
            "• При 20% удаления будет удалена каждая пятая точка\n"
            "• При 33% удаления будет удалена каждая третья точка\n\n"
            "Преимущества:\n"
            "• Сохраняет общую форму сигнала\n"
            "• Простота реализации\n"
            "• Равномерное распределение оставшихся точек\n\n"
            "Недостатки:\n"
            "• Может пропускать важные особенности сигнала\n"
            "• Не учитывает значения точек"
        )
    
    def get_max_thinning_description(self):
        return QApplication.translate("filters",
            "Удаление максимальных значений - удаление заданного процента точек с наибольшими значениями.\n\n"
            "Применение:\n"
            "• Удаление положительных выбросов\n"
            "• Ограничение диапазона данных\n"
            "• Подготовка данных для алгоритмов, чувствительных к максимумам\n\n"
            "Особенности:\n"
            "• Может искажать пиковые значения сигнала\n"
            "• Полезно для данных с асимметричным распределением\n"
            "• Не сохраняет форму сигнала в области максимумов"
        )
    
    def get_min_thinning_description(self):
        return QApplication.translate("filters",
            "Удаление минимальных значений - удаление заданного процента точек с наименьшими значениями.\n\n"
            "Применение:\n"
            "• Удаление отрицательных выбросов\n"
            "• Игнорирование фонового шума\n"
            "• Подготовка данных для алгоритмов, чувствительных к минимумам\n\n"
            "Особенности:\n"
            "• Может искажать минимальные значения сигнала\n"
            "• Полезно для данных с асимметричным распределением\n"
            "• Не сохраняет форму сигнала в области минимумов"
        )
    
    # Новые описания для нормировки (добавлено)
    def get_normalize_description(self):
        return QApplication.translate("filters",
            "Нормировка данных - преобразование данных к стандартному диапазону значений.\n\n"
            "Применение:\n"
            "• Подготовка данных для машинного обучения\n"
            "• Сравнение сигналов с разными амплитудами\n"
            "• Улучшение сходимости алгоритмов\n"
            "• Визуализация данных в едином масштабе\n\n"
            "Доступные методы:\n"
            "1. 0-1 (Min-Max) - приведение к диапазону [0, 1]\n"
            "2. -1-1 - приведение к диапазону [-1, 1]\n"
            "3. Z-score - стандартизация (среднее=0, std=1)\n"
            "4. Robust - устойчивая нормировка на основе медианы и IQR\n\n"
            "Нормировка применяется только к значениям Y (данным), X-координаты остаются без изменений."
        )
    
    def get_normalize_group_description(self):
        return QApplication.translate("filters",
            "Группа параметров для нормировки данных\n\n"
            "Нормировка (стандартизация) преобразует данные к определенному диапазону значений.\n"
            "Это полезно для:\n"
            "• Машинного обучения и нейронных сетей\n"
            "• Сравнения сигналов разной амплитуды\n"
            "• Ускорения сходимости градиентных методов\n"
            "• Устранения влияния масштаба на анализ данных\n"
        )
    
    def get_norm_type_description(self):
        return QApplication.translate("filters",
            "Выбор типа нормировки:\n\n"
            "1. 0-1 (Min-Max):\n"
            "   • Диапазон: [0, 1]\n"
            "   • Формула: (x - min) / (max - min)\n"
            "   • Чувствителен к выбросам\n\n"
            "2. -1-1:\n"
            "   • Диапазон: [-1, 1]\n"
            "   • Формула: 2*(x - min)/(max - min) - 1\n"
            "   • Сохраняет знак исходных отклонений\n\n"
            "3. Z-score:\n"
            "   • Среднее = 0, Стандартное отклонение = 1\n"
            "   • Формула: (x - mean) / std\n"
            "   • Хорош для данных с нормальным распределением\n\n"
            "4. Robust (медиана/IQR):\n"
            "   • На основе медианы и межквартильного размаха\n"
            "   • Устойчив к выбросам\n"
            "   • Формула: (x - median) / IQR\n"
        )

class filtersClass():
    def __init__(self):
        self.filters_callbacks = []
        self.thinning_callbacks = []
        self.filt_window = filterWin()

        self.filt_window.median_button.clicked.connect( lambda: self.prepare_filters(self.med_filt) )
        self.filt_window.average_button.clicked.connect( lambda: self.prepare_filters(self.average_filt) )      
        self.filt_window.calman_button.clicked.connect( lambda: self.prepare_filters(self.calman_filt) )
        self.filt_window.exp_mean_button.clicked.connect( lambda: self.prepare_filters(self.exp_mean_filt) )
        self.filt_window.thinning_button.clicked.connect( lambda: self.prepare_filters(self.thinning_filt) )
        self.filt_window.normalize_button.clicked.connect( lambda: self.prepare_filters(self.normalize_filt) )

    def set_filter_slot(self, slot_func):
        self.filters_callbacks.append(slot_func)
    
    def set_thinning_slot(self, slot_func):
        self.thinning_callbacks.append(slot_func)

    def prepare_filters(self, func):
        self.range_avg = int(self.filt_window.spin_average.value())
        self.range_median = int(self.filt_window.spin_median.value())
        self.alpha_exp = float(self.filt_window.spin_exp_mean.value())
        self.thinning_percent = int(self.filt_window.spin_thinning.value())
        self.thinning_uniform = self.filt_window.check_uniform.isChecked()
        self.thinning_max = self.filt_window.check_max.isChecked()
        self.thinning_min = self.filt_window.check_min.isChecked()
        self.thinning_first = self.filt_window.check_first.isChecked()
        self.thinning_last = self.filt_window.check_last.isChecked()
        
        self.norm_type = self.filt_window.combo_norm_type.currentText()

        for callback in self.filters_callbacks:
            callback(func)
    
    def med_filt(self, x: Union[list, np.ndarray], y: Union[list, np.ndarray]) -> Tuple[np.ndarray, np.ndarray, str]:
        """
        Применяет медианный фильтр к входным данным.
        
        Функция создает скользящее окно размера `self.range_median` вокруг каждого элемента 
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
        k2 = (self.range_median - 1) // 2
        data_y = np.zeros ((len (y), self.range_median), dtype=y.dtype)
        data_y[:,k2] = y
        for i in range (k2):
            j = k2 - i
            data_y[j:,i] = y[:-j]
            data_y[:j,i] = y[0]
            data_y[:-j,-(i+1)] = y[j:]
            data_y[-j:,-(i+1)] = y[-1]

        data_y_ret = np.median(data_y, axis=1)
        x_data = x[-len(data_y_ret):]
        return x_data, data_y_ret, QApplication.translate("GraphWindow","Медиана({})").format(self.range_median)

    def exp_mean_filt(self, x: Union[list, np.ndarray], y: Union[list, np.ndarray]) -> Tuple[np.ndarray, np.ndarray, str]:
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
        ema = data_y.ewm(alpha=self.alpha_exp, adjust=False).mean()

        ema_array = ema.to_numpy()


        x_data = x[-len(ema_array):]

        return x_data, ema_array, QApplication.translate("GraphWindow", "экспоненциальное среднее(alpha = {})").format( round(self.alpha_exp, 2) )

    def calman_filt(self, data):
        return data

    def average_filt(self, x: Union[list, np.ndarray], y: Union[list, np.ndarray]) -> Tuple[np.ndarray, np.ndarray, str]:
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
        N = self.range_avg
        y_data = np.convolve(y, np.ones(N)/N, 'valid')
        x_data = x[-len(y_data):]

        return x_data, y_data, QApplication.translate("GraphWindow","Скользящее среднее({})").format(N) #same #full #valid
    
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

    def thinning_filt(self, x: Union[list, np.ndarray], y: Union[list, np.ndarray]) -> Tuple[np.ndarray, np.ndarray, str]:
        """
        Применяет прореживание данных с учётом выбранных методов.
        Порядок применения: равномерно -> макс -> мин -> первые -> последние.
        """
        if self.thinning_percent == 0:
            return np.array(x).copy(), np.array(y).copy(), "Без прореживания"
        
        x_array = np.array(x)
        y_array = np.array(y)
        
        # Формируем список методов в нужном порядке
        methods = []
        if self.thinning_uniform:
            methods.append('uniform')
        if self.thinning_max:
            methods.append('max')
        if self.thinning_min:
            methods.append('min')
        if self.thinning_first:      # NEW
            methods.append('first')
        if self.thinning_last:       # NEW
            methods.append('last')

        if not methods:
            return x_array.copy(), y_array.copy(), "Без прореживания"
        
        percent_per_method = self.thinning_percent / len(methods)
        
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
            elif method == 'first':      # NEW
                current_x, current_y = self._apply_first_thinning(current_x, current_y, percent_per_method)
            elif method == 'last':       # NEW
                current_x, current_y = self._apply_last_thinning(current_x, current_y, percent_per_method)
        
        desc_methods = []
        if self.thinning_uniform:
            desc_methods.append("равномерно")
        if self.thinning_max:
            desc_methods.append("макс")
        if self.thinning_min:
            desc_methods.append("мин")
        if self.thinning_first:          # NEW
            desc_methods.append("первые")
        if self.thinning_last:           # NEW
            desc_methods.append("последние")
        
        description = f"Прореживание {self.thinning_percent}% ({', '.join(desc_methods)})"
        return current_x, current_y, description
    
    def normalize_filt(self, x: Union[list, np.ndarray], y: Union[list, np.ndarray]) -> Tuple[np.ndarray, np.ndarray, str]:
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
        
        norm_type = self.norm_type
        
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

def show_tooltip_example():
    app = QApplication([])
    
    window = filterWin()
    
    window.setWindowTitle("Фильтры данных с подробными описаниями")
    window.show()
    
    QToolTip.setFont(QFont('Arial', 10))
    QToolTip.setStyleSheet("""
        QToolTip {
            background-color: #f0f0f0;
            color: #000000;
            border: 2px solid #cccccc;
            padding: 5px;
            border-radius: 3px;
            opacity: 240;
            max-width: 600px;
        }
    """)
    
    app.exec_()

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    
    widget = filtersClass()
    widget.filt_window.setWindowTitle("Фильтры данных")
    widget.filt_window.show()
    sys.exit(app.exec_())