from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QMenu,
    QAction, QApplication, QDialog, QTextEdit, QDialogButtonBox,
    QTabBar, QToolButton, QInputDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPoint
from PyQt5.QtGui import QColor, QIcon, QPixmap, QPainter, QBrush, QPen

import logging

logger = logging.getLogger(__name__)

STATUS_COLORS = {
    "running":       QColor("#4aa3f8"),
    "downloaded":    QColor("#c8c8c8"),
    "imported":      QColor("#c8c8c8"),
    "ok":            QColor("#7ad07a"),
    "Exp completed": QColor("#7ad07a"),
}

STATUS_LABELS = {
    "running":       "выполняется",
    "downloaded":    "загружена",
    "imported":      "импортирована",
    "Exp completed": "завершена",
    "ok":            "завершена",
}

class SessionTabBar(QTabBar):
    """QTabBar с сигналами: двойной клик по вкладке и контекстное меню по вкладке."""

    tab_double_clicked = pyqtSignal(int)
    tab_context_menu = pyqtSignal(int, QPoint)

    def mouseDoubleClickEvent(self, event):
        idx = self.tabAt(event.pos())
        if idx >= 0:
            self.tab_double_clicked.emit(idx)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        idx = self.tabAt(event.pos())
        if idx >= 0:
            self.tab_context_menu.emit(idx, event.globalPos())
            event.accept()
            return
        super().contextMenuEvent(event)


class SessionWidget(QWidget):
    session_selected = pyqtSignal(str)
    session_deleted = pyqtSignal(str)
    session_renamed = pyqtSignal(str, str)
    session_description_updated = pyqtSignal(str, str)
    session_reordered = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sessions_data = []
        self._suppress = False
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        self.tab_bar = SessionTabBar()
        self.tab_bar.setExpanding(False)
        self.tab_bar.setMovable(True)          # ← включено перетаскивание
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.setUsesScrollButtons(True)
        self.tab_bar.setElideMode(Qt.ElideRight)
        self.tab_bar.setDrawBase(False)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)
        self.tab_bar.tab_double_clicked.connect(self._on_tab_double_clicked)
        self.tab_bar.tab_context_menu.connect(self._on_tab_context_menu)
        self.tab_bar.tabMoved.connect(self._on_tab_moved)   # ← новое

        self.all_sessions_btn = QToolButton()
        self.all_sessions_btn.setText("▾")
        self.all_sessions_btn.setToolTip("Все сессии")
        self.all_sessions_btn.setPopupMode(QToolButton.InstantPopup)
        self.all_sessions_menu = QMenu(self.all_sessions_btn)
        self.all_sessions_btn.setMenu(self.all_sessions_menu)

        layout.addWidget(self.tab_bar, 1)
        layout.addWidget(self.all_sessions_btn)

    # ------------------------------------------------------------------
    # Иконка статуса (цветной кружок)
    # ------------------------------------------------------------------
    @staticmethod
    def _status_icon(status: str) -> QIcon:
        color = STATUS_COLORS.get(status, QColor("#ffffff"))
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(160), 1))
        painter.drawEllipse(2, 2, 8, 8)
        painter.end()
        return QIcon(pixmap)

    def _tooltip_for(self, session: dict) -> str:
        name = session.get('name', '')
        status = session.get('status', '')
        label = STATUS_LABELS.get(status, status)
        desc = session.get('description') or ''
        parts = [name, f"Статус: {label}"]
        if desc:
            parts.append(desc)
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Синхронизация из контроллера
    # ------------------------------------------------------------------

    def update_session(self, session):
        for i, s in enumerate(self.sessions_data):
            if s['id'] == session['id']:
                self.sessions_data[i] = dict(session)
                break
        self.refresh_tab(session['id'])

    def update_sessions(self, sessions):
        """Полная перестройка всех вкладок из списка сессий."""
        self.sessions_data = list(sessions)
        self._rebuild_view()

    def add_session_view(self, session):
        self.sessions_data.append(session)
        self._rebuild_view()

    def select_session(self, session_id: str):
        """Программно выбрать вкладку без эмита session_selected."""
        self._select_without_emit(session_id)

    # ------------------------------------------------------------------
    def _rebuild_view(self):
        current_id = self._current_id()

        self._suppress = True
        try:
            while self.tab_bar.count() > 0:
                self.tab_bar.removeTab(0)

            for session in self.sessions_data:
                status = session.get('status', '')
                name = session.get('name', '')
                icon = self._status_icon(status)
                tip = self._tooltip_for(session)

                idx = self.tab_bar.addTab(icon, name)
                self.tab_bar.setTabToolTip(idx, tip)
                self.tab_bar.setTabData(idx, session['id'])
                if status == "running":
                    self.tab_bar.setTabButton(idx, QTabBar.RightSide, None)
        finally:
            self._suppress = False

        self._rebuild_all_sessions_menu()

        if current_id and any(s['id'] == current_id for s in self.sessions_data):
            self._select_without_emit(current_id)
        elif self.sessions_data:
            self._select_without_emit(self.sessions_data[0]['id'])

    def _on_tab_moved(self, from_idx: int, to_idx: int):
        if self._suppress:
            return
        if (0 <= from_idx < len(self.sessions_data)
                and 0 <= to_idx < len(self.sessions_data)):
            item = self.sessions_data.pop(from_idx)
            self.sessions_data.insert(to_idx, item)
            self._rebuild_all_sessions_menu()
            self.session_reordered.emit([s['id'] for s in self.sessions_data])

    def _rebuild_all_sessions_menu(self):
        self.all_sessions_menu.clear()
        current_id = self._current_id()
        for session in self.sessions_data:
            icon = self._status_icon(session.get('status', ''))
            label = session.get('name', '')
            action = QAction(icon, label, self.all_sessions_menu)
            action.setCheckable(True)
            action.setChecked(session['id'] == current_id)
            action.triggered.connect(
                lambda checked=False, sid=session['id']: self._on_menu_select(sid)
            )
            self.all_sessions_menu.addAction(action)

    def _select_without_emit(self, session_id: str):
        self._suppress = True
        try:
            for i in range(self.tab_bar.count()):
                if self.tab_bar.tabData(i) == session_id:
                    self.tab_bar.setCurrentIndex(i)
                    break
        finally:
            self._suppress = False

    def _current_id(self):
        idx = self.tab_bar.currentIndex()
        if 0 <= idx < self.tab_bar.count():
            return self.tab_bar.tabData(idx)
        return None

    def _find_session(self, session_id):
        for s in self.sessions_data:
            if s['id'] == session_id:
                return s
        return None

    # ------------------------------------------------------------------
    # Обработчики
    # ------------------------------------------------------------------
    def _on_tab_changed(self, index: int):
        if self._suppress:
            return
        if 0 <= index < self.tab_bar.count():
            sid = self.tab_bar.tabData(index)
            if sid:
                self.session_selected.emit(sid)

    def _on_tab_close_requested(self, index: int):
        if 0 <= index < self.tab_bar.count():
            sid = self.tab_bar.tabData(index)
            if sid:
                self.session_deleted.emit(sid)

    def _on_tab_double_clicked(self, index: int):
        if 0 <= index < self.tab_bar.count():
            sid = self.tab_bar.tabData(index)
            self._rename_session(sid)

    def _on_tab_context_menu(self, index: int, global_pos: QPoint):
        sid = self.tab_bar.tabData(index)
        if sid is None:
            return
        self._show_context_menu(sid, global_pos)

    def _on_menu_select(self, session_id: str):
        self._select_without_emit(session_id)
        self.session_selected.emit(session_id)

    # ------------------------------------------------------------------
    def _show_context_menu(self, session_id: str, global_pos: QPoint):
        menu = QMenu(self)

        rename_action = QAction("Переименовать", menu)
        rename_action.triggered.connect(lambda: self._rename_session(session_id))
        menu.addAction(rename_action)

        desc_action = QAction("Описание...", menu)
        desc_action.triggered.connect(lambda: self._edit_description(session_id))
        menu.addAction(desc_action)

        menu.addSeparator()

        delete_action = QAction("Удалить", menu)
        delete_action.triggered.connect(lambda: self.session_deleted.emit(session_id))
        menu.addAction(delete_action)

        menu.exec_(global_pos)

    def _rename_session(self, session_id: str):
        session = self._find_session(session_id)
        if session is None:
            return
        old_name = session.get('name', '')
        new_name, ok = QInputDialog.getText(
            self, "Переименовать сессию", "Новое имя:", text=old_name
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return
        self.session_renamed.emit(session_id, new_name)

    def refresh_tab(self, session_id: str):
        """Обновить текст, иконку статуса и tooltip вкладки из self.sessions_data."""
        for s in self.sessions_data:
            if s['id'] == session_id:
                for i in range(self.tab_bar.count()):
                    if self.tab_bar.tabData(i) == session_id:
                        self.tab_bar.setTabText(i, s.get('name', ''))
                        self.tab_bar.setTabIcon(i, self._status_icon(s.get('status', '')))
                        self.tab_bar.setTabToolTip(i, self._tooltip_for(s))
                        break
                self._rebuild_all_sessions_menu()
                return

    def _edit_description(self, session_id: str):
        session = self._find_session(session_id)
        if session is None:
            return
        current = session.get('description', '') or ''

        dialog = QDialog(self)
        dialog.setWindowTitle("Описание сессии")
        dialog.setModal(True)
        dialog.resize(400, 300)

        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setPlainText(current)
        text_edit.setPlaceholderText("Введите описание сессии...")
        layout.addWidget(text_edit)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(dialog.accept)
        bbox.rejected.connect(dialog.reject)
        layout.addWidget(bbox)

        if dialog.exec_() == QDialog.Accepted:
            new_desc = text_edit.toPlainText()
            self.session_description_updated.emit(session_id, new_desc)

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
        self.widget.session_reordered.connect(self._session_reordered)

    def _session_description_updated(self, session_id, new_description):
        logger.info(f"_session_description_updated {session_id} {new_description}")
        for session in self.sessions:
            if session['id'] == session_id:
                session['description'] = new_description
                self.widget.update_session(session)
                self.session_description_changed.emit(session_id, str(new_description))
                break

    def _session_reordered(self, ordered_ids):
        by_id = {s['id']: s for s in self.sessions}
        self.sessions = [by_id[sid] for sid in ordered_ids if sid in by_id]
    
    def update_session_description(self, session_id, new_description):
        logger.info(f"update_session_description {session_id=} {new_description}")
        for session in self.sessions:
            if session['id'] == session_id:
                    session['description'] = new_description
                    self.widget.update_session(session)
                    break

    def _session_renamed(self, session_id, new_name):
        logger.info(f"_session_renamed {session_id} {new_name}")
        for session in self.sessions:
            if session['id'] == session_id:
                session['name'] = new_name
                self.widget.update_session(session)
                self.session_name_changed.emit(session_id, str(new_name))
                break

    def update_view(self):
        logger.info(f"update_view, session list : {self.sessions}")
        self.widget.update_sessions(self.sessions)

    def handle_session_selected(self, session_id):
        for session in self.sessions:
            if session['id'] == session_id:
                logger.info(f"current_session_changed emitted {session_id}")
                self.current_session_changed.emit(session['id'])
                break

    def set_current_session(self, session_id):
        """Синхронизировать выбранную вкладку без эмита current_session_changed."""
        self.widget.select_session(session_id)

    def set_session_name(self, session_id, name: str):
        logger.info(f"set_session_name {session_id} {name}")
        for session in self.sessions:
            if session['id'] == session_id:
                session['name'] = name
                self.widget.update_session(session)
                break

    def set_session_status(self, session_id, status: str):
        logger.info(f"set_session_status {session_id} {status} list: {self.sessions}")
        for session in self.sessions:
            if session['id'] == session_id:
                session['status'] = status
                self.update_view()
                break

    def add_session(self, session_data: dict):
        logger.info(f"Adding session {session_data}")
        logger.info(f"list before add: {self.sessions}")
        self.sessions.append(session_data)
        self.widget.add_session_view(session_data)
        #self.update_view()

    def handle_session_deleted(self, session_id):
        """Сигнал от вкладки. Реальное удаление (с подтверждением) — в
        sessionController.delete_session, который сам вызовет
        SessionSelectControl.delete_session после QMessageBox.Yes."""
        self.session_deleted.emit(session_id)

    def delete_session(self, session_id):
        logger.info(f"Deleting session {session_id}")
        logger.info(f"list before delete: {self.sessions}")
        self.sessions[:] = [s for s in self.sessions if s['id'] != session_id]
        self.update_view()

    def get_all_ids(self):
        return [s['id'] for s in self.sessions]
    
    def get_free_id(self) -> str:
        all_ids = self.get_all_ids()
        logger.info(f"all_ids: {all_ids}")
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