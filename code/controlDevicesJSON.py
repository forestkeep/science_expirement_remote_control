import json
import os

from device_creator.dev_creator import templates

def validate_json_schema(file_path, templates):
    # Чтение JSON файла
    with open(file_path, 'r') as file:
        data = json.load(file)

    device_type = data.get("device_type")
    if device_type not in templates:
        return False, "Неверный device_type"

    template = templates[device_type]

    # Сравнение полей
    for key in template.keys():
        if key not in data:
            return False, f"Отсутствует поле: {key}"

        # Проверка вложенных словарей
        if isinstance(template[key], dict):
            for sub_key in template[key].keys():
                if sub_key not in data[key]:
                    return False, f"Отсутствует подполе: {sub_key} в поле {key}"

    return True, "JSON валиден"

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
