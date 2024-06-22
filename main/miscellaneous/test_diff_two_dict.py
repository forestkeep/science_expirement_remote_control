class different:
    def __init__(self) -> None:
        self.previous_dict = {}


    def find_changes(self, current_dict):
            changes = []

            for device, device_data in current_dict.items():
                if device not in self.previous_dict:
                    changes.append(f"Добавлено новое устройство '{device}'")
                else:
                    for channel, channel_data in device_data.items():
                        if channel not in self.previous_dict[device]:
                            changes.append(f"Добавлен канал '{channel}' в устройстве '{device}'")
                        else:
                            prev_channel_data = self.previous_dict[device][channel]
                            for key, value in channel_data.items():
                                if key not in prev_channel_data:
                                    changes.append(f"Добавлен ключ '{key}' в канал '{channel}' у устройства '{device}'")
                                elif len(value) != len(prev_channel_data[key]):
                                    changes.append(f"Изменены данные в ключе '{key}' в канале '{channel}' устройства '{device}'")

            if not changes:
                changes.append("Нет обновлений в данных")

            self.previous_dict = current_dict
            return changes

prev_dict = {
    'device1': {'ch_1': {'time': [], "name1": [], "name2": []}}
}

dict1 = {
    'device1': {'ch_1': {'time': [1, 2, 3], "name1": ["A"], "name2": ["X", "Y"]},
                'ch_2': {'time': [1, 2], "name1": ["B"], "name2": ["Z"]},
                'ch_3': {'time': [1], "name1": [], "name2": ["W"]}
                }
}

dict2 = {
    'device1': {'ch_1': {'time': [1, 2, 3], "name1": ["A"], "name2": ["X", "Y"]},
                'ch_2': {'time': [1, 2], "name1": ["B"], "name2": ["Z"]},
                'ch_3': {'time': [1], "name1": [], "name2": ["W"]}
                },
    'device2': {'ch_1': {'time': [1, 2, 3], "name1": ["A"], "name2": ["X", "Y"]},
                'ch_2': {'time': [1, 2], "name1": ["B"], "name2": ["Z"]},
                'ch_3': {'time': [1], "name1": [], "name2": ["W"]}
                }
}

dict3 = {
    'device1': {'ch_1': {'time': [1, 2, 3], "name1": ["A"], "name2": ["X", "Y"]},
                'ch_2': {'time': [1, 2], "name1": ["B"], "name2": ["Z"]},
                'ch_3': {'time': [1], "name1": [], "name2": ["W"]}
                },
    'device2': {'ch_1': {'time': [1, 2, 3], "name1": ["A"], "name2": ["X", "Y"]},
                'ch_2': {'time': [1, 2, 7], "name1": ["B"], "name2": ["Z"]},
                'ch_3': {'time': [1], "name1": [], "name2": ["W"]}
                }
}

arr = different()

result = arr.find_changes(prev_dict)
for change in result:
    print(change)

print("###########################################")

result = arr.find_changes(dict1)
for change in result:
    print(change)


print("###########################################")

result = arr.find_changes(dict2)
for change in result:
    print(change)