# graph/core/undo_manager.py
"""
Инфраструктура undo/redo для одной сессии.

- UndoCommand   — базовый интерфейс команды.
- SessionUndoManager — менеджер стеков отмены/повтора.
                       Глубина ограничена max_depth; при переполнении
                       самая старая команда вытесняется (FIFO).
"""
from __future__ import annotations

import logging
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

DEFAULT_UNDO_DEPTH = 50


class UndoCommand:
    """Базовый класс команды. Наследники реализуют undo() и redo()."""

    def text(self) -> str:
        """Короткое человекочитаемое описание для UI."""
        return ""

    def undo(self) -> None:
        raise NotImplementedError

    def redo(self) -> None:
        raise NotImplementedError


class SessionUndoManager(QObject):
    """
    Менеджер истории отмен/повторов для ОДНОЙ сессии.

    * Хранит два стека: _undo_stack и _redo_stack.
    * push() добавляет уже выполненную команду и очищает redo.
    * При push(execute=True) команда выполняется внутри push.
    * Глубина ограничена max_depth; лишние старые команды отбрасываются.
    """

    state_changed = pyqtSignal()

    def __init__(self, max_depth: int = DEFAULT_UNDO_DEPTH, parent=None):
        super().__init__(parent)
        self._undo_stack: list[UndoCommand] = []
        self._redo_stack: list[UndoCommand] = []
        self._max_depth = max(1, int(max_depth))
        self._is_applying = False

    # ---------------- state --------------------------------------------
    def can_undo(self) -> bool:
        return bool(self._undo_stack) and not self._is_applying

    def can_redo(self) -> bool:
        return bool(self._redo_stack) and not self._is_applying

    def undo_text(self) -> str:
        return self._undo_stack[-1].text() if self._undo_stack else ""

    def redo_text(self) -> str:
        return self._redo_stack[-1].text() if self._redo_stack else ""

    @property
    def is_applying(self) -> bool:
        return self._is_applying

    # ---------------- commands -----------------------------------------
    def push(self, command: UndoCommand, execute: bool = False) -> None:
        """
        Зарегистрировать команду.

        :param execute: если True — команда вызывается сама через redo()
                        (полезно, когда действие не было выполнено заранее).
        """
        if self._is_applying:
            return
        if execute:
            command.redo()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        while len(self._undo_stack) > self._max_depth:
            self._undo_stack.pop(0)
        self.state_changed.emit()

    def undo(self) -> None:
        if not self.can_undo():
            return
        cmd = self._undo_stack.pop()
        self._is_applying = True
        try:
            cmd.undo()
        except Exception:
            logger.exception("SessionUndoManager: undo failed")
        finally:
            self._is_applying = False
        self._redo_stack.append(cmd)
        self.state_changed.emit()

    def redo(self) -> None:
        if not self.can_redo():
            return
        cmd = self._redo_stack.pop()
        self._is_applying = True
        try:
            cmd.redo()
        except Exception:
            logger.exception("SessionUndoManager: redo failed")
        finally:
            self._is_applying = False
        self._undo_stack.append(cmd)
        self.state_changed.emit()

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.state_changed.emit()
