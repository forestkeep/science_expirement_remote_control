"""Инструмент «Оценка неопределённости». Пишет результат в CurveDataStore."""
from __future__ import annotations

import numpy as np

from ..models import (
    AnalysisToolDescriptor, ParamDescriptor, ParamType,
    PlacementType, ToolCategory,
)
from ..registry import AnalysisToolRegistry
from .base import AnalysisContext, AnalysisStrategy, ValidationResult

_registry = AnalysisToolRegistry.instance()


class UncertaintyEstimateStrategy(AnalysisStrategy):
    """Стратегия не пишет в store — контроллер обрабатывает её отдельно
    (см. AnalysisController.apply → ветка uncertainty)."""

    def validate(self, params, sources):
        if not sources:
            return ValidationResult(False, "Не выделено кривых")
        return ValidationResult(True)

    def compute(self, context: AnalysisContext, params: dict):
        # Ничего не возвращаем — payload формируется в контроллере через
        # compute_uncertainty(). Здесь достаточно пустышки.
        return None, []

    def describe(self, params):
        return params.get("method", "std")


def _register():
    _registry.register(AnalysisToolDescriptor(
        tool_id="uncertainty.estimate",
        category=ToolCategory.STATISTICS,
        placement_type=PlacementType.UNCERTAINTY,
        title_key="analysis.tool.uncertainty.estimate.title",
        tooltip_key="analysis.tool.uncertainty.estimate.tooltip",
        param_schema=[
            ParamDescriptor(
                "method", ParamType.CHOICE,
                default="std",
                choices=[
                    ("std",       "analysis.param.uncertainty.method.std"),
                    ("sem",       "analysis.param.uncertainty.method.sem"),
                    ("ci95",      "analysis.param.uncertainty.method.ci95"),
                    ("bootstrap", "analysis.param.uncertainty.method.bootstrap"),
                    ("manual",    "analysis.param.uncertainty.method.manual"),
                ],
                title_key="analysis.param.uncertainty.method",
            ),
            ParamDescriptor("window", ParamType.INT, default=0, min=0, max=1000,
                            title_key="analysis.param.uncertainty.window"),
            ParamDescriptor("level", ParamType.FLOAT, default=0.95, min=0.5, max=0.999,
                            title_key="analysis.param.uncertainty.level"),
            ParamDescriptor("iterations", ParamType.INT, default=200, min=10, max=5000,
                            title_key="analysis.param.uncertainty.iterations"),
            ParamDescriptor("y_err", ParamType.FLOAT, default=0.0,
                            title_key="analysis.param.uncertainty.y_err"),
        ],
        strategy_factory=UncertaintyEstimateStrategy,
    ))


_register()