from PyQt5.QtWidgets import (QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QHBoxLayout, QVBoxLayout, QPushButton, QMenu, QAbstractItemView,
                             QAction, QFileDialog, QApplication, QDialog, QTextEdit, QDialogButtonBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPoint

import logging

import pandas as pd
import numpy as np

from graph.Link_data_import_win import Check_data_import_win, SheetSelectionDialog
from graph.Message_graph import messageDialog

logger = logging.getLogger(__name__)

class ButtonsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    def init_ui(self):
        self.btn_import_data = QPushButton(QApplication.translate("filters","Импортировать данные"))
        self.btn_import_osc = QPushButton(QApplication.translate("filters","Импортировать осциллограммы"))
        self.btn_compare_sessions = QPushButton(QApplication.translate("filters","Сравнение сессий"))
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_import_data)
        button_layout.addWidget(self.btn_import_osc)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_compare_sessions)

class SessionWidget(QWidget):
    session_selected = pyqtSignal(str)
    session_deleted = pyqtSignal(str)

    session_renamed = pyqtSignal(str, str)  # session_id, new_name
    session_description_updated = pyqtSignal(str, str)  # session_id, new_description


    def __init__(self, parent=None):
        super().__init__(parent)
        self.sessions_data = []
        self.init_ui()
        
    def init_ui(self):
        self.layout = QVBoxLayout(self)
              
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", QApplication.translate("filters","Имя"), QApplication.translate("filters","Статус")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        self.layout.addWidget(self.table)

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
        """Открывает модальное окно для редактирования описания сессии"""
        if 0 <= row < len(self.sessions_data):
            session = self.sessions_data[row]
            session_id = session['id']
            
            # Получаем текущее описание, если оно есть
            current_description = session.get('description', '')
            
            # Создаем диалоговое окно
            dialog = QDialog(self)
            dialog.setWindowTitle("Редактирование описания")
            dialog.setModal(True)
            dialog.resize(400, 300)
            
            layout = QVBoxLayout(dialog)
            
            # Текстовое поле для описания
            text_edit = QTextEdit()
            text_edit.setPlainText(current_description)
            text_edit.setPlaceholderText("Введите описание сессии...")
            layout.addWidget(text_edit)
            
            # Кнопки OK и Cancel
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            # Показываем диалог и обрабатываем результат
            if dialog.exec_() == QDialog.Accepted:
                new_description = text_edit.toPlainText()
                
                # Обновляем данные сессии
                session['description'] = new_description
                
                # Испускаем сигнал об обновлении описания
                self.session_description_updated.emit(session_id, new_description)

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
    session_description_changed = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.sessions = []  # Пример данных: [{'id': 1, 'name': 'test', 'status': 'ok'}]
        self.widget = SessionWidget()
        
        self.widget.session_selected.connect(self.handle_session_selected)
        self.widget.session_deleted.connect(self.handle_session_deleted)
        self.widget.session_renamed.connect(self._session_renamed)
        self.widget.session_description_updated.connect(self._session_description_updated)

    def _session_description_updated(self, session_id, new_description):
        for session in self.sessions:
            if session['id'] == session_id:
                session['description'] = new_description
                logger.info(f"session_description_changed emitted {session_id}")
                self.session_description_changed.emit(session_id, str(new_description))
                break
    
    def update_session_description(self, session_id, new_description):
        for session in self.sessions:
            if session['id'] == session_id:
                session['description'] = new_description
                self.widget.update_sessions(self.sessions)
                break

    def _session_renamed(self, session_id, new_name):
        for session in self.sessions:
            if session['id'] == session_id:
                logger.info(f"session_name_changed emitted id:{session_id} last_name:{session['name']} new_name:{new_name}")
                session['name'] = new_name
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