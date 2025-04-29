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
                             QSizePolicy, QSplitter, QTabWidget, QWidget, QMenu, QAction, QVBoxLayout, QStackedWidget)

try:
    from filters_win import filtersClass
    from graph_main import graphMain
    from notification import NotificationWidget
    from osc_wave_graph import graphOsc
    from tabPage_win import tabPage
    from tree_curves import treeWin
    from dataManager import graphDataManager
    from paramSelectors import paramSelector, paramController
    from graphSelectAdapter import graphSelectAdapter
    from select_session import SessionSelectControl
except:
    from graph.filters_win import filtersClass
    from graph.graph_main import graphMain
    from graph.notification import NotificationWidget
    from graph.osc_wave_graph import graphOsc
    from graph.tabPage_win import tabPage
    from graph.tree_curves import treeWin
    from graph.dataManager import graphDataManager
    from graph.paramSelectors import paramSelector, paramController
    from graph.graphSelectAdapter import graphSelectAdapter
    from graph.select_session import SessionSelectControl

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

    def __init__(self, import_data_win=None):
        super().__init__()
        self.setWindowTitle("Online Graph")
        self.setGeometry(100, 100, 1200, 700)
        self.notification = None
        self.initUI(import_data_win=import_data_win)

    def initUI(self, import_data_win):
        self.__add_menu()

        self.mainWidget = QWidget(self)
        self.main_lay = QVBoxLayout(self.mainWidget)
        self.setWindowIcon(QIcon('picture/graph.png')) 
        self.setCentralWidget(self.mainWidget)

        self.stack = QStackedWidget(self)

        splitter = QSplitter(0)
        
        splitter.addWidget(self.stack)
        splitter.addWidget(import_data_win)

        splitter.setSizes([self.height() // 2, self.height() // 8])

        self.main_lay.addWidget(splitter)

    def __add_menu(self):
        self.menubar = self.menuBar()
        self.menu = QMenu(self.menubar)
        self.menu.setObjectName("menu")

        self.save_installation_button_as = QAction(self)
        self.save_installation_button = QAction(self)
        self.open_installation_button = QAction(self)
        self.add_device_button = QAction(self)

        self.convert_buf_button = QAction(self)

        self.menu.addAction(self.save_installation_button)
        self.menu.addAction(self.save_installation_button_as)
        self.menu.addAction(self.open_installation_button)
        self.menu.addSeparator()
        self.menu.addAction(self.add_device_button)
        self.menu.addSeparator()
        self.menu.addAction(self.convert_buf_button)
        self.menubar.addAction(self.menu.menuAction())

        self.set = QMenu(self.menubar)
        self.menubar.addAction(self.set.menuAction())
        self.develop_mode = QAction(self)
        self.general_settings = QAction(self)

        self.info = QMenu(self.menubar)
        self.menubar.addAction(self.info.menuAction())
        self.instruction = QAction(self)
        self.about_autors = QAction(self)
        self.version = QAction(self)
        self.setAcceptDrops(True)

        file_menu = self.menubar.addMenu("Файл") 
        file_menu.addAction(self.save_installation_button)
        file_menu.addAction(self.save_installation_button_as)
        file_menu.addAction(self.open_installation_button)
        file_menu.addSeparator()
        file_menu.addAction(self.add_device_button)
        file_menu.addSeparator()
        file_menu.addAction(self.convert_buf_button)

        settings_menu = self.menubar.addMenu("Сессия")
        settings_menu.addAction(self.develop_mode)
        settings_menu.addAction(self.general_settings)

class GraphSession(QWidget):
    graph_win_close_signal = pyqtSignal(int)

    def __init__(self, id, name):
        super().__init__()
        self.notification = None
        self.session_id = id
        self.session_name = name
        self.initUI()

    def initUI(self):

        self.up_lay = QHBoxLayout(self)

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

        self.filter_class.set_filter_slot(self.filters_callback)#при нажатии кнопок в фильтре будет вызываться эта функция

        self.up_lay.addWidget(splitter)

        self.tab1 = tabPage(1)
        self.tab2 = tabPage(2)

        self.tabWidget.addTab(self.tab1, QApplication.translate("GraphWindow", "Графики") )
        self.tabWidget.addTab(self.tab2, QApplication.translate("GraphWindow", "Осциллограммы") )  # Placeholder for another tab

        self.graph_main = graphMain(tablet_page=self.tab1, main_class=self, select_data_wid = self.select_win)
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

    def closeEvent(self, event):
        self.graph_win_close_signal.emit(1)

class running_exp_test(QWidget):
    def __init__(self,graph_class, max_points, periodsec):
        super().__init__()
        self.test = test_graph()
        self.gen = self.test.append_values()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.gen_new_data)
        self.counter_test = 0
        self.max_points = max_points
        self.periodsec = periodsec
        self.graph_class = graph_class

    def run(self):
        self.id = self.graph_class.start_new_session("test",is_experiment_running=True, use_timestamps=True)
        self.timer.start(int(self.periodsec*1000))

    def gen_new_data(self):
        """функция раз в n секунд генерирует словарь и обновляет данные"""
        self.graph_class.update_session_data(self.id, (next(self.gen)))
        self.counter_test += 1

        if self.counter_test >= self.max_points:
            self.counter_test = 0
            self.timer.stop()
            self.graph_class.stop_session_running( self.id )

class sessionController():
    def __init__(self):
        self.session_selector = SessionSelectControl()
        self.controll_sessions_win = self.session_selector.widget

        self.session_selector.current_session_changed.connect(self.change_session)
        self.session_selector.session_deleted.connect(self.delete_session)
        self.session_selector.new_data_imported.connect(self.data_imported)
        self.session_selector.session_name_changed.connect(self.change_session_name)

        self.graphics_win = GraphWindow(self.controll_sessions_win)

        self.graph_sessions = {}

    def show(self):
        self.graphics_win.show()

    def stop_session_running(self, session_id):
        if self.graph_sessions.get(session_id):
            self.graph_sessions[session_id].data_manager.stop_session_running()

    def start_new_session(self, session_name: str, use_timestamps: bool = False, is_experiment_running: bool = False, new_data = None) -> int:
        session_id = self.session_selector.get_free_id()
        self.__create_session(session_name, session_id, use_timestamps, is_experiment_running, new_data)
        if is_experiment_running:
            status = "running"
        self.session_selector.add_session({'id': session_id, 'name': session_name, 'status': status})
        return session_id

    def __create_session(self, session_name: str, session_id: str, use_timestamps: bool = False, is_experiment_running: bool = False, new_data = None):
        new_session_graph = GraphSession(session_id, session_name)
        try:
            new_session_graph.data_manager.start_new_session(session_id, use_timestamps, is_experiment_running, new_data)
        except Exception as e:
            logger.warning(f"Failed to start session {session_id} {e}")

        self.graph_sessions[session_id] = new_session_graph
        self.graphics_win.stack.addWidget(new_session_graph)

    def change_session(self, session_id: int):
        if self.graph_sessions.get(session_id) is not None:
            self.graphics_win.stack.setCurrentWidget(self.graph_sessions[session_id])
        else:
            logger.warning(f"Session {session_id} not found")

    def data_imported(self,session_name: str, session_id: str, data: dict):
        self.__create_session(session_name, session_id, new_data=data)

    def delete_session(self, session_id: str):
        self.graphics_win.stack.removeWidget(self.graph_sessions[session_id])
        self.graph_sessions[session_id].deleteLater()
        del self.graph_sessions[session_id]

    def change_session_name(self, session_id: str, session_name: str):
        self.graph_sessions[session_id].session_name = session_name

    def update_session_data(self, session_id: str, data: dict) -> bool:
        if self.graph_sessions.get(session_id) is None:
            return False
        self.graph_sessions[session_id].data_manager.add_measurement_data(data)

    def get_session_id(self, session_name: str) -> int:
        for session_id in self.graph_sessions.keys():
            if self.graph_sessions[session_id].session_name == session_name:
                return session_id
        return None
    
    def decode_add_exp_parameters(self, session_id, entry, time) -> bool:
        if self.graph_sessions.get(session_id) is None:
            return False
        return self.graph_sessions[session_id].data_manager.decode_add_exp_parameters(entry, time)
    
def run_graph_process(queue):
    app = QApplication([])
    controller = sessionController()
    controller.controll_sessions_win.show()
    app.exec_()

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

    my_session_class = sessionController()
    my_session_class.graphics_win.show()

    test_class = running_exp_test(my_session_class, 50, 0.1)
    test_class.run()

    sys.exit(app.exec_())

    # py-spy record --native -o profile.svg -- python C:\Users\zahidovds\Desktop\virtual_for_uswindsens\main\graph\online_graph.py
