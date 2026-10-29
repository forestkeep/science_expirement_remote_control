"""Мелкие помощники для Matplotlib-рендерера."""
from __future__ import annotations
import logging

from ..presets.builtin import OKABE_ITO

logger = logging.getLogger(__name__)


def qt_style_to_mpl(style) -> object:
    """Qt.PenStyle → (offset, onoffseq) для matplotlib.

    Возвращает либо строку "-" (matplotlib принимает), либо кортеж
    (offset, onoffseq) для всех не-Solid стилей. Пропорции совпадают с
    экранными: Dash(4,2), Dot(1,3), DashDot(4,2,1,2), DashDotDot(4,2,1,2,1,2).
    """
    try:
        from PyQt5 import QtCore
    except Exception:
        return "-"
    mapping = {
        QtCore.Qt.SolidLine: "-",
        QtCore.Qt.DashLine: (0, (4, 2)),
        QtCore.Qt.DotLine: (0, (1, 3)),
        QtCore.Qt.DashDotLine: (0, (4, 2, 1, 2)),
        QtCore.Qt.DashDotDotLine: (0, (4, 2, 1, 2, 1, 2)),
    }
    if style is None:
        return "-"
    if style in mapping:
        return mapping[style]
    logger.warning("qt_style_to_mpl: неизвестный стиль %r, fallback '-'", style)
    return "-"


def color_for_series(saved_style, index: int, palette: str = "okabe_ito") -> str:
    if saved_style is not None:
        c = getattr(saved_style, "color", None)
        if c:
            return str(c)
    return OKABE_ITO[index % len(OKABE_ITO)]


def line_width_pt(saved_style, default: float = 1.0) -> float:
    if saved_style is None:
        return float(default)
    try:
        w = getattr(saved_style, "line_width", default)
        return max(0.1, float(w))
    except Exception:
        return float(default)


__all__ = ["qt_style_to_mpl", "color_for_series", "line_width_pt"]