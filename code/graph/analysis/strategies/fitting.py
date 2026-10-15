"""Стратегии фитинга: линейная, полиномиальная, Гаусс, Лоренц."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np

from ..models import (
    AnalysisToolDescriptor, OverlayPayload, ParamDescriptor, ParamType,
    PlacementType, ToolCategory,
)
from ..registry import AnalysisToolRegistry
from .base import AnalysisContext, AnalysisStrategy, ValidationResult

logger = logging.getLogger(__name__)

_registry = AnalysisToolRegistry.instance()


class LinearFitStrategy(AnalysisStrategy):
    def validate(self, params, sources):
        if not sources:
            return ValidationResult(False, "Не выделено кривых")
        for s in sources:
            if len(s.x) < 2:
                return ValidationResult(False, "Мало точек")
        return ValidationResult(True)

    def compute(self, context: AnalysisContext, params: Dict[str, Any]):
        results = []
        for snap in context.sources:
            x = np.asarray(snap.x, dtype=float)
            y = np.asarray(snap.y, dtype=float)
            mask = np.isfinite(x) & np.isfinite(y)
            x, y = x[mask], y[mask]
            if len(x) < 2:
                continue
            k, b = np.polyfit(x, y, 1)
            y_fit = k * x + b
            y_pred = k * x + b
            ss_res = float(np.sum((y - y_pred) ** 2))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            results.append({
                "curve": snap.root_name,
                "x": x,
                "y": y_fit,
                "k": float(k),
                "b": float(b),
                "r2": float(r2),
                "n": int(len(x)),
            })
        return OverlayPayload(
            x=[r["x"] for r in results],
            y=[r["y"] for r in results],
            style_hint={"dashed": True, "thickness_factor": 0.75},
        ), results

    def describe(self, params):
        return "линейная"


class PolynomialFitStrategy(AnalysisStrategy):
    def validate(self, params, sources):
        if not sources:
            return ValidationResult(False, "Не выделено кривых")
        deg = int(params.get("degree", 2))
        for s in sources:
            if len(s.x) < deg + 1:
                return ValidationResult(False, f"Нужно ≥ {deg + 1} точек")
        return ValidationResult(True)

    def compute(self, context: AnalysisContext, params: Dict[str, Any]):
        deg = max(2, min(6, int(params.get("degree", 2))))
        results = []
        for snap in context.sources:
            x = np.asarray(snap.x, dtype=float)
            y = np.asarray(snap.y, dtype=float)
            mask = np.isfinite(x) & np.isfinite(y)
            x, y = x[mask], y[mask]
            if len(x) < deg + 1:
                continue
            coeffs = np.polyfit(x, y, deg)
            y_fit = np.polyval(coeffs, x)
            ss_res = float(np.sum((y - y_fit) ** 2))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            results.append({
                "curve": snap.root_name,
                "x": x, "y": y_fit,
                "coeffs": coeffs.tolist(),
                "degree": deg,
                "r2": float(r2),
            })
        return OverlayPayload(
            x=[r["x"] for r in results],
            y=[r["y"] for r in results],
            style_hint={"dashed": True, "thickness_factor": 0.75},
        ), results

    def describe(self, params):
        return f"полином deg={params.get('degree', 2)}"


def _gaussian(x, amp, mu, sigma, base):
    return base + amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def _lorentz(x, amp, mu, gamma, base):
    return base + amp / (1.0 + ((x - mu) / gamma) ** 2)


class _PeakFitStrategy(AnalysisStrategy):
    _peak_fn = None
    _init_guess = None

    def validate(self, params, sources):
        if not sources:
            return ValidationResult(False, "Не выделено кривых")
        return ValidationResult(True)

    def compute(self, context: AnalysisContext, params: Dict[str, Any]):
        try:
            from scipy.optimize import curve_fit
        except ImportError:
            logger.warning("scipy не установлен, фит пиков недоступен")
            return OverlayPayload(), []

        results = []
        for snap in context.sources:
            x = np.asarray(snap.x, dtype=float)
            y = np.asarray(snap.y, dtype=float)
            mask = np.isfinite(x) & np.isfinite(y)
            x, y = x[mask], y[mask]
            if len(x) < 4:
                continue
            try:
                p0 = self._init_guess(x, y)
                popt, _ = curve_fit(self._peak_fn, x, y, p0=p0, maxfev=5000)
                y_fit = self._peak_fn(x, *popt)
                results.append({
                    "curve": snap.root_name,
                    "x": x, "y": y_fit,
                    "params": popt.tolist(),
                })
            except Exception as exc:
                logger.warning("fit failed for %s: %s", snap.root_name, exc)
        return OverlayPayload(
            x=[r["x"] for r in results],
            y=[r["y"] for r in results],
            style_hint={"dashed": True, "thickness_factor": 0.75},
        ), results


class GaussianFitStrategy(_PeakFitStrategy):
    _peak_fn = staticmethod(_gaussian)

    @staticmethod
    def _init_guess(x, y):
        amp = float(np.nanmax(y) - np.nanmin(y))
        mu = float(x[int(np.nanargmax(y))])
        sigma = float((x[-1] - x[0]) / 6.0) or 1.0
        base = float(np.nanmin(y))
        return [amp, mu, sigma, base]

    def describe(self, params):
        return "Gaussian"


class LorentzFitStrategy(_PeakFitStrategy):
    _peak_fn = staticmethod(_lorentz)

    @staticmethod
    def _init_guess(x, y):
        amp = float(np.nanmax(y) - np.nanmin(y))
        mu = float(x[int(np.nanargmax(y))])
        gamma = float((x[-1] - x[0]) / 6.0) or 1.0
        base = float(np.nanmin(y))
        return [amp, mu, gamma, base]

    def describe(self, params):
        return "Lorentz"


def _register():
    _registry.register(AnalysisToolDescriptor(
        tool_id="fit.linear",
        category=ToolCategory.FITTING,
        placement_type=PlacementType.OVERLAY,
        title_key="analysis.tool.fit.linear.title",
        tooltip_key="analysis.tool.fit.linear.tooltip",
        param_schema=[],
        strategy_factory=LinearFitStrategy,
    ))
    _registry.register(AnalysisToolDescriptor(
        tool_id="fit.polynomial",
        category=ToolCategory.FITTING,
        placement_type=PlacementType.OVERLAY,
        title_key="analysis.tool.fit.polynomial.title",
        param_schema=[
            ParamDescriptor("degree", ParamType.INT, default=2, min=2, max=6,
                            title_key="analysis.param.fit.polynomial.degree"),
        ],
        strategy_factory=PolynomialFitStrategy,
    ))
    _registry.register(AnalysisToolDescriptor(
        tool_id="fit.gaussian",
        category=ToolCategory.FITTING,
        placement_type=PlacementType.OVERLAY,
        title_key="analysis.tool.fit.gaussian.title",
        param_schema=[],
        strategy_factory=GaussianFitStrategy,
    ))
    _registry.register(AnalysisToolDescriptor(
        tool_id="fit.lorentz",
        category=ToolCategory.FITTING,
        placement_type=PlacementType.OVERLAY,
        title_key="analysis.tool.fit.lorentz.title",
        param_schema=[],
        strategy_factory=LorentzFitStrategy,
    ))


_register()