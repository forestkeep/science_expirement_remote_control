"""Поисковые стратегии: пики, впадины, пороговые события."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from scipy.signal import find_peaks as _scipy_find_peaks
    _HAS_SCIPY = True
except ImportError:  # pragma: no cover — scipy есть в проекте (fitting.py)
    _scipy_find_peaks = None
    _HAS_SCIPY = False

from ..models import (
    AnalysisToolDescriptor, AnnotationPayload, ParamDescriptor, ParamType,
    PlacementType, ToolCategory,
)
from ..registry import AnalysisToolRegistry
from .base import AnalysisContext, AnalysisStrategy, ValidationResult

logger = logging.getLogger(__name__)
_registry = AnalysisToolRegistry.instance()

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------
_P_MIN_HEIGHT = "min_height"
_P_MIN_PROMINENCE = "min_prominence"
_P_MIN_DISTANCE = "min_distance"
_P_MIN_WIDTH = "min_width"
_P_REL_HEIGHT = "rel_height"
_P_PLATEAU_SIZE = "plateau_size"
_P_MAX_POINTS = "max_points"

_DEFAULT_REL_HEIGHT = 0.5
_MIN_DISTANCE_FLOOR = 1
_PLATEAU_SIZE_FLOOR = 1
_MAX_POINTS_DEFAULT = 500
_MAX_POINTS_LIMIT = 100_000


@dataclass(frozen=True)
class _SearchParams:
    min_height: Optional[float]
    min_prominence: Optional[float]
    min_distance: int
    min_width: Optional[float]
    rel_height: float
    plateau_size: Optional[int]
    max_points: int        # NEW


# ---------------------------------------------------------------------------
# Валидация — чистые проверки, без try/except. Ошибка описывается в
# ValidationResult, а не исключением.
# ---------------------------------------------------------------------------
def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)

# ---------------------------------------------------------------------------
# Единственное место, где мы решаем, что передать в scipy. Всё «не задано»
# (None / 0 / 1) отсекается здесь — чтобы не нагружать find_peaks
# ненужными вычислениями (prominence, width).
# ---------------------------------------------------------------------------
def _build_find_peaks_kwargs(p: _SearchParams) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}

    if p.min_height is not None:
        kwargs["height"] = float(p.min_height)

    if p.min_prominence is not None and p.min_prominence > 0.0:
        kwargs["prominence"] = float(p.min_prominence)

    if p.min_distance > _MIN_DISTANCE_FLOOR:
        kwargs["distance"] = int(p.min_distance)

    if p.min_width is not None and p.min_width > 0.0:
        kwargs["width"] = float(p.min_width)
        kwargs["rel_height"] = float(p.rel_height)

    if p.plateau_size is not None and p.plateau_size >= _PLATEAU_SIZE_FLOOR:
        kwargs["plateau_size"] = int(p.plateau_size)

    return kwargs


# ---------------------------------------------------------------------------
# Общая стратегия. is_valley — единственный параметр, отличающий peaks от
# valleys. Никаких наследований с переопределением compute().
# ---------------------------------------------------------------------------
class _BaseSearchStrategy(AnalysisStrategy):
    is_valley: bool = False

    # ------------------------------------------------------------------
    def validate(self, params: Dict[str, Any],
                 sources: List[Any]) -> ValidationResult:
        if not sources:
            return ValidationResult(False, "Не выделено кривых")
        if not _HAS_SCIPY:
            return ValidationResult(False, "scipy не установлен — поиск пиков недоступен")
        return _validate_search_params(params or {})

    # ------------------------------------------------------------------
    def compute(self, context: AnalysisContext,
                params: Dict[str, Any]) -> Tuple[AnnotationPayload, List[Dict[str, Any]]]:
        """Найти пики/впадины.

        Гарантии:
        * не бросает исключений при некорректных params — возвращает
          пустой payload;
        * не бросает исключений при отсутствии scipy — пустой payload;
        * ``points`` содержит все найденные точки (для всех источников),
          ``per_curve`` — разбивку по источникам с полными свойствами.
        """
        label = "valleys" if self.is_valley else "peaks"

        # Валидация повторяется (validate() не всегда вызывается контроллером).
        validation = _validate_search_params(params or {})
        if not validation.ok:
            logger.warning("search: invalid params: %s", validation.message)
            return AnnotationPayload(points=[], label=label), []

        if not _HAS_SCIPY:
            logger.error("search: scipy is not installed")
            return AnnotationPayload(points=[], label=label), []

        sp = _coerce_search_params(params or {})
        kwargs = _build_find_peaks_kwargs(sp)

        points: List[Dict[str, Any]] = []
        per_curve: List[Dict[str, Any]] = []

        for snap in context.sources:
            x = np.asarray(snap.x, dtype=float)
            y = np.asarray(snap.y, dtype=float)

            mask = np.isfinite(x) & np.isfinite(y)
            x, y = x[mask], y[mask]
            if len(y) < 3:
                per_curve.append({
                    "curve": snap.root_name, "peaks": [], "count": 0,
                    "total_found": 0, "truncated": False,
                    "note": "too few points",
                })
                continue

            target = -y if self.is_valley else y
            idxs, props = _scipy_find_peaks(target, **kwargs)

            total_found = int(len(idxs))
            truncated = False

            # --- NEW: обрезаем топ-N по prominence ---
            if total_found > sp.max_points:
                if "prominences" in props and len(props["prominences"]) == total_found:
                    scores = np.asarray(props["prominences"], dtype=float)
                else:
                    scores = np.asarray(target[idxs], dtype=float)
                order = np.argsort(scores)[::-1][:sp.max_points]
                order = np.sort(order)  # вернуть порядок по X, чтобы выглядело аккуратно

                idxs = idxs[order]
                for key in (
                    "peak_heights", "prominences", "widths", "plateau_sizes",
                    "left_bases", "right_bases", "left_ips", "right_ips",
                ):
                    if key in props and len(props[key]) == total_found:
                        props[key] = np.asarray(props[key])[order]

                truncated = True
                logger.info(
                    "search: truncated %d -> %d for %s",
                    total_found, sp.max_points, snap.root_name,
                )

            if len(idxs) == 0:
                per_curve.append({
                    "curve": snap.root_name, "peaks": [], "count": 0,
                    "total_found": total_found, "truncated": truncated,
                })
                continue

            heights      = props.get("peak_heights")
            prominences  = props.get("prominences")
            widths       = props.get("widths")
            plateau_sizes = props.get("plateau_sizes")

            local: List[Dict[str, Any]] = []
            for j, i in enumerate(idxs):
                pt: Dict[str, Any] = {
                    "curve": snap.root_name,
                    "x": float(x[i]),
                    "y": float(y[i]),
                    "index": int(i),
                }
                if heights is not None:
                    pt["height"] = float(heights[j])
                if prominences is not None:
                    pt["prominence"] = float(prominences[j])
                if widths is not None:
                    pt["width"] = float(widths[j])
                if plateau_sizes is not None:
                    pt["plateau_size"] = int(plateau_sizes[j])

                points.append(pt)
                local.append(pt)

            per_curve.append({
                "curve": snap.root_name,
                "peaks": local,
                "count": len(local),
                "total_found": total_found,
                "truncated": truncated,
            })

        return AnnotationPayload(points=points, label=label), per_curve

    # ------------------------------------------------------------------
    def describe(self, params: Dict[str, Any]) -> str:
        sp = _coerce_search_params(params or {})
        return _format_describe(sp, self.is_valley)


class PeakSearchStrategy(_BaseSearchStrategy):
    is_valley = False


class ValleySearchStrategy(_BaseSearchStrategy):
    is_valley = True


# ---------------------------------------------------------------------------
# Валидация
# ---------------------------------------------------------------------------
def _validate_search_params(params: Dict[str, Any]) -> ValidationResult:
    raw = params or {}

    if _P_MIN_HEIGHT in raw and raw[_P_MIN_HEIGHT] is not None:
        if not _is_number(raw[_P_MIN_HEIGHT]):
            return ValidationResult(False, "min_height должен быть числом")

    if _P_MIN_PROMINENCE in raw and raw[_P_MIN_PROMINENCE] is not None:
        v = raw[_P_MIN_PROMINENCE]
        if not _is_number(v):
            return ValidationResult(False, "min_prominence должен быть числом")
        if float(v) < 0.0:
            return ValidationResult(False, "min_prominence не может быть < 0")

    if _P_MIN_DISTANCE in raw and raw[_P_MIN_DISTANCE] is not None:
        v = raw[_P_MIN_DISTANCE]
        if not isinstance(v, int) or isinstance(v, bool):
            return ValidationResult(False, "min_distance должен быть целым")
        if v < 0:
            return ValidationResult(False, "min_distance не может быть < 0")

    if _P_MIN_WIDTH in raw and raw[_P_MIN_WIDTH] is not None:
        v = raw[_P_MIN_WIDTH]
        if not _is_number(v):
            return ValidationResult(False, "min_width должен быть числом")
        if float(v) < 0.0:
            return ValidationResult(False, "min_width не может быть < 0")

    if _P_REL_HEIGHT in raw and raw[_P_REL_HEIGHT] is not None:
        v = raw[_P_REL_HEIGHT]
        if not _is_number(v):
            return ValidationResult(False, "rel_height должен быть числом")
        if not (0.0 <= float(v) <= 1.0):
            return ValidationResult(False, "rel_height должен быть в диапазоне [0, 1]")

    if _P_PLATEAU_SIZE in raw and raw[_P_PLATEAU_SIZE] is not None:
        v = raw[_P_PLATEAU_SIZE]
        if not isinstance(v, int) or isinstance(v, bool):
            return ValidationResult(False, "plateau_size должен быть целым")
        if v < 0:
            # 0 == без ограничения; проверяем только отрицательные
            return ValidationResult(False, "plateau_size не может быть < 0")

    return ValidationResult(True)


# ---------------------------------------------------------------------------
# Приведение типов
# ---------------------------------------------------------------------------
def _coerce_search_params(params: Dict[str, Any]) -> _SearchParams:
    raw = params or {}

    def _float_or_none(key: str) -> Optional[float]:
        v = raw.get(key)
        return None if v is None else float(v)

    min_height = _float_or_none(_P_MIN_HEIGHT)
    if min_height is not None and min_height == 0.0:
        min_height = None

    min_prominence = _float_or_none(_P_MIN_PROMINENCE)
    min_width = _float_or_none(_P_MIN_WIDTH)

    raw_distance = raw.get(_P_MIN_DISTANCE)
    min_distance = _MIN_DISTANCE_FLOOR
    if raw_distance is not None:
        min_distance = max(_MIN_DISTANCE_FLOOR, int(raw_distance))

    raw_rel = raw.get(_P_REL_HEIGHT)
    rel_height = _DEFAULT_REL_HEIGHT
    if raw_rel is not None:
        rel_height = max(0.0, min(1.0, float(raw_rel)))

    raw_plateau = raw.get(_P_PLATEAU_SIZE)
    plateau_size: Optional[int] = None
    if raw_plateau is not None and int(raw_plateau) >= _PLATEAU_SIZE_FLOOR:
        plateau_size = int(raw_plateau)

    raw_max = raw.get(_P_MAX_POINTS)
    if raw_max is None:
        max_points = _MAX_POINTS_DEFAULT
    else:
        max_points = int(raw_max)
        if max_points < 1:
            max_points = _MAX_POINTS_DEFAULT
        elif max_points > _MAX_POINTS_LIMIT:
            max_points = _MAX_POINTS_LIMIT

    return _SearchParams(
        min_height=min_height,
        min_prominence=min_prominence,
        min_distance=min_distance,
        min_width=min_width,
        rel_height=rel_height,
        plateau_size=plateau_size,
        max_points=max_points,
    )

# ---------------------------------------------------------------------------
# Описание — только ASCII в "знаковых" местах.
# ---------------------------------------------------------------------------
def _format_describe(p: _SearchParams, is_valley: bool) -> str:
    parts: List[str] = []
    if p.min_height is not None:
        parts.append(f"h>={p.min_height:g}")
    if p.min_prominence is not None and p.min_prominence > 0.0:
        parts.append(f"prom>={p.min_prominence:g}")
    if p.min_distance > _MIN_DISTANCE_FLOOR:
        parts.append(f"dist>={p.min_distance}")
    if p.min_width is not None and p.min_width > 0.0:
        parts.append(f"w>={p.min_width:g}")
    if p.plateau_size is not None:
        parts.append(f"plateau>={p.plateau_size}")

    base = "впадины" if is_valley else "пики"
    if not parts:
        return base
    return f"{base}: " + "; ".join(parts)


# ---------------------------------------------------------------------------
# Схема параметров: добавляем show_labels
# ---------------------------------------------------------------------------
def _search_params_schema(prefix: str) -> List[ParamDescriptor]:
    return [
        ParamDescriptor(
            _P_MIN_HEIGHT, ParamType.FLOAT, default=0.0,
            title_key=f"{prefix}.{_P_MIN_HEIGHT}",
            tooltip_key=f"{prefix}.{_P_MIN_HEIGHT}.tooltip",
        ),
        ParamDescriptor(
            _P_MIN_PROMINENCE, ParamType.FLOAT, default=0.0, min=0.0,
            title_key=f"{prefix}.{_P_MIN_PROMINENCE}",
            tooltip_key=f"{prefix}.{_P_MIN_PROMINENCE}.tooltip",
        ),
        ParamDescriptor(
            _P_MIN_DISTANCE, ParamType.INT, default=1,
            min=0, max=100_000,
            title_key=f"{prefix}.{_P_MIN_DISTANCE}",
            tooltip_key=f"{prefix}.{_P_MIN_DISTANCE}.tooltip",
        ),
        ParamDescriptor(
            _P_MIN_WIDTH, ParamType.FLOAT, default=0.0, min=0.0,
            title_key=f"{prefix}.{_P_MIN_WIDTH}",
            tooltip_key=f"{prefix}.{_P_MIN_WIDTH}.tooltip",
        ),
        ParamDescriptor(
            _P_REL_HEIGHT, ParamType.FLOAT, default=_DEFAULT_REL_HEIGHT,
            min=0.0, max=1.0, step=0.05,
            title_key=f"{prefix}.{_P_REL_HEIGHT}",
            tooltip_key=f"{prefix}.{_P_REL_HEIGHT}.tooltip",
        ),
        ParamDescriptor(
            _P_PLATEAU_SIZE, ParamType.INT, default=0, min=0, max=100_000,
            title_key=f"{prefix}.{_P_PLATEAU_SIZE}",
            tooltip_key=f"{prefix}.{_P_PLATEAU_SIZE}.tooltip",
        ),
        ParamDescriptor(
            _P_MAX_POINTS, ParamType.INT, default=_MAX_POINTS_DEFAULT,
            min=1, max=_MAX_POINTS_LIMIT,
            title_key=f"{prefix}.{_P_MAX_POINTS}",
            tooltip_key=f"{prefix}.{_P_MAX_POINTS}.tooltip",
        ),
        ParamDescriptor(
            "show_labels", ParamType.BOOL, default=False,
            title_key=f"{prefix}.show_labels",
            tooltip_key=f"{prefix}.show_labels.tooltip",
        ),
    ]

def _register() -> None:
    _registry.register(AnalysisToolDescriptor(
        tool_id="search.peaks",
        category=ToolCategory.SEARCH,
        placement_type=PlacementType.ANNOTATION,
        title_key="analysis.tool.search.peaks.title",
        tooltip_key="analysis.tool.search.peaks.tooltip",
        param_schema=_search_params_schema("analysis.param.search.peaks"),
        strategy_factory=PeakSearchStrategy,
    ))
    _registry.register(AnalysisToolDescriptor(
        tool_id="search.valleys",
        category=ToolCategory.SEARCH,
        placement_type=PlacementType.ANNOTATION,
        title_key="analysis.tool.search.valleys.title",
        tooltip_key="analysis.tool.search.valleys.tooltip",
        param_schema=_search_params_schema("analysis.param.search.valleys"),
        strategy_factory=ValleySearchStrategy,
    ))


_register()