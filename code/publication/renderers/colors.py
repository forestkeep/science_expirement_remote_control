"""Единственный резолвер цвета линии: используется рендером и валидатором."""
from __future__ import annotations
from typing import Optional

from ..presets.builtin import OKABE_ITO


def get_palette() -> list:
    return list(OKABE_ITO)


def resolve_line_color(slot, index: int, panel, line_style) -> str:
    """Вернуть цвет линии по правилам контракта.

    Приоритет:
      1) panel.use_source_color=True и line_style.color задан → цвет из источника;
      2) иначе — OKABE_ITO[index % len].
    """
    if getattr(panel, "use_source_color", True) and line_style is not None:
        color = getattr(line_style, "color", None)
        if color:
            return str(color)
    return OKABE_ITO[index % len(OKABE_ITO)]


__all__ = ["resolve_line_color", "get_palette"]