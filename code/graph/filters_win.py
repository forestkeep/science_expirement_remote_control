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

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton, QDoubleSpinBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import pandas as pd
import numpy as np

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

        self.median_button.setMinimumSize(30, 20)
        self.average_button.setMinimumSize(30, 20)
        self.calman_button.setMinimumSize(30, 20)
        self.exp_mean_button.setMinimumSize(30, 20)

        self.spin_median   = QSpinBox() 
        self.spin_average  = QSpinBox()
        self.spin_calman   = QSpinBox()
        self.spin_calman2  = QSpinBox()
        self.spin_exp_mean = QDoubleSpinBox()

        self.spin_calman.setMaximum(10)
        self.spin_calman2.setMaximum(10)
        self.spin_exp_mean.setMaximum(1)

        self.spin_exp_mean.setSingleStep(0.01)

        main_layout.addLayout(self.create_layer_filter("Медианный фильтр", [self.create_spin_box("Окно", self.spin_median)],
                                                                            self.median_button) )
        
        main_layout.addLayout(self.create_layer_filter("Бегущее среднее", [self.create_spin_box("Окно", self.spin_average)],
                                                                           self.average_button) )
        '''
        main_layout.addLayout(self.create_layer_filter("Фильтр Калмана", [self.create_spin_box("Q", self.spin_calman),
                                                                          self.create_spin_box("R", self.spin_calman2)],
                                                                          self.calman_button) )
        '''
        main_layout.addLayout(self.create_layer_filter("Экспоненциальное \n среднее",
                                                        [self.create_spin_box("Коэфф", self.spin_exp_mean)],
                                                         self.exp_mean_button)  )

        self.setLayout(main_layout)

    def create_spin_box(self, label, spinbox):
        spin_widget = QWidget()
        lay = QVBoxLayout(spin_widget)

        lay.setContentsMargins(0, 0, 0, 0)

        spinbox.setMaximumSize(50, 20)
        label_widget = QLabel(label)

        lay.addWidget(label_widget)
        lay.addWidget(spinbox)

        return spin_widget

    def create_layer_filter(self, filter_name, spinboxes, button):
        filter_layout = QVBoxLayout()

        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        filter_label = QLabel(filter_name)
        filter_label.setAlignment(Qt.AlignCenter)
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

class filtersClass():
    def __init__(self):
        self.filters_callbacks = []
        self.filt_window = filterWin()


        self.filt_window.median_button.clicked.connect( lambda: self.prepare_filters(self.med_filt) )
        self.filt_window.average_button.clicked.connect( lambda: self.prepare_filters(self.average_filt) )      
        self.filt_window.calman_button.clicked.connect( lambda: self.prepare_filters(self.calman_filt) )
        self.filt_window.exp_mean_button.clicked.connect( lambda: self.prepare_filters(self.exp_mean_filt) )

    def set_filter_slot(self, slot_func):
        '''сюда передаются калбеки сигналов фильтров. При срабатывании какой-либо кнопки фильтра в эти калбеки будет передана ссылка на функцию фильтр'''
        self.filters_callbacks.append(slot_func)

    def prepare_filters(self, func):
        self.range_avg = int(self.filt_window.spin_average.value())
        self.range_median = int(self.filt_window.spin_median.value())
        self.alpha_exp = float(self.filt_window.spin_exp_mean.value())
        #TODO:reading coeff for filters
        for callback in self.filters_callbacks:
            callback(func)

    def med_filt(self, data):
        """
        Applies a median filter to the input data.

        This function constructs a sliding window of size `self.range_median` 
        around each element of the input `data`, and calculates the median 
        value within the window. The edges are padded using the border values 
        of the input data to handle incomplete windows at the boundaries.

        Parameters:
            data (array-like): The input array of data to be filtered.

        Returns:
            np.ndarray: The array of filtered data with the same length as the input data.
        """
        k2 = (self.range_median - 1) // 2
        y = np.zeros ((len (data), self.range_median), dtype=data.dtype)
        y[:,k2] = data
        for i in range (k2):
            j = k2 - i
            y[j:,i] = data[:-j]
            y[:j,i] = data[0]
            y[:-j,-(i+1)] = data[j:]
            y[-j:,-(i+1)] = data[-1]
        return np.median(y, axis=1)

    def exp_mean_filt(self, data):

        data = pd.Series(data)
        ema = data.ewm(alpha=self.alpha_exp, adjust=False).mean()
        return ema

    def calman_filt(self, data):
        return data

    def average_filt(self, data):
        N = self.range_avg

        return np.convolve(data, np.ones(N)/N, 'valid') #same #full #valid


def test_filters():
    import matplotlib.pyplot as plt
    np.random.seed(42)
    x = np.linspace(0, 10, 100)
    clean_data = np.sin(x)
    noise = np.random.normal(0, 0.5, size=x.shape)
    noisy_data = clean_data + noise

    filter_instance = filtersClass()
    filter_instance.filt_window.spin_average.setValue(5)
    filter_instance.filt_window.spin_median.setValue(5)
    filter_instance.filt_window.spin_exp_mean.setValue(0.1)

    filter_instance.range_avg = 5
    filter_instance.range_median = 5
    filter_instance.alpha_exp = 0.5

    filtered_average = filter_instance.average_filt(noisy_data)
    filtered_median = filter_instance.med_filt(noisy_data)
    filtered_exp_mean = filter_instance.exp_mean_filt(noisy_data)

    plt.figure(figsize=(12, 6))
    plt.plot(x, noisy_data, label='Зашумленные данные', color='gray', alpha=0.5)
    plt.plot(x, clean_data, label='Чистый сигнал', color='green', linestyle='--')
    plt.plot(x[:len(filtered_average)], filtered_average, label='Отфильтрованные (среднее)', color='blue')
    plt.plot(x, filtered_median, label='Отфильтрованные (медиана)', color='orange')
    plt.plot(x, filtered_exp_mean, label='Отфильтрованные (экспоненциальный)', color='purple')

    plt.title('Фильтрация сигналов')
    plt.legend()
    plt.xlabel('Время')
    plt.ylabel('Амплитуда')
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':

    import sys
    app = QApplication(sys.argv)
    test_filters()
    widget = filtersClass()
    widget.filt_window.setWindowTitle("Фильтры данных")
    widget.filt_window.show()
    sys.exit(app.exec_())