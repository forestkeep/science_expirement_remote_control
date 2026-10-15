"""Дифференциальные инструменты: производная, интеграл, скользящее окно."""
from __future__ import annotations

import numpy as np

from ..models import (
    AnalysisToolDescriptor, AttachedPayload, ParamDescriptor, ParamType,
    PlacementType, ToolCategory,
)
from ..registry import AnalysisToolRegistry
from .base import AnalysisContext, AnalysisStrategy, ValidationResult

_registry = AnalysisToolRegistry.instance()


class DerivativeStrategy(AnalysisStrategy):
    def validate(self, params, sources):
        if not sources:
            return ValidationResult(False, "Не выделено кривых")
        return ValidationResult(True)

    def compute(self, context: AnalysisContext, params: Dict[str, Any]):
        window = int(params.get("window", 0) or 0)
        xs, ys, details = [], [], []
        for snap in context.sources:
            x = np.asarray(snap.x, dtype=float)
            y = np.asarray(snap.y, dtype=float)
            if len(x) < 2:
                continue
            dydx = np.gradient(y, x)
            if window > 1:
                k = np.ones(window) / window
                dydx = np.convolve(dydx, k, mode="same")
            xs.append(x)
            ys.append(dydx)
            details.append({"curve": snap.root_name,
                            "y_label": "d/dx",
                            "panel_title": "d/dx"})
        return AttachedPayload(x=xs, y=ys, y_label="d/dx",
                               panel_title="Производная"), details

    def describe(self, params):
        return "d/dx"


class IntegralStrategy(AnalysisStrategy):
    def compute(self, context: AnalysisContext, params: Dict[str, Any]):
        xs, ys, details = [], [], []
        for snap in context.sources:
            x = np.asarray(snap.x, dtype=float)
            y = np.asarray(snap.y, dtype=float)
            if len(x) < 2:
                continue
            cum = np.concatenate([[0.0], np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(x))])
            xs.append(x)
            ys.append(cum)
            details.append({"curve": snap.root_name,
                            "y_label": "∫",
                            "panel_title": "Интеграл"})
        return AttachedPayload(x=xs, y=ys, y_label="∫",
                               panel_title="Интеграл"), details

    def describe(self, params):
        return "∫"


def _register():
    _registry.register(AnalysisToolDescriptor(
        tool_id="diff.derivative",
        category=ToolCategory.DIFFERENTIAL,
        placement_type=PlacementType.ATTACHED,
        title_key="analysis.tool.diff.derivative.title",
        param_schema=[
            ParamDescriptor("window", ParamType.INT, default=0, min=0, max=100,
                            title_key="analysis.param.diff.window"),
        ],
        strategy_factory=DerivativeStrategy,
    ))
    _registry.register(AnalysisToolDescriptor(
        tool_id="diff.integral",
        category=ToolCategory.DIFFERENTIAL,
        placement_type=PlacementType.ATTACHED,
        title_key="analysis.tool.diff.integral.title",
        param_schema=[],
        strategy_factory=IntegralStrategy,
    ))


_register()