import pandas as pd
from typing import Dict, List
import numpy as np

COUNT = """
COUNT - количество не пропущенных (не NaN) значений в столбце.
Используется для оценки объёма валидных данных.
"""

MEAN = """
MEAN - среднее арифметическое, вычисляемое как сумма всех значений, делённая на их количество.
Чувствительно к выбросам. Характеризует центральную тенденцию.
"""

MEDIAN = """
MEDIAN - медиана, то есть значение, делящее упорядоченный ряд пополам (50-й перцентиль).
Устойчива к выбросам.
"""

MODE = """
MODE - мода, наиболее часто встречающееся значение в выборке.
Если таких значений несколько, берётся первое (наименьшее по порядку).
"""

STD = """
STD - стандартное отклонение (квадратный корень из дисперсии).
Показывает разброс данных относительно среднего. Имеет ту же размерность, что и данные.
"""

VAR = """
VAR - дисперсия, мера разброса данных, равная среднему квадрату отклонений от среднего.
Имеет размерность квадрата исходных единиц.
"""

MIN = """
MIN - минимальное значение в столбце (без учёта NaN).
"""

MAX = """
MAX - максимальное значение в столбце (без учёта NaN).
"""

RANGE = """
RANGE - размах, разность между максимальным и минимальным значениями.
Простейший показатель вариации.
"""

CV = """
CV - коэффициент вариации (стандартное отклонение, делённое на среднее по модулю).
Безразмерная величина, позволяющая сравнивать разброс разнородных данных.
Корректно определён только при ненулевом среднем.
"""

SKEW = """
SKEW - коэффициент асимметрии, характеризующий скошенность распределения.
Положительное значение означает правый хвост (выбросы больше среднего).
Отрицательное – левый хвост. Ноль – симметричное распределение.
"""

KURTOSIS = """
KURTOSIS - эксцесс, мера «островершинности» распределения относительно нормального.
Положительный эксцесс – более острый пик, отрицательный – более плоский.
"""

Q25 = """
Q25 - первый квартиль (25-й перцентиль), ниже которого находятся 25% значений.
"""

Q50 = """
Q50 - второй квартиль (50-й перцентиль), совпадает с медианой.
"""

Q75 = """
Q75 - третий квартиль (75-й перцентиль), ниже которого находятся 75% значений.
"""

IQR = """
IQR - интерквартильный размах (Q75 - Q25), робастная мера разброса.
Используется для обнаружения выбросов: значения вне [Q25-1.5*IQR; Q75+1.5*IQR].
"""

SUM = """
SUM - сумма всех значений в столбце (без учёта NaN).
"""

N_ZEROS = """
N_ZEROS - количество значений, равных нулю (включая целые 0 и 0.0).
"""

N_POSITIVE = """
N_POSITIVE - количество положительных значений (>0).
"""

N_NEGATIVE = """
N_NEGATIVE - количество отрицательных значений (<0).
"""

MISSING_RATIO = """
MISSING_RATIO - доля пропущенных значений (NaN) в столбце.
Вычисляется как (общее число строк - количество не-NaN) / общее число строк.
"""

STATISTICS_DESCRIPTIONS = {
    "count": COUNT,
    "mean": MEAN,
    "median": MEDIAN,
    "mode": MODE,
    "std": STD,
    "var": VAR,
    "min": MIN,
    "max": MAX,
    "range": RANGE,
    "cv": CV,
    "skew": SKEW,
    "kurtosis": KURTOSIS,
    "q25": Q25,
    "q50": Q50,
    "q75": Q75,
    "iqr": IQR,
    "sum": SUM,
    "n_zeros": N_ZEROS,
    "n_positive": N_POSITIVE,
    "n_negative": N_NEGATIVE,
    "missing_ratio": MISSING_RATIO,
}


class StatisticsCalculator():

    @staticmethod
    def _compute_column_statistics(series: pd.Series, requested_stats: List[str]) -> Dict[str, float]:
            """
            Вычисляет запрошенные статистики для pandas Series.
            Возвращает словарь {название_статистики: значение}.
            """
            stats = {}
            clean_series = series.dropna()
            n_total = len(series)
            n_non_null = len(clean_series)

            for stat in requested_stats:
                if stat == "count":
                    stats[stat] = n_non_null
                elif stat == "mean":
                    stats[stat] = clean_series.mean() if n_non_null > 0 else np.nan
                elif stat == "median":
                    stats[stat] = clean_series.median() if n_non_null > 0 else np.nan
                elif stat == "mode":
                    mode_val = clean_series.mode()
                    stats[stat] = mode_val.iloc[0] if len(mode_val) > 0 else np.nan
                elif stat == "std":
                    stats[stat] = clean_series.std() if n_non_null > 1 else np.nan
                elif stat == "var":
                    stats[stat] = clean_series.var() if n_non_null > 1 else np.nan
                elif stat == "min":
                    stats[stat] = clean_series.min() if n_non_null > 0 else np.nan
                elif stat == "max":
                    stats[stat] = clean_series.max() if n_non_null > 0 else np.nan
                elif stat == "range":
                    if n_non_null > 0:
                        stats[stat] = clean_series.max() - clean_series.min()
                    else:
                        stats[stat] = np.nan
                elif stat == "cv":
                    mean_val = clean_series.mean()
                    std_val = clean_series.std()
                    if n_non_null > 0 and mean_val != 0 and not np.isnan(mean_val):
                        stats[stat] = std_val / abs(mean_val)
                    else:
                        stats[stat] = np.nan
                elif stat == "skew":
                    stats[stat] = clean_series.skew() if n_non_null >= 3 else np.nan
                elif stat == "kurtosis":
                    stats[stat] = clean_series.kurtosis() if n_non_null >= 4 else np.nan
                elif stat == "q25":
                    stats[stat] = clean_series.quantile(0.25) if n_non_null > 0 else np.nan
                elif stat == "q50":
                    stats[stat] = clean_series.quantile(0.50) if n_non_null > 0 else np.nan
                elif stat == "q75":
                    stats[stat] = clean_series.quantile(0.75) if n_non_null > 0 else np.nan
                elif stat == "iqr":
                    q75 = clean_series.quantile(0.75) if n_non_null > 0 else np.nan
                    q25 = clean_series.quantile(0.25) if n_non_null > 0 else np.nan
                    stats[stat] = q75 - q25 if not (np.isnan(q75) or np.isnan(q25)) else np.nan
                elif stat == "sum":
                    stats[stat] = clean_series.sum() if n_non_null > 0 else np.nan
                elif stat == "n_zeros":
                    stats[stat] = (clean_series == 0).sum() if n_non_null > 0 else np.nan
                elif stat == "n_positive":
                    stats[stat] = (clean_series > 0).sum() if n_non_null > 0 else np.nan
                elif stat == "n_negative":
                    stats[stat] = (clean_series < 0).sum() if n_non_null > 0 else np.nan
                elif stat == "missing_ratio":
                    stats[stat] = (n_total - n_non_null) / n_total if n_total > 0 else np.nan
            return stats
    
    @staticmethod
    def get_description_stat(stat_name: str) -> str:
        return STATISTICS_DESCRIPTIONS.get(stat_name, False)