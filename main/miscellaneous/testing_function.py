import time

def parse_parameters(arr):
    device, channel = arr[0].split()
    parameters = []
    
    for entry in arr[1:]:
        name, value = entry[0].split('=')
        value = float(value)
        parameters.append([name, value])
    
    return device, channel, parameters


array = ['DP832A_1 ch-1', ['voltage_set=10.0'], ['voltage_rel=21.940766351704543'], ['current_set=3.0'], ['current_rel=1.0706034171426237'], ['rel=458']]
device, channel, parameters = parse_parameters(array)

print("Device:", device)
print("Channel:", channel)
print("Parameters:")
for parameter in parameters:
    print(parameter[0], parameter[1])

print(888888888888888888888888888888888888888888888888888888888)

def update_parameters(data, entry):
    start_time = 19
    device, channel = entry[0].split()
    parameter_pairs = entry[1:]
    
    if device not in data:
        data[device] = {}
    if channel not in data[device]:
        data[device][channel] = {}
    
    for parameter_pair in parameter_pairs:
        name, value = parameter_pair[0].split('=')
        value = float(value)
        
        if name not in data[device][channel]:
            data[device][channel][name] = []
        data[device][channel][name].append(value)

    data[device][channel]['time'] = time.time() - start_time

# Пример использования функции
data_dict = {}

array = ['DP832A_1 ch-1', ['voltage_set=10.0'], ['voltage_rel=21.940766351704543'], ['current_set=3.0'], ['current_rel=1.0706034171426237'], ['rel=458']]

update_parameters(data_dict, array)
array = ['DP832A_8 ch-1', ['voltage_set=10.0'], ['voltage_rel=21.940766351704543'], ['current_set=3.0'], ['current_rel=1.0706034171426237'], ['rel=458']]
update_parameters(data_dict, array)
array = ['RRRRRRR_8 ch-1', ['set=10.0'], ['YT=21.940766351704543'], ['current_set=3.0'], ['current_rel=1.0706034171426237'], ['rel=458']]
update_parameters(data_dict, array)

print(data_dict)