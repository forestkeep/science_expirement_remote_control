"""Undo/redo-команды для подсистемы анализа."""
from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List

from PyQt5.QtWidgets import QApplication

from common.undo.manager import UndoCommand

logger = logging.getLogger(__name__)

_TR = lambda s: QApplication.translate("GraphWindow", s)


class _BaseAnalysisCommand(UndoCommand):
    def __init__(self, controller) -> None:
        self.controller = controller


class ApplyAnalysisCommand(_BaseAnalysisCommand):
    def __init__(self, controller, artifact) -> None:
        super().__init__(controller)
        self.artifact = artifact

    def text(self) -> str:
        return _TR("Применение анализа")

    def redo(self) -> None:
        self.controller._do_apply(self.artifact)

    def undo(self) -> None:
        self.controller._do_remove(self.artifact.id)


class RemoveAnalysisCommand(_BaseAnalysisCommand):
    def __init__(self, controller, artifact) -> None:
        super().__init__(controller)
        self.artifact = artifact

    def text(self) -> str:
        return _TR("Удаление результата анализа")

    def redo(self) -> None:
        self.controller._do_remove(self.artifact.id)

    def undo(self) -> None:
        self.controller._do_apply(self.artifact)


class UpdateAnalysisParamsCommand(_BaseAnalysisCommand):
    def __init__(self, controller, artifact_id: str,
                 old_params: Dict[str, Any], new_params: Dict[str, Any],
                 old_payload: Any, new_payload: Any) -> None:
        super().__init__(controller)
        self.artifact_id = artifact_id
        self.old_params = copy.deepcopy(old_params)
        self.new_params = copy.deepcopy(new_params)
        self.old_payload = old_payload
        self.new_payload = new_payload

    def text(self) -> str:
        return _TR("Пересчёт результата анализа")

    def redo(self) -> None:
        self.controller._do_update_params(self.artifact_id, self.new_params,
                                          self.new_payload)

    def undo(self) -> None:
        self.controller._do_update_params(self.artifact_id, self.old_params,
                                          self.old_payload)


class ApplyUncertaintyCommand(_BaseAnalysisCommand):
    """Запись погрешностей в CurveDataStore."""
    def __init__(self, controller, root_name: str, record) -> None:
        super().__init__(controller)
        self.root_name = root_name
        self.record = record

    def text(self) -> str:
        return _TR("Оценка неопределённости")

    def redo(self) -> None:
        self.controller._do_apply_uncertainty(self.root_name, self.record)

    def undo(self) -> None:
        self.controller._do_remove_uncertainty(self.root_name, self.record.id)


class RemoveUncertaintyCommand(_BaseAnalysisCommand):
    def __init__(self, controller, root_name: str, record_id: str) -> None:
        super().__init__(controller)
        self.root_name = root_name
        self.record_id = record_id

    def text(self) -> str:
        return _TR("Удаление оценки неопределённости")

    def redo(self) -> None:
        self.controller._do_remove_uncertainty(self.root_name, self.record_id)

    def undo(self) -> None:
        self.controller._do_restore_uncertainty(self.root_name, self.record_id)


class MacroAnalysisCommand(_BaseAnalysisCommand):
    """Композит для каскадных операций (удаление кривой + её артефактов)."""
    def __init__(self, controller) -> None:
        super().__init__(controller)
        self._commands: List[UndoCommand] = []

    def add(self, cmd: UndoCommand) -> None:
        self._commands.append(cmd)

    def text(self) -> str:
        return _TR("Групповая операция анализа")

    def redo(self) -> None:
        for cmd in self._commands:
            cmd.redo()

    def undo(self) -> None:
        for cmd in reversed(self._commands):
            cmd.undo()