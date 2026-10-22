"""Слоистое наследование стиля с троичным состоянием.

Порядок приоритета (последний побеждает):
    safe_defaults → style_profile → journal_preset
    → lab_profile → figure_overrides → panel_overrides → element_overrides.

Ключ пути (строкой, чтобы переживать JSON):
    "figure.font.size"
    "panel.<panel_id>.line.width"
    "element.<element_id>.size"

resolve_style(spec, path) → effective_value или MISSING.
set_override(spec, path, value) → записывает в нужный узел.
clear_override(spec, path) → помечает MISSING в override-узле.
list_overrides(spec) → активные overrides (без MISSING).
"""
from __future__ import annotations
from typing import Any, Dict

from ..core.sentinel import MISSING


class StyleStack:
    def __init__(
        self,
        spec,
        safe_defaults: Dict[str, Any],
        style_profile: Dict[str, Any],
        journal_defaults: Dict[str, Any],
        lab_profile: Dict[str, Any] = None,
    ):
        self.spec = spec
        self.safe_defaults = dict(safe_defaults or {})
        self.style_profile = dict(style_profile or {})
        self.journal_defaults = dict(journal_defaults or {})
        self.lab_profile = dict(lab_profile or {})

    def resolve(self, path: str) -> Any:
        value = MISSING
        for layer in (
            self.safe_defaults, self.style_profile,
            self.journal_defaults, self.lab_profile,
        ):
            v = layer.get(path, MISSING)
            if v is not MISSING:
                value = v

        if path.startswith("figure.") or path.startswith("element."):
            v = self.spec.figure_overrides.get(path, MISSING)
            if v is not MISSING:
                value = v
        elif path.startswith("panel."):
            parts = path.split(".", 2)
            if len(parts) >= 2:
                panel = self.spec.find_panel(parts[1])
                if panel is not None:
                    v = panel.style_overrides.get(path, MISSING)
                    if v is not MISSING:
                        value = v
        return value

    def resolve_default(self, path: str, fallback: Any = None) -> Any:
        v = self.resolve(path)
        return v if v is not MISSING else fallback


# ---- free-function API (требование ТЗ) --------------------------------

def _set_get_node(spec, path: str):
    """Вернуть (контейнер, ключ) куда писать override."""
    if path.startswith("panel."):
        parts = path.split(".", 2)
        if len(parts) >= 2:
            panel = spec.find_panel(parts[1])
            if panel is not None:
                return panel.style_overrides, path
    return spec.figure_overrides, path


def resolve_style(spec, path: str,
                  safe_defaults: Dict[str, Any] = None,
                  style_profile: Dict[str, Any] = None,
                  journal_defaults: Dict[str, Any] = None,
                  lab_profile: Dict[str, Any] = None) -> Any:
    stack = StyleStack(spec, safe_defaults or {}, style_profile or {},
                       journal_defaults or {}, lab_profile or {})
    return stack.resolve(path)


def set_override(spec, path: str, value: Any) -> None:
    target, key = _set_get_node(spec, path)
    target[key] = value


def clear_override(spec, path: str) -> None:
    target, key = _set_get_node(spec, path)
    if key in target:
        target[key] = MISSING


def list_overrides(spec) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in spec.figure_overrides.items():
        if v is not MISSING:
            out[k] = v
    for panel in spec.panels:
        for k, v in panel.style_overrides.items():
            if v is not MISSING:
                out[k] = v
    return out