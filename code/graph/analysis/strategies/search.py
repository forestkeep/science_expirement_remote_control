"""Поисковые стратегии: пики, впадины, пороговые события."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np

from ..models import (
    AnalysisToolDescriptor, AnnotationPayload, ParamDescriptor, ParamType,
    PlacementType, ToolCategory,
)
from ..registry import AnalysisToolRegistry
from .base import AnalysisContext, AnalysisStrategy, ValidationResult

logger = logging.getLogger(__name__)
_registry = AnalysisToolRegistry.instance()


class PeakSearchStrategy(AnalysisStrategy):
    def validate(self, params, sources):
        if not sources:
            return ValidationResult(False, "Не выделено кривых")
        return ValidationResult(True)

    def compute(self, context: AnalysisContext, params: Dict[str, Any]):
        min_height = params.get("min_height", None)
        min_distance = int(params.get("min_distance", 1) or 1)
        points: List[Dict[str, Any]] = []
        per_curve = []
        for snap in context.sources:
            x = np.asarray(snap.x, dtype=float)
            y = np.asarray(snap.y, dtype=float)
            mask = np.isfinite(x) & np.isfinite(y)
            x, y = x[mask], y[mask]
            if len(y) < 3:
                continue
            idxs = self._find_peaks(y, min_height, min_distance)
            local = []
            for i in idxs:
                pt = {"curve": snap.root_name, "x": float(x[i]),
                      "y": float(y[i]), "index": int(i)}
                points.append(pt)
                local.append(pt)
            per_curve.append({"curve": snap.root_name, "peaks": local,
                              "count": len(local)})
        return AnnotationPayload(points=points, label="peaks"), per_curve

    @staticmethod
    def _find_peaks(y, min_height, min_distance):
        peaks = []
        for i in range(1, len(y) - 1):
            if y[i] > y[i - 1] and y[i] > y[i + 1]:
                if min_height is not None and y[i] < min_height:
                    continue
                if peaks and (i - peaks[-1]) < min_distance:
                    continue
                peaks.append(i)
        return peaks

    def describe(self, params):
        return "peaks"


class ValleySearchStrategy(PeakSearchStrategy):
    def compute(self, context, params):
        payload, per_curve = super().compute(context, params)
        # инвертируем Y для поиска впадин
        points = payload.points
        for p in points:
            p["y"] = -p["y"]
        payload.label = "valleys"
        return payload, per_curve

    def describe(self, params):
        return "valleys"


def _register():
    _registry.register(AnalysisToolDescriptor(
        tool_id="search.peaks",
        category=ToolCategory.SEARCH,
        placement_type=PlacementType.ANNOTATION,
        title_key="analysis.tool.search.peaks.title",
        param_schema=[
            ParamDescriptor("min_height", ParamType.FLOAT, default=0.0,
                            title_key="analysis.param.search.peaks.min_height",
                            tooltip_key="analysis.param.search.peaks.min_height.tooltip"),
            ParamDescriptor("min_distance", ParamType.INT, default=1, min=1, max=1000,
                            title_key="analysis.param.search.peaks.min_distance",
                            tooltip_key="analysis.param.search.peaks.min_distance.tooltip"),
        ],
        strategy_factory=PeakSearchStrategy,
    ))
    _registry.register(AnalysisToolDescriptor(
        tool_id="search.valleys",
        category=ToolCategory.SEARCH,
        placement_type=PlacementType.ANNOTATION,
        title_key="analysis.tool.search.valleys.title",
        param_schema=[
            ParamDescriptor("min_height", ParamType.FLOAT, default=0.0,
                            title_key="analysis.param.search.valleys.min_height",
                            tooltip_key="analysis.param.search.valleys.min_height.tooltip"),
            ParamDescriptor("min_distance", ParamType.INT, default=1, min=1, max=1000,
                            title_key="analysis.param.search.valleys.min_distance",
                            tooltip_key="analysis.param.search.valleys.min_distance.tooltip"),
        ],
        strategy_factory=ValleySearchStrategy,
    ))


_register()