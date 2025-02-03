import numpy as np
from scipy.integrate import simpson


def calculate_hysteresis_parameters(H: np.ndarray, M: np.ndarray):
    """
    Рассчитывает параметры петли магнитного гистерезиса после центрирования данных.

    :param H: numpy массив значений напряженности магнитного поля (абсцисса)
    :param M: numpy массив значений намагниченности (ордината)
    :return: словарь с параметрами петли гистерезиса
    """
    # Центрирование данных
    H_centered = H - np.mean(H)
    M_centered = M - np.mean(M)

    # Интерполяция пересечения с осями, если нет нулевых значений
    if not np.any(M_centered == 0):
        H_zero_crossings = np.interp(0, M_centered, H_centered)
    else:
        H_zero_crossings = np.array([H_centered[np.where(M_centered == 0)][0]])

    if not np.any(H_centered == 0):
        M_zero_crossings = np.interp(0, H_centered, M_centered)
    else:
        M_zero_crossings = np.array([M_centered[np.where(H_centered == 0)][0]])

    # Коэрцитивная сила (Hc) - H при M = 0
    Hc_values = float(H_zero_crossings) if H_zero_crossings is not None else None

    # Остаточная намагниченность (Mr) - M при H = 0
    Mr_values = float(M_zero_crossings) if M_zero_crossings is not None else None

    # Максимальная намагниченность (Mm)
    Mm = np.max(np.abs(M_centered))

    # Площадь петли гистерезиса (интеграл M dH)
    area = simpson(y = M_centered, x = H_centered)

    return {
        "Коэрцитивная сила (Hc)": Hc_values,
        "Остаточная намагниченность (Mr)": Mr_values,
        "Максимальная намагниченность (Mm)": float(Mm),
        "Площадь петли гистерезиса": float(area)
    }


# Пример использования (чтение данных из файла):
filename = r"graph\calc_magnetostriction\данные для тестирования2.txt"
data = np.loadtxt(filename)
H, M = data[:, 0], data[:, 1]

params = calculate_hysteresis_parameters(H, M)
print(params)
