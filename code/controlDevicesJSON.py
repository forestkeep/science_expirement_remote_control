# code/controlDevicesJSON.py
"""JSON-приборы: чтение/валидация/индексация через единый файловый слой.

Внешнее API (get_new_JSON_devs / search_devices_json / validate_json_schema)
сохранено для device_selector. Внутреннее чтение папки — через scan_folder
с hint="device_spec", без собственных os.listdir + try/except.

Валидация по шаблону (templates из dev_template) уже произошла внутри
DeviceSpec.parse — повторный validate_json_schema в hot-path не нужен.
validate_json_schema оставлена как публичная утилита (используется в
__main__ и внешними вызовами).

`_spec_to_raw` восстанавливает dict в исходной форме (без `kind`),
потому что `devFile.json_data` — это legacy-представление для
power_supply.load_json и templates, а не семантический payload нового слоя.
"""
from __future__ import annotations

import json
import os

from file_io import scan_folder

from Devices.device_spec import DeviceSpec
from device_creator.dev_template import templates


def _spec_to_raw(spec: DeviceSpec) -> dict:
    """Восстановить исходный dict из DeviceSpec для legacy-API.

    Специально без `kind`: `devFile.json_data` должен быть совместим
    с power_supply.load_json и lookup'ом по `templates[device_type]`.
    """
    payload = {
        "schema_version": int(spec.schema_version),
        "device_type": spec.device_type,
        "device_name": spec.device_name,
        "number_channels": int(spec.number_channels),
        "commands": dict(spec.commands),
    }
    if spec.channels_parameters:
        payload["channels parameters"] = dict(spec.channels_parameters)
    for k, v in (spec.extras or {}).items():
        payload.setdefault(k, v)
    return payload


def validate_json_schema(file_path, templates, data=None):
    """Валидация JSON-объекта по шаблону прибора.

    Работает с dict (не с моделью), так как проверяет внешний контракт
    templates. Используется в __main__ и внешними вызовами; в
    get_new_JSON_devs не вызывается (DeviceSpec.parse уже проверил).
    """
    if data is None:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
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
    """Просканировать папку, вернуть dict[name, devFile].

    Использует scan_folder(..., hint="device_spec"). Объект в
    result.objects уже прошёл проверку в DeviceSpec.parse (device_type
    есть в templates, device_name не пуст), поэтому повторно
    validate_json_schema не вызываем.
    """
    # lazy import: device_selector импортирует этот модуль на старте,
    # поэтому devFile берём в момент вызова — цикла импорта нет.
    from device_selector import devFile

    new_devs: dict = {}
    if not os.path.isdir(directory):
        return new_devs

    result = scan_folder(directory, extensions=["json"], hint="device_spec")

    for path, spec in result.objects:
        raw = _spec_to_raw(spec)
        new_devs[spec.device_name] = devFile(
            path=str(path),
            name=spec.device_name,
            message="JSON валиден",
            status=True,
            json_data=raw,
        )

    for err in result.errors:
        p = err.path
        filename = p.name if p is not None else "?"
        new_devs[filename] = devFile(
            path=str(p) if p is not None else "",
            name=filename,
            message=str(err.reason or err),
            status=False,
            json_data={},
        )

    return new_devs


def search_devices_json(directory) -> dict:
    """Просканировать папку, вернуть dict[device_name, file_path]."""
    result: dict = {}
    if not os.path.isdir(directory):
        return result
    scan = scan_folder(directory, extensions=["json"], hint="device_spec")
    for path, spec in scan.objects:
        result[spec.device_name] = str(path)
    return result


if __name__ == "__main__":
    json_devices = search_devices_json("Devices/JSONDevices")
    for device, file_path in json_devices.items():
        result, message, _ = validate_json_schema(file_path, templates)
        print(device, result, message)