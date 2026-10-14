"""
Pure data container for a single curve.

No Qt, no pyqtgraph, no UI. Holds raw/filtered arrays, filter history
and metadata. Notifies subscribers when data changes.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

import numpy as np

from graph.core.dataManager import relationData
from graph.core.filters_instance_class import FilterCommand

logger = logging.getLogger(__name__)


class legendName:
    """User-facing legend name of a curve (original/custom/previous)."""

    def __init__(self, name: str) -> None:
        self._name = name
        self.current_name = name
        self.previous_name = ""

    def set_custom(self, name: str) -> None:
        self.previous_name = self._name
        self._name = name
        self.current_name = name


class CurveDataStore:
    """Owns the data and filter pipeline of one curve."""

    def __init__(self, data: relationData) -> None:
        if data is None:
            raise ValueError("CurveDataStore requires relationData")
        self.rel_data: relationData = data

        raw_x = np.asarray(data.x_result)
        raw_y = np.asarray(data.y_result)
        n = min(len(raw_x), len(raw_y))
        # Копии — чтобы правки из инспектора не утекали в graphDataManager
        self.raw_data_x = np.array(raw_x[:n], copy=True)
        self.raw_data_y = np.array(raw_y[:n], copy=True)
        self.filtered_x_data = self.raw_data_x.copy()
        self.filtered_y_data = self.raw_data_y.copy()
        self.filters_history: List[FilterCommand] = []

        self.curve_name: str = data.current_name
        self.is_name_curve_customized: bool = False
        self.legend: legendName = legendName(self.curve_name)

        self.device: Optional[str] = None
        self.ch: Optional[str] = None
        self.number: Optional[int] = None

        self._on_changed: List[Callable[[], None]] = []

    # -- observers ---------------------------------------------------
    def on_changed(self, cb: Callable[[], None]) -> None:
        if cb not in self._on_changed:
            self._on_changed.append(cb)

    def off_changed(self, cb: Callable[[], None]) -> None:
        try:
            self._on_changed.remove(cb)
        except ValueError:
            pass

    def _notify_changed(self) -> None:
        for cb in list(self._on_changed):
            try:
                cb()
            except Exception:
                logger.exception("CurveDataStore: on_changed callback failed")

    # -- naming ------------------------------------------------------
    def change_name(self, name: str) -> None:
        self.is_name_curve_customized = True
        self.curve_name = name
        self.legend.set_custom(name)
        self._notify_changed()

    def reset_name(self) -> None:
        self.is_name_curve_customized = False
        self.curve_name = self.rel_data.current_name
        self.legend.set_custom(self.curve_name)
        self._notify_changed()

    def update_aliases(self, x_name: str, y_name: str) -> None:
        self.rel_data.update_names(x_name, y_name)
        if not self.is_name_curve_customized:
            self.curve_name = self.rel_data.current_name
            self.legend.set_custom(self.curve_name)
        self._notify_changed()

    # -- data --------------------------------------------------------
    def set_data(self, new_rel_data: relationData) -> None:
        old_x = self.rel_data.x_current_name if self.rel_data else None
        old_y = self.rel_data.y_current_name if self.rel_data else None
        self.rel_data = new_rel_data
        if old_x is not None or old_y is not None:
            new_rel_data.update_names(old_x, old_y)

        raw_x = np.asarray(new_rel_data.x_result)
        raw_y = np.asarray(new_rel_data.y_result)
        n = min(len(raw_x), len(raw_y))
        self.raw_data_x = np.array(raw_x[:n], copy=True)
        self.raw_data_y = np.array(raw_y[:n], copy=True)
        self._rebuild_filtered()
        self._notify_changed()
        self._rebuild_filtered()
        self._notify_changed()

    def set_raw_point(self, index: int, x=None, y=None):
        """
        Изменить одну точку (raw) локально.
        Возвращает (old_x, old_y, new_x, new_y) или None, если индекс невалиден.
        Пересобирает filtered_* через filters_history и уведомляет подписчиков
        (CurvePresenter.refresh обновит график, recalc_stats пересчитает статистику).
        graphDataManager НЕ затрагивается — raw_* хранится как копия.
        """
        n = len(self.raw_data_x)
        if index < 0 or index >= n:
            return None
        old_x = float(self.raw_data_x[index])
        old_y = float(self.raw_data_y[index])
        new_x = old_x if x is None else float(x)
        new_y = old_y if y is None else float(y)
        self.raw_data_x[index] = new_x
        self.raw_data_y[index] = new_y
        self._rebuild_filtered()
        self._notify_changed()
        return old_x, old_y, new_x, new_y

    def data_reset(self) -> bool:
        same = (
            self.filtered_x_data.shape == self.raw_data_x.shape
            and np.array_equal(self.filtered_x_data, self.raw_data_x)
            and self.filtered_y_data.shape == self.raw_data_y.shape
            and np.array_equal(self.filtered_y_data, self.raw_data_y)
        )
        if same:
            return False
        self.filtered_x_data = self.raw_data_x.copy()
        self.filtered_y_data = self.raw_data_y.copy()
        return True

    def _rebuild_filtered(self) -> None:
        self.data_reset()
        for f in self.filters_history:
            self.filtered_x_data, self.filtered_y_data, _ = f.apply(
                self.filtered_x_data, self.filtered_y_data
            )

    # -- filters -----------------------------------------------------
    def set_filter(self, fc: FilterCommand) -> str:
        self.filtered_x_data, self.filtered_y_data, message = fc.apply(
            self.filtered_x_data, self.filtered_y_data
        )
        self.filters_history.append(fc)
        self._notify_changed()
        return message

    def delete_filter(self, fc: FilterCommand) -> None:
        if fc not in self.filters_history:
            return
        self.filters_history.remove(fc)
        self._rebuild_filtered()
        self._notify_changed()

    def clear_filters(self) -> None:
        self.filters_history = []
        self.data_reset()
        self._notify_changed()

    # -- session -----------------------------------------------------
    def stop_session(self) -> None:
        if not self.data_reset():
            logger.debug("CurveDataStore.stop_session: data was not filtered")
        self._notify_changed()