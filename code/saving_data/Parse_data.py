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
from datetime import datetime

import pandas
import openpyxl
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from send2trash import send2trash
from PyQt5 import QtWidgets
import multiprocessing
import time
from PyQt5.QtCore import QTimer

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

class savingDataClass:
    def __init__(self) -> None:
        pass

    def __save_excell(self, output_file_path, result_name):

        message = ""
        status = True

        excel_writer = None

        if os.path.exists(output_file_path):
            mode = "a"
            try:
                excel_writer = pandas.ExcelWriter(
                    output_file_path, 
                    engine='openpyxl', 
                    mode=mode,
                    if_sheet_exists='new'
                )
            except PermissionError as e:
                output_file_path = self.get_free_file_name(output_file_path)

            except Exception as e:
                message = f"{type(e).__name__} - {e}"
                return output_file_path, message, False

        if excel_writer is None:
            mode = "w"
            excel_writer = pandas.ExcelWriter(
                output_file_path, 
                engine='openpyxl', 
                mode=mode
            )

        result = self.resul_df

        try:
            result.to_excel(excel_writer, sheet_name=result_name, index=False)

        except Exception as e:
            message += f"{type(e).__name__} - {e}"
            return output_file_path, message, False

        finally:
            excel_writer.close()

        return output_file_path, message, status
    
    def get_free_file_name(self, output_file_path):
        output_file_path = output_file_path[:-5] + "(0).xlsx"
        for i in range(1, 100):
            output_file_path = output_file_path[:-8] + f"({i}).xlsx"
            if os.path.exists(output_file_path):
                if i == 99:
                    pass
                continue
            else:
                return output_file_path
            
    def __save_txt(self, output_file_path, result_name):
        status = False

        try:
            with open(output_file_path, "a") as file:
                file.write(f"\n#############################################\n")
                file.write(f"{result_name}\n")
                file.write(f"#############################################\n")
                file.write(self.resul_df.to_string(index=False))
                status = True
        except Exception as e:
            message = f"{type(e).__name__} - {e}"

        return output_file_path, "", status

    def __save_origin(self, output_file_path, result_name):
        return output_file_path, "", False

    def __get_device(self, devices, name, ch):
        for dev in devices:
            if dev.name_device == name and dev.ch == ch:
                return dev
        return False

    def save_data(self, input_file_path, output_file_path, output_type, result_name, result_description, meta_data):

        status = True
        try:
            self.__parse_data(input_file_path)
        except MemoryError:
            logger.warning(f"Недостаточно памяти при парсинге буферного файла")
            message = QApplication.translate("parse_data","Не хватает оперативной памяти для обработки буферного файла. " \
            "Не волнуйтесь, данные измерений не пострадали. Попробуйте перезагрузить приложение и сохранить результаты из буферного файла.")
            status = False

        if status:
            self.resul_df = self.build_data_frame(result_description, meta_data)

            if not result_name:
                result_name = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

            if output_type == type_save_file.txt:
                output_file_path, message, status = self.__save_txt(output_file_path, result_name)
            elif output_type == type_save_file.excel:
                output_file_path, message, status = self.__save_excell(output_file_path, result_name)
            elif output_type == type_save_file.origin:
                output_file_path, message, status = self.__save_origin(output_file_path, result_name)
            else:
                logger.warning(f"тип сохранения не определен {output_type}")
                message = QApplication.translate("parse_data","Тип сохранения не определен")
                status = False

        return output_file_path, message, status

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
                        line.find("installation start") != -1
                    ):  # нам подсунули нужный файл
                        is_file_correct = True
                        continue

                if line.find("Settings ") != -1 and line.find("ch-") == -1:
                    setting_reading_device = True  # здесь начало считывания настроек девайса
                    dev = line.split()[1]
                    self.buf_settings_device = []
                    continue

                if setting_reading_device:
                    if line.find("Settings ") != -1 and line.find("ch-") != -1:
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
                    if line.find("Settings ") != -1 and line.find("ch-") != -1:
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

                        time_data_len = len(dev.data["time"])

                        current_time = buf[0]
                        buf = buf[3 : len(buf)]
                        for param in buf:
                            param = param[2 : len(param) - 2]
                            # получили значение в формате ['name','xxx'] где name - название параметра, xxx - число или статус
                            param = param.split("=")
                            if len(param) >= 2:
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
                                        arr = dev.data[param[0]]
                                        arr.extend(['fail'] * (time_data_len - len(arr) - 1))
                                        arr.append(param[1])
                                    else:
                                        dev.data[param[0]] = ['fail'] * (time_data_len - 1) + [param[1]]
                                    
    def build_data_frame(self, result_description = None, meta_data = None) -> pandas.DataFrame:
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
            data_frame[str(h)] = []
            if result_description:
                if h == 0:
                    data_frame[str(h)].append(result_description)
                else:
                    data_frame[str(h)].append(" ")

            if meta_data:
                if h == 0:
                    data_frame[str(h)].append(meta_data)
                else:
                    data_frame[str(h)].append(" ")

        h = 0
        number_tab = []
        k = 0
        for i in range(len(self.devices)):
            text = QApplication.translate("parse_data", "Прибор:{device} канал:{ch}")
            text = text.format(device=self.devices[i].name_device, ch=self.devices[i].ch)
            data_frame[str(h)].append(
                text
            )
            h += 1

            number_tab.append(len(self.devices[i].data))
            k += 1
            for j in range(number_tab[k - 1]):
                data_frame[str(h)].append(" ")
                h += 1

        h = 0
        for i in range(len(self.devices)):
            for param_name in self.devices[i].data.keys():
                data_frame[str(h)].append(f"{param_name}")
                h += 1
            data_frame[str(h)].append(" ")
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
                        data_frame[str(h)].append(f"{param_val[i]}")
                        h += 1
                    except:
                        data_frame[str(h)].append(f"---")
                        h += 1
                data_frame[str(h)].append(" ")
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
                    data_frame[str(h)].append(f"{self.devices[i].settings[k]}")
                    h += 1
                except:
                    data_frame[str(h)].append(f"---")
                    h += 1
                if i < len(self.devices):
                    for j in range(number_tab[d]):
                        data_frame[str(h)].append(" ")
                        h += 1
                    d += 1
            h = 0

        waves_frames = []
        max_rows = 950000-2
        for dev in self.devices:
            waves_dict = {" ": [QApplication.translate("parse_data", "Время"), QApplication.translate("parse_data", "Шаг")]}

            for wave in dev.osc_data:
                num_splits = (len(wave.data) // max_rows) + 1
                for i in range(num_splits):
                    key = wave.name + f"({i})"
                    start_idx = i*max_rows
                    end_idx = min((i+1)*max_rows, len(wave.data) )
                    waves_dict[key] = [wave.time, wave.step]
                    for j in range(start_idx, end_idx, 1):
                        waves_dict[key].append(wave.data[j])

            if waves_dict != {" ": [QApplication.translate("parse_data","Время") , QApplication.translate("parse_data","Шаг")]}:
                data = waves_dict
                df = pandas.DataFrame(dict([(k, pandas.Series(v)) for k, v in data.items()]))

                waves_frames.append(df)

        df = pandas.DataFrame(data_frame)

        waves_frames.insert(0, df)

        result_df = pandas.concat(waves_frames, axis=1)


        return result_df

def run_saving_worker(queue, input_file_path, output_file_path, output_type, 
                      is_delete_buf_file, result_name, result_description, meta_data):
    try:
        save_class = savingDataClass()
        status = True
        message = ""

        output_file_path, message, status = save_class.save_data(
                input_file_path, output_file_path, output_type, result_name, result_description, meta_data
            )
        if status:
            if is_delete_buf_file:
                try:
                    send2trash(input_file_path)
                    queue.put({
                        'status': status,
                        'output_file_path': output_file_path,
                        'message': message,
                        'deleted_buf_file': input_file_path
                    })
                except Exception as e:
                    message += f"\nФайл сохранен, но буферный файл не удалось отправить в корзину - {e}"
                    queue.put({
                        'status': status,
                        'output_file_path': output_file_path,
                        'message': message
                    })
            else:
                queue.put({
                    'status': status,
                    'output_file_path': output_file_path,
                    'message': message
                })
        else:
            queue.put({
                'status': status,
                'output_file_path': output_file_path,
                'message': message
            })
    except Exception as e:
        print(e)
        queue.put({
            'status': False,
            'output_file_path': None,
            'message': f"Критическая ошибка: {str(e)}"
        })

class saving_data_processing:
    def __init__(self, info_callback=None):
        self.info_callback = info_callback
        self.queue = multiprocessing.Queue()
        self.saving_process = None
        self.process_start_time = 0
        self.next_report_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_queue_and_status)

        self.input_file_path = None
        self.output_file_path = None
        self.output_type = None
        self.is_delete_buf_file = None
        self.result_name = "Result"
        self.result_description = ""
        self.meta_data = None
        self.adress_return = None

    def terminate(self):
        if self.saving_process and self.saving_process.is_alive():
            self.saving_process.terminate()
            self.saving_process.join()

    def set_parameters(self, input_file_path, output_file_path, output_type, 
                       is_delete_buf_file, result_name, result_description, meta_data):
        self.input_file_path = input_file_path
        self.output_file_path = output_file_path
        self.output_type = output_type
        self.is_delete_buf_file = is_delete_buf_file
        self.meta_data = meta_data
        
        if result_name:
            self.result_name = result_name
        if result_description:
            self.result_description = result_description

    def set_adress_return(self, adress_return):
        self.adress_return = adress_return

    def start_saving(self):
        if not all([self.input_file_path, self.output_file_path, self.adress_return]):
            raise ValueError("Не установлены обязательные параметры или callback")
        
        self.saving_process = multiprocessing.Process(
            target=run_saving_worker,
            args=(
                self.queue,
                self.input_file_path,
                self.output_file_path,
                self.output_type,
                self.is_delete_buf_file,
                self.result_name,
                self.result_description,
                self.meta_data
            )
        )
        self.process_start_time = time.perf_counter()
        self.next_report_time = self.process_start_time + 60*3
        self.timer.start(5000)
        self.saving_process.start()
        if self.info_callback is not None:
                self.info_callback(f"Сохраняем результаты {self.input_file_path} в {self.output_file_path}")

    def _check_queue_and_status(self):
        while not self.queue.empty():
            try:
                result = self.queue.get_nowait()
                self._handle_result(result)
                return
            except:
                break

        current_time = time.perf_counter()

        if current_time >= self.next_report_time:
            elapsed = int(current_time - self.process_start_time)

            if self.info_callback is not None:
                self.info_callback(f"Сохранение результатов в {self.output_file_path} идет дольше обычного: {elapsed // 60} мин {elapsed % 60} сек. Пожалуйста, подождите...")
                
            self.next_report_time = current_time + 60*30
        
        if not self.saving_process.is_alive():
            self.timer.stop()
            self.saving_process.join()

    def _handle_result(self, result):
        self.timer.stop()
        if self.saving_process.is_alive():
            self.saving_process.terminate()
        
        if result['status']:
            if 'deleted_buf_file' in result:
                self.adress_return(
                    status=result['status'],
                    output_file_path=result['output_file_path'],
                    message=result['message'],
                    deleted_buf_file=result['deleted_buf_file']
                )
            else:
                self.adress_return(
                    status=result['status'],
                    output_file_path=result['output_file_path'],
                    message=result['message']
                )
        else:
            self.adress_return(
                status=result['status'],
                output_file_path=result['output_file_path'],
                message=result['message']
            )

class savingController():
    def __init__(self):
        self.saving_processes = []
        self.info_callback = None

    def set_info_callback(self, func):
        self.info_callback = func

    def terminate_saving_processes(self):
        for process in self.saving_processes:
            process.saving_process.terminate()
        self.saving_processes = []

    def process_and_export(self,input_file_path, output_file_path, output_type, meas_session_data,  is_delete_buf_file, func_result):
        result_name = meas_session_data.session_name
        result_descriptions = meas_session_data.session_description
        meta_data = meas_session_data.get_meta_data()
        save = saving_data_processing(self.info_callback)
        save.set_parameters(
            input_file_path, 
            output_file_path, 
            output_type, 
            is_delete_buf_file,
            result_name,
            result_descriptions,
            meta_data
        )
        save.set_adress_return(func_result)
        save.start_saving()
        self.saving_processes.append(save)

start = time.perf_counter()

def info_callback(message):
    print(message)
    
def func_answer_test(status, output_file_path, message, deleted_buf_file = False):
    global start

    if status == True:  
        print(f"Результаты сохранены в {output_file_path}")
    else:
        print("Ошибка сохранения.", message)

    print(f"Время выполнения {time.perf_counter() - start}")

class mock_measSessionData:
    def __init__(self):
        self.session_name = ''
        self.session_description = ''
        self.session_start_time = ''
        self.session_end_time = ''
        self.session_duration = ''
        self.measurement_parameters = {}

    def get_meta_data(self) -> str:
        return f"start_time={self.session_start_time}\nend_time={self.session_end_time}\nduration={self.session_duration}"

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    input_file = "pig_in_a_poke_1_2025-06-03 15-57-25.txt"
    is_delete_buf_file = False
    output_file_path = "testData.xlsx"
    meas_session_data = mock_measSessionData()
    saving_ctrl = savingController()
    saving_ctrl.set_info_callback(info_callback)

    saving_ctrl.process_and_export(input_file, output_file_path, type_save_file.excel,meas_session_data,is_delete_buf_file, func_answer_test)
    sys.exit(app.exec_())
    

    
