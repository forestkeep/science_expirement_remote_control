import json
import os
from dataclasses import dataclass
from device_creator.dev_creator import templates

@dataclass
class devFile:
    path: str
    name: str
    message: str
    status: bool
    json_data: dict

def validate_json_schema(file_path, templates):
    with open(file_path, 'r') as file:
        data = json.load(file)

    device_type = data.get("device_type")
    if device_type not in templates:
        return False, "Неверный device_type", data

    template = templates[device_type]

    # Сравнение полей
    for key in template.keys():
        if key not in data:
            return False, f"Отсутствует поле: {key}", data

        if isinstance(template[key], dict):
            for sub_key in template[key].keys():
                if sub_key not in data[key]:
                    return False, f"Отсутствует подполе: {sub_key} в поле {key}", data

    return (True, "JSON валиден", data)


def get_new_JSON_devs(directory) -> dict:
        new_devs = {}
        json_devices = search_devices_json(directory)
        for device, file_path in json_devices.items():
            result, message, data = validate_json_schema(file_path, templates)
            new_devs[device] = devFile(path=file_path, name=device, message=message, status=result, json_data=data)
        return new_devs

def search_devices_json(directory) -> dict:
    """
    Scans the specified directory for .json files.
    
    For each found .json file, it searches for the "device_name" field 
    and stores its value in a dictionary where the key is the value 
    from the "device_name" field, and the value is the path to that file.
    
    Parameters:
    directory (str): The path to the directory to be scanned.

    Returns:
    dict: A dictionary with device names and corresponding file paths.
    """
    result = {}
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)
                device_name = data.get('device_name')
                if device_name:
                    result[device_name] = file_path
    return result

if __name__ == "__main__":
    json_devices = search_devices_json("Devices/JSONDevices")
    for device, file_path in json_devices.items():
        result, message = validate_json_schema(file_path, templates)
        print(device,result, message)
