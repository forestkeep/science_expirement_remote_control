import enum
from datetime import datetime
import pandas
from pandas.io.excel import ExcelWriter
import os


class saved_data():
    '''класс хранения данных для отдельно взятого канала устройства'''

    def __init__(self, name_device, ch) -> None:
        self.name_device = name_device
        self.ch = ch
        self.settings = []
        self.data = {}


class type_save_file(enum.Enum):
    txt = 1
    excel = 2
    origin = 3


class saving_data():
    def __init__(self) -> None:
        pass

    def __save_excell(self, output_file_path):
        column_number = 0
        max_dev_data_len = 0
        max_dev_set_len = 0
        for dev in self.devices:
            column_number += len(dev.data.keys()) + 1
            if 'time' in dev.data:
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
            data_frame[h].append(
                f"Прибор:{self.devices[i].name_device} канал:{self.devices[i].ch}")
            h += 1

            number_tab.append(len(self.devices[i].data))
            k += 1
            # print("знаков табуляции", number_tab)
            for j in range(number_tab[k-1]):
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
            if 'time' in dev.data:
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
                    # print("знаков табуляции", number_tab)
                    for j in range(number_tab[d]):
                        data_frame[h].append(" ")
                        h += 1
                    d += 1
            h = 0
        # for i in data_frame.values():
     # print(len(i))
     # print(i)
        df = pandas.DataFrame(data_frame)
        # df.to_excel('teams.xlsx')

        daytime = datetime.now().strftime("%Y-%m-%d %H-%M-%S")

        with ExcelWriter(output_file_path,
                         mode="a" if os.path.exists(output_file_path) else "w") as excel_writer:
            df.to_excel(excel_writer, sheet_name=daytime)

    def __save_txt(self, output_file_path):
        '''вывод параметров приборов рядом друг с другом'''
        with open(output_file_path, "a") as file:
            daytime = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            file.write(f"\nзапись от {daytime}\n")
            number_tab = []
            k = 0
            for i in range(len(self.devices)):
                file.write(
                    f"Прибор:{self.devices[i].name_device} канал:{self.devices[i].ch}")
                '''определяем, сколько знаков табуляции нужно поставить'''
                if i < len(self.devices)-1:
                    number_tab.append(len(self.devices[i].data)+1)
                    k += 1
                    # print("знаков табуляции", number_tab)
                    for j in range(number_tab[k-1]):
                        file.write("\t")
            file.write("\n")

            for i in range(len(self.devices)):
                for param_name in self.devices[i].data.keys():
                    file.write(f"{param_name}\t")
                file.write("\t")
            file.write("\n")

            '''ищем максимальный индекс по данным из всех приборов'''
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
            #print(number_tab)

            '''ищем максимальный индекс по настройкам из всех приборов'''
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

                    if i < len(self.devices)-1:
                        # print("знаков табуляции", number_tab)
                        for j in range(number_tab[d]):
                            file.write("\t")
                        d += 1
                file.write("\n")

    def __save_origin(self, output_file_path):
        pass

    def __get_device(self, devices, name, ch):
        for dev in devices:
            if dev.name_device == name and dev.ch == ch:
                return dev
        return False

    def save_data(self, input_file_path, output_file_path, output_type):
        self.__parse_data(input_file_path)
        if output_type == type_save_file.txt:
            self.__save_txt(output_file_path)
        elif output_type == type_save_file.excel:
            self.__save_excell(output_file_path)
        elif output_type == type_save_file.origin:
            self.__save_origin(output_file_path)

    def __parse_data(self, input_file_path):
        is_file_correct = False
        self.devices = []
        setting_reading = False
        parameters_reading = False
        with open(input_file_path) as file:
            lines = file.readlines()
            for line in lines:
                if is_file_correct == False:
                    if line.find("Запущена установка") != -1:  # нам подсунули нужный файл
                        is_file_correct = True
                        #print("файл определен как файл результатов")
                        continue

                if line.find("Настройки") != -1:
                    setting_reading = True
                    dev = line.split()
                    buf = saved_data(dev[1], dev[2])
                    self.devices.append(buf)
                    # print(dev)
                    continue

                if setting_reading:
                    '''читаем настройки устройства до первой пустой строки'''
                    if line.find("--------------------") != -1:
                        # print("разделитель")
                        setting_reading = False
                        continue
                    else:
                        self.devices[len(self.devices) -
                                     1].settings.append(line.rstrip('\n'))
                        continue

                if parameters_reading == False and len(self.devices) > 0 and setting_reading == False:
                    '''если выполнено это условие, то найстройки всех приборов записаны и мы начинаем считывать параметры построчно и раскидывать их по приборам и каналам'''
                    parameters_reading = True
                    # print("начинаем считывать параметры")
                if parameters_reading:
                    buf = line.split()
                    # получаем класс, куда нужно записывать данные
                    dev = self.__get_device(self.devices, buf[1], buf[2])
                    if dev != False:
                        if "time" in dev.data:
                            dev.data["time"].append(buf[0])
                        else:
                            dev.data["time"] = [buf[0]]
                        buf = buf[3:len(buf)]
                        for param in buf:
                            param = param[2:len(param)-2]
                            # получили значение в формате ['name','xxx'] где name - название параметра, xxx - число или статус
                            param = param.split("=")
                            if param[0] in dev.data:
                                dev.data[param[0]].append(param[1])
                            else:
                                dev.data[param[0]] = [param[1]]

        # for dev in self.devices:
        #    print(dev, dev.name_device, dev.ch, dev.settings)
def process_and_export(input_file_path, output_file_path, output_type):
    save = saving_data()
    save.save_data(input_file_path, output_file_path, output_type)

if __name__ == "__main__":
    save = saving_data()
    input_file = "DP832A_4_2024-04-21 18-32-20.txt"
    save.save_data(input_file, "output_data.xlsx", type_save_file.excel)
