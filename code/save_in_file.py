def process_input_strings(input_strings):
    instruments_data = {}

    # Обработка строк
    for input_string in input_strings:
        elements = input_string.split()
        instrument_name = elements[1]
        measurements = [element.strip("[]") for element in elements[2:]]

        # Если прибора нет в словаре, создаем его
        if instrument_name not in instruments_data:
            instruments_data[instrument_name] = {}

        # Обработка измерений для текущего прибора
        for measurement in measurements:
            name, value = map(str.strip, measurement.split('='))
            value = value.rstrip("'")  # Убираем возможные символы "'" в конце значения

            # Если измерение уже есть в словаре, добавляем новое значение
            if name in instruments_data[instrument_name]:
                instruments_data[instrument_name][name].append(float(value))
            else:
                # Если измерения нет, создаем новую запись в словаре
                instruments_data[instrument_name][name] = [float(value)]

    return instruments_data

def print_instruments_data(instruments_data):
    for instrument_name, measurements_dict in instruments_data.items():
        # Замена знаков ',' на пробелы и удаление знаков "'"
        columns = [column.replace(',', ' ').replace("'", "") for column in measurements_dict.keys()]
        # Добавление столбца с названием прибора
        columns.insert(0, 'Instrument')
        print(' '.join(columns))

        # Вывод соответствующих значений
        for i in range(len(list(measurements_dict.values())[0])):
            values = [instrument_name] + [str(measurements_dict[column][i]).center(len(column)) for column in measurements_dict.keys()]
            print(' '.join(values))

if __name__ == "__main__":
    # Чтение строк из текстового файла
    with open(r"C:\Users\asus\Desktop\TEST\testirovanie.txt", "r") as file:
        input_strings = file.readlines()

    result = process_input_strings(input_strings)

    # Вывод результата
    print_instruments_data(result)