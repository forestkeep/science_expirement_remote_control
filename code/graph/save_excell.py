import threading
import numpy as np
import pandas as pd
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, Optional
from graph.dataManager import measTimeData
import logging
import re

from openpyxl import Workbook
from openpyxl.workbook.child import INVALID_TITLE_REGEX

logger = logging.getLogger(__name__)

class ExcelSaver:
    """Сохраняет словарь листов в Excel-файл в отдельном потоке."""

    def __init__(self):
        self._sheets: Dict[str, Dict[str, measTimeData]] = {}
        self._lock = threading.Lock()
        self._save_thread: Optional[threading.Thread] = None
        self._save_event = threading.Event()

    def add_data(self, data: Dict[str, Dict[str, measTimeData]]) -> None:
        with self._lock:
            self._sheets = deepcopy(data)

    def add_sheet(self, sheet_name: str, sheet_data: Dict[str, measTimeData]) -> None:
        title = INVALID_TITLE_REGEX.sub(' ', sheet_name)
        if title != sheet_name:
            logger.info(f"sheet name changed from {sheet_name} to {title} because of invalid characters in the name")
            sheet_name = title
        with self._lock:
            self._sheets[sheet_name] = deepcopy(sheet_data)

    def save(self, filepath: str) -> None:
        with self._lock:
            sheets_copy = deepcopy(self._sheets)

        self._save_event.clear()
        self._save_thread = threading.Thread(
            target=self._save_worker,
            args=(filepath, sheets_copy),
            daemon=True
        )
        self._save_thread.start()

    def wait(self, timeout: Optional[float] = None) -> bool:
        if self._save_thread is None:
            return True
        self._save_thread.join(timeout)
        return not self._save_thread.is_alive()

    @property
    def is_saving(self) -> bool:
        return self._save_thread is not None and self._save_thread.is_alive()

    def _save_worker(self, filepath: str, sheets: Dict[str, Dict[str, measTimeData]]) -> None:
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                for sheet_name, params in sheets.items():
                    # Фильтруем параметры с непустыми значениями
                    valid_params = {
                        k: v for k, v in params.items()
                        if v.par_val is not None and len(v.par_val) > 0
                    }
                    if not valid_params:
                        logger.warning(f"Пустой лист {sheet_name} не сохранён")
                        continue

                    # Группируем параметры по (device, channel)
                    groups: Dict[tuple, Dict[str, measTimeData]] = {}
                    for name, mdata in valid_params.items():
                        key = (mdata.device, mdata.ch)
                        groups.setdefault(key, {})[name] = mdata

                    # Записываем каждую группу как отдельный горизонтальный блок
                    current_col = 0
                    for (dev, ch), group_params in groups.items():
                        # Длины всех параметров в группе должны совпадать
                        lens = {len(m.par_val) for m in group_params.values()}
                        if len(lens) > 1:
                            raise ValueError(
                                f"В листе '{sheet_name}' для device={dev}, channel={ch} "
                                f"обнаружены разные длины значений параметров: {lens}"
                            )
                        length = next(iter(lens))

                        # Индекс (время или порядковый номер) – один для всей группы
                        first_mdata = next(iter(group_params.values()))
                        if (first_mdata.num_or_time is not None 
                                and len(first_mdata.num_or_time) == length):
                            index_vals = first_mdata.num_or_time
                        else:
                            index_vals = list(range(length))

                        # Собираем широкую таблицу для этого device/channel
                        data = {
                            'device': [dev] * length,
                            'channel': [ch] * length,
                            'Index': index_vals
                        }
                        for name, mdata in group_params.items():
                            data[name] = mdata.par_val

                        df = pd.DataFrame(data)
                        # Фиксированный порядок столбцов: device, channel, Index, параметры
                        param_names = list(group_params.keys())
                        df = df[['device', 'channel', 'Index'] + param_names]

                        # Выводим блок на лист, начиная с текущего столбца
                        df.to_excel(
                            writer,
                            sheet_name=sheet_name,
                            startrow=0,
                            startcol=current_col,
                            index=False
                        )
                        # Смещаемся вправо: ширина блока + 1 пустая колонка
                        current_col += df.shape[1] + 1

        except Exception as e:
            logger.error(f"Ошибка при сохранении Excel: {e}")
            raise
        finally:
            self._save_event.set()