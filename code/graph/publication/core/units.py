"""Точные конвертации единиц. ».

Matplotlib хранит прямоугольники осей в долях фигуры (0..1). Мы конвертируем
мм панели в доли фигуры по точной формуле с флипом по Y (у Matplotlib origin
снизу-слева, у нас координаты панели — сверху-слева).
"""
from __future__ import annotations
from typing import Tuple

MM_PER_INCH = 25.4
PT_PER_INCH = 72.0


def mm_to_inch(mm: float) -> float:
    return float(mm) / MM_PER_INCH


def mm_to_points(mm: float) -> float:
    return float(mm) / MM_PER_INCH * PT_PER_INCH


def mm_to_px(mm: float, dpi: float) -> int:
    return int(round(float(mm) / MM_PER_INCH * float(dpi)))


def panel_rect_to_figure_fraction(
    x_mm: float, y_mm: float, w_mm: float, h_mm: float,
    fig_w_mm: float, fig_h_mm: float,
) -> Tuple[float, float, float, float]:
    """(x_mm, y_mm, w_mm, h_mm) в мм (y — сверху) → (x, y, w, h) в долях
    фигуры для `fig.add_axes` (y — снизу).
    """
    if fig_w_mm <= 0 or fig_h_mm <= 0:
        raise ValueError("figure size must be positive")
    x = float(x_mm) / fig_w_mm
    w = float(w_mm) / fig_w_mm
    h = float(h_mm) / fig_h_mm
    y = 1.0 - (float(y_mm) + float(h_mm)) / fig_h_mm
    return x, y, w, h


def figure_fraction_to_panel_rect(
    x_frac: float, y_frac: float, w_frac: float, h_frac: float,
    fig_w_mm: float, fig_h_mm: float,
) -> Tuple[float, float, float, float]:
    """Обратное преобразование (y считается сверху, как у панели)."""
    x_mm = x_frac * fig_w_mm
    w_mm = w_frac * fig_w_mm
    h_mm = h_frac * fig_h_mm
    y_mm = fig_h_mm - (y_frac + h_frac) * fig_h_mm
    return x_mm, y_mm, w_mm, h_mm