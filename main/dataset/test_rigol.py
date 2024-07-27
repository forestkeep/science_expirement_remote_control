import os, threading
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import medfilt

def calc_integral(arr, step):
    return np.sum((arr[:-1] + arr[1:])*step/2)

def find_sign_change(derivative):
    sign_changes = []
    for i in range(1, len(derivative)):
        if np.sign(derivative[i]) != np.sign(derivative[i - 1]) and np.sign(derivative[i]) > 0:
            sign_changes.append(i)  # Индекс точки, где происходит смена знака
    return sign_changes

def derivative_at_each_point(x, dx):
    derivative = np.zeros_like(x)
    
    for i in range(1, len(x) - 1):
        derivative[i] = (x[i+1] - x[i-1]) / (2 * dx)
    
    # Вычисление производной на краях массива с использованием односторонних разностей
    derivative[0] = (x[1] - x[0]) / dx
    derivative[-1] = (x[-1] - x[-2]) / dx
    
    return derivative

def plot_multiple_series(*lists, step=1, label1 = "", x, y, label2):
    """
    Строит график для нескольких списков с заданным шагом между значениями.

    :param lists: Списки значений для построения графика.
    :param step: Шаг между значениями на графике.
    """

    fig, axs = plt.subplots(2, 1, figsize=(10, 8))  # Два графика вертикально
    x_values = np.arange(0, len(lists[0]) * step, step)
    x_values = x_values[:len(lists[0])]
    print(f"{len(lists[0])=} {len(lists[1])=} {len(x_values)=}")
    for i, lst in enumerate(lists):
        axs[0].plot(x_values, lst, label=f'CH {i + 1}')
    
    axs[0].set_title(label1)
    axs[0].set_xlabel('X-axis')
    axs[0].set_ylabel('Y-axis')
    axs[0].legend()
    axs[0].grid()


    axs[1].plot(x, y, marker='o', linestyle='-', color='b')  # Строим график

    axs[1].set_title(label2)  # Заголовок графика
    axs[1].set_xlabel('X')  # Подпись по оси X
    axs[1].set_ylabel('Y')  # Подпись по оси Y
    axs[1].grid(True)  # Включаем сетку
    axs[1].axhline(0, color='black',linewidth=0.5, ls='--')  # Добавляем горизонтальную линию на уровне 0
    axs[1].axvline(0, color='black',linewidth=0.5, ls='--')  # Добавляем вертикальную линию на уровне 0

    plt.tight_layout()
    plt.show()

def threshold_mean_std(data):
    """Вычисляет порог на основе среднего значения и стандартного отклонения."""
    mean = np.mean(data)
    std_dev = np.std(data)
    k = 2  # Можно настроить коэффициент
    threshold = mean + k * std_dev
    return threshold

def threshold_median(data):
    """Вычисляет порог на основе медианы и интерквартильного размаха."""
    Q1 = np.percentile(data, 40)
    Q3 = np.percentile(data, 60)
    IQR = Q3 - Q1
    threshold = Q3 + 1.5 * IQR  # Порог устанавливается на уровне Q3 + 1.5 * IQR
    return threshold


def calculate_results(C):
    Q2 = 1.67#сильно влияет на форму петли. уточнить влияние, для чего она введена?

    noise_level1 = threshold_mean_std(C)
    print(f"{noise_level1=}")
    noise_level2 = threshold_median(C)
    print(f"{noise_level2=}")
    noise_level = noise_level2

    n = len(C)

    # Вычисление средних значений и сдвигов
    D2 = np.mean(C)
    E2 = C - D2
    F2 = np.where(np.abs(E2) > noise_level, 1, 0)
    
    G2 = E2 * F2
    H2 = np.mean(G2)

    # Интегрирование
    I2 = G2 - H2
    J2 = np.cumsum(I2)  # Кусковая сумма
    K2 = J2 - np.max(J2) / 2
    L2 = K2 + Q2

    # Нормировка
    M = np.where(L2 <= 0, L2 / np.min(L2), L2 / -np.max(L2))

    return M

def plot_arrays(x, y, label):
    plt.figure(figsize=(10, 6))  # Задаем размер графика
    plt.plot(x, y, marker='o', linestyle='-', color='b')  # Строим график

    plt.title(label)  # Заголовок графика
    plt.xlabel('X')  # Подпись по оси X
    plt.ylabel('Y')  # Подпись по оси Y
    plt.grid(True)  # Включаем сетку
    #plt.axhline(0, color='black',linewidth=0.5, ls='--')  # Добавляем горизонтальную линию на уровне 0
    #plt.axvline(0, color='black',linewidth=0.5, ls='--')  # Добавляем вертикальную линию на уровне 0
    plt.show()  # Отображаем график



def test_calc(arr1, arr2, increment):
            # Выводим полученный словарь
            #print(data_dict)
            #print(f"{len(data_dict['CH1'])=}   {len(data_dict['CH2'])=}")
            # Определяем размер окна
            #window_size =  int(input("Введите размер окна для фильтра: "))
            # Создаем массив весов для скользящего среднего
            data_dict = {}
            data_dict['CH1'] = arr1
            data_dict['CH2'] = arr2
            window_size = 50
            weights = np.ones(window_size) / window_size
            data_dict['CH2_mean'] = np.convolve(data_dict['CH2'], weights, mode='same')


            integral = calc_integral(arr = data_dict['CH1'], step = increment)
            derivative = derivative_at_each_point(x = data_dict['CH2_mean'], dx = increment)
            interval_index = np.array(find_sign_change(data_dict['CH2_mean']))
            interval_values = interval_index*increment
            #print(f"{integral=}")
            #print(f"{derivative=}")
            print(f"{interval_values=}")
            #plot_arrays(data_dict['CH1'], data_dict['CH2'], selected_file)

            start_point = input("начальная точка? ")
            if start_point.upper() == "AUTO":
                start_index = interval_index[0]
                stop_index = interval_index[1]
            else:
                start_index = int(start_point)
                num_points = int(input("количество точек? "))
                stop_index = start_index + num_points


            R = 100+90
            d = 14.2
            A = R*(3.1415*2*d/2*(10**(-12)))
            C = 16
            X =  data_dict['CH2'][start_index: stop_index]/A + C
            Y = calculate_results(data_dict['CH1'][start_index: stop_index])


            size1 = len(X)
            size2 = len(Y)

            if size1 > size2:

                X = X[:size2]
            elif size2 > size1:
                Y = Y[:size1]
            #plot_arrays(X, Y, selected_file)

            plot_multiple_series(data_dict['CH1'][start_index: stop_index], 
                                data_dict['CH2'][start_index: stop_index],
                                step= increment , 
                                label1 = selected_file, x=X, y=Y, label2=selected_file)

if __name__ == "__main__":
    # Получаем текущую директорию
    current_directory = os.path.dirname(os.path.abspath(__file__))

    print(f"{current_directory=}")

    # Находим все файлы во всех вложенных директориях
    all_files = []
    for root, dirs, files in os.walk(current_directory):
        for file in files:
            all_files.append(os.path.join(root, file))

    # Выводим список файлов с номерами
    for index, file in enumerate(all_files):
        print(f"{index + 1}: {file}")
    while True:
        # Запрашиваем у пользователя номер файла
        file_number = int(input("Введите номер нужного файла: ")) - 1
        # Проверяем, что номер файла корректен 
        if 0 <= file_number < len(all_files):
            selected_file = all_files[file_number]
            df = pd.read_csv(selected_file, sep=';')

            # Создаем словарь для хранения данных
            data_dict = {}
            
            # Считываем данные из DataFrame
            #print(df.columns)
            for column in df.columns:
                # Конвертируем данные в float и помещаем в словарь
                data_dict[column] = df[column].astype(str).tolist()
            #print(data_dict)
            for key, values in data_dict.items():
                # Новая переменная для хранения конвертированных значений
                converted_values = []
                for val in values:
                    val = val.replace(',', '.')
                    try:
                        # Пытаемся конвертировать в float
                        if val == "nan":
                            continue
                        converted_values.append(float(val))
                    except ValueError:
                        # Игнорируем неконвертируемые значения
                        continue
                # Обновляем словарь с новыми списками значений
                data_dict[key] = np.array(converted_values)


            test_calc(arr1 = data_dict['CH1'], arr2 = data_dict['CH2'], increment=data_dict['Increment'][0] )
        
        else:
            print("Неверный номер файла.")
