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

import sys
import time

import logging
from PyQt5.QtCore import QPoint, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QMainWindow,
                             QSizePolicy, QSplitter, QTabWidget, QWidget)

try:
    from filters_win import filtersClass
    from graph_main import graphMain
    from notification import NotificationWidget
    from osc_wave_graph import graphOsc
    from tabPage_win import tabPage
    from tree_curves import treeWin
    from dataManager import graphDataManager
    from importData import controlImportData
    from importData import importDataWin
    from paramSelectors import paramSelector, paramController
    from graphSelectAdapter import graphSelectAdapter
except:
    from graph.filters_win import filtersClass
    from graph.graph_main import graphMain
    from graph.notification import NotificationWidget
    from graph.osc_wave_graph import graphOsc
    from graph.tabPage_win import tabPage
    from graph.tree_curves import treeWin
    from graph.dataManager import graphDataManager
    from graph.importData import controlImportData
    from graph.importData import importDataWin
    from graph.paramSelectors import paramSelector, paramController
    from graph.graphSelectAdapter import graphSelectAdapter


logger = logging.getLogger(__name__)

def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        logger.info(f"Метод {func.__name__} выполнялся {end_time - start_time} с")
        return result

    return wrapper

class GraphWindow(QMainWindow):
    graph_win_close_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Online Graph")
        self.setGeometry(100, 100, 1200, 700)
        self.notification = None
        self.initUI()

    def initUI(self):
        self.mainWidget = QWidget(self)
        self.setWindowIcon(QIcon('picture/graph.png')) 
        self.setCentralWidget(self.mainWidget)
        self.mainLayout = QHBoxLayout(self.mainWidget)

        self.filter_class = filtersClass()

        self.tree_class = treeWin(main_class=self)

        self.tabWidget = QTabWidget()

        splitter = QSplitter()
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        splitter.setOrientation(1)  # 1 - вертикальный

        splitter.addWidget(self.tree_class)
        splitter.addWidget(self.tabWidget)
        splitter.addWidget(self.filter_class.filt_window)

        splitter.setHandleWidth(1)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 10)
        splitter.setStretchFactor(2, 1)

        one_deca_part = int(self.width()/10)
        splitter.setSizes([one_deca_part, one_deca_part*9, 0])

        self.data_manager = graphDataManager()
        self.select_win = paramSelector()
        self.select_controller = paramController( self.select_win )
        self.import_data_win = importDataWin()
        self.import_data_manager = controlImportData(self.import_data_win, self.data_manager, self)

        self.filter_class.set_filter_slot(self.filters_callback)#при нажатии кнопок в фильтре будет вызываться эта функция

        self.mainLayout.addWidget(splitter)

        self.tab1 = tabPage(1)
        self.tab2 = tabPage(2)

        self.tabWidget.addTab(self.tab1, QApplication.translate("GraphWindow", "Графики") )
        self.tabWidget.addTab(self.tab2, QApplication.translate("GraphWindow", "Осциллограммы") )  # Placeholder for another tab

        self.graph_main = graphMain(tablet_page=self.tab1, main_class=self, import_data_widget=self.import_data_win, select_data_wid = self.select_win)
        self.graph_wave = graphOsc(self.tab2, self)

        self.adapter_main_graph = graphSelectAdapter(self.graph_main, self.select_controller, self.data_manager, self.tree_class, 'main', self)

        self.tabWidget.setCurrentIndex(0)

    def show_tooltip(self, message, show_while_not_click = False, timeout = 3000):
        if self.notification is None:
            self.notification = NotificationWidget(parent=self)

        self.notification.set_message(message)

        note_size = self.notification.sizeHint()
        pos = QPoint(self.width() - note_size.width() , self.height() - note_size.height())

        self.notification.move(pos)

        if show_while_not_click:
            self.notification.show()
        else:
            self.notification.show_with_animation(timeout=timeout)

    def filters_callback(self, filter_func):

        is_apply = True
        if self.data_manager is not None:
            if self.data_manager.is_session_running():
                is_apply = False

        if is_apply:
            active_tab_index = self.tabWidget.currentIndex()
            if active_tab_index == 0:
                self.graph_main.set_filters(filter_func)
            elif active_tab_index == 1:
                self.graph_wave.set_filters(filter_func)

            self.show_tooltip( QApplication.translate("GraphWindow","Фильтры применены к выделенным графикам. \n Для сброса фильтров выделите графики и нажмите кнопку esc."), timeout=5000)
        else:
            self.show_tooltip( QApplication.translate("GraphWindow","Дождитесь окончания эксперимента"), timeout=3000)

    def update_graphics(self, new_data: dict, is_exp_stop = False):
        '''is_exp_stop - флаг остановки эксперимента, передается, когда эксперимент завершается, принудительно переводит окно графиков в расщиренный режим просмотра'''
        if new_data:
            self.data_manager.add_measurement_data(new_data)

    def set_default(self):
        self.graph_main.set_default()
        self.graph_wave.set_default()

    def gen_new_data(self):
        """функция раз в n секунд генерирует словарь и обновляет данные"""
        self.update_graphics(next(self.gen))
        self.counter_test += 1

        if self.counter_test >= 100:
            self.counter_test = 0
            self.timer.stop()
            self.data_manager.stop_session_running()

    def test_update(self, periodsec):
        self.test = test_graph()
        self.gen = self.test.append_values()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.gen_new_data)
        self.timer.start(int(periodsec*1000))
        self.counter_test = 0

    def closeEvent(self, event):
        self.graph_win_close_signal.emit(1)

if __name__ == "__main__":
    import os
    logger = logging.getLogger(__name__)
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter(FORMAT))

    logging.basicConfig(handlers=[console], level=logging.DEBUG)

    import qdarktheme
    from test_main_graph import test_graph
    app = QApplication(sys.argv)
    qdarktheme.setup_theme("dark", corner_shape="sharp", custom_colors={"primary": "#DDBCFF"})
    mainWindow = GraphWindow()
    mainWindow.data_manager.start_new_session("test",is_experiment_running=True, use_timestamps=True)
    mainWindow.show()
    mainWindow.test_update(periodsec=0.1)

    #mainWindow.update_param_in_comboxes()
    sys.exit(app.exec_())

    # py-spy record --native -o profile.svg -- python C:\Users\zahidovds\Desktop\virtual_for_uswindsens\main\graph\online_graph.py
