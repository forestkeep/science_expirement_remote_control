import logging
from PyQt5.QtCore import QPoint, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QMainWindow,
                             QSizePolicy, QSplitter, QTabWidget, QWidget, QDialog, QAction, QVBoxLayout, QStackedWidget, QFileDialog)

logger = logging.getLogger(__name__)


class CompareWindowMediator:


    def __init__(self, session_id, session_name, alias_manager, graph_session, ses_uuid=None, parent=None):
        """
        :param session_id: идентификатор сессии
        :param session_name: имя сессии
        :param alias_manager: менеджер алиасов (внешний объект)
        :param ses_uuid: UUID сессии (если None, генерируется автоматически)
        :param parent: родительский QWidget для окна (необязательно)
        """
        self.session_id = session_id
        self.session_name = session_name
        self.alias_manager = alias_manager
        self.ses_uuid = ses_uuid
        self.parent = parent

        self.window = None
        self.graph_session = graph_session

        self._create_window()

    def _create_window(self):
        """Создаёт главное окно и помещает в него GraphSession."""
        self.window = QMainWindow(self.parent)
        self.window.setWindowTitle(f"Graph Session: {self.session_name}")

        # Устанавливаем виджет как центральный
        self.window.setCentralWidget(self.graph_session)

        # Подключаем сигнал закрытия GraphSession к обработчику
        self.graph_session.graph_win_close_signal.connect(self._on_graph_session_closed)

    def get_graph_fields(self):
        return self.graph_session.graph_main.graphView

    def _on_graph_session_closed(self, value):
        """
        Вызывается при закрытии виджета GraphSession.
        Закрывает главное окно и выполняет дополнительную очистку при необходимости.
        """
        if self.window:
            self.window.close()
        # Здесь можно добавить дополнительную логику, например, уведомление других частей приложения

    # ------------------- Методы управления окном -------------------
    def show(self):
        """Показывает окно."""
        if self.window:
            self.window.show()

    def hide(self):
        """Скрывает окно."""
        if self.window:
            self.window.hide()

    def close(self):
        """Закрывает окно (и виджет внутри)."""
        if self.window:
            self.window.close()

    def is_visible(self):
        """Возвращает True, если окно видимо."""
        return self.window is not None and self.window.isVisible()

    # ------------------- Методы управления данными и состоянием GraphSession -------------------
    def update_graphics(self, new_data: dict, is_exp_stop=False):
        """
        Передаёт новые данные в GraphSession для обновления графиков.
        :param new_data: словарь с данными
        :param is_exp_stop: флаг окончания эксперимента
        """
        if self.graph_session:
            self.graph_session.update_graphics(new_data, is_exp_stop)

    def set_default(self):
        """Сбрасывает состояние графиков к умолчанию."""
        if self.graph_session:
            self.graph_session.set_default()

    def show_tooltip(self, message, show_while_not_click=False, timeout=3000):
        """
        Показывает всплывающую подсказку внутри GraphSession.
        :param message: текст подсказки
        :param show_while_not_click: если True, подсказка остаётся до клика
        :param timeout: время отображения (мс), если show_while_not_click=False
        """
        if self.graph_session:
            self.graph_session.show_tooltip(message, show_while_not_click, timeout)