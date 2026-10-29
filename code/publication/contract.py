"""Контракт «источник vs пресет» как исполняемый документ.

CONTRACT — единственный источник правды о том, откуда берётся каждый
визуальный атрибут публикационной фигуры. Рендерер не имеет права
читать атрибуты источника/пресета, не описанные здесь.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Origin(Enum):
    SOURCE_STYLE = "source_style"
    SOURCE_DATA = "source_data"
    PANEL_OVERRIDE = "panel_override"
    PRESET = "preset"
    PRESET_PALETTE = "preset_palette"
    CONSTANT = "constant"


@dataclass(frozen=True)
class Attr:
    key: str
    origin: Origin
    fallback: object = None
    path_in_preset: str = ""
    validates: bool = False


CONTRACT = (
    # --- Стиль кривой из источника ---
    Attr("line.color", Origin.SOURCE_STYLE, fallback="#1f77b4"),
    Attr("line.width", Origin.SOURCE_STYLE, fallback=1.0),
    Attr("line.style", Origin.SOURCE_STYLE, fallback="Solid"),
    Attr("marker.symbol", Origin.SOURCE_STYLE, fallback=None),
    Attr("marker.size", Origin.SOURCE_STYLE, fallback=5),
    Attr("marker.edge", Origin.SOURCE_STYLE, fallback="#ffffff"),
    Attr("marker.face", Origin.SOURCE_STYLE, fallback="#ffffff"),

    # --- Данные ---
    Attr("curve.name", Origin.SOURCE_DATA, fallback=""),

    # --- Переопределение панели ---
    Attr("axis.x_label", Origin.PANEL_OVERRIDE, fallback=""),
    Attr("axis.y_label", Origin.PANEL_OVERRIDE, fallback=""),
    Attr("panel.title", Origin.PANEL_OVERRIDE, fallback=""),

    # --- Из пресета ---
    Attr("axes.line_width", Origin.PRESET, fallback=0.5,
         path_in_preset="figure.axes.line_width"),
    Attr("axes.tick_size", Origin.PRESET, fallback=7.0,
         path_in_preset="figure.axes.tick_size"),
    Attr("axes.label_size", Origin.PRESET, fallback=8.0,
         path_in_preset="figure.axes.label_size"),
    Attr("font.family", Origin.PRESET, fallback="DejaVu Sans",
         path_in_preset="figure.font.family"),
    Attr("legend.enabled", Origin.PRESET, fallback=True,
         path_in_preset="legend.enabled"),
    Attr("legend.font_size", Origin.PRESET, fallback=7.0,
         path_in_preset="legend.font_size"),
    Attr("figure.dpi", Origin.PRESET, fallback=300,
         path_in_preset="figure.dpi", validates=True),
    Attr("figure.background", Origin.PRESET, fallback="#ffffff",
         path_in_preset="figure.background"),

    # --- Не переносится в v1 ---
    Attr("uncertainty.bars", Origin.CONSTANT, fallback=None),
    Attr("analysis.attached", Origin.CONSTANT, fallback=None),
    Attr("analysis.domain", Origin.CONSTANT, fallback=None),
)


_ATTR_MAP = {a.key: a for a in CONTRACT}


def get_attr(key: str) -> Attr:
    """Найти атрибут в CONTRACT. KeyError с осмысленным сообщением."""
    try:
        return _ATTR_MAP[key]
    except KeyError:
        raise KeyError(
            f"Атрибут {key!r} отсутствует в CONTRACT. "
            f"Добавьте его в publication/contract.py::CONTRACT — "
            f"рендерер не имеет права обращаться к атрибутам вне контракта."
        )


def render_readme() -> str:
    """Markdown-таблица «ключ | источник | fallback | примечание»."""
    lines = [
        "| ключ | источник | fallback | примечание |",
        "|------|----------|----------|------------|",
    ]
    for a in CONTRACT:
        note = ""
        if a.validates:
            note = "участвует в валидации"
        if a.origin is Origin.CONSTANT and a.fallback is None:
            note = "не переносится в v1"
        fb = "" if a.fallback is None else f"`{a.fallback}`"
        lines.append(f"| `{a.key}` | {a.origin.value} | {fb} | {note} |")
    return "\n".join(lines)


__all__ = ["Origin", "Attr", "CONTRACT", "get_attr", "render_readme"]