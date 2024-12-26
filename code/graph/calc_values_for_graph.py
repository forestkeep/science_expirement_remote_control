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
    @staticmethod
    def combine_and_sort_arrays(array1, array2):
        # Удаление дубликатов и сортировка в одном шаге
        unique_values = np.unique(np.concatenate((array1, array2)))
        return unique_values

    @staticmethod
    def find_closest_in_array(array, num):
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

    def linear_interpolation(x1, y1, x3, y3, x2):
        if x1 == x3:
            return y1
         
        denominator = x3 - x1
        clip_min = 1e-10
        if denominator > -1*clip_min and denominator < 0:
            denominator= np.clip(denominator, -1*clip_min, None)
        if denominator < clip_min and denominator > 0:
            denominator= np.clip(denominator, None, clip_min)

        y2 = y1 + (y3 - y1) * ((x2 - x1) / denominator)

        return y2
    
    @staticmethod
    def combine_interpolate_arrays(arr_time_x1, arr_time_x2, values_y1, values_y2):
        
        '''дополняет оба входных массива точек (х,у) так,
        чтобы в них обоих был одинаковый набор x компонент,
        y рассчитывается с помощью линейной интерполяции
        '''
        arr_time_x1 = np.array(arr_time_x1)
        arr_time_x2 = np.array(arr_time_x2)
        values_y1 = np.array(values_y1)
        values_y2 = np.array(values_y2)

        if arr_time_x1.size == arr_time_x2.size and np.all(arr_time_x1 == arr_time_x2):
            return values_y1, values_y2, arr_time_x1

        main_x_arr = ArrayProcessor.combine_and_sort_arrays(arr_time_x1, arr_time_x2)

        y1_new = np.empty(main_x_arr.size)
        y2_new = np.empty(main_x_arr.size)
        is_y1_filled = np.zeros(main_x_arr.size, dtype=bool)
        is_y2_filled = np.zeros(main_x_arr.size, dtype=bool)

        # Индексы для `arr_time_x` и `arr_time_y`
        index_x = np.searchsorted(arr_time_x1, main_x_arr)
        index_y = np.searchsorted(arr_time_x2, main_x_arr)

        for i in range(len(main_x_arr)):
            t = main_x_arr[i]

            if index_x[i] > 0 and arr_time_x1[index_x[i] - 1] == t:
                y1_new[i] = values_y1[index_x[i] - 1]
                is_y1_filled[i] = True
            elif index_x[i] < len(arr_time_x1) and arr_time_x1[index_x[i]] == t:
                y1_new[i] = values_y1[index_x[i]]
                is_y1_filled[i] = True

            if index_y[i] > 0 and arr_time_x2[index_y[i] - 1] == t:
                y2_new[i] = values_y2[index_y[i] - 1]
                is_y2_filled[i] = True
            elif index_y[i] < len(arr_time_x2) and arr_time_x2[index_y[i]] == t:
                y2_new[i] = values_y2[index_y[i]]
                is_y2_filled[i] = True

        for i in range(len(main_x_arr)):
            t = main_x_arr[i]

            if is_y1_filled[i] and not is_y2_filled[i]:
                indexy1, indexy2 = ArrayProcessor.find_closest_in_array(arr_time_x2, t)
                y2_new[i] = ArrayProcessor.linear_interpolation(
                    arr_time_x2[indexy1],
                    values_y2[indexy1],
                    arr_time_x2[indexy2],
                    values_y2[indexy2],
                    t,
                )
            elif is_y2_filled[i] and not is_y1_filled[i]:
                indexy1, indexy2 = ArrayProcessor.find_closest_in_array(arr_time_x1, t)
                y1_new[i] = ArrayProcessor.linear_interpolation(
                    arr_time_x1[indexy1],
                    values_y1[indexy1],
                    arr_time_x1[indexy2],
                    values_y1[indexy2],
                    t,
                )

        return y1_new, y2_new, main_x_arr
    
    @staticmethod
    def are_all_arrays_equal(arrays: list[np.ndarray]) -> bool:
        first_array = arrays[0]
        return all(np.array_equal(first_array, array) for array in arrays)
    
    @staticmethod
    def combine_all_arrays(all_x: list, all_y: list, timeout = 5) -> list:
        status = True
        start_stamp = time.time()
        while not ArrayProcessor.are_all_arrays_equal(all_x):
            for i in range(len(all_x)-1):
                all_y[i], all_y[i+1], main_x  = ArrayProcessor.combine_interpolate_arrays(
                                                        arr_time_x1 = all_x[i],
                                                        arr_time_x2 = all_x[i+1],
                                                        values_y1   = all_y[i],
                                                        values_y2   = all_y[i+1]
                                                        )
                all_x[i+1] = main_x
                all_x[i] = main_x

            if time.time() - start_stamp >= timeout:
                status = False


        return all_x, all_y, status


class TestArrayProcessor(unittest.TestCase):
    def setUp(self):
        pass

    def test_linear_interpolation(self):
        # Тесты для функции __linear_interpolation
        self.assertAlmostEqual(ArrayProcessor.linear_interpolation(0, 0, 10, 10, 5), 5 )
        self.assertAlmostEqual(ArrayProcessor.linear_interpolation(0, 0, 10, 10, 0), 0)
        self.assertAlmostEqual(ArrayProcessor.linear_interpolation(0, 0, 10, 10, 10), 10)
        self.assertAlmostEqual(ArrayProcessor.linear_interpolation(1, 2, 3, 4, 2), 3)
        self.assertAlmostEqual(ArrayProcessor.linear_interpolation(1, 2, 5, 6, 3), 4)

    def test_combine_interpolate_arrays(self):
        # Тесты для функции combine_interpolate_arrays
        arr_time_x1 = [1, 2, 3]
        arr_time_x2 = [2, 3, 4]
        values_y1 = [10, 20, 30]
        values_y2 = [15, 25, 35]

        y1_new, y2_new, main_x_arr = ArrayProcessor.combine_interpolate_arrays(arr_time_x1, arr_time_x2, values_y1, values_y2)

        expected_y1_new = [10,  20, 30, 40]
        expected_y2_new = [5, 15, 25, 35]
        expected_main_x_arr = [1, 2, 3, 4]

        np.testing.assert_array_equal(y1_new, expected_y1_new)
        np.testing.assert_array_equal(y2_new, expected_y2_new)
        np.testing.assert_array_equal(main_x_arr, expected_main_x_arr)

    def test_combine_interpolate_arrays_with_overlap(self):
        arr_time_x1 = [1, 3, 5]
        arr_time_x2 = [2, 4]
        values_y1 = [10, 30, 50]
        values_y2 = [20, 40]

        y1_new, y2_new, main_x_arr = ArrayProcessor.combine_interpolate_arrays(arr_time_x1, arr_time_x2, values_y1, values_y2)

        expected_y1_new = [10, 20, 30, 40, 50]
        expected_y2_new = [10, 20, 30, 40, 50]
        expected_main_x_arr = [1, 2, 3, 4, 5]

        np.testing.assert_array_equal(y1_new, expected_y1_new)
        np.testing.assert_array_equal(y2_new, expected_y2_new)
        np.testing.assert_array_equal(main_x_arr, expected_main_x_arr)

    def test_combine_all_arrays_equal(self):
        # Тест, когда все массивы уже равны
        all_x = [np.array([1, 2, 3]), np.array([1, 2, 3])]
        all_y = [np.array([10, 20, 30]), np.array([10, 20, 30])]

        result_x, result_y, _ = ArrayProcessor.combine_all_arrays(all_x, all_y)

        np.testing.assert_array_equal(result_x[0], result_x[1])
        np.testing.assert_array_equal(result_y[0], result_y[1])

    def test_combine_all_arrays_interpolate(self):
        # Тест с разными значениями, требующими интерполяции
        all_x = [np.array([1, 3]), np.array([2, 4])]
        all_y = [np.array([10, 30]), np.array([20,40])]

        result_x, result_y, _ = ArrayProcessor.combine_all_arrays(all_x, all_y)

        # Проверка, что результат содержит объединенные массивы
        expected_x = [np.array([1, 2, 3, 4]),  np.array([1, 2, 3, 4])]
        expected_y = [np.array([10, 20, 30, 40]), np.array([10, 20, 30, 40])]

        np.testing.assert_array_equal(result_x, expected_x)
        np.testing.assert_array_equal(result_y, expected_y)


    def test_combine_all_arrays_empty(self):
        # Тест на пустые массивы
        all_x = [np.array([]), np.array([])]
        all_y = [np.array([]), np.array([])]

        result_x, result_y, _ = ArrayProcessor.combine_all_arrays(all_x, all_y)

        # Проверка, что результат все равно пустой массив
        np.testing.assert_array_equal(result_x[0], np.array([]))
        np.testing.assert_array_equal(result_y[0], np.array([]))

    def test_combine_multiple_arrays(self):
        # Тест с произвольным числом массивов
        all_x = [
            np.array([1, 2, 3]),
            np.array([3, 4, 5]),
            np.array([5, 6])
        ]
        all_y = [
            np.array([10, 20, 30]),
            np.array([30, 40, 50]),
            np.array([50, 60])
        ]

        result_x, result_y, _ = ArrayProcessor.combine_all_arrays(all_x, all_y)

        # Проверка на правильность объединения
        expected_x = np.array([1, 2, 3, 4, 5, 6])
        expected_y = np.array([10, 20, 30, 40, 50, 60])  # Значения интерполируются корректно

        np.testing.assert_array_equal(result_x[0], expected_x)
        self.assertTrue(np.all(np.isin(result_y[0], expected_y)) and np.all(np.isin(result_y[1], expected_y)))



if __name__ == "__main__":

    unittest.main()
    '''
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
    '''




    


# kernprof -l -v C:\Users\zahidovds\Desktop\virtual_for_uswindsens\main\graph\calc_values_for_graph.py
