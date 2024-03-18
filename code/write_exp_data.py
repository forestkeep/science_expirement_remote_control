import pandas as pd
from datetime import datetime
import re
from enum import Enum

class type_save_file(Enum):
    txt = 1
    excel = 2
    origin = 3

def extract_settings(file_path):
    settings = {}
    current_setting = None
    print(file_path)
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith("Настройки"):
                current_setting = line.split(":")[1].strip()
                settings[current_setting] = {}
            elif "-" in line:
                key, value = re.split(r'\s*-\s*', line, maxsplit=1)
                settings[current_setting][key.strip()] = value.strip()

    # Удаляем последнюю строку, если она существует



    return settings
def process_and_export(input_file_path, output_file_path, output_type):
    # Определяем функцию обработки строк
    def process_input_strings(input_strings):
        instruments_data = {}

        # Обработка строк
        for input_string in input_strings:
            elements = input_string.split()

            # Проверка, что в строке достаточно элементов
            if len(elements) >= 4:
                # Время будет последним элементом в строке
                time_str = elements[0].split()[-1]
                instrument_name = elements[1]

                # Создаем словарь для текущего прибора, если его еще нет
                if instrument_name not in instruments_data:
                    instruments_data[instrument_name] = {'Time': []}

                # Добавление времени в список времени для текущего прибора
                instruments_data[instrument_name]['Time'].append(time_str)

                measurements = [element.strip("[]") for element in elements[2:]]

                # Обработка измерений для текущего прибора
                for measurement in measurements:
                    # Проверка наличия разделителя '=' в строке измерения
                    if '=' in measurement:
                        name, value = map(str.strip, measurement.split('='))
                        value = value.rstrip("'")  # Убираем возможные символы "'" в конце значения

                        # Если это phase, disp1 или disp2
                        if name in {'phase', 'disp1', 'disp2'}:
                            # Создаем столбец phase, если его еще нет
                            if 'phase' not in instruments_data[instrument_name]:
                                instruments_data[instrument_name]['phase'] = []

                            # Добавляем значение в соответствующий столбец
                            instruments_data[instrument_name][name].append(float(value))
                        else:
                            # Если измерение уже есть в словаре прибора, добавляем новое значение
                            if name in instruments_data[instrument_name]:
                                instruments_data[instrument_name][name].append(float(value))
                            else:
                                # Если измерения нет, создаем новую запись в словаре прибора
                                instruments_data[instrument_name][name] = [float(value)]
                    else:
                        print("Ошибка: Неверный формат измерения:", measurement)
            else:
                print("Ошибка: Недостаточно элементов в строке:", input_string)

        return instruments_data

        # Определяем функцию обработки настроек

    settings = extract_settings(input_file_path)

    #del settings[""]["16"]


    # Определяем функцию экспорта в Excel
    def export_to_excel(instruments_data, output_file_path):
        # Создание DataFrame из словаря
        df_measurements = pd.DataFrame.from_dict(
            {(instrument_name, key): measurements_list for instrument_name, measurements_dict in
             instruments_data.items() for key, measurements_list in measurements_dict.items()}, orient='index')
        df_measurements.index = pd.MultiIndex.from_tuples(df_measurements.index)
        df_measurements.index.names = ['Instrument', 'Measurement']

        # Создание DataFrame из словаря настроек
        df_settings = pd.DataFrame(settings)

        # Экспорт DataFrame в Excel
        with pd.ExcelWriter(output_file_path) as writer:
            df_measurements.to_excel(writer, sheet_name='Measurements')
            df_settings.to_excel(writer, sheet_name='Settings')

    # Определяем функцию экспорта в текстовый файл
    def export_to_text(instruments_data, output_file_path):
        with open(output_file_path, 'w') as file:
            for instrument_name, measurements_dict in instruments_data.items():
                file.write(f"{instrument_name}\n")
                for key, measurements_list in measurements_dict.items():
                    for value in measurements_list:
                        file.write(f"{key}: {value}\n")
                file.write('\n')

    # Чтение строк из текстового файла
    with open(input_file_path) as file:
        input_strings = file.readlines()

    # Обработка исходных строк
    result = process_input_strings(input_strings)

    # Экспорт в зависимости от выбранного типа файла
    if output_type == type_save_file.txt:
        export_to_text(result, output_file_path)
    elif output_type == type_save_file.excel:
        export_to_excel(result, output_file_path)
    elif output_type == type_save_file.origin:
        # Дополнительные действия для сохранения в оригинальном формате
        pass
    else:
        print("Ошибка: Неверно указан тип файла")



if __name__ == "__main__":
    # Пример использования:
    process_and_export(fr"C:\Users\zahidovds\Desktop\virtual_for_uswindsens\code\code\code\Maisheng.txt", fr"C:\Users\zahidovds\Desktop\virtual_for_uswindsens\code\code\code\Maisheng.xlsx", type_save_file.excel)
    #print(extract_settings(fr"C:\Users\asus\Desktop\remake\Maisheng1_Lock in2_2024-03-05 16-13-03.txt"))