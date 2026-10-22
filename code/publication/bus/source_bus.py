"""SourceBus: live-подписка на sessionController.

- Слушает `data_manager.val_parameters_added` (батч-сигнал каждые ~1с).
- Слушает `analysis_controller.artifacts_changed` (для data-bound аннотаций).
- Публикует `source_changed(session_id)` и `artifacts_changed(session_id)`.

Так как sessionController не эмитит события «создана новая сессия»,
SourceBus периодически (раз в 3с) делает attach ко всем сессиям.
Это тонкий слой; публикационная модель от него не зависит.
"""
from __future__ import annotations
import logging
from typing import Dict, Set

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class SourceBus(QObject):
    source_changed = pyqtSignal(str)       # session_id
    artifacts_changed = pyqtSignal(str)    # session_id

    def __init__(self, session_controller, parent=None):
        super().__init__(parent)
        self.session_controller = session_controller
        self._attached: Set[str] = set()
        self._attach_all()
        # Периодический scan (см. docstring)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(3000)
        self._poll_timer.timeout.connect(self._attach_all)
        self._poll_timer.start()

    def _attach_all(self) -> None:
        try:
            sessions = getattr(self.session_controller, "graph_sessions", {}) or {}
        except Exception:
            return
        for sid in list(sessions.keys()):
            if sid in self._attached:
                continue
            self._attach_session(sid)

    def _attach_session(self, sid: str) -> None:
        sess = self.session_controller.graph_sessions.get(sid)
        if sess is None:
            return
        dm = getattr(sess, "data_manager", None)
        if dm is not None and hasattr(dm, "val_parameters_added"):
            dm.val_parameters_added.connect(
                lambda _data=None, _sid=sid: self._emit_source(_sid)
            )
        ac = getattr(sess, "analysis_controller", None)
        if ac is not None and hasattr(ac, "artifacts_changed"):
            ac.artifacts_changed.connect(
                lambda _sid=sid: self._emit_artifacts(_sid)
            )
        self._attached.add(sid)

    def _emit_source(self, sid: str) -> None:
        try:
            self.source_changed.emit(sid)
        except Exception:
            logger.exception("source_changed emit failed")

    def _emit_artifacts(self, sid: str) -> None:
        try:
            self.artifacts_changed.emit(sid)
        except Exception:
            logger.exception("artifacts_changed emit failed")

    def ensure_all_attached(self) -> None:
        """Форсировать attach (для явной перезагрузки)."""
        self._attach_all()

    def shutdown(self) -> None:
        self._poll_timer.stop()