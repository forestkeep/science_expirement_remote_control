from __future__ import annotations

import json
import logging
from typing import Any

import h5py
import numpy as np

from .codec import get_codec
from .schema import Attr, Schema

logger = logging.getLogger(__name__)

_MISSING = object()


def _decode_unknown(raw: Any) -> Any:
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw
    if isinstance(raw, np.ndarray):
        return raw.tolist() if raw.ndim else raw.item()
    if isinstance(raw, np.generic):
        return raw.item()
    return raw


def _encode_unknown(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool, bytes)):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)


def _read_value(group: h5py.Group, attr: Attr) -> Any:
    key = attr.hdf5_key()

    if attr.nested_schema is not None:
        if key not in group:
            return attr.default
        values, extras = read_attrs(group[key], attr.nested_schema)
        try:
            obj = attr.nested_schema.target(**values)
        except TypeError as exc:
            logger.warning("read_attrs: cannot build %s: %s",
                           attr.nested_schema.target.__name__, exc)
            return attr.default
        if hasattr(obj, "extras"):
            obj.extras = extras
        return obj

    if attr.mapping_schema is not None:
        if key not in group:
            return attr.default
        source = group[key]
        result = {}
        for name in source:
            item = source[name]
            if not isinstance(item, h5py.Group):
                continue
            values, extras = read_attrs(item, attr.mapping_schema)
            try:
                obj = attr.mapping_schema.target(**values)
            except TypeError as exc:
                logger.warning("read_attrs: cannot build mapping item %s: %s",
                               name, exc)
                continue
            if hasattr(obj, "extras"):
                obj.extras = extras
            result[name] = obj
        return result

    if attr.is_list and attr.type == "ndarray":
        if key in group and isinstance(group[key], h5py.Group):
            item_group = group[key]
            count = int(item_group.attrs.get("count", 0))
            items = []
            for index in range(count):
                item_key = f"item_{index}"
                if item_key in item_group:
                    items.append(np.asarray(item_group[item_key][:]))
            return items

        legacy = []
        index = 0
        while f"{key}_{index}" in group:
            legacy.append(np.asarray(group[f"{key}_{index}"][:]))
            index += 1
        if legacy:
            return legacy

        if key in group:
            return [np.asarray(group[key][:])]

        return attr.default

    if attr.is_dataset:
        if key not in group:
            return attr.default
        try:
            return get_codec(attr.type).decode(group[key][:])
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("read_attrs: %s dataset: %s", attr.name, exc)
            return attr.default

    if key not in group.attrs:
        return attr.default
    raw = group.attrs[key]
    try:
        return get_codec(attr.type).decode(raw)
    except (ValueError, TypeError) as exc:
        logger.warning("read_attrs: %s invalid value %r: %s",
                       attr.name, raw, exc)
        return attr.default


def read_attrs(group: h5py.Group, schema: Schema) -> tuple[dict, dict]:
    values: dict = {}
    extras: dict = {}

    for attr in schema.attrs:
        values[attr.name] = _read_value(group, attr)

    known = schema.hdf5_names()
    for key, raw in group.attrs.items():
        if key in known:
            continue
        extras[key] = _decode_unknown(raw)

    return values, extras


def write_attrs(group: h5py.Group, obj: Any, schema: Schema) -> None:
    known = schema.hdf5_names()

    for attr in schema.attrs:
        key = attr.hdf5_key()
        value = getattr(obj, attr.name, attr.default)

        if attr.nested_schema is not None:
            if value is None:
                continue
            if key in group:
                del group[key]
            write_attrs(group.create_group(key), value, attr.nested_schema)
            continue

        if attr.mapping_schema is not None:
            if key in group:
                del group[key]
            mapping_group = group.create_group(key)
            for map_key, map_value in (value or {}).items():
                safe_key = str(map_key)
                write_attrs(
                    mapping_group.create_group(safe_key),
                    map_value,
                    attr.mapping_schema,
                )
            continue

        if attr.is_list and attr.type == "ndarray":
            if key in group:
                del group[key]
            list_group = group.create_group(key)
            items = list(value or [])
            list_group.attrs["count"] = len(items)
            for index, item in enumerate(items):
                list_group.create_dataset(
                    f"item_{index}",
                    data=np.asarray(item),
                    compression="gzip",
                )
            continue

        try:
            encoded = get_codec(attr.type).encode(value)
        except (TypeError, ValueError) as exc:
            logger.warning("write_attrs: encode %s failed: %s", attr.name, exc)
            continue

        if attr.is_dataset:
            if encoded is None:
                continue
            if key in group:
                del group[key]
            try:
                group.create_dataset(key, data=encoded, compression="gzip")
            except (OSError, TypeError, ValueError) as exc:
                logger.warning("write_attrs: dataset %s failed: %s", key, exc)
        else:
            try:
                group.attrs[key] = encoded
            except (OSError, TypeError, ValueError) as exc:
                logger.warning("write_attrs: attr %s failed: %s", key, exc)

    for key, value in (getattr(obj, "extras", None) or {}).items():
        if key in known:
            continue
        try:
            group.attrs[key] = _encode_unknown(value)
        except (OSError, TypeError, ValueError) as exc:
            logger.warning("write_attrs: extras[%r] failed: %s", key, exc)