"""Чистые хелперы для парсинга значений.

Используются вместо вложенных try/except, где исключение — не ошибка,
а ожидаемая ветка разбора.
"""
from __future__ import annotations

from typing import Any, Optional


def parse_int_or_none(value: Any) -> Optional[int]:
    """int(value) или None, если значение не приводится к int.

    ``None``, ``""``, нечисловые строки и объекты → ``None``.
    Исключения не используются как сигнал «нет значения».
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_best_number(value: Any) -> Any:
    """int → float → bool → str."""
    try:
        import numpy as np
        if isinstance(value, np.ndarray):
            if value.ndim == 0 or value.size == 1:
                value = value.item()
            else:
                return value
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.bool_):
            return bool(value)
    except ImportError:
        pass

    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return value