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
        self._controller.stop_session_running(session_id)

    # ------------------------------------------------------------------ #
    # Передача данных                                                     #
    # ------------------------------------------------------------------ #

    def push_batch(self, session_id: str, batch: dict) -> bool:
        """
        Принять словарь данных от внешнего модуля.
        Формат — тот же, что у graphDataManager.add_measurement_data.
        Возвращает True/None в зависимости от состояния сессии.
        """
        return self._controller.update_session_data(session_id, batch)

    def push_measurement(self, session_id: str, entry, time) -> bool:
        """Принять одиночное измерение в формате decode_add_exp_parameters."""
        return self._controller.decode_add_exp_parameters(session_id, entry, time)

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