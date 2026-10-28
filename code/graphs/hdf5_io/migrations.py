from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 2


def _v0_to_v1(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    if (
        "is_multiple_y1_enabled" not in data
        and "is_multiple_selection_enabled" in data
    ):
        data["is_multiple_y1_enabled"] = bool(
            data["is_multiple_selection_enabled"]
        )
    data.setdefault("is_multiple_y2_enabled", False)
    return data


def _v1_to_v2(data: dict) -> dict:
    if not isinstance(data, dict):
        return data
    data.setdefault("edit_all_axes", True)
    data.setdefault("applied_preset_name", "—")
    return data


MIGRATIONS: dict[int, Callable[[dict], dict]] = {
    0: _v0_to_v1,
    1: _v1_to_v2,
}


def migrate(data: Any, from_version: int) -> Any:
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
            logger.warning(
                "migrate: step %d→%d failed: %s",
                version,
                version + 1,
                exc,
            )
            break
        version += 1
    return data