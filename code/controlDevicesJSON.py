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

def validate_json_schema(file_path, templates, data=None):
    if data is None:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except FileNotFoundError:
            return False, f"Файл {file_path} не был найден", None
        except (OSError, json.JSONDecodeError) as exc:
            return False, f"Ошибка чтения JSON: {exc}", None

    if not isinstance(data, dict):
        return False, "JSON должен быть объектом", data

    device_type = data.get("device_type")
    if device_type not in templates:
        return False, "Неверный device_type", data

    template = templates[device_type]

    for key in template.keys():
        if key not in data:
            return False, f"Отсутствует поле: {key}", data

        if isinstance(template[key], dict):
            if not isinstance(data.get(key), dict):
                return False, f"Поле {key} должно быть объектом", data
            for sub_key in template[key].keys():
                if sub_key not in data[key]:
                    return False, f"Отсутствует подполе: {sub_key} в поле {key}", data

    return True, "JSON валиден", data

def get_new_JSON_devs(directory) -> dict:
    new_devs = {}

    if not os.path.isdir(directory):
        return new_devs

    for filename in os.listdir(directory):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(directory, filename)
        data = None
        message = ""
        status = False

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            message = f"Ошибка чтения JSON: {exc}"
            new_devs[filename] = devFile(
                path=file_path,
                name=filename,
                message=message,
                status=False,
                json_data={},
            )
            continue

        if not isinstance(data, dict):
            new_devs[filename] = devFile(
                path=file_path,
                name=filename,
                message="JSON должен быть объектом",
                status=False,
                json_data={},
            )
            continue

        device_name = data.get('device_name')
        if not device_name:
            new_devs[filename] = devFile(
                path=file_path,
                name=filename,
                message="Отсутствует device_name",
                status=False,
                json_data=data,
            )
            continue

        status, message, _ = validate_json_schema(file_path, templates, data)
        new_devs[device_name] = devFile(
            path=file_path,
            name=device_name,
            message=message,
            status=status,
            json_data=data,
        )

    return new_devs


def search_devices_json(directory) -> dict:
    result = {}

    if not os.path.isdir(directory):
        return result

    for filename in os.listdir(directory):
        if not filename.endswith('.json'):
            continue

        file_path = os.path.join(directory, filename)

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(data, dict):
            device_name = data.get('device_name')
            if device_name:
                result[device_name] = file_path

    return result

if __name__ == "__main__":
    json_devices = search_devices_json("Devices/JSONDevices")
    for device, file_path in json_devices.items():
        result, message = validate_json_schema(file_path, templates)
        print(device,result, message)
