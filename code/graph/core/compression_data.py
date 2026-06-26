import numpy as np
from typing import Optional, Tuple

def lttb_downsample(
    x: np.ndarray,
    y: np.ndarray,
    n_out: Optional[int] = None,
    max_points: int = 1000,
    preserve_endpoints: bool = True,
    remove_nan: bool = True,
    **kwargs
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Прореживание последовательности точек алгоритмом LTTB.
    Порядок точек задаётся их индексами в массивах.

    Параметры
    ----------
    x : np.ndarray
        Координаты по оси X (могут быть неупорядоченными).
    y : np.ndarray
        Координаты по оси Y.
    n_out : int, опционально
        Желаемое количество точек на выходе. Если None, используется max_points.
    max_points : int, по умолчанию 1000
        Максимальное число точек, если n_out не задан.
    preserve_endpoints : bool, по умолчанию True
        Всегда ли сохранять первую и последнюю точки (по порядку).
    remove_nan : bool, по умолчанию True
        Удалять ли пары, содержащие NaN.
    **kwargs : дополнительные параметры
        Задел для будущих расширений, например:
            - use_x: bool (по умолчанию True) – учитывать ли X при расчёте площади.
            - parallel: bool – использовать ли параллельные вычисления.
            - error_tolerance: float – допустимая ошибка для адаптивного сжатия.

    Возвращает
    ----------
    x_out : np.ndarray
        Прореженные координаты X (в том же порядке).
    y_out : np.ndarray
        Прореженные координаты Y.
    """
    if len(x) != len(y):
        raise ValueError("Массивы x и y должны иметь одинаковую длину")
    if len(x) == 0:
        return np.array([]), np.array([])

    if remove_nan:
        mask = ~(np.isnan(x) | np.isnan(y))
        x, y = x[mask], y[mask]
        if len(x) == 0:
            return np.array([]), np.array([])

    if n_out is None:
        n_out = min(len(x), max_points)
    n_out = int(n_out)
    if n_out < 2:
        n_out = 2
    if n_out >= len(x):
        return x.copy(), y.copy()

    data = np.column_stack((x, y))
    N = len(data)

    step = (N - 2) / (n_out - 2)

    selected_idx = [0]
    prev_idx = 0

    use_x = kwargs.get('use_x', True)

    for i in range(1, n_out - 1):
        left = int(1 + (i - 1) * step)
        right = int(1 + i * step)
        if i == n_out - 2:
            right = N

        if right <= left:
            left = right - 1
            if left < 1:
                left = 1

        if i == n_out - 2:
            avg_x, avg_y = data[-1, 0], data[-1, 1]
        else:
            next_start = right
            next_end = int(1 + (i + 1) * step)
            if next_end > N:
                next_end = N
            if next_start >= next_end:
                next_start = right
                next_end = min(next_start + 1, N)
            avg_x = np.mean(data[next_start:next_end, 0])
            avg_y = np.mean(data[next_start:next_end, 1])

        px, py = data[prev_idx, 0], data[prev_idx, 1]
        nx, ny = avg_x, avg_y

        bucket = data[left:right]
        x2 = bucket[:, 0]
        y2 = bucket[:, 1]

        if use_x:
            area = np.abs((x2 - px) * (ny - py) - (nx - px) * (y2 - py))
        else:
            area = np.abs(y2 - py)

        max_pos = np.argmax(area)
        selected_idx.append(left + max_pos)
        prev_idx = selected_idx[-1]

    if preserve_endpoints:
        if selected_idx[-1] != N - 1:
            selected_idx.append(N - 1)
    else:
        if selected_idx[-1] != N - 1:
            selected_idx.append(N - 1)

    selected_idx = sorted(set(selected_idx))

    return data[selected_idx, 0], data[selected_idx, 1]