"""
Pure data container for a single curve.

No Qt, no pyqtgraph, no UI. Holds raw/filtered arrays, filter history
and metadata. Notifies subscribers when data changes.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

import numpy as np

from graphs.core.dataManager import relationData
from PyQt5 import QtCore
from graphs.core.filters_instance_class import FilterCommand

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
        
        self.raw_data_x = np.array(raw_x[:n], copy=True)
        self.raw_data_y = np.array(raw_y[:n], copy=True)
        self._filtered_x_data = self.raw_data_x.copy()
        self._filtered_y_data = self.raw_data_y.copy()
        self._filtered_dirty = False
        self.filters_history: List[FilterCommand] = []

        self._data_version: int = 0

        self._rebuild_scheduled: bool = False
        self._detached: bool = False

        self._on_data_changed: List[Callable[[], None]] = []
        self._on_meta_changed: List[Callable[[], None]] = []

        self.curve_name: str = data.current_name
        self.is_name_curve_customized: bool = False
        self.legend: legendName = legendName(self.curve_name)

        self.device: Optional[str] = None
        self.ch: Optional[str] = None
        self.number: Optional[int] = None

        self._on_changed: List[Callable[[], None]] = []

        # --- Погрешности ---
        self.uncertainty_records: list = []
        self.active_uncertainty_ids: set = set()
        self.uncertainty_style: dict = {}

    # -- observers ---------------------------------------------------
    def on_data_changed(self, cb): 
        if cb not in self._on_data_changed:
            self._on_data_changed.append(cb)

    def on_meta_changed(self, cb):
        if cb not in self._on_meta_changed:
            self._on_meta_changed.append(cb)

    def off_data_changed(self, cb):
        try: self._on_data_changed.remove(cb)
        except ValueError: pass

    def off_meta_changed(self, cb):
        try: self._on_meta_changed.remove(cb)
        except ValueError: pass

    # обратная совместимость:
    def on_changed(self, cb):   self.on_data_changed(cb)
    def off_changed(self, cb):  self.off_data_changed(cb)

    def _notify_data_changed(self) -> None:
        for cb in list(self._on_data_changed):
            try: cb()
            except Exception: logger.exception("store: on_data_changed failed")

    def _notify_meta_changed(self) -> None:
        for cb in list(self._on_meta_changed):
            try: cb()
            except Exception: logger.exception("store: on_meta_changed failed")

    # для мест, которые меняют и данные, и метаданные одновременно
    def _notify_changed(self) -> None:
        self._notify_data_changed()
        self._notify_meta_changed()

    def _bump_version(self) -> None:
        self._data_version += 1

    @property
    def data_version(self) -> int:
        return self._data_version

    # -- naming ------------------------------------------------------
    def change_name(self, name: str) -> None:
        self.is_name_curve_customized = True
        self.curve_name = name
        self.legend.set_custom(name)
        self._notify_meta_changed()

    def reset_name(self) -> None:
        self.is_name_curve_customized = False
        self.curve_name = self.rel_data.current_name
        self.legend.set_custom(self.curve_name)
        self._notify_meta_changed()

    def update_aliases(self, x_name: str, y_name: str) -> None:
        self.rel_data.update_names(x_name, y_name)
        if not self.is_name_curve_customized:
            self.curve_name = self.rel_data.current_name
            self.legend.set_custom(self.curve_name)
        self._notify_meta_changed()

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
        self._filtered_dirty = True          # ← обязательно
        self._rebuild_filtered()
        self._bump_version()                 # ← обязательно
        self._notify_data_changed()

    def _do_reset_arrays(self) -> bool:
        """Скопировать raw → filtered без нотификации и бампа версии."""
        if not self._filtered_dirty:
            return False
        self._filtered_x_data = self.raw_data_x.copy()
        self._filtered_y_data = self.raw_data_y.copy()
        self._filtered_dirty = False
        return True

    def data_reset(self) -> bool:
        """Публичный сброс: применяется извне, нотифицирует при изменении."""
        if not self._do_reset_arrays():
            return False
        self._bump_version()
        self._notify_data_changed()
        return True

    

    def delete_filter(self, fc: FilterCommand) -> None:
        if fc not in self.filters_history:
            return
        self.filters_history.remove(fc)
        self._filtered_dirty = True          # ← обязательно
        self._rebuild_filtered()
        self._bump_version()
        self._notify_data_changed()

    def clear_filters(self) -> None:
        if not self.filters_history and not self._filtered_dirty:
            return
        self.filters_history = []
        self._filtered_dirty = True
        self._rebuild_filtered()
        self._bump_version()
        self._notify_data_changed()

    def stop_session(self) -> None:
        if self._do_reset_arrays():
            self._bump_version()
            self._notify_data_changed()
        else:
            logger.debug("CurveDataStore.stop_session: data was not filtered")

    def _schedule_rebuild_filtered(self) -> None:
        """Отложенный пересчёт filtered_* (дебаунс 200 мс)."""
        self._filtered_dirty = True           # ← обязательно: _do_reset_arrays потом скопирует
        if self._rebuild_scheduled:
            return
        self._rebuild_scheduled = True
        QtCore.QTimer.singleShot(200, self._do_rebuild_filtered)

    def _do_rebuild_filtered(self) -> None:
        self._rebuild_scheduled = False
        if self._detached:
            return
        self._rebuild_filtered()
        self._bump_version()
        self._notify_data_changed()

    #-------------------------------------------------------------------

    def set_raw_point(self, index: int, x=None, y=None):
        n = len(self.raw_data_x)
        if index < 0 or index >= n:
            return None
        old_x = float(self.raw_data_x[index])
        old_y = float(self.raw_data_y[index])
        new_x = old_x if x is None else float(x)
        new_y = old_y if y is None else float(y)
        self.raw_data_x[index] = new_x
        self.raw_data_y[index] = new_y

        # быстрый путь: фильтров нет, длины raw и filtered совпадают
        if (not self.filters_history
                and len(self._filtered_x_data) == n
                and len(self._filtered_y_data) == n):
            self._filtered_x_data[index] = new_x
            self._filtered_y_data[index] = new_y
            self._filtered_dirty = False
            self._bump_version()
            self._notify_data_changed()
            return old_x, old_y, new_x, new_y

        # медленный путь: пересборка через дебаунс
        self._schedule_rebuild_filtered()
        return old_x, old_y, new_x, new_y

    # -- filters -----------------------------------------------------
    def _rebuild_filtered(self) -> None:
        """Пересобрать filtered_* из raw_* + filters_history. Без нотификации.

        Вызывающие обязаны выставить self._filtered_dirty = True перед
        вызовом и сами бампнуть версию/нотифицировать после.
        Отключённые фильтры (enabled=False) пропускаются.
        """
        self._do_reset_arrays()
        for f in self.filters_history:
            if not getattr(f, "enabled", True):
                continue
            self._filtered_x_data, self._filtered_y_data, _ = f.apply(
                self._filtered_x_data, self._filtered_y_data
            )
        self._filtered_dirty = bool(self.filters_history)

    def set_filter(self, fc: FilterCommand) -> str:
        if not hasattr(fc, "enabled"):
            fc.enabled = True
        self._filtered_x_data, self._filtered_y_data, message = fc.apply(
            self._filtered_x_data, self._filtered_y_data
        )
        self.filters_history.append(fc)
        self._filtered_dirty = True
        self._bump_version()
        self._notify_data_changed()
        return message

    def set_filter_enabled(self, fc: FilterCommand, enabled: bool) -> None:
        """Включить/выключить фильтр без его удаления из истории."""
        if fc not in self.filters_history:
            return
        enabled = bool(enabled)
        if fc.enabled == enabled:
            return
        fc.enabled = enabled
        self._filtered_dirty = True
        self._rebuild_filtered()
        self._bump_version()
        self._notify_data_changed()

    def move_filter(self, fc: FilterCommand, new_index: int) -> None:
        """Переместить фильтр в истории и пересобрать данные.

        Порядок применения фильтров влияет на результат (например,
        «нормировка → медиана» ≠ «медиана → нормировка»). Метод переносит
        фильтр ``fc`` на позицию ``new_index`` в ``filters_history`` и
        пересобирает ``filtered_*``, чтобы кривая сразу отобразила
        результат в новом порядке.
        """
        if fc not in self.filters_history:
            return
        old_index = self.filters_history.index(fc)

        n = len(self.filters_history)
        if new_index < 0:
            new_index = 0
        if new_index >= n:
            new_index = n - 1

        if new_index == old_index:
            return

        self.filters_history.pop(old_index)
        self.filters_history.insert(new_index, fc)
        self._filtered_dirty = True
        self._rebuild_filtered()
        self._bump_version()
        self._notify_data_changed()

    def update_filter_params(self, fc: FilterCommand, new_params: dict) -> None:
        """Обновить параметры фильтра и пересобрать данные на лету."""
        if fc not in self.filters_history:
            return
        changed = False
        for key, value in (new_params or {}).items():
            if fc.params.get(key) != value:
                fc.params[key] = value
                changed = True
        if not changed:
            return
        self._filtered_dirty = True
        self._rebuild_filtered()
        self._bump_version()
        self._notify_data_changed()

    # -- uncertainty -------------------------------------------------
    def active_uncertainty_records(self) -> list:
        return [r for r in self.uncertainty_records if r.id in self.active_uncertainty_ids]

    def add_uncertainty(self, record) -> None:
        self.uncertainty_records.append(record)
        self.active_uncertainty_ids.add(record.id)
        self._notify_meta_changed()

    def remove_uncertainty(self, record_id: str) -> None:
        self.uncertainty_records = [r for r in self.uncertainty_records if r.id != record_id]
        self.active_uncertainty_ids.discard(record_id)
        self._notify_meta_changed()

    def set_uncertainty_active(self, record_id: str, active: bool) -> None:
        if active:
            self.active_uncertainty_ids.add(record_id)
        else:
            self.active_uncertainty_ids.discard(record_id)
        self._notify_meta_changed()

    @property
    def filtered_x_data(self):
        return self._filtered_x_data

    @filtered_x_data.setter
    def filtered_x_data(self, value):
        self._filtered_x_data = value
        self._filtered_dirty = True

    @property
    def filtered_y_data(self):
        return self._filtered_y_data

    @filtered_y_data.setter
    def filtered_y_data(self, value):
        self._filtered_y_data = value
        self._filtered_dirty = True