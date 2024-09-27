class connectObject:
    def __init__(self, device, ch, type, value, num, color):
        self.name = f"{device} {ch}"
        self.type_trigger = type
        self.value_trigger = value
        self.number_meas = num
        self.color = color

def create_objects(main_dict):
    objects = []
    
    # Список уникальных цветов
    unique_colors = ["красный", "зеленый", "синий", "желтый", "фиолетовый", "оранжевый"]
    color_map = {}
    color_index = 0

    for device, channels in main_dict.items():
        # Присваиваем цвет, если еще не присвоили
        if device not in color_map:
            if color_index < len(unique_colors):
                color_map[device] = unique_colors[color_index]
                color_index += 1
            else:
                color_map[device] = "серый"  # цвет по умолчанию, если цветов не осталось
        
        color = color_map[device]
        
        for ch, params in channels.items():
            obj = connectObject(
                device=device,
                ch=ch,
                type=params["type_trigger"],
                value=params["Value_trigger"],
                num=params["Num_meas"],
                color=color
            )
            objects.append(obj)
    
    return objects

# Пример использования
main_dict = {
    "device1": {
        "ch_1": {
            "type_trigger": "Таймер",
            "Value_trigger": 30,
            "Num_meas": "num",
        },
    },
    "device2": {
        "ch_1": {
            "type_trigger": "Внешний сигнал",
            "Value_trigger": "device2 ch_1 something",
            "Num_meas": "Пока активны другие приборы",
        },
    },
    "device3": {
        "ch_1": {
            "type_trigger": "Таймер",
            "Value_trigger": 15,
            "Num_meas": 5,
        },
        "ch_2": {
            "type_trigger": "Таймер",
            "Value_trigger": 10,
            "Num_meas": "num",
        },
        "ch_8": {
            "type_trigger": "Таймер",
            "Value_trigger": 10,
            "Num_meas": "num",
        }
    },
    "device4": {
        "ch_1": {
            "type_trigger": "Внешний сигнал",
            "Value_trigger": "device4 ch_1 something",
            "Num_meas": "num",
        },
    },
    "device5": {
        "ch_1": {
            "type_trigger": "Таймер",
            "Value_trigger": 20,
            "Num_meas": "num",
        },
    },
}

objects_list = create_objects(main_dict)

for obj in objects_list:
    print(obj.name, obj.type_trigger, obj.value_trigger, obj.number_meas, obj.color)

'''
main_dict = {
            "device1": {
                "ch_1": {
                    "type_trigger": "type",
                    "Value_trigger": "value",
                    "Num_meas": "num",
                },
            },
            "device3": {
                "ch_1": {
                    "type_trigger": "type",
                    "Value_trigger": "value",
                    "Num_meas": "num",
                },
                "ch_2": {
                    "type_trigger": "type",
                    "Value_trigger": "value",
                    "Num_meas": "num",
                },
                "ch_3": {
                    "type_trigger": "type",
                    "Value_trigger": "value",
                    "Num_meas": "num",
                }
            },
            "device4": {
                "ch_1": {
                    "type_trigger": "type",
                    "Value_trigger": "value",
                    "Num_meas": "num",
                },
            },
        }

"type" Может иметь значения "Таймер" или "Внешний сигнал"
"Num meas" Может иметь в качестве значения число или "Пока активны другие приборы"
"Value trigger" будет числом секунд, если "type" = "Таймер". Или строку такого формата f"{device_name} {ch_name} {something}". device_name - имя устройства, ch_name - имя канала из словаря
'''