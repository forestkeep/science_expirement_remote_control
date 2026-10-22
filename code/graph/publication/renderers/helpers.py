"""Мелкие помощники для Matplotlib-рендерера."""
from __future__ import annotations
from typing import Any, Dict, Optional

from ..presets.builtin import OKABE_ITO


def qt_style_to_mpl(style) -> str:
    try:
        from PyQt5 import QtCore
        mapping = {
            QtCore.Qt.SolidLine: "-",
            QtCore.Qt.DashLine: "--",
            QtCore.Qt.DotLine: ":",
            QtCore.Qt.DashDotLine: "-.",
        }
        return mapping.get(style, "-")
    except Exception:
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