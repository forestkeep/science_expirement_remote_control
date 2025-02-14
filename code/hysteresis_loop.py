import numpy as np
import matplotlib

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from scipy.integrate import trapezoid

def apply_threshold(array, threshold=0.004):
    return np.where(np.abs(array) > threshold, 1, 0)

def remove_plateau(H, M, threshold=0.0001):
    # параметр threshold отвечает за то, насколько сильно или слабо мы отсеиваем
    # множество одинаковых значений, например, когда поле выходит в насыщение в одну и в другую сторону,
    # эти отрезки могут быть очень растянутыми и сильно влиять на вычисления, которые участвуют в построении графика,
    # поэтому нужно, чтобы была возможность настройки этого параметра перед запуском построения,
    # иначе график может отображаться некорректно
    dM = np.abs(np.gradient(M))
    mask = dM > threshold
    return H[mask], M[mask]

def calculate_hysteresis_parameters(H, M):
    H_centered = H - np.mean(H)
    M_centered = M - np.mean(M)

    M_zero_crossings = np.where(np.diff(np.sign(M_centered)))[0]
    Hc_values = float(np.mean(H_centered[M_zero_crossings])) if len(M_zero_crossings) > 1 else float(
        H_centered[M_zero_crossings[0]]) if len(M_zero_crossings) == 1 else None

    if len(M_zero_crossings) > 0:
        H_mid = float(np.mean(H_centered[M_zero_crossings]))
    else:
        H_mid = None

    if H_mid is not None:
        mask = np.isclose(H_centered, H_mid, atol=0.001)
        if np.any(mask):
            M_upper = np.max(M_centered[mask])
            M_lower = np.min(M_centered[mask])
            Mr_values = float(np.mean([np.abs(M_upper), np.abs(M_lower)]))
        else:
            Mr_values = None
    else:
        Mr_values = None

    Mm_positive = np.max(M_centered[M_centered > 0])
    Mm_negative = np.min(M_centered[M_centered < 0])
    Mm = float(np.mean([np.abs(Mm_positive), np.abs(Mm_negative)]))

    area = float(trapezoid(M_centered, H_centered))

    return {
        "Коэрцитивная сила (Hc), Э": Hc_values * 1000 / 4 / 3.14,
        "Остаточная намагниченность, (Mr), магнитный момент": Mr_values,
        "Максимальная намагниченность (Mm), магнитный момент": Mm,
        "Площадь петли гистерезиса": area
    }

def process_magnetization_data(M):
    M_avg = np.full_like(M, np.mean(M))
    M_diff = M - M_avg
    M_threshold = apply_threshold(M_diff)
    M_multiplied = M_diff * M_threshold
    M_avg_4 = np.mean(M_multiplied)
    M_diff_5 = M_multiplied - M_avg_4
    M_integral = np.zeros_like(M_diff_5)
    M_integral[0] = M_diff_5[0]
    for i in range(1, len(M_diff_5)):
        M_integral[i] = M_diff_5[i] + M_integral[i - 1]
    return M_integral

def plot_hysteresis_loop_and_calculate_parameters(H, M):
    H_filtered, M_filtered = remove_plateau(H, M)
    M_processed = process_magnetization_data(M_filtered)
    params = calculate_hysteresis_parameters(H_filtered, M_processed)

    plt.figure(figsize=(8, 6))
    plt.plot((H_filtered - np.mean(H_filtered))*1000/4/3.14, M_processed - np.mean(M_processed), 'b-', label='Петля гистерезиса')
    plt.xlabel("H (центрированное)")
    plt.ylabel("M (центрированное)")
    plt.title("График петли гистерезиса")
    plt.legend()
    plt.grid()

    plt.show() #опциональная команда для отображения графика, можешь посмотреть, как он выглядит

    return params, (H_filtered - np.mean(H_filtered))*1000/4/3.14, M_processed - np.mean(M_processed)

#[
def read_data_from_file(filename):
    data = np.loadtxt(filename)
    H = data[:, 0]
    M = data[:, 1]
    return H, M

filename = "test_data.txt"
H, M = read_data_from_file(filename)
#] удалить этот кусок кода при передаче исходных массивов через основную программу
params = plot_hysteresis_loop_and_calculate_parameters(H, M)
# Здесь переменной params передаются: параметры петли гистерезиса в виде словаря,
# массивы со значениями поля и намагниченности, которые уже можно использовать для построения графика,
# то есть через индексы переменной param можно вытащить всё, что нужно

# H и M - исходные массивы поля и ЭДС, т.е. показания с датчиков Холла и напряжение

# Единицы измерения: H - Э (Эрстед), M - магнитный момент (это то в чем выводится, переводил из А/м в Э)

# Переменной передаём результат функции plot_hysteresis_loop_and_calculate_parameters и через индексы вытаскиваем всё необходимое

# Для наглядности
print(params[0])
print(params[1])
print(params[2])