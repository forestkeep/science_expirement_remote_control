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

import random
import time
import math
import itertools
import random

import numpy as np
import pandas as pd


class test_graph:

    def __init__(self, is_sine_wave = False):
        self.start_time = time.time()
        #ch1, ch2, step = self.read_param_from_test()
        ch1, ch2, step = [1], [2], 0.002
        if is_sine_wave:
            self.sin_gen = self.generate_sine_wave()
        
        self.main_dict = {
            '''
            "device1": {"ch_1": {self.get_param(): [self.get_values(), [0] ]}},
            '''
            "device3": {
                "ch_1": {
                    self.get_param(): [self.get_values(), [0] ],
                    "wavech": [[ch1], [0] ],
                    "scale": [[step], [0] ],
                },
                
                "ch_2": {
                    self.get_param(): [self.get_values(), [0] ],
                    self.get_param(): [self.get_values(), [0] ],
                    self.get_param(): [self.get_values(), [0] ],
                },
                
                "ch_3": {"wavech": [[ch2], [0] ], "scale": [[step], [0] ]},
                "ch_4": {
                    "wavech": [ [self.generate_random_list(10, 0, 10)], [0] ],
                    "scale": [[0.002], [0]],
                
                },
                
            },
            
            "device4": {
                "ch_1": {
                    "wavech": [[self.generate_random_list(10, 0, 10)], [0] ],
                    "scale": [[0.002], [0] ],
                }
            
            },
            
        }

        if is_sine_wave:   
            val, x = next(self.sin_gen)

            self.main_dict = {
                "device3": {
                    "ch_1": {
                        self.get_param(): [self.get_values(), [0] ],
                        "wavech": [[ch1], [0] ],
                        "scale": [[step], [0] ],
                    },
                    "ch_2": {
                        self.get_param(): [self.get_values(), [0] ],
                        "SIN": [val, [x]]
                    }, 
                },  
            }

        else:
            self.main_dict = {
                "device3": {
                    "ch_1": {
                        self.get_param(): [self.get_values(), [0] ],
                        "wavech": [[ch1], [0] ],
                        "scale": [[step], [0] ],
                    },
                    "ch_2": {
                        self.get_param(): [self.get_values(), [0] ],
                    }, 
                },  
            }

        '''
        
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
        
        self.main_dict = {
            "АКИП":{
                "ch-2":{
                    "time": [1,2,3,4,5,6,7,8,9,10],
                    "voltage": [1,3,2,8,2,9,8,3,7,15],
                }
            },
            "MXN":{
                "ch-1":{
                    "time": [1,2,3,4,5,6,7,8,9,10],
                    "curent": [2,4,6,8,10,12,14,16,25,40],
                }
            }
        }
        '''

    def generate_sine_wave(self, step=0.1, interval=10, amplitude=1, modulation_interval=100):
        for x in range(1000):
            t = x * step

            modulating_amplitude = (math.sin(2 * math.pi * t / modulation_interval) + 1) / 2
            
            value = amplitude * modulating_amplitude * math.sin(2 * math.pi * t / interval)
            
            noise = random.uniform(-3, 3)
            value += noise
            
            yield value, x

    def read_param_from_test(self):
        import os

        current_directory = os.path.dirname(os.path.abspath(__file__))

        file_name = "test_loop.csv"

        full_path = os.path.join(current_directory, file_name)

        df = pd.read_csv(full_path, sep=";")

        data_dict = {}

        for column in df.columns:
            data_dict[column] = df[column].astype(str).tolist()
        for key, values in data_dict.items():
            converted_values = []
            for val in values:
                val = val.replace(",", ".")
                try:
                    if val == "nan":
                        continue
                    converted_values.append(float(val))
                except ValueError:
                    continue
            data_dict[key] = np.array(converted_values)

        return data_dict["CH1"], data_dict["CH2"], data_dict["Increment"][0]

    def get_param(self):
        random_X = ["R", "L", "C", "PHAS", "V", "I", "D", "|Z|", "Q", "T", "Freq", "len"]
        return random.choice(random_X)

    def get_values(self):
        return [random.randint(1, 10)]

    def generate_random_list(self, size, lower_bound=0, upper_bound=100):

        frequency = np.random.uniform(
            lower_bound, upper_bound
        )
        x = np.linspace(0, 2 * np.pi, size)
        sine_wave = list(
            np.round(np.sin(frequency * x), 2)
        )

        return sine_wave

    def update_dict(self, main_dict):
        """изменяет число в каждой конечной ветке c 50% шансом"""
        for channels in main_dict.values():
            for channel, parameters in channels.items():
                for key, value in parameters.items():
                    if random.random() < 0.5:
                        #value[0] = [[]]
                        #value[1] = [[]]
                        pass
                        #continue

                    if key == "SIN":
                        pass
                        val, x = next(self.sin_gen)
                        value[0] = [val]
                        value[1] = [x]
                    elif (
                        isinstance(value, list)
                        and key != "wavech"
                    ):
                        buf = value[0][0] + random.randint(-10, 10)*(1 + random.uniform(-0.2, 0.2))
                        value[0] = [buf]
                        value[1] = [round(time.time() - self.start_time, 3)]
                    elif (
                        isinstance(value, list)
                        or key == "wavech"
                    ):
                        # Если ключ содержит 'wave', добавляем случайное число в каждый вложенный список
                        value[0] =[self.generate_random_list(
                                size=10, lower_bound=0, upper_bound=10)]
                        value[1] = [round(time.time() - self.start_time, 3)]
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
        time_dict = all_values[:list_size]
        time_dict.sort()
        return time_dict