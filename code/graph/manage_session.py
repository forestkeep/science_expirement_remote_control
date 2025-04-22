from PyQt5.QtWidgets import (QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QHBoxLayout, QVBoxLayout, QPushButton, QMenu, QAbstractItemView,
                             QLabel, QAction, QLineEdit, QFileDialog,)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPoint
from PyQt5.QtGui import QIcon, QContextMenuEvent, QPixmap

import logging
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QCheckBox, QHBoxLayout,QLabel,
                             QListWidget, QSizePolicy, QVBoxLayout, QWidget, QPushButton, QSpacerItem, QComboBox)
from PyQt5.QtWidgets import (QApplication, QCheckBox, QFileDialog, QHBoxLayout,
                             QLabel, QListWidget, QListWidgetItem, QPushButton,
                             QSizePolicy, QSpacerItem, QVBoxLayout, QWidget, QDialog, QComboBox, QLineEdit)
from PyQt5.QtGui import QFont, QFontMetrics
import pandas as pd
import numpy as np

try:
    from calc_values_for_graph import ArrayProcessor
    from colors import GColors, cold_colors, warm_colors
    from Link_data_import_win import Check_data_import_win
    from curve_data import linearData
    from Message_graph import messageDialog
    from dataManager import graphDataManager
except:
    from graph.calc_values_for_graph import ArrayProcessor
    from graph.colors import GColors, cold_colors, warm_colors
    from graph.Link_data_import_win import Check_data_import_win
    from graph.curve_data import linearData
    from graph.Message_graph import messageDialog
    from graph.dataManager import graphDataManager


logger = logging.getLogger(__name__)

class SessionWidget(QWidget):
    session_selected = pyqtSignal(str)  # session_id
    session_deleted = pyqtSignal(int)
    import_data_requested = pyqtSignal()
    import_oscillograms_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sessions_data = []  # Хранилище данных сессий
        self.init_ui()
        
    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.btn_import_data = QPushButton("Импортировать данные")
        self.btn_import_osc = QPushButton("Импортировать осциллограммы")
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_import_data)
        button_layout.addWidget(self.btn_import_osc)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["ID", "Имя", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)  # Включаем контекстное меню
        self.table.customContextMenuRequested.connect(self.show_context_menu)  # Подключаем обработчик
        
        self.layout.addLayout(button_layout)
        self.layout.addWidget(self.table)
        
        # Сигналы
        self.btn_import_data.clicked.connect(self.import_data_requested)
        self.btn_import_osc.clicked.connect(self.import_oscillograms_requested)
        self.table.cellDoubleClicked.connect(self._on_cell_double_click)
        self.table.cellClicked.connect(self._on_cell_clicked)

    def update_sessions(self, sessions):
        print(sessions)
        self.sessions_data = sessions  # Сохраняем данные
        self.table.setRowCount(len(sessions))
        for row, session in enumerate(sessions):
            self.table.setItem(row, 0, QTableWidgetItem(str(session['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(session['name']))
            # Статус с иконкой (колонка 1)
            status_label = QLabel()
            status_label.setAlignment(Qt.AlignCenter)
            status_label.setPixmap(self._get_status_icon(session['status']))
            self.table.setCellWidget(row, 2, status_label)

    def _get_status_icon(self, status):
        # Пример реализации (замените на свои иконки)
        icon_path = ":/icons/status_ok.png" if status == "ok" else ":/icons/status_error.png"
        return QPixmap(icon_path).scaled(20, 20)

    def show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        
        rename_action = QAction("Переименовать", self)
        delete_action = QAction("Удалить", self)
        desc_action = QAction("Добавить описание", self)
        
        menu.addAction(rename_action)
        menu.addAction(delete_action)
        menu.addAction(desc_action)
        
        selected_row = self.table.rowAt(pos.y())
        if selected_row == -1:
            return
        
        # Подключаем действия с передачей номера строки
        rename_action.triggered.connect(lambda: self._start_rename_session(selected_row))
        delete_action.triggered.connect(lambda: self._delete_session(selected_row))
        desc_action.triggered.connect(lambda: self._add_description(selected_row))
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _start_rename_session(self, row):
        if 0 <= row < len(self.sessions_data):
            old_name_item = self.table.item(row, 1)
            self.table.editItem(old_name_item)

    def _delete_session(self, row):
        if 0 <= row < len(self.sessions_data):
            session_id = self.sessions_data[row]['id']
            self.session_deleted.emit(session_id)

    def _add_description(self, row):
        # Реализация через диалог или inline редактирование
        pass

    def _on_cell_double_click(self, row, col):
        if col == 1:  # Только для колонки с именем
            self._start_rename_session(row)

    def _on_cell_clicked(self, row, col):
        session_name = self.table.item(row, 0).text()
        self.session_selected.emit(session_name)

class SessionController(QObject):
    current_session_changed = pyqtSignal(int)
    session_name_changed = pyqtSignal(str, str)
    session_deleted = pyqtSignal(int)
    new_data_imported = pyqtSignal(str, int, dict)

    def __init__(self):
        super().__init__()
        self.sessions = []  # Пример данных: [{'id': 1, 'name': 'test', 'status': 'ok'}]
        self.widget = SessionWidget()
        
        # Подключение сигналов
        self.widget.session_selected.connect(self.handle_session_selected)
        self.widget.session_deleted.connect(self.handle_session_deleted)
        self.widget.import_data_requested.connect(self.handle_import_data)
        self.widget.import_oscillograms_requested.connect(self.handle_import_osc)

    def update_view(self):
        self.widget.update_sessions(self.sessions)

    def handle_session_selected(self, session_name):
        print(f"Selected session: {session_name}")
        for session in self.sessions:
            if session['name'] == session_name:
                self.current_session_changed.emit(session['id'])
                print(session['id'])
                break

    def add_session(self, session_data):
        self.sessions.append(session_data)
        self.update_view()

    def handle_session_deleted(self, session_id):
        # Логика удаления сессии
        self.sessions = [s for s in self.sessions if s['id'] != session_id]
        self.session_deleted.emit(session_id)
        self.update_view()

    def get_all_ids(self):
        return [s['id'] for s in self.sessions]
    
    def get_free_id(self):
        return max(self.get_all_ids(), default=0) + 1

    def handle_import_data(self):

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, ans = QFileDialog.getOpenFileName(
            caption=QApplication.translate("GraphWindow", "укажите путь импорта"),
            directory="",
            filter="Книга Excel (*.xlsx)",
            options=options,
        )
        
        if fileName:
            if ans == "Книга Excel (*.xlsx)":

                df = pd.read_excel(fileName, engine='openpyxl')

                df = df.dropna(axis=1, how='all')

                df_col_type = type(df.columns[0])

                window = Check_data_import_win(sorted([str(col) for col in df.columns]))
                ans = window.exec_()
                if ans == QDialog.Accepted: 
                    selected_columns = [df_col_type(cb.text()) for cb in window.checkboxes if cb.isChecked()]
                else:
                    return
                
                if not selected_columns:
                    logger.warning("No selected columns. Import aborted")
                    return

                result = {}
                errors_col = []

                for col in selected_columns:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='raise')
                    except ValueError:
                        errors_col.append(str(col))
                        continue

                    
                if errors_col != []:
                    res = ', '.join(errors_col)
                    text = QApplication.translate("GraphWindow", "В столбцах {res} обнаружены данные, которые не получается преобразовать в числа.\nПри построение эти точки будут пропущены.")
                    text = text.format(res = res)
                    message = messageDialog(
                        title = QApplication.translate("GraphWindow","Сообщение"),
                        text= text
                    )
                    message.exec_()
                    
                for col in selected_columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    col_ = str(col).replace('(', '[').replace(')', ']')
                    buf = np.array( df[col].tolist())
                    result[col_] = [ buf, np.array([i for i in range(len(buf))]) ]

                id = self.get_free_id()
                self.add_session({'id': id, 'name': fileName, 'status': 'imported'})
                self.new_data_imported.emit(fileName, id, result)

    def handle_import_osc(self):
        # Логика импорта осциллограмм
        pass

# Пример использования
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    controller = SessionController()
    
    # Тестовые данные
    controller.sessions = [
        {'id': 1, 'name': 'Session 1', 'status': 'ok'},
        {'id': 2, 'name': 'Session 2', 'status': 'error'},
        {'id': 3, 'name': 'Session 3', 'status': 'imported'}
    ]
    controller.update_view()

    controller.add_session({'id': 4, 'name': 'Session 4', 'status': 'ok'})

    print(controller.get_all_ids())
    print(controller.get_free_id())
    
    controller.widget.show()
    sys.exit(app.exec_())