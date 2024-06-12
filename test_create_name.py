import random

def create_name_param(main_dict):
    output_list = []

    for device, channels in main_dict.items():
        for channel, values in channels.items():
            #print(values.items())
            for key, value in values.items():
                #print(key)
                if key != 'time':
                    output_list.append(f'{key}({device} {channel})')
    return output_list



def get_param():
    random_X = ["R", "L", "C", "PHAS", "V", "I"]
    return random.choice(random_X)

def get_values():
    return [random.randint(1, 100) for _ in range(1, 11)]

time_dict = {i for i in range(1, 11)}

main_dict = {
                'device1': {
                    'ch-1': {'time': time_dict, get_param(): get_values()}
                },
                'device2': {
                    'ch-1': {'time': time_dict, get_param(): get_values(), get_param(): get_values(), get_param(): get_values()},
                    'ch-2': {'time': time_dict, get_param(): get_values()},
                    'ch-3': {'time': time_dict, get_param(): get_values()}
                },
                'device3': {
                    'ch-1': {'time': time_dict, get_param(): get_values()},
                    'ch-2': {'time': time_dict, get_param(): get_values(), get_param(): get_values(), get_param(): get_values()}
                }
        }

def decode_name_patameters(string_y):
    buf_y = string_y.split("(")
    parameter_y = buf_y[0]
    device_y = buf_y[1].split(" ")[0]
    ch_y = buf_y[1].split(" ")[1][:-1]

    return main_dict[device_y][ch_y]['time'], main_dict[device_y][ch_y][parameter_y]


# Вызов функции и вывод результата
result_list = create_name_param(main_dict)
for item in result_list:
    print(item, decode_name_patameters(item))