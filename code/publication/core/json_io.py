"""Сериализация + миграции схемы.

Схема версионирована (SCHEMA_VERSION). Миграции — пошаговые, от N к N+1.
"""
from __future__ import annotations
import json
import logging
from typing import Any, Dict

from .sentinel import MISSING

logger = logging.getLogger(__name__)
SCHEMA_VERSION = 1


def _serialize_style_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Отбросить MISSING при сохранении."""
    return {k: v for k, v in d.items() if v is not MISSING}


def save_spec(spec, path: str) -> None:
    data = spec.to_dict()
    data["schema_version"] = SCHEMA_VERSION
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def load_spec(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data = _migrate(data)
    from ..model.figure_model import FigureSpec
    return FigureSpec.from_dict(data)


def _migrate(data: Dict[str, Any]) -> Dict[str, Any]:
    version = int(data.get("schema_version", 1))
    if version > SCHEMA_VERSION:
        raise ValueError(
            f"spec schema_version={version} > supported={SCHEMA_VERSION}"
        )
    # Пример будущей миграции:
    # if version == 1:
    #     data = _migrate_1_to_2(data)
    #     version = 2
    return data