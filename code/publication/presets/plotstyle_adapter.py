"""Опциональная интеграция PlotStyle.

PlotStyle — необязательная зависимость. Если импорт удался и PlotStyle
предоставляет `get_style(name) -> dict`, адаптер возвращает словарь,
транслированный в наши ключи. Иначе — fallback на встроенные пресеты.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import plotstyle as _plotstyle  # type: ignore
    _AVAILABLE = True
except Exception:
    _plotstyle = None
    _AVAILABLE = False


class PlotStyleAdapter:
    """Тонкий адаптер. Не тянет PlotStyle в обязательные зависимости."""

    def is_available(self) -> bool:
        return _AVAILABLE

    def load_style(self, name: str) -> Optional[Dict[str, Any]]:
        if not _AVAILABLE:
            return None
        try:
            style = None
            for attr in ("get_style", "load_style", "read_style"):
                fn = getattr(_plotstyle, attr, None)
                if callable(fn):
                    style = fn(name)
                    break
            if style is None:
                return None
            return self._translate(style)
        except Exception:
            logger.exception("PlotStyleAdapter.load_style(%r) failed", name)
            return None

    def _translate(self, raw: Any) -> Dict[str, Any]:
        """Перевести произвольный dict PlotStyle в наши ключи.

        Это консервативный маппинг: если PlotStyle не знает про наши ключи,
        мы просто ничего не выигрываем и остаёмся на safe_defaults.
        """
        out: Dict[str, Any] = {}
        if not isinstance(raw, dict):
            return out
        if "font_size" in raw:
            out["figure.font.size"] = float(raw["font_size"])
        if "font_family" in raw:
            out["figure.font.family"] = str(raw["font_family"])
        if "line_width" in raw:
            out["figure.line.width"] = float(raw["line_width"])
        if "axes_line_width" in raw:
            out["figure.axes.line_width"] = float(raw["axes_line_width"])
        return out