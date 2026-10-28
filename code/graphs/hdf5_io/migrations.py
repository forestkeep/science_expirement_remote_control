"""Цепочка миграций схемы проекта.

Все «дефолты для старых файлов» (типа is_multiple_y1_enabled ←
is_multiple_selection_enabled) живут здесь, а не размазаны по
getattr(..., fallback) в адаптерах.

Миграции обязаны быть идемпотентными: apply(d) ∘ apply(d) == apply(d).
Это позволяет безопасно запускать migrate(d, from_version=0) на уже
мигрированных данных.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 1


def _v0_to_v1(data: dict) -> dict:
    """v0 → v1: is_multiple_selection_enabled становится синонимом y1.

    Также проставляет is_multiple_y2_enabled (в старых файлах не было).
    """
    if not isinstance(data, dict):
        return data
    if ("is_multiple_y1_enabled" not in data
            and "is_multiple_selection_enabled" in data):
        data["is_multiple_y1_enabled"] = bool(data["is_multiple_selection_enabled"])
    data.setdefault("is_multiple_y2_enabled", False)
    return data


MIGRATIONS: dict[int, Callable[[dict], dict]] = {
    0: _v0_to_v1,
}


def migrate(data: Any, from_version: int) -> Any:
    """Прогнать данные через цепочку миграций от from_version к CURRENT."""
    if not isinstance(data, dict):
        return data
    version = int(from_version) if from_version is not None else 0
    while version < CURRENT_SCHEMA_VERSION:
        step = MIGRATIONS.get(version)
        if step is None:
            logger.warning("migrate: no step from version %d", version)
            break
        try:
            data = step(data)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("migrate: step %d→%d failed: %s", version, version + 1, exc)
            break
        version += 1
    return data