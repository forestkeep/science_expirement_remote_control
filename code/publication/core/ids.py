"""Детерминированные ID.

ID назначаются в момент создания объекта в модели и сохраняются в спецификации.
Повторный рендер той же спецификации всегда даёт тот же выход — потому что ID
берутся из файла, а сортировка стабильная.
"""
from __future__ import annotations
from typing import Set


class IdGen:
    """Счётчик ID с заданным префиксом (на уровне FigureSpec)."""

    def __init__(self, prefix: str, start: int = 1):
        self.prefix = prefix
        self.counter = int(start)

    def next(self) -> str:
        self.counter += 1
        return f"{self.prefix}_{self.counter:04d}"

    def reserve(self, used: Set[str]) -> None:
        """Пропустить уже занятые ID, чтобы не сгенерировать дубликат."""
        while self.next() in used:
            pass