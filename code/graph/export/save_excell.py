import threading
import numpy as np
import pandas as pd
from copy import deepcopy
from typing import Dict, Optional, List
from graph.core.dataManager import measTimeData
import logging
from graph.core.statistics_calc import StatisticsCalculator

from openpyxl.workbook.child import INVALID_TITLE_REGEX

logger = logging.getLogger(__name__)


class ExcelSaver:
    """Сохраняет словарь листов в Excel-файл в отдельном потоке с возможностью добавления статистики под числовыми столбцами."""

    def __init__(self):
        self._sheets: Dict[str, Dict[str, measTimeData]] = {}
        self._lock = threading.Lock()
        self._save_thread: Optional[threading.Thread] = None
        self._save_event = threading.Event()
        self._sheet_descriptions: Dict[str, str] = {}

        self._statistics_config = {
            "enabled": False,
            "stats_list": [ 
                "count", "mean", "median", "mode", "std", "var", "min", "max",
                "range", "cv", "skew", "kurtosis", "q25", "q50", "q75", "iqr",
                "sum", "n_zeros", "n_positive", "n_negative", "missing_ratio"
            ],
            "columns": None
        }

     # ------------------- Новые методы для работы с описаниями листов -------------------
    def set_sheet_description(self, sheet_name: str, description: Optional[str]) -> None:
        """
        Устанавливает текстовое описание для указанного листа.
        :param sheet_name: имя листа
        :param description: описание (строка). Если None или пустая строка, описание удаляется.
        """
        # Очищаем имя листа от недопустимых символов
        title = INVALID_TITLE_REGEX.sub(' ', sheet_name)
        if title != sheet_name:
            logger.info(f"sheet name changed from {sheet_name} to {title} because of invalid characters in the name")
            sheet_name = title

        with self._lock:
            if description is None or str(description).strip() == '':
                self._sheet_descriptions.pop(sheet_name, None)
            else:
                self._sheet_descriptions[sheet_name] = str(description)

    def get_sheet_description(self, sheet_name: str) -> Optional[str]:
        """Возвращает описание листа (или None, если не задано)."""
        with self._lock:
            return self._sheet_descriptions.get(sheet_name)

    def add_sheet(self, sheet_name: str, sheet_data: Dict[str, measTimeData], description: str = None) -> None:
        """
        Добавляет лист с данными.
        :param sheet_name: имя листа
        :param sheet_data: словарь параметров
        :param description: описание листа
        """
        title = INVALID_TITLE_REGEX.sub(' ', sheet_name)
        if title != sheet_name:
            logger.info(f"sheet name changed from {sheet_name} to {title} because of invalid characters in the name")
            sheet_name = title

        with self._lock:
            self._sheets[sheet_name] = deepcopy(sheet_data)
            if description is not None and str(description).strip() != '':
                self._sheet_descriptions[sheet_name] = str(description)

    def set_statistics_config(self, enabled: bool, stats_list: Optional[List[str]] = None,
                              columns: Optional[List[str]] = None) -> None:
        """
        Настройка сохранения статистики.
        :param enabled: включать ли статистику
        :param stats_list: список названий статистик (если None – используются все доступные)
        :param columns: список имён параметров (столбцов), для которых считать статистику (None – все числовые)
        """
        with self._lock:
            self._statistics_config["enabled"] = enabled
            if stats_list is not None:
                valid_stats = [s for s in stats_list if s in self._statistics_config["stats_list"]]
                if len(valid_stats) != len(stats_list):
                    logger.warning(f"Некоторые статистики не распознаны: {set(stats_list) - set(valid_stats)}")
                self._statistics_config["stats_list"] = valid_stats
            if columns is not None:
                self._statistics_config["columns"] = columns
            else:
                self._statistics_config["columns"] = None

    def enable_statistics(self, stats_list: Optional[List[str]] = None, columns: Optional[List[str]] = None) -> None:
        """Удобный метод для включения статистики с указанными параметрами."""
        self.set_statistics_config(True, stats_list, columns)

    def disable_statistics(self) -> None:
        """Выключить сохранение статистики."""
        self.set_statistics_config(False)

    def add_data(self, data: Dict[str, Dict[str, measTimeData]]) -> None:
        with self._lock:
            self._sheets = deepcopy(data)

    def save(self, filepath: str) -> None:
        with self._lock:
            sheets_copy = deepcopy(self._sheets)
            descriptions_copy = deepcopy(self._sheet_descriptions)

        self._save_event.clear()
        self._save_thread = threading.Thread(
            target=self._save_worker,
            args=(filepath, sheets_copy, descriptions_copy),
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

    @staticmethod
    def _write_statistics_to_sheet(sheet, startrow: int, startcol: int,
                                   param_names: List[str], stats_dict: Dict[str, Dict[str, float]],
                                   stat_names: List[str]) -> None:
        """
        Записывает таблицу статистики в лист openpyxl.
        :param sheet: объект листа openpyxl
        :param startrow: строка, с которой начинать запись (0-индекс)
        :param startcol: столбец, с которого начинать запись (0-индекс)
        :param param_names: имена параметров (столбцов), для которых есть статистика
        :param stats_dict: словарь {параметр: {статистика: значение}}
        :param stat_names: список названий статистик в порядке вывода
        """
        sheet.cell(row=startrow + 1, column=startcol + 1, value="Statistic")
        for col_idx, pname in enumerate(param_names):
            sheet.cell(row=startrow + 1, column=startcol + 2 + col_idx, value=pname)

        for row_idx, stat in enumerate(stat_names):
            sheet.cell(row=startrow + 2 + row_idx, column=startcol + 1, value=stat)
            for col_idx, pname in enumerate(param_names):
                val = stats_dict.get(pname, {}).get(stat, np.nan)
                if pd.notna(val):
                    sheet.cell(row=startrow + 2 + row_idx, column=startcol + 2 + col_idx, value=val)

    def _save_worker(self, filepath: str, sheets: Dict[str, Dict[str, measTimeData]],
                     descriptions: Dict[str, str]) -> None:
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                for sheet_name, params in sheets.items():
                    # Обработка описания листа
                    description = descriptions.get(sheet_name)
                    has_description = description is not None and str(description).strip() != ''
                    startrow = 1 if has_description else 0

                    # Если описание есть, создаём лист заранее и записываем описание в A1
                    if has_description:
                        # Создаём лист, если он ещё не существует в книге
                        if sheet_name not in writer.book.sheetnames:
                            writer.book.create_sheet(sheet_name)
                        sheet = writer.book[sheet_name]
                        sheet.cell(row=1, column=1, value=description)  # первый столбец, первая строка

                    # Фильтруем параметры с непустыми значениями
                    valid_params = {
                        k: v for k, v in params.items()
                        if v.par_val is not None and len(v.par_val) > 0
                    }
                    if not valid_params:
                        logger.warning(f"Пустой лист {sheet_name} не сохранён")
                        continue

                    # Группировка по (device, channel)
                    groups: Dict[tuple, Dict[str, measTimeData]] = {}
                    for name, mdata in valid_params.items():
                        key = (mdata.device, mdata.ch)
                        groups.setdefault(key, {})[name] = mdata

                    current_col = 0
                    stats_enabled = self._statistics_config["enabled"]
                    requested_stats = self._statistics_config["stats_list"][:] if stats_enabled else []
                    stats_columns_filter = self._statistics_config["columns"]

                    for (dev, ch), group_params in groups.items():
                        # Проверка длин
                        lens = {len(m.par_val) for m in group_params.values()}
                        if len(lens) > 1:
                            raise ValueError(
                                f"В листе '{sheet_name}' для device={dev}, channel={ch} "
                                f"обнаружены разные длины значений параметров: {lens}"
                            )
                        length = next(iter(lens))

                        first_mdata = next(iter(group_params.values()))
                        if (first_mdata.num_or_time is not None
                                and len(first_mdata.num_or_time) == length):
                            index_vals = first_mdata.num_or_time
                        else:
                            index_vals = list(range(length))

                        data = {
                            'device': [dev] * length,
                            'channel': [ch] * length,
                            'Index': index_vals
                        }
                        for name, mdata in group_params.items():
                            data[name] = mdata.par_val

                        df = pd.DataFrame(data)
                        param_names = list(group_params.keys())
                        df = df[['device', 'channel', 'Index'] + param_names]

                        # Запись DataFrame в лист
                        df.to_excel(
                            writer,
                            sheet_name=sheet_name,
                            startrow=startrow,
                            startcol=current_col,
                            index=False,
                            header=True,
                        )

                        # Статистика (если включена)
                        if stats_enabled and requested_stats:
                            numeric_cols = [col for col in param_names if col not in ['device', 'channel', 'Index']]
                            if stats_columns_filter is not None:
                                numeric_cols = [col for col in numeric_cols if col in stats_columns_filter]

                            if numeric_cols:
                                stats_for_params = {}
                                for col in numeric_cols:
                                    series = df[col]
                                    col_stats = StatisticsCalculator._compute_column_statistics(series, requested_stats)
                                    stats_for_params[col] = col_stats

                                # Позиция для статистики: после данных + 1 пустая строка
                                stats_startrow = startrow + df.shape[0] + 2
                                sheet = writer.sheets[sheet_name]  # получаем лист после записи df
                                self._write_statistics_to_sheet(
                                    sheet=sheet,
                                    startrow=stats_startrow,
                                    startcol=current_col+2,
                                    param_names=numeric_cols,
                                    stats_dict=stats_for_params,
                                    stat_names=requested_stats
                                )

                        current_col += df.shape[1] + 1  # +1 для разделительного пустого столбца

        except Exception as e:
            logger.error(f"Ошибка при сохранении Excel: {e}")
            raise
        finally:
            self._save_event.set()