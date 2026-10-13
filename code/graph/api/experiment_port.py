import logging

logger = logging.getLogger(__name__)


class ExperimentPort:
    """Фасад над sessionController для удалённого управления экспериментом."""

    def __init__(self, controller):
        self._controller = controller

    # ------------------------------------------------------------------ #
    # Жизненный цикл сессии                                              #
    # ------------------------------------------------------------------ #

    def start_session(self, name: str, use_timestamps: bool = False,
                      meta: dict = None, uuid: str = None) -> str | bool:
        """Создать live-сессию. Возвращает id или False."""
        return self._controller.start_new_session(
            session_name=name,
            use_timestamps=use_timestamps,
            is_experiment_running=True,
            uuid=uuid,
        )

    def stop_session(self, session_id: str) -> None:
        """Завершить live-сессию."""
        if not self.has_session(session_id):
            logger.warning(f"stop_session: session {session_id} not found")
            return
        self._controller.stop_session_running(session_id)

    # ------------------------------------------------------------------ #
    # Передача данных                                                     #
    # ------------------------------------------------------------------ #

    def push_batch(self, session_id: str, batch: dict) -> bool:
        """
        Принять словарь данных от внешнего модуля.
        Формат — тот же, что у graphDataManager.add_measurement_data.
        """
        if not self.has_session(session_id):
            logger.warning(f"push_batch: session {session_id} not found")
            return False
        return self._controller.update_session_data(session_id, batch)

    def push_measurement(self, session_id: str, entry, time) -> bool:
        """Принять одиночное измерение в формате decode_add_exp_parameters."""
        if not self.has_session(session_id):
            logger.warning(f"push_measurement: session {session_id} not found")
            return False
        return self._controller.decode_add_exp_parameters(session_id, entry, time)

    def decode_add_exp_parameters(self, session_id: str, entry, time) -> bool:
        """Совместимый алиас для старого кода."""
        return self.push_measurement(session_id, entry, time)

    # ------------------------------------------------------------------ #
    # Состояние                                                           #
    # ------------------------------------------------------------------ #

    def get_status(self, session_id: str) -> str | None:
        """'running' | 'stopped' | None, если сессия не найдена."""
        session = self._controller.graph_sessions.get(session_id)
        if session is None:
            return None
        return "running" if session.is_live() else "stopped"

    def has_session(self, session_id: str) -> bool:
        return session_id in self._controller.graph_sessions

    def get_session_name(self, session_id: str) -> str | None:
        """Вернуть имя сессии или None."""
        if not self.has_session(session_id):
            logger.warning(f"get_session_name: session {session_id} not found")
            return None
        return self._controller.get_session_name(session_id)

    def change_session_name(self, session_id: str, new_name: str) -> bool:
        """Переименовать сессию. True, если удалось."""
        if not self.has_session(session_id):
            logger.warning(f"change_session_name: session {session_id} not found")
            return False
        return self._controller.change_session_name(session_id, new_name)