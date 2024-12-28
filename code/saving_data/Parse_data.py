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

import copy
import enum
import logging
import os
import threading
from datetime import datetime

import pandas
from pandas.io.excel import ExcelWriter
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class osc_data:
    def __init__(self) -> None:
        self.data = []
        self.name = None
        self.time = None
        self.step = None


class saved_data:
    """класс хранения данных для отдельно взятого канала устройства"""

    def __init__(self, name_device, ch) -> None:
        self.name_device = name_device
        self.ch = ch
        self.settings = []
        self.data = {}
        self.osc_data = []


class type_save_file(enum.Enum):
    txt = 1
    excel = 2
    origin = 3


class saving_data:
    def __init__(self) -> None:
        saving_thread = threading.Thread(target=self.save_data)

    def __save_excell(self, output_file_path):
        column_number = 0
        max_dev_data_len = 0
        max_dev_set_len = 0
        for dev in self.devices:
            column_number += len(dev.data.keys()) + 1
            if "time" in dev.data:
                if len(dev.data["time"]) > max_dev_data_len:
                    max_dev_data_len = len(dev.data["time"])
            if len(dev.settings) > max_dev_set_len:
                max_dev_set_len = len(dev.settings)

        data_frame = {}
        for h in range(column_number):
            data_frame[h] = []

        h = 0
        number_tab = []
        k = 0
        for i in range(len(self.devices)):
            text = QApplication.translate("parse_data", "Прибор:{device} канал:{ch}")
            text = text.format(device=self.devices[i].name_device, ch=self.devices[i].ch)
            data_frame[h].append(
                text
            )
            h += 1

            number_tab.append(len(self.devices[i].data))
            k += 1
            for j in range(number_tab[k - 1]):
                data_frame[h].append(" ")
                h += 1

        h = 0
        for i in range(len(self.devices)):
            for param_name in self.devices[i].data.keys():
                data_frame[h].append(f"{param_name}")
                h += 1
            data_frame[h].append(" ")
            h += 1

        h = 0
        max_index = 0
        for dev in self.devices:
            if "time" in dev.data:
                if len(dev.data["time"]) > max_index:
                    max_index = len(dev.data["time"])

        for i in range(max_index):
            for dev in self.devices:
                for param_val in dev.data.values():
                    try:
                        data_frame[h].append(f"{param_val[i]}")
                        h += 1
                    except:
                        data_frame[h].append(f"---")
                        h += 1
                data_frame[h].append(" ")
                h += 1
            h = 0

        max_index = 0
        for dev in self.devices:
            if len(dev.settings) > max_index:
                max_index = len(dev.settings)

        for k in range(max_index):
            d = 0
            for i in range(len(self.devices)):
                try:
                    data_frame[h].append(f"{self.devices[i].settings[k]}")
                    h += 1
                except:
                    data_frame[h].append(f"---")
                    h += 1
                if i < len(self.devices):
                    for j in range(number_tab[d]):
                        data_frame[h].append(" ")
                        h += 1
                    d += 1
            h = 0

        waves_frames = []
        for dev in self.devices:
            waves_dict = {" ": [QApplication.translate("parse_data","Время") , QApplication.translate("parse_data","Шаг")]}

            for wave in dev.osc_data:
                key = wave.name
                waves_dict[key] = [wave.time, wave.step]
                for val in wave.data:
                    waves_dict[key].append(val)

            if waves_dict != {" ": [QApplication.translate("parse_data","Время") , QApplication.translate("parse_data","Шаг")]}:
                data = waves_dict
                df = pandas.DataFrame(
                    dict([(k, pandas.Series(v)) for k, v in data.items()])
                )
                waves_frames.append(df)#TODO: если строк в данном дата фрейме больше 1000000 то нужно дробить его на несколько

        #========================
        for frame in waves_frames:
            if len(frame) > 1000000:
                raise Exception("число строк больше одного миллиона, сохранение в эксель невозможно.")
        #========================

        df = pandas.DataFrame(data_frame)
        waves_frames.insert(0, df)
        result_df = pandas.concat(waves_frames, axis=1)

        daytime = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

        print(df.columns)

        if os.path.exists(output_file_path):
            mode = "a"
        else:
            mode = "w"
        try:
            with ExcelWriter(
                output_file_path, engine="openpyxl", mode=mode
            ) as excel_writer:
                result_df.to_excel(excel_writer, sheet_name=daytime)
        except PermissionError:
            logger.warning(
                f"Эксель файл не записан {output_file_path=} {self.input_file=} меняем название"
            )
            output_file_path = output_file_path[:-5] + "(0).xlsx"
            for i in range(1, 100):
                output_file_path = output_file_path[:-8] + f"({str(i)}).xlsx"
                if os.path.exists(output_file_path):
                    if i == 99:
                        pass
                    continue
                else:
                    with ExcelWriter(output_file_path, mode="w") as excel_writer:
                        result_df.to_excel(excel_writer, sheet_name=daytime)
                    break

        return output_file_path

    def __save_txt(self, output_file_path):
        """вывод параметров приборов рядом друг с другом"""
        with open(output_file_path, "a") as file:
            daytime = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            file.write(f"\nзапись от {daytime}\n")
            number_tab = []
            k = 0
            for i in range(len(self.devices)):
                text = QApplication.translate("parse_data", "Прибор:{device} канал:{ch}")
                text = text.format(device = self.devices[i].name_device, ch = self.devices[i].ch)
                                              
                file.write(
                    text
                )
                """определяем, сколько знаков табуляции нужно поставить"""
                if i < len(self.devices) - 1:
                    number_tab.append(len(self.devices[i].data) + 1)
                    k += 1
                    for j in range(number_tab[k - 1]):
                        file.write("\t")
            file.write("\n")

            for i in range(len(self.devices)):
                for param_name in self.devices[i].data.keys():
                    file.write(f"{param_name}\t")
                file.write("\t")
            file.write("\n")

            """ищем максимальный индекс по данным из всех приборов"""
            max_index = 0
            for dev in self.devices:
                if len(dev.data["time"]) > max_index:
                    max_index = len(dev.data["time"])

            for i in range(max_index):
                for dev in self.devices:
                    for param_val in dev.data.values():
                        try:
                            file.write(f"{param_val[i]}\t")
                        except:
                            file.write(f"---\t")
                    file.write("\t")
                file.write("\n")

            """ищем максимальный индекс по настройкам из всех приборов"""
            max_index = 0
            for dev in self.devices:
                if len(dev.settings) > max_index:
                    max_index = len(dev.settings)
            for k in range(max_index):
                d = 0
                for i in range(len(self.devices)):
                    try:
                        file.write(f"{self.devices[i].settings[k]}")
                    except:
                        file.write(f"---")

                    if i < len(self.devices) - 1:
                        for j in range(number_tab[d]):
                            file.write("\t")
                        d += 1
                file.write("\n")
        return output_file_path

    def __save_origin(self, output_file_path):
        return output_file_path

    def __get_device(self, devices, name, ch):
        for dev in devices:
            if dev.name_device == name and dev.ch == ch:
                return dev
        return False

    def save_data(self, input_file_path, output_file_path, output_type, is_delete_buf_file):
        self.__parse_data(input_file_path)
        if output_type == type_save_file.txt:
            output_file_path = self.__save_txt(output_file_path)
        elif output_type == type_save_file.excel:
            output_file_path = self.__save_excell(output_file_path)
        elif output_type == type_save_file.origin:
            output_file_path = self.__save_origin(output_file_path)
        if is_delete_buf_file == True:
            os.remove(input_file_path)
        return output_file_path

    def __parse_data(self, input_file_path):
        self.input_file = input_file_path
        is_file_correct = False
        self.devices = []
        self.buf_settings_device = []
        setting_reading = False
        setting_reading_device = False
        parameters_reading = False
        num_wave_osc = 0
        with open(input_file_path) as file:
            lines = file.readlines()
            for line in lines:
                if is_file_correct == False:
                    if (
                        line.find(QApplication.translate("parse_data","Запущена установка")) != -1
                    ):  # нам подсунули нужный файл
                        is_file_correct = True
                        # print("файл определен как файл результатов")
                        continue

                if line.find(QApplication.translate("parse_data","Настройки")) != -1 and line.find("ch-") == -1:
                    setting_reading_device = (
                        True  # здесь начало считывания настроек девайса
                    )
                    dev = line.split()[1]
                    self.buf_settings_device = []
                    continue

                if setting_reading_device:
                    if line.find(QApplication.translate("parse_data","Настройки")) != -1 and line.find("ch-") != -1:
                        # отсюда начинается считывание настрроек для канала, переносим туда настройки девайса и формируем класс записи
                        setting_reading_device = False
                        setting_reading = True

                        ch = line.split()[1]
                        buf = saved_data(dev, ch)
                        buf.settings = copy.deepcopy(self.buf_settings_device)
                        self.buf_settings_device = []
                        self.devices.append(buf)
                        continue
                    else:
                        self.buf_settings_device.append(line.rstrip("\n"))

                if setting_reading:
                    """читаем настройки канала до первой пустой строки или до начала настроек следующего канала"""
                    if line.find(QApplication.translate("parse_data","Настройки")) != -1 and line.find("ch-") != -1:
                        ch = line.split()[1]
                        buf = saved_data(dev, ch)
                        buf.settings = copy.deepcopy(self.buf_settings_device)
                        self.devices.append(buf)
                        self.buf_settings_device = []
                        continue
                    elif line.find("--------------------") != -1:
                        setting_reading = False
                        continue
                    else:
                        self.devices[len(self.devices) - 1].settings.append(
                            line.rstrip("\n")
                        )
                        continue

                if (
                    parameters_reading == False
                    and len(self.devices) > 0
                    and setting_reading == False
                    and setting_reading_device == False
                ):
                    """если выполнено это условие, то найстройки всех приборов записаны и мы начинаем считывать параметры построчно и раскидывать их по приборам и каналам"""
                    parameters_reading = True
                if parameters_reading:
                    buf = line.split()
                    if buf == []:
                        continue
                    dev = self.__get_device(self.devices, buf[1], buf[2])
                    if dev != False:
                        if "time" in dev.data:
                            dev.data["time"].append(buf[0])
                        else:
                            dev.data["time"] = [buf[0]]
                        current_time = buf[0]
                        buf = buf[3 : len(buf)]
                        for param in buf:
                            param = param[2 : len(param) - 2]
                            # получили значение в формате ['name','xxx'] где name - название параметра, xxx - число или статус
                            param = param.split("=")
                            if param[0] == "step":
                                # гарантируется, что при снятии осциллограммы снимается и шаг между точками, так же гарантируется, что в строке результата он стоит до осциллограммы
                                current_step = param[1]
                            elif "wave" in param[0]:
                                data = osc_data()
                                data.name = (
                                    f"{dev.name_device}_{param[0]}_{num_wave_osc}"
                                )
                                num_wave_osc += 1
                                data.time = current_time
                                data.step = current_step
                                wave_osc = param[1].split("|")
                                for val in wave_osc:
                                    data.data.append(val)

                                dev.osc_data.append(data)
                            else:
                                if param[0] in dev.data:
                                    dev.data[param[0]].append(param[1])
                                else:
                                    dev.data[param[0]] = [param[1]]

class saving_data_processing:
        def __init__(self):
            self.saving_data = threading.Thread(target=self.run_saving)
        def set_parameters(self, input_file_path, output_file_path, output_type, is_delete_buf_file):
            self.input_file_path = input_file_path
            self.output_file_path = output_file_path
            self.output_type = output_type
            self.is_delete_buf_file = is_delete_buf_file
        def set_adress_return(self, adress_return):
            self.adress_return = adress_return
        def run_saving(self):
            save = saving_data()
            status = True
            message = ""
            try:
                self.output_file_path = save.save_data(
                    self.input_file_path, self.output_file_path, self.output_type, self.is_delete_buf_file
                )
            except Exception as e:
                message = e
                status = False
                pass
            self.adress_return(status, self.output_file_path, message)
        
def process_and_export(
    input_file_path, output_file_path, output_type, is_delete_buf_file, func_result
):
    save = saving_data_processing()
    save.set_parameters(
        input_file_path, 
        output_file_path, 
        output_type, 
        is_delete_buf_file
    )
    save.set_adress_return(func_result)
    save.saving_data.start()
    
def func_answer_test(status, output_file_path, message):
    if status == True:  
        print(f"Результаты сохранены в {output_file_path}")
    else:
        print("Ошибка сохранения.", message)

if __name__ == "__main__":
    input_file = "rig_test_data.txt"
    is_delete_buf_file = False
    output_file_path = "testData.xlsx"

    process_and_export(input_file, output_file_path, type_save_file.excel, is_delete_buf_file, func_answer_test)
    

    
