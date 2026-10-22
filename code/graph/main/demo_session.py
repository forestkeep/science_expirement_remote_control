"""Демо-сессии: 2 прибора × 3 канала × уникальная математическая функция × 10 000 точек.

* live-демо:    каждую секунду добавляет по 100 точек на канал (100 тиков).
* статик-демо:  все 10 000 точек загружаются сразу и остаются в проекте.
"""
import logging

import numpy as np
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class DemoDataGenerator:
    """Детерминированный генератор демо-данных.

    Каждый канал каждого прибора — своя математическая функция со своим
    именем параметра. Имена попадают в ключ ``device-channel-param``
    внутри ``graphDataManager`` и потом превращаются в подписи на графике,
    легенде и в дереве кривых (после применения алиасов).
    """

    NUM_POINTS = 10000
    TICK_SIZE = 100
    DEVICES = ("Демо-прибор A", "Демо-прибор B")
    CHANNELS = ("Канал 1", "Канал 2", "Канал 3")

    # device -> channel -> (param_name, callable(t) -> ndarray)
    SERIES = {
        DEVICES[0]: {
            CHANNELS[0]: ("sin",        lambda t: np.sin(2.0 * np.pi * t / 10.0)),
            CHANNELS[1]: ("cos",        lambda t: 0.5 * np.cos(2.0 * np.pi * t / 5.0)),
            CHANNELS[2]: ("saw",        lambda t: ((t / 10.0) % 1.0) - 0.5),
        },
        DEVICES[1]: {
            CHANNELS[0]: ("damped_sin", lambda t: np.exp(-0.05 * t) * np.sin(2.0 * np.pi * t / 4.0)),
            CHANNELS[1]: ("parabola",   lambda t: 0.001 * (t - 50.0) ** 2),
            CHANNELS[2]: ("gaussian",   lambda t: np.exp(-((t - 50.0) ** 2) / 200.0)),
        },
    }

    @classmethod
    def generate(cls):
        """Возвращает ``(t, series)``.

        ``series[device][channel] = (param_name, y_array)`` — та же форма,
        что и в ``cls.SERIES``, только вместо лямбд уже посчитанные массивы.
        """
        t = np.linspace(0.0, 100.0, cls.NUM_POINTS)
        series = {}
        for device, channels in cls.SERIES.items():
            series[device] = {}
            for channel, (param, func) in channels.items():
                series[device][channel] = (param, func(t))
        return t, series

    @classmethod
    def make_batch(cls, t_slice, series_slice):
        """Формат, ожидаемый ``graphDataManager.add_measurement_data``:

        ``{device: {channel: {param_name: [y_list, t_list]}}}``

        Имя параметра берётся из ``series_slice`` — ``sin``, ``cos``, …
        """
        batch = {}
        for device, channels in series_slice.items():
            batch[device] = {}
            for channel, (param, y) in channels.items():
                batch[device][channel] = {
                    param: [list(y), list(t_slice)],
                }
        return batch


def auto_select_first_channel(session_controller, session_id):
    """После первого батча данных выбирает X=time и Y=первый канал.

    Делает демо-сессию сразу полезной — кривая появляется без ручного
    выбора параметров в селекторе.
    """
    session = session_controller.graph_sessions.get(session_id)
    if session is None or not hasattr(session, "select_controller"):
        return
    try:
        all_params = session.data_manager.get_name_params()
        x_name = next((c for c in ("time", "numbers") if c in all_params), None)
        if x_name is None:
            return
        y_params = [p for p in all_params if p not in ("time", "numbers")]
        if not y_params:
            return
        session.select_controller.set_selections(
            x_param=x_name,
            y_first_params=[y_params[0]],
            y_second_params=[],
            is_signal=True,
        )
    except Exception:
        logger.exception("auto_select_first_channel failed")


class LiveDemoController(QObject):
    """Ведущий live-сессии: 100 точек/сек, 100 тиков, потом stop."""

    finished = pyqtSignal()

    def __init__(self, session_controller, session_name="Демо (live)"):
        super().__init__()
        self._ctrl = session_controller
        self._name = session_name
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._cursor = 0
        self._session_id = None
        self._t = None
        self._series = None
        self._auto_select_done = False

    def start(self):
        self._t, self._series = DemoDataGenerator.generate()
        self._cursor = 0
        self._auto_select_done = False
        self._session_id = self._ctrl.start_new_session(
            session_name=self._name,
            use_timestamps=True,
            is_experiment_running=True,
        )
        if not self._session_id:
            logger.error("Live demo: failed to start session")
            return False
        self._timer.start(1000)
        return True

    def stop(self):
        self._timer.stop()
        if self._session_id is not None:
            try:
                self._ctrl.stop_session_running(self._session_id)
            except Exception:
                logger.exception("Live demo: stop failed")
            self._session_id = None

    def _tick(self):
        if self._session_id is None:
            self._timer.stop()
            return

        start = self._cursor
        end = min(start + DemoDataGenerator.TICK_SIZE,
                  DemoDataGenerator.NUM_POINTS)
        if end <= start:
            self._finish()
            return

        t_slice = self._t[start:end]
        series_slice = {
            d: {c: (param, y[start:end])
                for c, (param, y) in chans.items()}
            for d, chans in self._series.items()
        }
        batch = DemoDataGenerator.make_batch(t_slice, series_slice)

        try:
            self._ctrl.update_session_data(self._session_id, batch)
        except Exception:
            logger.exception("Live demo: update_session_data failed")
            self._finish()
            return

        if not self._auto_select_done:
            self._auto_select_done = True
            QTimer.singleShot(
                0,
                lambda: auto_select_first_channel(self._ctrl, self._session_id),
            )

        self._cursor = end
        if self._cursor >= DemoDataGenerator.NUM_POINTS:
            self._finish()

    def _finish(self):
        self._timer.stop()
        if self._session_id is not None:
            try:
                self._ctrl.stop_session_running(self._session_id)
            except Exception:
                logger.exception("Live demo: stop_session_running failed")
            self._session_id = None
        self.finished.emit()


class StaticDemoLoader:
    """Загружает полный набор 10 000 точек в остановленную (review) сессию."""

    def __init__(self, session_controller, session_name="Демо (статика)"):
        self._ctrl = session_controller
        self._name = session_name

    def load(self):
        t, series = DemoDataGenerator.generate()
        batch = DemoDataGenerator.make_batch(t, series)
        session_id = self._ctrl.start_new_session(
            session_name=self._name,
            use_timestamps=True,
            is_experiment_running=False,
        )
        if not session_id:
            logger.error("Static demo: failed to start session")
            return None
        try:
            self._ctrl.update_session_data(session_id, batch)
        except Exception:
            logger.exception("Static demo: update_session_data failed")
            return None
        QTimer.singleShot(
            0,
            lambda: auto_select_first_channel(self._ctrl, session_id),
        )
        return session_id