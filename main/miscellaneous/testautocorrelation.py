import numpy as np
import matplotlib.pyplot as plt

def modulated_sinusoidal(amplitude_carrier, frequency_carrier, phase_carrier, 
                          amplitude_modulator, frequency_modulator, phase_modulator, 
                          duration, sample_rate):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)  # Время
    # Главная (несущая) синусоида с фазой
    carrier = amplitude_carrier * np.sin(2 * np.pi * frequency_carrier * t + phase_carrier)
    # Модулирующая синусоида с фазой
    modulator = amplitude_modulator * np.sin(2 * np.pi * frequency_modulator * t + phase_modulator)
    # Модулированный сигнал
    modulated_signal = carrier * (1 + modulator)  # Амплитудная модуляция
    return t, modulated_signal

# Пример использования
amplitude_carrier = 1.0
frequency_carrier = 20.0       # Гц
phase_carrier = 0.0           # Фаза несущей
amplitude_modulator = 0.9
frequency_modulator = 0.5      # Гц
phase_modulator = np.pi / 1    # Фаза модулятора
phase_modulator = -1.3
duration = 2.0                  # секунды
sample_rate = 100               # выборки в секунду

t, modulated_points = modulated_sinusoidal(amplitude_carrier, frequency_carrier, phase_carrier, 
                                            amplitude_modulator, frequency_modulator, phase_modulator, 
                                            duration, sample_rate)
def autocorrelation(x, y):
    n = len(y)
    result = [0] * (2 * n - 1)

    # Вычисляем автокорреляцию
    for lag in range(n):
        for i in range(n - lag):
            result[lag] += y[i] * y[i + lag]

    for lag in range(1, n):
        for i in range(n - lag):
            result[n - 1 + lag] += y[i] * y[i + lag]

    # Нормировка
    max_corr = max(result)
    normalized_result = [x / max_corr for x in result]

    return normalized_result

# Пример использования
x = [i / 100 for i in range(100)]  # Массив x
y = [2 * (1 if (5 * xi) % 1 < 0.5 else -1) for xi in x]  # Квадратный сигнал для y

# Вычисление автокорреляционной функции
auto_corr = autocorrelation(t,modulated_points)
# Построение графика
plt.plot(auto_corr)
plt.title('Модулированная синусоидальная функция с фазой')
plt.xlabel('Время (с)')
plt.ylabel('Амплитуда')
plt.grid()
plt.show()