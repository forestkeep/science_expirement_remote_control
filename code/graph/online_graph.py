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
import random

import logging
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QPoint, QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QMainWindow,
                             QSizePolicy, QSplitter, QTabWidget, QWidget, QDialog, QAction, QVBoxLayout, QStackedWidget, QFileDialog)

from graph.filters_win import filtersClass
from graph.graph_main import manageGraph
from graph.notification import NotificationWidget
from graph.osc_wave_graph import graphOsc
from graph.tabPage_win import tabPage
from PyQt5.QtCore import QEvent
from graph.tree_curves import treeWin
from graph.dataManager import graphDataManager
from graph.paramSelectors import paramSelector, paramController
from graph.graphSelectAdapter import graphSelectAdapter
from graph.select_session import SessionSelectControl
from graph.buttons_panel import ButtonsControl
from graph.osc_selector import OscilloscopeSelector
from graph.waveSelectAdapter import waveSelectAdapter
from graph.hdf5_io.facade import HDF5Facade
from graph.select_compare_data import MultiSelectionDialog
from graph.parameter_alias_manager import ParameterAliasManager
from graph.compare_sessions_graph import CompareWindowMediator
from graph.animation_graph.animation_widget import AnimationWindow
import uuid
import numpy as np
from functions import open_log_file
from graph.filters_instance_class import FilterCommand

try:
    from parameter_alias_manager import ParameterAliasManager, ParameterAliasDialog
except:
    from .parameter_alias_manager import ParameterAliasManager, ParameterAliasDialog
#from graph.saving_controller import savingController

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

    def __init__(self, session_selector, import_buttons=None):
        super().__init__()
        self.setWindowTitle("Online Graph")
        self.setGeometry(100, 100, 1200, 700)
        self.notification = None
        self.initUI(session_selector = session_selector,import_buttons=import_buttons)

    def initUI(self, session_selector, import_buttons):
        self.__add_menu()

        self.mainWidget = QWidget(self)
        self.main_lay = QVBoxLayout(self.mainWidget)
        self.setWindowIcon(QIcon('picture/graph.png'))
        self.setCentralWidget(self.mainWidget)

        self.stack = QStackedWidget(self)
        self.stack.setMinimumWidth(0)
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        splitter = QSplitter(0)
        splitter.addWidget(self.stack)
        splitter.addWidget(session_selector)

        self.splitter = splitter
        self.session_selector = session_selector

        self.splitter.setSizes([self.width() - 50, 50])

        self.session_selector.installEventFilter(self)

        self.main_lay.addWidget(self.splitter)
        self.main_lay.addWidget(import_buttons)

        self.main_lay.setStretch(0, 1)
        self.main_lay.setStretch(1, 0)

    def __add_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu(QApplication.translate('graph',"Файл") )

        data_menu = menubar.addMenu(QApplication.translate('graph',"Данные") )
        self.rename_param_action = QAction(QApplication.translate('graph',"Изменить имена параметров"), self)
        self.read_all_statistics_action = QAction(QApplication.translate('graph',"Показать статистику"), self)

        self.log_path_open = QtWidgets.QAction(QApplication.translate('graph',"Открыть лог файл"),self)
        
        self.save_action = QAction(QApplication.translate('graph',"Сохранить"), self)
        self.save_action.setShortcut("Ctrl + S")
        self.save_action_as = QAction(QApplication.translate('graph',"Сохранить как..."), self)
        self.save_action_as.setShortcut("Ctrl + Shift + S")
        self.load_action = QAction(QApplication.translate('graph',"Загрузить"), self)
        self.load_action.setShortcut("Ctrl + O")
        
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_action_as)
        file_menu.addAction(self.load_action)
        file_menu.addAction(self.log_path_open)

        data_menu.addAction(self.rename_param_action)
        #data_menu.addAction(self.read_all_statistics_action)

    def eventFilter(self, obj, event):
        if obj == self.session_selector:
            if event.type() == QEvent.Enter:
                desired_height = self._compute_desired_session_height()
                desired_height = max(self.session_selector.minimumHeight(),
                                    min(desired_height, self.session_selector.maximumHeight()))
                total_height = self.splitter.height()
                self.splitter.setSizes([total_height - desired_height, desired_height])
            elif event.type() == QEvent.Leave:
                min_height = self.session_selector.minimumHeight()
                min_height = max(self.session_selector.minimumHeight(), 50)
                total_height = self.splitter.height()
                self.splitter.setSizes([total_height - min_height, min_height])
        return super().eventFilter(obj, event)

    def _compute_desired_session_height(self):
        if hasattr(self.session_selector, 'table'):
            table = self.session_selector.table
            total_height = table.horizontalHeader().height()
            total_height += table.verticalHeader().height()
            for row in range(table.rowCount()):
                total_height += table.rowHeight(row)
            return total_height
        else:
            return self.session_selector.sizeHint().height()
        
    def closeEvent(self, event):
        self.graph_win_close_signal.emit(1)
        event.accept()
        
class GraphSession(QWidget):
    graph_win_close_signal = pyqtSignal(int)

    def __init__(self, id, name, alias_manager, session_controller, simple_mode=False, ses_uuid=None,):
        super().__init__()
        self.alias_manager = alias_manager
        self.notification = None
        self.session_id = id
        self.session_controller = session_controller
        self.session_name = name
        self.description = None
        self.uuid = uuid.uuid4().hex if ses_uuid is None else ses_uuid
        logger.info(f"Session {self.uuid=} created")
        self._simple_mode = simple_mode
        self.initUI()

    def get_compare_graph(self):
        return self.session_controller.get_compare_graph()
    
    def animation_start(self, animator):
        self.session_controller.animation_start(animator)

    def initUI(self):
        simple = self._simple_mode
        self.up_lay = QHBoxLayout(self)

        if not simple:
            self.filter_class = filtersClass()
            self.tree_class = treeWin(main_class=self)

        self.tabWidget = QTabWidget()

        splitter = QSplitter()
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        splitter.setOrientation(1)

        if not simple:
            splitter.addWidget(self.tree_class)
        splitter.addWidget(self.tabWidget)
        if not simple:
            splitter.addWidget(self.filter_class.filt_window)

        splitter.setHandleWidth(1)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 10)
        splitter.setStretchFactor(2, 1)

        one_deca_part = self.width() // 10
        splitter.setSizes([one_deca_part, one_deca_part * 9, 0])

        self.select_win = None

        if not simple:
            self.data_manager = graphDataManager(alias_manager=self.alias_manager)
            self.select_win = paramSelector(alias_manager=self.alias_manager)
            self.select_controller = paramController(self.select_win, alias_manager=self.alias_manager)
            self.filter_class.set_filter_slot(self.filters_callback)

        self.up_lay.addWidget(splitter)

        self.tab1 = tabPage(1)
        self.tab2 = tabPage(2)

        self.tabWidget.addTab(self.tab1, QApplication.translate("GraphWindow", "Графики"))
        self.tabWidget.addTab(self.tab2, QApplication.translate("GraphWindow", "Осциллограммы"))

        self.selector_osc = OscilloscopeSelector()

        self.graph_main = manageGraph(
            tablet_page=self.tab1,
            main_class=self,
            select_data_wid=self.select_win,
            alias_manager=self.alias_manager
        )
        self.graph_wave = graphOsc(
            self.tab2,
            self.selector_osc,
            self,
            alias_manager=self.alias_manager
        )

        if not simple:
            self.adapter_main_graph = graphSelectAdapter(
                self.graph_main,
                self.select_controller,
                self.data_manager,
                self.tree_class,
                'main',
                self
            )
            self.adapter_osc_graph = waveSelectAdapter(
                self.graph_wave,
                self.selector_osc,
                self.data_manager,
                'osc',
                self
            )

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

    def filters_callback(self, filter_comand: FilterCommand):

        is_apply = True
        if self.data_manager is not None:
            if self.data_manager.is_session_running():
                is_apply = False

        if is_apply:
            active_tab_index = self.tabWidget.currentIndex()
            if active_tab_index == 0:
                self.graph_main.set_filters(filter_comand)
            elif active_tab_index == 1:
                self.graph_wave.set_filters(filter_comand)

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
        self.test1 = test_graph(is_sine_wave=True)
        self.test2 = test_graph()
        self.gen1 = self.test1.append_values()
        self.gen2 = self.test2.append_values()
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
        if random.random() < 0.5:
            gen = self.gen1
        else:
            gen = self.gen2
        self.graph_class.update_session_data(self.id, (next(gen)))
        self.counter_test += 1

        if self.counter_test >= self.max_points:
            self.counter_test = 0
            self.timer.stop()
            self.graph_class.stop_session_running( self.id )

class sessionController():
    def __init__(self):
        self.alias_manager = ParameterAliasManager()
        self.session_selector = SessionSelectControl()
        self.buttons_controller = ButtonsControl(self.session_selector)
        self.button_ctrl_win = self.buttons_controller.widget
        self.controll_sessions_win = self.session_selector.widget

        self.session_selector.current_session_changed.connect(self.change_session)
        self.session_selector.session_deleted.connect(self.delete_session)
        self.session_selector.session_name_changed.connect(self._session_renamed)
        self.session_selector.session_description_changed.connect(self._session_description_changed)

        self.buttons_controller.new_data_imported.connect(self.data_imported)
        self.buttons_controller.compare_sessions_requested.connect(self.compare_sessions)

        self.graphics_win = GraphWindow(self.controll_sessions_win, self.buttons_controller.widget)
        self.graphics_win.graph_win_close_signal.connect(self.close_graph_window)
        self.graphics_win.save_action.triggered.connect(self.push_button_save_graph)
        self.graphics_win.load_action.triggered.connect(self.push_button_open_graph)
        self.graphics_win.log_path_open.triggered.connect(open_log_file)
        self.graphics_win.save_action_as.triggered.connect(self.push_button_save_graph_as)
        self.graphics_win.rename_param_action.triggered.connect(self.show_alias_dialog)
        self.graphics_win.read_all_statistics_action.triggered.connect(self.read_statistics)
        self.way_to_save_file = None

        self.graph_sessions = {}
        self.compare_graph = None

    def close_graph_window(self):
        if self.compare_graph is not None:
            self.compare_graph.close()

    def animation_start(self, animator):
        self.animation_win = AnimationWindow(animator=animator)
        self.animation_win.show()
            
    def compare_sessions(self):
        data = {}
        for session_id, session in self.graph_sessions.items():
            data[session_id] = {"name": session.session_name, "values": session.data_manager.get_name_params()}
        data_test = {
            101: {"name": "Фрукты", "values": ["яблоко", "банан", "апельсин", "киви"]},
            102: {"name": "Овощи", "values": ["морковь", "картофель", "помидор", "огурец"]},
            103: {"name": "Ягоды", "values": ["клубника", "малина", "черника", "ежевика"]},
            104: {"name": "Фрукты", "values": ["груша", "персик", "слива"]}
        }

        exclude = ["numbers", "time", "timestamp"]

        is_valid = True
        '''
        dialog = MultiSelectionDialog(data, exclude_list=exclude, min_items=2)
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            is_valid = True
            print("Выбранные данные после фильтрации (ключи - ID):")
            for id_key, values in result.items():
                name = data[id_key]["name"]
                print(f"{id_key} ({name}): {values}")
        else:
            print("Отмена")
        '''

        if is_valid:
            graph_compare = GraphSession(
                id=125,
                name="test",
                alias_manager=self.alias_manager,
                session_controller=self,
                simple_mode=True,
                ses_uuid=125
            )
            self.compare_graph = CompareWindowMediator(1,     
                                                       "test",
                                                       self.alias_manager,
                                                       graph_compare,
                                                    )
            
            self.compare_graph.window.show()
            
    def get_compare_graph(self):
        if self.compare_graph is None:
            graph_compare = GraphSession(
                id=125,
                name="compare",
                alias_manager=self.alias_manager,
                session_controller=self,
                simple_mode=True,
                ses_uuid=125
            )
            self.compare_graph = CompareWindowMediator(1,     
                                                       "test",
                                                       self.alias_manager,
                                                       graph_compare,
                                                    )
        self.compare_graph.window.show()
        return self.compare_graph

    def push_button_open_log(self):
        if self.way_to_save_file is not None:
            os.startfile(self.way_to_save_file)

    def show_alias_dialog(self):
        """Показывает диалог управления псевдонимами"""
        #available_params = self.get_name_params()
        dialog = ParameterAliasDialog(self.alias_manager,  self.graphics_win)
        dialog.exec_()

    def read_statistics(self, group_by_param=True):
        if False:
            for session in self.graph_sessions.values():
                session_data = session.data_manager.get_all_data()
                main_data = session_data['main'].data
                print(session.session_name)
                print("mean, std, median, max, min")
                for name, value_data in main_data.items():
                    values = value_data.par_val
                    if values is not None:
                        print(self.alias_manager.get_alias(name), np.mean(values), np.std(values), np.median(values))
        else:
            param_data = {}
            
            for session in self.graph_sessions.values():
                session_data = session.data_manager.get_all_data()
                main_data = session_data['main'].data
                
                for name, value_data in main_data.items():
                    values = value_data.par_val
                    if values is not None:
                        alias = self.alias_manager.get_alias(name)
                        if alias not in param_data:
                            param_data[alias] = []
                        
                        param_data[alias].append({
                            'session_name': session.session_name,
                            'mean': np.mean(values),
                            'std': np.std(values),
                            'median': np.median(values)
                        })
            
            for param_name, sessions_data in param_data.items():
                print(f"Parameter: {param_name}")

                sorted_sessions_data = sorted(sessions_data, 
                                            key=lambda x: tuple(map(int, x['session_name'].split())))
                for data in sorted_sessions_data:
                    print(f"{data['session_name']}, {data['mean']}, {data['std']}")
                print()

    def push_button_save_graph(self):
        if self.way_to_save_file is not None:
            HDF5Facade().save_project(self, self.way_to_save_file)
        else:
            self.push_button_save_graph_as()
    
    def push_button_save_graph_as(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, ans = QtWidgets.QFileDialog.getSaveFileName(
            self.graphics_win,
            "Save File",
            "",
            "Installation(*.hdf5)",
            options=options,
        )
        if ans == "Installation(*.hdf5)":
            if ".hdf5" in fileName:
                self.way_to_save_file = fileName
            else:
                self.way_to_save_file = fileName + ".hdf5"
            HDF5Facade().save_project(self, self.way_to_save_file)

    def push_button_open_graph(self):
        logger.debug("нажата кнопка открыть график")
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, ans = QtWidgets.QFileDialog.getOpenFileName(
            self.graphics_win,
            "Open File",
            "",
            "Installation(*.hdf5)",
            options=options,
        )
        if ans == "Installation(*.hdf5)":
            HDF5Facade().load_project(fileName, self)
            self.way_to_save_file = fileName

    def show(self):
        self.graphics_win.show()

    def stop_session_running(self, session_id):
        if self.graph_sessions.get(session_id):
            self.graph_sessions[session_id].data_manager.stop_session_running()
            self.session_selector.set_session_status(session_id=session_id, status = "Exp completed")

    def start_new_session(self, session_name: str, use_timestamps: bool = False, is_experiment_running: bool = False, new_data = None, uuid = None) -> str | bool:
        session_id = self.session_selector.get_free_id()
        is_session_created = self.__create_session(session_name, session_id, use_timestamps, is_experiment_running, new_data, uuid)

        if is_session_created:
            if is_experiment_running:
                status = "running"
            else:
                status = "downloaded"
            self.session_selector.add_session({'id': session_id, 'name': session_name, 'status': status})

            self.change_session(session_id)

        return session_id if is_session_created else False

    def __create_session(self, session_name: str, session_id: str, use_timestamps: bool = False, is_experiment_running: bool = False, new_data = None, uuid = None) -> bool:
        new_session_graph = GraphSession(session_id, session_name, alias_manager=self.alias_manager, ses_uuid=uuid, session_controller = self)
        try:
            new_session_graph.data_manager.start_new_session(session_id, use_timestamps, is_experiment_running, new_data)
            logger.info(f"Session {session_id} created")
        except Exception as e:
            logger.warning(f"Failed to start session {session_id} {e}")
            return False

        self.graph_sessions[session_id] = new_session_graph
        self.graphics_win.stack.addWidget(new_session_graph)

        return True

    def change_session(self, session_id: str):
        if self.graph_sessions.get(session_id) is not None:
            self.graphics_win.stack.setCurrentWidget(self.graph_sessions[session_id])
        else:
            logger.warning(f"Session {session_id} not found")

    def data_imported(self,session_name: str, session_id: str, data: dict):
        status = self.__create_session(session_name, session_id, new_data=data)
        if status:
            self.graph_sessions[session_id].data_manager.stop_session_running()
            self.session_selector.add_session({'id': session_id, 'name': session_name, 'status': 'imported'})

    def delete_session(self, session_id: str):
        if self.graph_sessions.get(session_id) is not None:
            if not self.graph_sessions[session_id].data_manager.is_session_running():   
                self.graphics_win.stack.removeWidget(self.graph_sessions[session_id])
                self.graph_sessions[session_id].graph_main.destroy_all_curves()
                self.graph_sessions[session_id].deleteLater()
                del self.graph_sessions[session_id]
                #self.session_selector.delete_session(session_id)
            else:
                self.graph_sessions[session_id].show_tooltip(QApplication.translate("graph", "Сессию можно удалить только после остановки."))
                logger.warning(f"Session {session_id} is running. Broke session deletion.")

    def _session_renamed(self, session_id: str, new_session_name: str):
        logger.info(f"_session_renamed {session_id} {new_session_name}")
        if self.graph_sessions.get(session_id) is not None:
            self.graph_sessions[session_id].session_name = new_session_name
        else:
            logger.warning(f"Session {session_id} not found")

    def _session_description_changed(self, session_id: str, new_description: str):
        if self.graph_sessions.get(session_id) is not None:
            self.graph_sessions[session_id].description = new_description
        else:
            logger.warning(f"Session {session_id} not found")

    def update_session_description(self, session_id: str, new_description: str):
        logger.info(f"update_session_description {session_id} {new_description}")
        if self.graph_sessions.get(session_id) is None:
            logger.warning(f"Session {session_id} not found")
            return
        else:
            self.graph_sessions[session_id].description = new_description
            self.session_selector.update_session_description(session_id, new_description)

    def change_session_name(self, session_id: str, new_session_name: str) -> bool:
        logger.info(f"change_session_name {session_id} {new_session_name}")
        if self.graph_sessions.get(session_id) is None:
            return False
        self._session_renamed(session_id, new_session_name)
        self.session_selector.set_session_name(session_id, new_session_name)
        return True
    
    def update_session_data(self, session_id: str, data: dict) -> bool:
        if self.graph_sessions.get(session_id) is None:
            return False
        self.graph_sessions[session_id].data_manager.add_measurement_data(data)

    def get_session_id(self, session_name: str) -> int:
        logger.info(f"get_session_id {session_name}")
        for session_id in self.graph_sessions.keys():
            if self.graph_sessions[session_id].session_name == session_name:
                return session_id
        return None
    
    def get_session_name(self, session_id: str) -> str:
        logger.info(f"get_session_name {session_id} list: {self.graph_sessions}")
        if self.graph_sessions.get(session_id) is None:
            logger.warning(f"Session {session_id} not found")
            return None
        return self.graph_sessions[session_id].session_name
    
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

    test_class = running_exp_test(my_session_class, 65, 0.1)
    test_class.run()

    sys.exit(app.exec_())

    # py-spy record --native -o profile.svg -- python C:\Users\zahidovds\Desktop\virtual_for_uswindsens\main\graph\online_graph.py
