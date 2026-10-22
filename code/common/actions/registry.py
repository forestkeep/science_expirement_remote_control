from PyQt5.QtCore import QObject
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMenu
import logging

logger = logging.getLogger(__name__)


class ActionRegistry(QObject):
    """
    Центральный реестр действий. Новые фичи регистрируют QAction здесь,
    а меню и тулбары строятся из реестра — не наоборот.
    Контекст — строка ('curve', 'plot', 'session', ...), по ней группируются действия.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = {}  # action_id -> {"config": dict, "action": QAction}

    def register(self, action_id: str, text: str, callback, *,
                 shortcut: str = None, context: str = None,
                 checkable: bool = False, icon: str = None,
                 tooltip: str = None) -> QAction:
        if action_id in self._entries:
            logger.warning(f"Action '{action_id}' already registered; overwriting")

        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        if checkable:
            action.setCheckable(True)
        if icon:
            action.setIcon(QIcon(icon))
        if tooltip:
            action.setToolTip(tooltip)
        action.triggered.connect(lambda checked=False, cb=callback: cb())

        self._entries[action_id] = {
            "config": {
                "id": action_id, "text": text, "context": context,
                "checkable": checkable, "shortcut": shortcut,
            },
            "action": action,
        }
        return action

    def get(self, action_id: str):
        entry = self._entries.get(action_id)
        return entry["action"] if entry else None

    def get_actions_for_context(self, context: str) -> list:
        return [e["action"] for e in self._entries.values()
                if e["config"]["context"] == context]

    def has_context(self, context: str) -> bool:
        return any(e["config"]["context"] == context for e in self._entries.values())

    def add_actions_to_menu(self, menu: QMenu, context: str) -> list:
        """Добавить все действия контекста в существующее меню. Возвращает добавленные."""
        added = []
        for action in self.get_actions_for_context(context):
            menu.addAction(action)
            added.append(action)
        return added

    def remove(self, action_id: str) -> None:
        self._entries.pop(action_id, None)