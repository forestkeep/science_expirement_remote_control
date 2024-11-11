# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

import time
import unittest

import numpy as np


def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Метод {func.__name__} - {end_time - start_time} с")
        return result

    return wrapper


class ArrayProcessor:

    def __combine_and_sort_arrays(self, array1, array2):
        # Удаление дубликатов и сортировка в одном шаге
        unique_values = np.unique(np.concatenate((array1, array2)))
        return unique_values

    def __find_closest_in_array(self, array, num):
        low = 0
        high = array.size - 1
        if num < array[low]:
            return low + 1, low
        if num > array[high]:
            return high, high - 1

        while low <= high:
            mid = (low + high) // 2
            if array[mid] == num:
                return mid, mid
            elif array[mid] < num:
                low = mid + 1
            else:
                high = mid - 1

        if high < 0:
            return low + 1, low
        if low >= len(array):
            return high, high - 1

        if abs(array[low] - num) < abs(array[high] - num):
            return low, high
        else:
            return high, low

    def __linear_interpolation(self, x1, y1, x3, y3, x2):
        if x1 == x3:
            return y1
        y2 = y1 + (y3 - y1) * ((x2 - x1) / (x3 - x1))
        return y2

    @time_decorator
    def combine_interpolate_arrays(self, arr_time_x, arr_time_y, values_x, values_y):
        arr_time_x = np.array(arr_time_x)
        arr_time_y = np.array(arr_time_y)
        values_x = np.array(values_x)
        values_y = np.array(values_y)

        if arr_time_x.size == arr_time_y.size and np.all(arr_time_x == arr_time_y):
            return values_x, values_y, arr_time_x

        combine_arr_time = self.__combine_and_sort_arrays(arr_time_x, arr_time_y)

        x_new = np.empty(combine_arr_time.size)
        y_new = np.empty(combine_arr_time.size)
        is_x_filled = np.zeros(combine_arr_time.size, dtype=bool)
        is_y_filled = np.zeros(combine_arr_time.size, dtype=bool)

        # Индексы для `arr_time_x` и `arr_time_y`
        index_x = np.searchsorted(arr_time_x, combine_arr_time)
        index_y = np.searchsorted(arr_time_y, combine_arr_time)

        for i in range(len(combine_arr_time)):
            t = combine_arr_time[i]

            if index_x[i] > 0 and arr_time_x[index_x[i] - 1] == t:
                x_new[i] = values_x[index_x[i] - 1]
                is_x_filled[i] = True
            elif index_x[i] < len(arr_time_x) and arr_time_x[index_x[i]] == t:
                x_new[i] = values_x[index_x[i]]
                is_x_filled[i] = True

            if index_y[i] > 0 and arr_time_y[index_y[i] - 1] == t:
                y_new[i] = values_y[index_y[i] - 1]
                is_y_filled[i] = True
            elif index_y[i] < len(arr_time_y) and arr_time_y[index_y[i]] == t:
                y_new[i] = values_y[index_y[i]]
                is_y_filled[i] = True

        for i in range(len(combine_arr_time)):
            t = combine_arr_time[i]

            if is_x_filled[i] and not is_y_filled[i]:
                indexy1, indexy2 = self.__find_closest_in_array(arr_time_y, t)
                y_new[i] = self.__linear_interpolation(
                    arr_time_y[indexy1],
                    values_y[indexy1],
                    arr_time_y[indexy2],
                    values_y[indexy2],
                    t,
                )
            elif is_y_filled[i] and not is_x_filled[i]:
                indexy1, indexy2 = self.__find_closest_in_array(arr_time_x, t)
                x_new[i] = self.__linear_interpolation(
                    arr_time_x[indexy1],
                    values_x[indexy1],
                    arr_time_x[indexy2],
                    values_x[indexy2],
                    t,
                )

        return x_new, y_new, combine_arr_time


class TestArrayProcessor(unittest.TestCase):
    def setUp(self):
        self.calculator = ArrayProcessor()
        self.arr_time_x, self.val_x, self.arr_time_y, self.val_y = generate_arrays()

    def test_combine_interpolate_arrays(self):
        x, y, time = self.calculator.combine_interpolate_arrays(
            self.arr_time_x, self.arr_time_y, self.val_x, self.val_y
        )

        np.testing.assert_array_almost_equal(x, expected_x)
        np.testing.assert_array_almost_equal(y, expected_y)
        np.testing.assert_array_equal(time, expected_time)

        self.assertEqual(
            len(time), len(expected_time), "Length of time array does not match"
        )


# Пример вызова функции

if __name__ == "__main__":
    from test_calc_data import expected_time, expected_x, expected_y, generate_arrays

    unittest.main()
    """
    arr_time_x, val_x, arr_time_y, val_y = generate_arrays()

    calculator = ArrayProcessor()
    x, y, time = calculator.combine_interpolate_arrays(arr_time_x, arr_time_y, val_x, val_y)
    np.set_printoptions(threshold=np.inf)
    #print(np.array2string(x, separator=', '))
    #print(np.array2string(y, separator=', '))
    print(np.array2string(time, separator=', '))
    """


# kernprof -l -v C:\Users\zahidovds\Desktop\virtual_for_uswindsens\main\graph\calc_values_for_graph.py
