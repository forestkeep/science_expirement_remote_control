"""Headless API: рендер фигуры без открытия окна.

Использование в CI:
    from graph.publication.headless import render_headless
    render_headless("spec.json", "out/figure.pdf",
                    preset_id="nature_double",
                    data_provider=None)  # None → demo synthetic
"""
from __future__ import annotations
import logging
import os
from typing import Any, Callable, Dict, Optional

import numpy as np

from .core.json_io import load_spec, save_spec
from .model.figure_model import FigureSpec
from .model.panel import PanelSpec
from .model.session_ref import DataRef
from .model.stylestack import StyleStack, list_overrides
from .presets.builtin import SAFE_DEFAULTS
from .presets.loader import (
    load_journal_preset, load_style_profile_auto, load_lab_profile_auto,
)
from .renderers.mpl_renderer import MatplotlibRenderer
from .validation.validator import Validator
from .export.exporter import Exporter

logger = logging.getLogger(__name__)


def _make_stack(spec: FigureSpec, preset):
    return StyleStack(
        spec,
        safe_defaults=SAFE_DEFAULTS,
        style_profile=load_style_profile_auto(),
        journal_defaults=preset.defaults if preset else {},
        lab_profile=load_lab_profile_auto(),
    )


def render_headless(
    spec_path: str,
    output_path: str,
    preset_id: Optional[str] = None,
    data_provider: Optional[Callable] = None,
    export_dir: Optional[str] = None,
    include_png: bool = False,
) -> Dict[str, Any]:
    spec = load_spec(spec_path)
    if preset_id is None:
        preset_id = spec.journal_preset_id or spec.column_preset_id or "nature_double"
    preset = load_journal_preset(preset_id)
    spec.journal_preset_id = preset.id
    stack = _make_stack(spec, preset)

    resolver = data_provider or _demo_provider

    renderer = MatplotlibRenderer()
    fig = renderer.create_figure(spec)
    renderer.render(fig, spec, resolver, stack.resolve,
                    lambda ann_id: spec.get_data_bound_override(ann_id))
    fmt = os.path.splitext(output_path)[1].lstrip(".").lower() or "pdf"
    renderer.save(fig, output_path, fmt=fmt, dpi=int(_resolve_dpi(stack)))

    result = {"path": output_path, "format": fmt}

    if export_dir:
        report = Validator(spec, preset, stack, resolver).validate()
        exporter = Exporter(spec, preset, stack, resolver,
                            lambda ann_id: spec.get_data_bound_override(ann_id),
                            validation_report=report)
        pkg = exporter.export_package(export_dir, include_png=include_png)
        result["package"] = pkg
        result["validation"] = report.to_dict()

    return result


def _resolve_dpi(stack: StyleStack) -> int:
    from .core.sentinel import MISSING
    dpi = stack.resolve("figure.dpi")
    return 300 if dpi is MISSING else int(dpi)


def _demo_provider(panel: PanelSpec, data_ref: DataRef) -> Optional[Dict[str, Any]]:
    """Синтетические данные — для запуска примера без реальной сессии."""
    if data_ref is None or data_ref.is_empty():
        return None
    try:
        seed = sum(ord(c) for c in data_ref.series_root_name) % 7
    except Exception:
        seed = 0
    x = np.linspace(0, 10, 300)
    y = np.sin(x * (1 + seed * 0.5)) + 0.05 * np.cos(x * 20)
    return {
        "x": x, "y": y,
        "curve_name": data_ref.series_root_name,
        "x_name": "t, s", "y_name": "U, V",
        "saved_style": None,
        "panel_annotations": [],
    }