import random
import time
import numpy as np
import pandas as pd


class test_graph:

    def __init__(self):
        self.start_time = time.time()
        ch1, ch2, step = self.read_param_from_test()
        '''
        self.main_dict = {
            "device1": {"ch_1": {"time": [0], self.get_param(): self.get_values()}},
            "device3": {
                "ch_1": {
                    "time": [0],
                    self.get_param(): self.get_values(),
                    "wavech": [ch1],
                    "scale": [step],
                },
                "ch_2": {
                    "time": [0],
                    self.get_param(): self.get_values(),
                    self.get_param(): self.get_values(),
                    self.get_param(): self.get_values(),
                },
                "ch_3": {"time": [0], "wavech": [ch2], "scale": [step]},
                "ch_4": {
                    "time": [0],
                    "wavech": [self.generate_random_list(10, 0, 10)],
                    "scale": [0.002],
                },
            },
            "device4": {
                "ch_1": {
                    "time": [0],
                    "wavech": [self.generate_random_list(10, 0, 10)],
                    "scale": [0.002],
                }
            },
        }
        
        self.main_dict = {
            "АКИП-2404_1":{
                "ch-2_meas":{
                    "time": [1,2,3,4,5,6,7,8,9,10],
                    "voltage": [1,2,3,4,5,6,7,8,9,10],
                },
                "ch-1_meas":{
                    "time": [1,2,3,4,5,6,7,8,9,10],
                    "voltage": [2,4,6,8,10,12,14,16,18,20],
                }
            }
        }
        '''
        self.main_dict = {
            "АКИП":{
                "ch-2":{
                    "time": [1,2,3,4,5,6,7,8,9,10],
                    "voltage": [1,2,3,4,5,6,7,8,9,10],
                }
            },
            "MXN":{
                "ch-1":{
                    "time": [1,2,3,4,5,6,7,8,9,10],
                    "curent": [2,4,6,8,10,12,14,16,18,20],
                }
            }
        }

    def read_param_from_test(self):
        import os

        current_directory = os.path.dirname(os.path.abspath(__file__))

        file_name = "test_loop.csv"

        # Формирование полного пути
        full_path = os.path.join(current_directory, file_name)

        df = pd.read_csv(full_path, sep=";")

        # Создаем словарь для хранения данных
        data_dict = {}

        # Считываем данные из DataFrame
        for column in df.columns:
            # Конвертируем данные в float и помещаем в словарь
            data_dict[column] = df[column].astype(str).tolist()
        for key, values in data_dict.items():
            # Новая переменная для хранения конвертированных значений
            converted_values = []
            for val in values:
                val = val.replace(",", ".")
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

        return data_dict["CH1"], data_dict["CH2"], data_dict["Increment"][0]

    def get_param(self):
        random_X = ["R", "L", "C", "PHAS", "V", "I", "D", "|Z|", "Q"]
        return random.choice(random_X)

    def get_values(self):
        return [random.randint(1, 10) for _ in range(1)]

    def generate_random_list(self, size, lower_bound=0, upper_bound=100):

        frequency = np.random.uniform(
            lower_bound, upper_bound
        )  # Частота в диапазоне от 0.5 до 5.0
        x = np.linspace(0, 2 * np.pi, size)
        sine_wave = list(
            np.round(np.sin(frequency * x), 2)
        )  # Округляем до 2 знаков после запятой

        return sine_wave

    def update_dict(self, main_dict):
        """добавляет в каждый конечный список число"""
        for channel in main_dict.values():
            for key, value in channel.items():
                    if key == "time":
                        # Добавляем текущее время
                        value.append(round(time.time() - self.start_time))
                    elif (
                        isinstance(value, list)
                        and not any(isinstance(i, list) for i in value)
                        and key != "wavech"
                    ):
                        # Добавляем случайное число от 1 до 10 в конечные списки
                        value.append(random.randint(1, 10))
                    elif (
                        isinstance(value, list)
                        and any(isinstance(i, list) for i in value)
                        or key == "wavech"
                    ):
                        # Если ключ содержит 'wave', добавляем случайное число в каждый вложенный список
                        value.append(
                            self.generate_random_list(
                                size=100, lower_bound=0, upper_bound=10
                            )
                        )
        return main_dict

    def append_values(self):
        while True:
            self.main_dict = self.update_dict(self.main_dict)
            yield self.main_dict

    def get_time(self):
        start_range = 1
        end_range = 10
        list_size = 1
        all_values = list(range(start_range, end_range * list_size))
        random.shuffle(all_values)
        # Берем первые list_size элементов
        time_dict = all_values[:list_size]
        time_dict.sort()
        return time_dict