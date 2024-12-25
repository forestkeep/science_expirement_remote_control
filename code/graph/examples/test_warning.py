import numpy as np
import threading

class ObservableArray:
    def __init__(self, initial_data):
        self._data = np.array(initial_data)
        self._lock = threading.Lock()
        self._changed = threading.Event()
        self._changes_in_progress = False

    @property
    def data(self):
        with self._lock:
            return self._data.copy()

    @data.setter
    def data(self, new_data):
        with self._lock:
            self._data = np.array(new_data)
            self._changed.set()  # Уведомляет об изменении
            self._changes_in_progress = True

    def finish_changes(self):
        with self._lock:
            self._changes_in_progress = False
            self._changed.clear()

    def wait_for_change(self):
        # Ожидание изменения и ожидание его завершения
        self._changed.wait()
        self._changed.clear()

class MyClass:
    def __init__(self, initial_data):
        self.y_filtered_data = ObservableArray(initial_data)
        self.calculated_data = None
        self.start_auto_recalculation()

    def start_auto_recalculation(self):
        threading.Thread(target=self.auto_calculate, daemon=True).start()

    def auto_calculate(self):
        while True:
            self.y_filtered_data.wait_for_change()  # Ожидание изменения
            self.calculate_values()  # Пересчет данных всегда после изменения

    def calculate_values(self):
        # Пример расчета: здесь просто берем среднее
        self.calculated_data = np.mean(self.y_filtered_data.data)
        print(f'Пересчитанные данные: {self.calculated_data}')

def my_function(obj: MyClass):
    obj.start_auto_recalculation()
    return obj

import time
# Пример использования
my_class = MyClass([1, 2, 3, 4])

x : int = 15
answ = my_function(x)

my_class.y_filtered_data.data = [2, 3, 4, 5]  # Исполнение пересчета произойдет автоматически
time.sleep(1)  # Дожидаемся завершения потока
my_class.y_filtered_data.data = [2, 3, 89, 5]  # Исполнение пересчета произойдет автоматически

# Ожидание, чтобы увидеть вывод
time.sleep(1)  # Дожидаемся завершения потока
    


