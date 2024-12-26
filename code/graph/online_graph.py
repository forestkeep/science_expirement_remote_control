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

from PyQt5.QtCore import QTimer, pyqtSignal, QPoint, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QHBoxLayout,
    QWidget,
    QSplitter,
    QSizePolicy,
)

if __name__ == "__main__":
    from graph_main import graphMain
    from osc_wave_graph import graphOsc
    from tabPage_win import tabPage
    from filters_win import filtersClass
    from notification import NotificationWidget
    from tree_curves import treeWin
else:
    from graph.graph_main import graphMain
    from graph.osc_wave_graph import graphOsc
    from graph.tabPage_win import tabPage
    from graph.filters_win import filtersClass
    from graph.notification import NotificationWidget
    from graph.tree_curves import treeWin


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
        self.setGeometry(100, 100, 1200, 700)
        self.experiment_controller = experiment_controller
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

        #---------------------------------
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

        self.filter_class.set_filter_slot(self.filters_callback)#при нажатии кнопок в фильтре будет вызываться эта функция

        #---------------------------------

        self.mainLayout.addWidget(splitter)

        self.tab1 = tabPage(1)
        self.tab2 = tabPage(2)

        self.tabWidget.addTab(self.tab1, QApplication.translate("GraphWindow", "Графики") )
        self.tabWidget.addTab(self.tab2, QApplication.translate("GraphWindow", "Осциллограммы") )  # Placeholder for another tab

        self.graph_main = graphMain(tablet_page=self.tab1, main_class=self)
        self.graph_wave = graphOsc(self.tab2, self)

        self.graph_main.new_curve_selected.connect(self.tree_class.update_visible)
        self.graph_main.new_data_imported.connect(self.tree_class.clear_all)
        self.tree_class.curve_deleted.connect(self.graph_main.destroy_curve)
        self.tree_class.curve_shown.connect(self.graph_main.show_curve)
        self.tree_class.curve_hide.connect(self.graph_main.hide_curve)
        self.tree_class.curve_reset.connect(self.graph_main.reset_filters)
        self.tree_class.curve_created.connect(self.graph_main.add_curve_to_stack)

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
        if self.experiment_controller is not None:
            if self.experiment_controller.is_experiment_running():
                is_apply = False

        if is_apply:
            active_tab_index = self.tabWidget.currentIndex()
            if active_tab_index == 0:
                self.graph_main.set_filters(filter_func)
            elif active_tab_index == 1:
                self.graph_wave.set_filters(filter_func)

            self.show_tooltip("Фильтры применены к выделенным графикам. \n Для сброса фильтров выделите графики и нажмите кнопку esc.", timeout=5000)
        else:
            self.show_tooltip("Дождитесь окончания эксперимента", timeout=3000)

    def update_graphics(self, new_data: dict, is_exp_stop = False):
        '''is_exp_stop - флаг остановки эксперимента, передается, когда эксперимент завершается, принудительно переводит окно графиков в расщиренный режим просмотра'''
        if new_data:
            self.graph_main.update_dict_param(new=new_data, is_exp_stop=is_exp_stop)
            self.graph_wave.update_dict_param(new=new_data, is_exp_stop=is_exp_stop)

    def set_default(self):
        self.graph_main.set_default()
        self.graph_wave.set_default()

    def gen_new_data(self):
        """функция раз в n секунд генерирует словарь и обновляет данные"""
        self.update_graphics(next(self.gen))
        self.counter_test += 1
        if self.counter_test == 10:
            self.graph_main.reconfig_state()
            self.experiment_controller.running = False
            self.timer.stop()

    def test_update(self):
        self.test = test_graph()
        self.gen = self.test.append_values()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.gen_new_data)
        periodsec = 0.1
        self.timer.start(int(periodsec*1000))
        self.counter_test = 0
        self.experiment_controller = exprEmul()

    def closeEvent(self, event):
        self.graph_win_close_signal.emit(1)
class exprEmul():
    def __init__(self):
        self.running = True

    def is_experiment_running(self):
        return self.running

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
