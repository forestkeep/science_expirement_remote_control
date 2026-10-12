import unittest
import numpy as np

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