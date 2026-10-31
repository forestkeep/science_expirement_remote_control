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
    sessions_changed = pyqtSignal()        # принудительный ре-рендер при перезагрузке

    def __init__(self, session_controller, parent=None):
        super().__init__(parent)
        self.session_controller = session_controller
        self._attached: Set[str] = set()
        # sid -> [(kind, obj, callback), ...]
        self._connections: Dict[str, list] = {}

        self._attach_all(emit_sessions=False)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(3000)
        self._poll_timer.timeout.connect(self._attach_all)
        self._poll_timer.start()

    # ------------------------------------------------------------------
    def _attach_all(self, emit_sessions: bool = True) -> None:
        try:
            sessions = getattr(self.session_controller, "graph_sessions", {}) or {}
        except Exception:
            return

        current_ids = set(sessions.keys())

        # 1. Отвязать от исчезнувших сессий
        for sid in list(self._attached):
            if sid not in current_ids:
                self.detach_session(sid)

        # 2. Привязать новые
        new_attached = False
        for sid in current_ids:
            if sid in self._attached:
                continue
            self._attach_session(sid)
            new_attached = True

        if new_attached and emit_sessions:
            self.sessions_changed.emit()

    def _attach_session(self, sid: str) -> None:
        sess = self.session_controller.graph_sessions.get(sid)
        if sess is None:
            return

        dm = getattr(sess, "data_manager", None)
        if dm is not None and hasattr(dm, "val_parameters_added"):
            cb = lambda _data=None, _sid=sid: self._emit_source(_sid)
            dm.val_parameters_added.connect(cb)
            self._connections.setdefault(sid, []).append(("dm", dm, cb))

        ac = getattr(sess, "analysis_controller", None)
        if ac is not None and hasattr(ac, "artifacts_changed"):
            cb = lambda _sid=sid: self._emit_artifacts(_sid)
            ac.artifacts_changed.connect(cb)
            self._connections.setdefault(sid, []).append(("ac", ac, cb))

        self._attached.add(sid)

    def detach_session(self, sid: str) -> None:
        """Отключить все подписки от сессии (вызывается автоматически при
        исчезновении sid из graph_sessions, либо вручную)."""
        for kind, obj, cb in self._connections.pop(sid, []):
            try:
                if kind == "dm":
                    obj.val_parameters_added.disconnect(cb)
                else:
                    obj.artifacts_changed.disconnect(cb)
            except (TypeError, RuntimeError):
                pass
        self._attached.discard(sid)

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    def ensure_all_attached(self) -> None:
        """Форсировать attach и сообщить о перезагрузке сессий."""
        self._attach_all(emit_sessions=False)
        self.sessions_changed.emit()

    def shutdown(self) -> None:
        self._poll_timer.stop()
        for sid in list(self._attached):
            self.detach_session(sid)