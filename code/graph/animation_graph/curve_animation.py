import numpy as np
import logging
from PyQt5 import QtCore

logger = logging.getLogger(__name__)


class Animator(QtCore.QObject):
    """
    Аниматор для плавного отображения данных кривой (linearData).
    Поддерживает изменение скорости, паузу, а также последовательное применение фильтров после анимации.
    """
    finished = QtCore.pyqtSignal()                     # сигнал по завершении всей анимации (точек и фильтров)
    progress = QtCore.pyqtSignal(int, int)             # прогресс отображения точек (текущая точка, всего)
    filter_progress = QtCore.pyqtSignal(int, int)      # прогресс применения фильтров (текущий фильтр, всего)
    filter_applied = QtCore.pyqtSignal(object)         # применённый фильтр (экземпляр FilterCommand)

    def __init__(self, curve_data, parent=None):
        super().__init__(parent)
        self.curve = curve_data
        self.raw_x = curve_data.raw_data_x.copy()
        self.raw_y = curve_data.raw_data_y.copy()
        self.total_points = len(self.raw_x)

        self.curve_name = self.curve.curve_name

        # Для последовательного применения фильтров
        self.saved_filters = []          # копия истории фильтров на момент старта
        self.current_filter_index = 0

        self.current_index = 0
        self.speed_pps = 50              # точек в секунду
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_frame)

        self.filter_timer = QtCore.QTimer(self)
        self.filter_timer.timeout.connect(self._apply_next_filter)

        self._is_playing = False
        self._is_paused = False
        self._apply_filters_after = False
        self._filter_delay_ms = 500

    def get_curve_name(self):
        return self.curve_name

    def start(self, reset=True, apply_filters_after=False, filter_delay_ms=500):
        """
        Запуск анимации появления точек.

        :param reset: начинать с первого кадра
        :param apply_filters_after: после завершения анимации точек последовательно применять фильтры
        :param filter_delay_ms: задержка между применением фильтров (миллисекунды)
        """
        if self._is_playing and not self._is_paused:
            return


        self.current_index = 0
        # Сбрасываем данные к сырым (без фильтров)
        self.curve.filtered_x_data = self.raw_x.copy()
        self.curve.filtered_y_data = self.raw_y.copy()
        self.curve.update_all_plots_data()

        self._update_curve_data(0)

        self.saved_filters = list(self.curve.filters_history)

        self._apply_filters_after = apply_filters_after
        self._filter_delay_ms = filter_delay_ms
        self.current_filter_index = 0

        self._is_playing = True
        self._is_paused = False
        self._start_timer()

    @property
    def is_playing(self):
        return self._is_playing

    def stop(self, restore_filters=True):
        """
        Остановка анимации.

        :param restore_filters: восстановить ли исходную историю фильтров (и применить их все сразу)
        """
        self.timer.stop()
        self.filter_timer.stop()
        self._is_playing = False
        self._is_paused = False
        self._update_curve_data(self.total_points)#восстановление всех точек

        if self.saved_filters:
            # Восстанавливаем историю и применяем все фильтры сразу (без анимации)
            self.curve.clear_filters()
            for f in self.saved_filters:
                self.curve.set_filter(f)

        self.current_index = 0
        self.finished.emit()

    def pause(self):
        """Приостановить анимацию точек."""
        if self._is_playing and not self._is_paused:
            self.timer.stop()
            self._is_paused = True

    def resume(self):
        """Возобновить анимацию точек."""
        if self._is_playing and self._is_paused:
            self._start_timer()
            self._is_paused = False

    def set_speed(self, points_per_second: float):
        """Установить скорость анимации точек (точек в секунду)."""
        self.speed_pps = max(1, points_per_second)
        if self._is_playing and not self._is_paused:
            self._restart_timer()

    def set_duration(self, seconds: float):
        """Установить общую длительность анимации точек (секунд)."""
        if seconds <= 0:
            return
        new_speed = self.total_points / seconds
        self.set_speed(new_speed)

    def _start_timer(self):
        interval = max(1, int(1000 / self._get_frames_per_second()))
        self.timer.start(interval)

    def _restart_timer(self):
        if self.timer.isActive():
            self.timer.stop()
            self._start_timer()

    def _get_frames_per_second(self):
        desired_fps = min(60, max(10, self.speed_pps / 5))
        return desired_fps

    def _update_frame(self):
        if not self._is_playing or self._is_paused:
            return

        fps = self._get_frames_per_second()
        points_per_frame = max(1, int(self.speed_pps / fps))

        new_index = min(self.current_index + points_per_frame, self.total_points)
        if new_index == self.current_index:
            self._finish_animation()
            return

        self.current_index = new_index
        self._update_curve_data(self.current_index)
        self.progress.emit(self.current_index, self.total_points)

        if self.current_index >= self.total_points:
            self._finish_animation()

    def _update_curve_data(self, index):
        if index <= 0:
            x_slice = np.array([])
            y_slice = np.array([])
        else:
            x_slice = self.raw_x[:index]
            y_slice = self.raw_y[:index]
        self.curve.filtered_x_data = x_slice
        self.curve.filtered_y_data = y_slice
        self.curve.update_all_plots_data()

    def _finish_animation(self):
        """Завершение анимации точек."""
        self.timer.stop()
        self._is_playing = False
        self._is_paused = False

        if self._apply_filters_after and self.saved_filters:
            # Начинаем последовательное применение фильтров
            self.current_filter_index = 0
            self.curve.clear_filters()
            self.filter_timer.start(self._filter_delay_ms)
        else:
            # Восстанавливаем историю фильтров сразу и завершаем анимацию
            self.curve.clear_filters()
            for f in self.saved_filters:
                self.curve.set_filter(f)
            self.finished.emit()

    def _apply_next_filter(self):
        """Применяет следующий фильтр из сохранённого списка."""
        if self.current_filter_index >= len(self.saved_filters):
            self.filter_timer.stop()
            self.saved_filters = []
            self.finished.emit()
            return

        filter_cmd = self.saved_filters[self.current_filter_index]
        self.curve.set_filter(filter_cmd)
        self.filter_progress.emit(self.current_filter_index + 1, len(self.saved_filters))
        self.filter_applied.emit(filter_cmd)
        self.current_filter_index += 1