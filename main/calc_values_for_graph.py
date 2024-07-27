import numpy as np


class ArrayProcessor:
    def __combine_and_sort_arrays(self, array1, array2):
        combined = np.concatenate((array1, array2))
        sorted_array = np.sort(combined)  
        unique_values = np.unique(sorted_array)

        return unique_values

    def  __find_closest_in_array(self, array, num):
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

    def combine_interpolate_arrays(self, arr_time_x, arr_time_y, values_x, values_y):
        #print(f"{arr_time_x=} {values_x=} {arr_time_y=} {values_y=}")


        arr_time_x = np.array(arr_time_x)
        arr_time_y = np.array(arr_time_y)
        values_x = np.array(values_x)
        values_y = np.array(values_y)
        #print(f"{values_x=} {values_y=}")

        if arr_time_x.size == arr_time_y.size:
            if np.all(arr_time_x == arr_time_y):
                return values_x, values_y, arr_time_x

        #print(f"{arr_time_x=} {arr_time_y=}")
        combine_arr_time = self.__combine_and_sort_arrays(arr_time_x, arr_time_y)
        #print(f"{combine_arr_time=}")
        x_new = []
        y_new = []

        for i in range(combine_arr_time.size):
            if True in np.isin(arr_time_x, combine_arr_time[i]):
            #if combine_arr_time[i] in arr_time_x:

                indexy1 = np.where(np.in1d(arr_time_x, combine_arr_time[i]))[0]
                x_new = np.append(x_new, values_x[indexy1])

                if combine_arr_time[i] not in arr_time_y:

                    indexy2_1, indexy2_2 =  self.__find_closest_in_array(arr_time_y, combine_arr_time[i])
                    y_new = np.append(y_new, self.__linear_interpolation(arr_time_y[indexy2_1], values_y[indexy2_1], arr_time_y[indexy2_2], values_y[indexy2_2], combine_arr_time[i]))
                else:
                    indexy1 = np.where(np.in1d(arr_time_y, combine_arr_time[i]))[0]
                    y_new = np.append(y_new, values_y[indexy1])

            elif combine_arr_time[i] in arr_time_y:

                indexy1 = np.where(np.in1d(arr_time_y, combine_arr_time[i]))[0]
                y_new = np.append(y_new, values_y[indexy1])

                if combine_arr_time[i] not in arr_time_x:

                    indexy2_1, indexy2_2 =  self.__find_closest_in_array(arr_time_x, combine_arr_time[i])
                    x_new = np.append(x_new, self.__linear_interpolation(arr_time_x[indexy2_1], values_x[indexy2_1], arr_time_x[indexy2_2], values_x[indexy2_2], combine_arr_time[i]))
                else:
                    indexy1 = np.where(np.in1d(arr_time_x, combine_arr_time[i]))[0]
                    x_new = np.append(x_new, values_x[indexy1])

        return x_new, y_new, combine_arr_time


if __name__ == "__main__":
    arr_time_x = [1, 3, 4, 5]
    val_x =      [0, 10, 10, 5]
    arr_time_y = [1, 2, 4]
    val_y =      [-1, -5, 6]

    calculator = ArrayProcessor()
    x, y, time = calculator.combine_interpolate_arrays(arr_time_x, arr_time_y, val_x, val_y)
    print("X\ttime\tY")
    for i in range(len(x)):
        print(f"{x[i]}\t{time[i]}\t{y[i]}")

