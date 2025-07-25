from PyQt5.QtWidgets import (QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QHBoxLayout, QVBoxLayout, QPushButton, QMenu, QAbstractItemView,
                             QAction, QFileDialog, QApplication, QDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPoint

import logging

import pandas as pd
import numpy as np

from graph.Link_data_import_win import Check_data_import_win
from graph.Message_graph import messageDialog

logger = logging.getLogger(__name__)

class SessionWidget(QWidget):
    session_selected = pyqtSignal(str)
    session_deleted = pyqtSignal(str)
    import_data_requested = pyqtSignal()
    import_oscillograms_requested = pyqtSignal()
    session_renamed = pyqtSignal(str, str)  # session_id, new_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sessions_data = []
        self.init_ui()
        
    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.btn_import_data = QPushButton(QApplication.translate("filters","Импортировать данные"))
        self.btn_import_osc = QPushButton(QApplication.translate("filters","Импортировать осциллограммы"))
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_import_data)
        button_layout.addWidget(self.btn_import_osc)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", QApplication.translate("filters","Имя"), QApplication.translate("filters","Статус")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        self.layout.addWidget(self.table)
        self.layout.addLayout(button_layout)
        
        self.btn_import_data.clicked.connect(self.import_data_requested)
        self.btn_import_osc.clicked.connect(self.import_oscillograms_requested)
        self.table.cellDoubleClicked.connect(self._on_cell_double_click)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.model().dataChanged.connect(self._on_data_changed)

    def _on_data_changed(self, top_left, bottom_right):
        if top_left.column() <= 1 <= bottom_right.column():
            row = top_left.row()
            session_id_item = self.table.item(row, 0)
            new_name_item = self.table.item(row, 1)
            
            if session_id_item and new_name_item:
                session_id = session_id_item.text()
                new_name = new_name_item.text()
                
                for session in self.sessions_data:
                    if session['id'] == session_id:
                        session['name'] = new_name
                        break
                
                self.session_renamed.emit(session_id, new_name)

    def update_sessions(self, sessions):
        self.sessions_data = sessions
        self.table.setRowCount(len(sessions))
        for row, session in enumerate(sessions):
            self.table.setItem(row, 0, QTableWidgetItem(session['id']))
            self.table.setItem(row, 1, QTableWidgetItem(session['name']))
            self.table.setItem(row, 2, QTableWidgetItem(session['status']))

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
        if col == 1:
            self._start_rename_session(row)

    def _on_cell_clicked(self, row, col):
        session_id = self.table.item(row, 0).text()
        self.session_selected.emit(session_id)

class SessionSelectControl(QObject):
    current_session_changed = pyqtSignal(str)
    session_name_changed = pyqtSignal(str, str)
    session_deleted = pyqtSignal(str)
    new_data_imported = pyqtSignal(str, str, dict)

    def __init__(self):
        super().__init__()
        self.sessions = []  # Пример данных: [{'id': 1, 'name': 'test', 'status': 'ok'}]
        self.widget = SessionWidget()
        
        self.widget.session_selected.connect(self.handle_session_selected)
        self.widget.session_deleted.connect(self.handle_session_deleted)
        self.widget.import_data_requested.connect(self.handle_import_data)
        self.widget.import_oscillograms_requested.connect(self.handle_import_osc)
        self.widget.session_renamed.connect(self._session_renamed)

    def _session_renamed(self, session_id, new_name):
        for session in self.sessions:
            if session['id'] == session_id:
                session['name'] = new_name
                logger.info(f"session_name_changed emitted {session_id}")
                self.session_name_changed.emit(session_id, str(new_name))

    def update_view(self):
        self.widget.update_sessions(self.sessions)

    def handle_session_selected(self, session_id):
        for session in self.sessions:
            if session['id'] == session_id:
                logger.info(f"current_session_changed emitted {session_id}")
                self.current_session_changed.emit(session['id'])
                break

    def set_current_session(self, session_id):
        for session in self.sessions:
            if session['id'] == session_id:
                logger.info(f"current_session_changed emitted {id}")
                self.current_session_changed.emit(session['id'])
                break

    def set_session_name(self, session_id, name: str):
        for session in self.sessions:
            if session['id'] == session_id:
                session['name'] = name
                self.update_view()

    def set_session_status(self, session_id, status: str):
        for session in self.sessions:
            if session['id'] == session_id:
                session['status'] = status
                self.update_view()
                break

    def add_session(self, session_data: dict):
        logger.info(f"Adding session {session_data}")
        self.sessions.append(session_data)
        self.update_view()

    def handle_session_deleted(self, session_id):
        self.session_deleted.emit(session_id)

    def delete_session(self, session_id):
        self.sessions = [s for s in self.sessions if s['id'] != session_id]
        self.update_view()

    def get_all_ids(self):
        return [s['id'] for s in self.sessions]
    
    def get_free_id(self) -> str:
        all_ids = self.get_all_ids()
        new_id = str( max( [int(s) for s in self.get_all_ids()], default=0) + 1)
        return new_id

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
                #self.add_session({'id': id, 'name': fileName, 'status': 'imported'})
                logger.info(f"Data imported emitted {id}")
                self.new_data_imported.emit(fileName, id, result)
                #self.add_session({'id': id, 'name': fileName, 'status': 'imported'})

    def handle_import_osc(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, ans = QFileDialog.getOpenFileName(
            caption=QApplication.translate("GraphWindow","укажите путь импорта"),
            directory="",
            filter="Книга Excel (*.xlsx)",
            options=options,
        )
        
        #fileName = r"C:\Users\zahidovds\Desktop\testimport.xlsx"
        #ans = "Книга Excel (*.xlsx)"
        
        if fileName:
            if ans == "Книга Excel (*.xlsx)":
                df = pd.read_excel(fileName, engine='openpyxl')

                if 'time' not in df.columns:
                    self.is_time_column = False

                df = df.dropna(axis=1, how='all')

                window = Check_data_import_win(sorted([str(col) for col in df.columns]), None, True)
                ans = window.exec_()
                if ans == QDialog.Accepted: 
                    selected_step = window.step_combo.currentText()
                    selected_channels = [cb.text() for cb in window.checkboxes if cb.isChecked()]
                else:
                    return

                selected_channels.append(selected_step)
                errors_col = []

                for col in selected_channels:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='raise')
                    except ValueError:
                        errors_col.append(col)
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

                selected_channels.pop()

                import_time_scale_column = pd.to_numeric(df[selected_step], errors='coerce')

                import_time_scale = None
                for scale in import_time_scale_column:
                    if isinstance(scale, (float, int)) and scale > 0:
                        import_time_scale = scale
                        break

                if import_time_scale is None:
                    message = messageDialog(
                        title = QApplication.translate("GraphWindow","Сообщение"),
                        text= QApplication.translate("GraphWindow","Выбранный шаг не является числом или равен нулю, проверьте столбец с шагом времени")
                    )
                    return

                dev = {}
                result = {}
                df = df[[col for col in df.columns if col in selected_channels]]

                for col in selected_channels:
                    df[col] = (pd.to_numeric(df[col], errors='coerce'))
                df = df.dropna()

                '''
                for col in selected_channels:
                    col_ = col.replace('(', '[').replace(')', ']') + ' wavech'
                    volt_val = np.array( df[col].tolist() )
                    dev[col] = {col_: {0 : volt_val}, "scale": [import_time_scale for i in range(len(volt_val))]}
                '''
                    
                for index, col in enumerate(selected_channels):
                    col_ = str(col).replace('(', '[').replace(')', ']')
                    val = np.array( df[col].tolist())
                    result[col_] = {}
                    result[col_]['wavech'] = [ [val], [1]]
                    result[col_]["step"] = [[import_time_scale], [1]]

                '''формат
                data={'DS1104Z_1': {'ch-1_meas': {'wavech': [[[0.04, -0.0, 0.04, 0.04, 0.06, 0.04, 0.02, 0.04, 0.04, -0.0, 0.04, 0.02, 0.04, 0.04, 0.04, 0.02, 0.04, 0.04, 0.04, 0.04, 0.04, 0.06, 0.04, 0.04, 0.04, -0.0, 0.02, 0.02, 0.04, 0.04, 0.04, 0.04, 0.04, 0.02, 0.04, 0.04, 0.04, 0.04, 0.02, 0.04, 0.02, -0.0, 0.02, 0.04, 0.06, 0.04, 0.04, 0.04, 0.04, 0.02, 0.04, 0.04, 0.04, 0.04, 0.02, 0.04, 0.04, 0.02]], [4.367210099939257]],
                  'scale': [[5e-09], [4.367210099939257]], 'step': [[1e-09], [4.367210099939257]]}}}
                '''

                id = self.get_free_id()

                logger.info(f"Data imported emitted {id}")
                self.new_data_imported.emit(fileName, id, result)
                
                #self.add_session({'id': id, 'name': fileName, 'status': 'imported'})
            
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    controller = SessionSelectControl()
    
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