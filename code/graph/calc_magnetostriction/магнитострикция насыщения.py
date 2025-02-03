import numpy as np

def find_plateau(x_values, y_values):
    # Вычисляем первую производную (разность) по оси Y
    dy = np.diff(y_values)
    dx = np.diff(x_values)

    # Вычисляем отношение изменения Y к изменению X (приближенная производная)
    derivative = dy / dx

    # Находим минимальные изменения производной, что указывает на плато
    # В идеале, на плато производная будет близка к нулю
    min_change_index = np.argmin(np.abs(derivative))  # Индекс минимальной производной
    plateau_x = x_values[min_change_index]
    plateau_y = y_values[min_change_index]

    return plateau_x, plateau_y

# Пример использования:
x = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
y = [0, 2, 4, 6, 8, 10, 12, 12, 12, 11, 10]

plateau_x, plateau_y = find_plateau(x, y)
print(f"Plateau X: {plateau_x}, Plateau Y: {plateau_y}")
