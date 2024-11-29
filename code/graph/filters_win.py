from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton
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

        self.median_button = QPushButton("Применить")
        self.average_button = QPushButton("Применить")
        self.calman_button = QPushButton("Применить")
        self.exp_mean_button = QPushButton("Применить")

        self.median_button.setMinimumSize(30, 20)
        self.average_button.setMinimumSize(30, 20)
        self.calman_button.setMinimumSize(30, 20)
        self.exp_mean_button.setMinimumSize(30, 20)

        self.spin_median = QSpinBox() 
        self.spin_average = QSpinBox()
        self.spin_calman = QSpinBox()
        self.spin_calman2 = QSpinBox()
        self.spin_exp_mean = QSpinBox()
        self.spin_exp_mean2 = QSpinBox()
        self.spin_exp_mean3 = QSpinBox()

        main_layout.addLayout(self.create_layer_filter("Медианный фильтр", [self.create_spin_box("Порядок", self.spin_median)],
                                                                            self.median_button) )
        
        main_layout.addLayout(self.create_layer_filter("Бегущее среднее", [self.create_spin_box("Порядок", self.spin_average)],
                                                                           self.average_button) )
        
        main_layout.addLayout(self.create_layer_filter("Фильтр Калмана", [self.create_spin_box("Q", self.spin_calman),
                                                                          self.create_spin_box("R", self.spin_calman2)],
                                                                          self.calman_button) )
        
        main_layout.addLayout(self.create_layer_filter("Экспоненциальное \n среднее",
                                                        [self.create_spin_box("Коэфф", self.spin_exp_mean3),
                                                         self.create_spin_box("Макс", self.spin_exp_mean2),
                                                         self.create_spin_box("Коэфф", self.spin_exp_mean3)],
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

        font = QFont('Arial', 10, QFont.Bold)  # Установите желаемый шрифт
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
        print(self.range_avg)
        #TODO:reading coeff for filters
        for callback in self.filters_callbacks:
            callback(func)

    def med_filt(self, data):
        median = data.rolling(window=3).median()  
        return data

    def exp_mean_filt(self, data):
        return data

    def calman_filt(self, data):
        return data

    def average_filt(self, data):
        N = self.range_avg
        return np.convolve(data, np.ones((N,))/N)[(N-1):]


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    widget = filtersClass()
    widget.filt_window.setWindowTitle("Фильтры данных")
    widget.filt_window.show()
    sys.exit(app.exec_())