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
from PyQt5.QtCore import QTimer, pyqtSignal, QPropertyAnimation, QPoint, Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QHBoxLayout,
    QWidget,
    QSplitter,
    QSizePolicy,
    QFrame,
    QVBoxLayout,
    QLabel
)

if __name__ == "__main__":
    from graph_main import graphMain
    from osc_wave_graph import graphOsc
    from tabPage_win import tabPage
    from filters_win import filtersClass
    from notification import NotificationWidget
else:
    from graph.graph_main import graphMain
    from graph.osc_wave_graph import graphOsc
    from graph.tabPage_win import tabPage
    from graph.filters_win import filtersClass
    from graph.notification import NotificationWidget


def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        #print(f"Метод {func.__name__} - {end_time - start_time} с")
        return result

    return wrapper


class GraphWindow(QMainWindow):
    graph_win_close_signal = pyqtSignal(int)

    def __init__(self, experiment_controller = None):
        super().__init__()
        self.setWindowTitle("Online Graph")
        self.setGeometry(100, 100, 900, 600)
        self.experiment_controller = experiment_controller
        self.notification = None
        self.initUI()

    def initUI(self):
        # Main widget and layout
        self.mainWidget = QWidget(self)
        self.setWindowIcon(QIcon('picture/graph.png')) 
        self.setCentralWidget(self.mainWidget)
        self.mainLayout = QHBoxLayout(self.mainWidget)

        self.filter_class = filtersClass()

        # Create Tab Widget
        self.tabWidget = QTabWidget()

        #---------------------------------
        splitter = QSplitter()
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        splitter.setOrientation(1)  # 1 - вертикальный

        splitter.addWidget(self.tabWidget)
        splitter.addWidget(self.filter_class.filt_window)

        splitter.setStretchFactor(0, 10)
        splitter.setStretchFactor(1, 1)

        self.filter_class.set_filter_slot(self.filters_callback)#при нажатии кнопок в фильтре будет вызываться эта функция

        #---------------------------------

        self.mainLayout.addWidget(splitter)

        # Create first tab and set its layout
        self.tab1 = tabPage(1)
        self.tab2 = tabPage(2)

        # Add tabs to the tab widget
        self.tabWidget.addTab(self.tab1, QApplication.translate("GraphWindow", "Графики") )
        self.tabWidget.addTab(self.tab2, QApplication.translate("GraphWindow", "Осциллограммы") )  # Placeholder for another tab

        self.graph_main = graphMain(tablet_page=self.tab1, main_class=self)
        self.graph_wave = graphOsc(self.tab2, self)

        self.tabWidget.setCurrentIndex(0)  # Default to first tab

    def show_tooltip(self, message, show_while_not_click = False, timeout = 3000):
        if self.notification is None:
            self.notification = NotificationWidget(parent=self)

        self.notification.set_message(message)

        note_size = self.notification.sizeHint()
        pos = QPoint(self.width() - note_size.width() , self.height() - note_size.height())

        self.notification.move(pos)  # Перемещаем уведомление перед показом

        if show_while_not_click:
            self.notification.show()
        else:
            self.notification.show_with_animation(timeout=timeout)

    def filters_callback(self, filter_func):

        is_apply = True
        if self.experiment_controller is not None:
            if self.experiment_controller.is_experiment_running():
                is_apply = False

        if is_apply:
            active_tab_index = self.tabWidget.currentIndex()  # Получаем индекс активной вкладки
            if active_tab_index == 0:
                self.graph_main.set_filters(filter_func)
            elif active_tab_index == 1:
                self.graph_wave.set_filters(filter_func)

            self.show_tooltip("Фильтры применены к выделенным графикам. \n Для сброса фильтров выделите графики и нажмите кнопку esc.", timeout=5000)
        else:
            self.show_tooltip("Дождитесь окончания эксперимента", timeout=3000)

    def update_graphics(self, new_data: dict):
        if new_data:
            self.graph_main.update_dict_param(new=new_data)
            self.graph_wave.update_dict_param(new=new_data)

    def set_default(self):
        self.graph_main.set_default()
        self.graph_wave.set_default()

    def gen_new_data(self):
        """функция раз в n секунд генерирует словарь и обновляет данные"""
        sec = 10000
        self.update_graphics(next(self.gen))
        self.timer.start(sec*1000)

    def test_update(self):
        self.test = test_graph()
        self.gen = self.test.append_values()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.gen_new_data)
        self.timer.start(100)

    def closeEvent(self, event):  # эта функция вызывается при закрытии окна
        self.graph_win_close_signal.emit(1)

if __name__ == "__main__":
    from test_main_graph import test_graph
    import qdarktheme
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    mainWindow = GraphWindow()
    mainWindow.show()
    mainWindow.test_update()

    #mainWindow.update_param_in_comboxes()
    sys.exit(app.exec_())

    # py-spy record --native -o profile.svg -- python C:\Users\zahidovds\Desktop\virtual_for_uswindsens\main\graph\online_graph.py
