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
        
        denominator = x3 - x1
        clip_min = 1e-10
        denominator_clipped = np.clip(denominator, clip_min, None)

        print(y1, y3, x1, x2, x3)
        y2 = y1 + (y3 - y1) * ((x2 - x1) / denominator_clipped)

        return y2

    @time_decorator
    def combine_interpolate_arrays(self, arr_time_x1, arr_time_x2, values_y1, values_y2):
        
        '''дополняет оба входных массива точек (х,у) так,
        чтобы в них обоих был одинаковый набор x компонент,
        это удобно для дальнейшего усреднения массивов
        '''
        arr_time_x1 = np.array(arr_time_x1)
        arr_time_x2 = np.array(arr_time_x2)
        values_y1 = np.array(values_y1)
        values_y2 = np.array(values_y2)

        if arr_time_x1.size == arr_time_x2.size and np.all(arr_time_x1 == arr_time_x2):
            return values_y1, values_y2, arr_time_x1

        combine_arr_time = self.__combine_and_sort_arrays(arr_time_x1, arr_time_x2)

        x_new = np.empty(combine_arr_time.size)
        y_new = np.empty(combine_arr_time.size)
        is_x_filled = np.zeros(combine_arr_time.size, dtype=bool)
        is_y_filled = np.zeros(combine_arr_time.size, dtype=bool)

        # Индексы для `arr_time_x` и `arr_time_y`
        index_x = np.searchsorted(arr_time_x1, combine_arr_time)
        index_y = np.searchsorted(arr_time_x2, combine_arr_time)

        for i in range(len(combine_arr_time)):
            t = combine_arr_time[i]

            if index_x[i] > 0 and arr_time_x1[index_x[i] - 1] == t:
                x_new[i] = values_y1[index_x[i] - 1]
                is_x_filled[i] = True
            elif index_x[i] < len(arr_time_x1) and arr_time_x1[index_x[i]] == t:
                x_new[i] = values_y1[index_x[i]]
                is_x_filled[i] = True

            if index_y[i] > 0 and arr_time_x2[index_y[i] - 1] == t:
                y_new[i] = values_y2[index_y[i] - 1]
                is_y_filled[i] = True
            elif index_y[i] < len(arr_time_x2) and arr_time_x2[index_y[i]] == t:
                y_new[i] = values_y2[index_y[i]]
                is_y_filled[i] = True

        for i in range(len(combine_arr_time)):
            t = combine_arr_time[i]

            if is_x_filled[i] and not is_y_filled[i]:
                indexy1, indexy2 = self.__find_closest_in_array(arr_time_x2, t)
                y_new[i] = self.__linear_interpolation(
                    arr_time_x2[indexy1],
                    values_y2[indexy1],
                    arr_time_x2[indexy2],
                    values_y2[indexy2],
                    t,
                )
            elif is_y_filled[i] and not is_x_filled[i]:
                indexy1, indexy2 = self.__find_closest_in_array(arr_time_x1, t)
                x_new[i] = self.__linear_interpolation(
                    arr_time_x1[indexy1],
                    values_y1[indexy1],
                    arr_time_x1[indexy2],
                    values_y1[indexy2],
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

        len_end = len(time)

        len_start1 = len(self.arr_time_x)
        len_start2 = len(self.arr_time_y)

        np.testing.assert_array_almost_equal(x, expected_x)
        np.testing.assert_array_almost_equal(y, expected_y)
        np.testing.assert_array_equal(time, expected_time)

        self.assertGreaterEqual(len_end, len_start1)
        self.assertGreaterEqual(len_end, len_start2)

        self.assertEqual(
            len(time), len(expected_time), "Length of time array does not match"
        )

    def test_combine_interpolate_arrays(self):
        x, y, time = self.calculator.combine_interpolate_arrays(
            self.arr_time_x, self.arr_time_y, self.val_x, self.val_y
        )

        self.arr_time_x = np.array(self.arr_time_x)
        self.arr_time_y = np.array(self.arr_time_y)

        all_x_in_time = np.all(np.isin(self.arr_time_x, time))
        all_y_in_time = np.all(np.isin(self.arr_time_y, time))

        print(f"Все элементы из arr_time_x входят в time: {all_x_in_time}")
        print(f"Все элементы из arr_time_y входят в time: {all_y_in_time}")





# Пример вызова функции

if __name__ == "__main__":
    from test_calc_data import expected_time, expected_x, expected_y, generate_arrays
      


    unittest.main()
    arr_time_x, val_x, arr_time_y, val_y = generate_arrays()

    calculator = ArrayProcessor()
    x, y, time = calculator.combine_interpolate_arrays(arr_time_x, arr_time_y, val_x, val_y)
    np.set_printoptions(threshold=np.inf)

    
    arrx1 = [1,2,3,4,5]
    arrx2 = [1,3,4,5]

    arry1 = [1,2,3,4,5]
    arry2 = [2, 6, 8, 10]

    calculator = ArrayProcessor()
    arr1, arr2, gen_x = calculator.combine_interpolate_arrays(arrx1, arrx2, arry1, arry2)

    print(gen_x)
    print()

    print(arr1)
    print(arr2)




    


# kernprof -l -v C:\Users\zahidovds\Desktop\virtual_for_uswindsens\main\graph\calc_values_for_graph.py
