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

import random
import sys
import time

import numpy as np
import pandas as pd
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QListWidgetItem
)

if __name__ == "__main__":
    from graph_main import graphMain
    from osc_wave_graph import X
else:
    from graph.graph_main import graphMain
    from graph.osc_wave_graph import X


def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        #print(f"Метод {func.__name__} - {end_time - start_time} с")
        return result

    return wrapper


class test_graph:

    def __init__(self):
        self.start_time = time.time()
        ch1, ch2, step = self.read_param_from_test()
        self.main_dict = {
            "device1": {"ch_1": {"time": [0], self.get_param(): self.get_values()}},
            "device3": {
                "ch_1": {
                    "time": [0],
                    self.get_param(): self.get_values(),
                    "wavech": [ch1],
                    "scale": [step],
                },
                "ch_2": {
                    "time": [0],
                    self.get_param(): self.get_values(),
                    self.get_param(): self.get_values(),
                    self.get_param(): self.get_values(),
                },
                "ch_3": {"time": [0], "wavech": [ch2], "scale": [step]},
                "ch_4": {
                    "time": [0],
                    "wavech": [self.generate_random_list(10, 0, 10)],
                    "scale": [0.002],
                },
            },
            "device4": {
                "ch_1": {
                    "time": [0],
                    "wavech": [self.generate_random_list(10, 0, 10)],
                    "scale": [0.002],
                }
            },
        }

    def read_param_from_test(self):
        import os

        current_directory = os.path.dirname(os.path.abspath(__file__))

        file_name = "test_loop.csv"


        # Формирование полного пути
        full_path = os.path.join(current_directory, file_name)

        df = pd.read_csv(full_path, sep=";")

        # Создаем словарь для хранения данных
        data_dict = {}

        # Считываем данные из DataFrame
        for column in df.columns:
            # Конвертируем данные в float и помещаем в словарь
            data_dict[column] = df[column].astype(str).tolist()
        for key, values in data_dict.items():
            # Новая переменная для хранения конвертированных значений
            converted_values = []
            for val in values:
                val = val.replace(",", ".")
                try:
                    # Пытаемся конвертировать в float
                    if val == "nan":
                        continue
                    converted_values.append(float(val))
                except ValueError:
                    # Игнорируем неконвертируемые значения
                    continue
            # Обновляем словарь с новыми списками значений
            data_dict[key] = np.array(converted_values)

        return data_dict["CH1"], data_dict["CH2"], data_dict["Increment"][0]

    def get_param(self):
        random_X = ["R", "L", "C", "PHAS", "V", "I", "D", "|Z|", "Q"]
        return random.choice(random_X)

    def get_values(self):
        return [random.randint(1, 10) for _ in range(1)]

    def generate_random_list(self, size, lower_bound=0, upper_bound=100):

        frequency = np.random.uniform(
            lower_bound, upper_bound
        )  # Частота в диапазоне от 0.5 до 5.0
        x = np.linspace(0, 2 * np.pi, size)
        sine_wave = list(
            np.round(np.sin(frequency * x), 2)
        )  # Округляем до 2 знаков после запятой

        return sine_wave

    def update_dict(self, main_dict):
        """добавляет в каждый конечный список число"""
        for device, channels in main_dict.items():
            for channel, params in channels.items():
                for key, value in params.items():
                    if key == "time":
                        # Добавляем текущее время
                        value.append(round(time.time() - self.start_time))
                    elif (
                        isinstance(value, list)
                        and not any(isinstance(i, list) for i in value)
                        and key != "wavech"
                    ):
                        # Добавляем случайное число от 1 до 10 в конечные списки
                        value.append(random.randint(1, 10))
                    elif (
                        isinstance(value, list)
                        and any(isinstance(i, list) for i in value)
                        or key == "wavech"
                    ):
                        # Если ключ содержит 'wave', добавляем случайное число в каждый вложенный список
                        value.append(
                            self.generate_random_list(
                                size=100, lower_bound=0, upper_bound=10
                            )
                        )
        return main_dict

    def append_values(self):
        while True:
            self.main_dict = self.update_dict(self.main_dict)
            yield self.main_dict

    def get_time(self):
        start_range = 1
        end_range = 10
        list_size = 1
        all_values = list(range(start_range, end_range * list_size))
        random.shuffle(all_values)
        # Берем первые list_size элементов
        time_dict = all_values[:list_size]
        time_dict.sort()
        return time_dict

class GraphWindow(QMainWindow):
    graph_win_close_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Online Graph")
        self.setGeometry(100, 100, 900, 600)
        self.initUI()

    def initUI(self):
        # Main widget and layout
        self.mainWidget = QWidget(self)
        self.setWindowIcon(QIcon('picture/graph.png'))  # Укажите путь к вашей иконке
        self.setCentralWidget(self.mainWidget)
        self.mainLayout = QVBoxLayout(self.mainWidget)

        # Create Tab Widget
        self.tabWidget = QTabWidget()
        self.mainLayout.addWidget(self.tabWidget)

        # Create first tab and set its layout
        self.tab1 = QWidget()
        self.tab2 = QWidget()

        # Add tabs to the tab widget
        self.tabWidget.addTab(self.tab1, QApplication.translate("GraphWindow", "Графики") )
        self.tabWidget.addTab(self.tab2, QApplication.translate("GraphWindow", "Осциллограммы") )  # Placeholder for another tab

        self.graph_main = graphMain(tablet_page=self.tab1)
        self.graph_wave = X(self.tab2)

        self.tabWidget.setCurrentIndex(0)  # Default to first tab

    def update_graphics(self, new_data: dict):
        if new_data:
            self.graph_main.update_dict_param(new=new_data)
            self.graph_wave.update_dict_param(new=new_data)

    def set_default(self):
        self.graph_main.set_default()
        self.graph_wave.set_default()

    def gen_new_data(self):
        """функция раз в секунду генерирует словарь и обновляет данные"""

        self.update_graphics(next(self.gen))
        self.timer.start(10000)

    def test_update(self):
        self.test = test_graph()
        self.gen = self.test.append_values()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.gen_new_data)
        self.timer.start(100)

    def closeEvent(self, event):  # эта функция вызывается при закрытии окна
        self.graph_win_close_signal.emit(1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = GraphWindow()
    mainWindow.show()
    #mainWindow.test_update()

    #mainWindow.update_param_in_comboxes()
    sys.exit(app.exec_())

    # py-spy record --native -o profile.svg -- python C:\Users\zahidovds\Desktop\virtual_for_uswindsens\main\graph\online_graph.py
