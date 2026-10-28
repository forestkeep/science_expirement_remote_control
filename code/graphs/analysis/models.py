"""Модели данных подсистемы анализа: артефакты, дескрипторы, payload'ы."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class PlacementType(Enum):
    OVERLAY = "overlay"
    ATTACHED = "attached"
    DOMAIN = "domain"
    ANNOTATION = "annotation"
    UNCERTAINTY = "uncertainty"


class ToolCategory(Enum):
    FITTING = "A"
    SEARCH = "B"
    DIFFERENTIAL = "C"
    SPECTRAL = "D"
    STATISTICS = "E"


class ParamType(Enum):
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    CHOICE = "choice"
    TEXT = "text"


@dataclass
class ParamDescriptor:
    name: str
    type: ParamType
    default: Any = None
    title_key: str = ""
    tooltip_key: str = ""
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    choices: List[Any] = field(default_factory=list)
    depends_on: Optional[Dict[str, Any]] = None


@dataclass
class OverlayPayload:
    kind: str = "overlay"
    x: Any = None
    y: Any = None
    style_hint: Dict[str, Any] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttachedPayload:
    kind: str = "attached"
    x: Any = None
    y: Any = None
    y_label: str = ""
    panel_title: str = ""
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainPayload:
    kind: str = "domain"
    x: Any = None
    y: Any = None
    x_label: str = ""
    y_label: str = ""
    tab_title: str = ""
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnnotationPayload:
    kind: str = "annotation"
    points: List[Dict[str, Any]] = field(default_factory=list)
    label: str = ""
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UncertaintyPayload:
    kind: str = "uncertainty"
    x_err: Any = None
    y_err: Any = None
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceSnapshot:
    root_name: str
    x: Any = None
    y: Any = None
    x_name: str = ""
    y_name: str = ""
    device: str = ""
    ch: str = ""
    number_axis: int = 1
    saved_style: Any = None
    curve_name: str = ""


@dataclass
class AnalysisArtifact:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tool_id: str = ""
    source_curve_ids: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    placement_type: PlacementType = PlacementType.OVERLAY
    payload: Any = None
    visibility: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    order_index: int = 0
    preset_id: Optional[str] = None
    active_uncertainty_id: Optional[str] = None
    description: str = ""
    handle: Any = None
    leader_curve_id: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)

    def clone_with_new_id(self) -> "AnalysisArtifact":
        import copy
        new = copy.copy(self)
        new.id = uuid.uuid4().hex
        new.handle = None
        new.created_at = datetime.now()
        return new


@dataclass
class AnalysisToolDescriptor:
    tool_id: str
    category: ToolCategory
    placement_type: PlacementType
    title_key: str
    tooltip_key: str = ""
    icon_name: str = ""
    param_schema: List[ParamDescriptor] = field(default_factory=list)
    strategy_factory: Optional[Callable[[], Any]] = None
    requires_review_mode: bool = True
    supports_multi_source: bool = True
    is_async: bool = False


# ---------------------------------------------------------------------
# Локализация. Русский текст — источник перевода.
# ---------------------------------------------------------------------
_RU_TITLES = {
    "analysis.tool.fit.linear.title":        "Линейная интерполяция",
    "analysis.tool.fit.linear.tooltip":      "Прямая y = k·x + b",
    "analysis.tool.fit.polynomial.title":    "Полиномиальная интерполяция",
    "analysis.tool.fit.polynomial.tooltip":  "Полином степени 2–6",
    "analysis.tool.fit.gaussian.title":      "Гауссова интерполяция",
    "analysis.tool.fit.gaussian.tooltip":    "Колоколообразная кривая (пики)",
    "analysis.tool.fit.lorentz.title":       "Лоренцева интерполяция",
    "analysis.tool.fit.lorentz.tooltip":     "Лоренцева кривая (пики)",

    "analysis.tool.search.peaks.title":      "Поиск максимумов",
    "analysis.tool.search.peaks.tooltip":    "Локальные максимумы",
    "analysis.tool.search.valleys.title":    "Поиск минимумов",
    "analysis.tool.search.valleys.tooltip":  "Локальные минимумы",

    "analysis.param.search.peaks.min_prominence":   "Мин. prominence пика",
    "analysis.param.search.valleys.min_prominence": "Мин. prominence впадины",
    "analysis.param.search.peaks.min_width":        "Мин. ширина пика",
    "analysis.param.search.valleys.min_width":      "Мин. ширина впадины",
    "analysis.param.search.peaks.rel_height":       "Отн. высота для ширины",
    "analysis.param.search.valleys.rel_height":     "Отн. высота для ширины",
    "analysis.param.search.peaks.plateau_size":     "Мин. размер плато",
    "analysis.param.search.valleys.plateau_size":   "Мин. размер плато",
    "analysis.param.search.peaks.show_labels":      "Показывать значения на графике",
    "analysis.param.search.valleys.show_labels":    "Показывать значения на графике",

    "analysis.param.search.peaks.min_prominence.tooltip":
        "Минимальная prominence пика над соседними минимумами. "
        "0 — без ограничения. Лучший фильтр против шума.",
    "analysis.param.search.valleys.min_prominence.tooltip":
        "Минимальная prominence впадины над соседними максимумами. "
        "0 — без ограничения. Лучший фильтр против шума.",
    "analysis.param.search.peaks.min_width.tooltip":
        "Минимальная ширина пика в единицах X. 0 — без ограничения.",
    "analysis.param.search.valleys.min_width.tooltip":
        "Минимальная ширина впадины в единицах X. 0 — без ограничения.",
    "analysis.param.search.peaks.rel_height.tooltip":
        "Относительная высота (0..1) от prominence, на которой меряется ширина. "
        "0.5 — FWHM. Используется только при min_width > 0.",
    "analysis.param.search.valleys.rel_height.tooltip":
        "Относительная высота (0..1) от prominence, на которой меряется ширина впадины.",
    "analysis.param.search.peaks.plateau_size.tooltip":
        "Минимальный размер плоской вершины пика в точках. 0 — без ограничения.",
    "analysis.param.search.valleys.plateau_size.tooltip":
        "Минимальный размер плоского дна впадины в точках. 0 — без ограничения.",
    "analysis.param.search.peaks.show_labels.tooltip":
        "Показывать подписи x=…, y=… над каждым пиком.",
    "analysis.param.search.valleys.show_labels.tooltip":
        "Показывать подписи x=…, y=… над каждой впадиной.",

    "analysis.param.search.peaks.max_points":   "Макс. точек на графике",
    "analysis.param.search.valleys.max_points": "Макс. точек на графике",
    "analysis.param.search.peaks.max_points.tooltip":
        "Если найдено больше — на графике остаются самые значимые по prominence. "
        "Увеличивает нагрузку на отрисовку при больших значениях.",
    "analysis.param.search.valleys.max_points.tooltip":
        "Если найдено больше — на графике остаются самые значимые по prominence.",

    "analysis.param.search.peaks.show_labels":   "Подписи значений",
    "analysis.param.search.valleys.show_labels": "Подписи значений",
    "analysis.param.search.peaks.show_labels.tooltip":
        "Показывать x=…, y=… над точками. Включается только для результатов "
        "не больше 30 точек — иначе это сильно замедляет отрисовку.",
    "analysis.param.search.valleys.show_labels.tooltip":
        "Показывать x=…, y=… над точками (до 30 точек).",

    "analysis.param.search.peaks.min_height.tooltip":
        "Минимальная высота пика в единицах Y. 0 — без ограничения.",
    "analysis.param.search.valleys.min_height.tooltip":
        "Минимальная глубина впадины в единицах Y. 0 — без ограничения.",
    "analysis.param.search.peaks.min_distance.tooltip":
        "Минимальное расстояние между соседними пиками в точках индекса. "
        "0/1 — без ограничения.",
    "analysis.param.search.valleys.min_distance.tooltip":
        "Минимальное расстояние между соседними впадинами в точках индекса. "
        "0/1 — без ограничения.",

    "analysis.tool.diff.derivative.title":   "Производная",
    "analysis.tool.diff.derivative.tooltip": "Численная производная dY/dX",
    "analysis.tool.diff.integral.title":     "Интеграл",
    "analysis.tool.diff.integral.tooltip":   "Численный интеграл ∫Y dX",

    "analysis.tool.spectral.fft.title":      "Спектр (FFT)",
    "analysis.tool.spectral.fft.tooltip":    "Быстрое преобразование Фурье",
    "analysis.tool.spectral.autocorr.title": "Автокорреляция",
    "analysis.tool.spectral.autocorr.tooltip":"Автокорреляционная функция",

    "analysis.tool.uncertainty.estimate.title":   "Погрешности точек",
    "analysis.tool.uncertainty.estimate.tooltip": "Полосы погрешностей (error bars) на точках кривой",

    "analysis.param.fit.polynomial.degree":        "Степень полинома",
    "analysis.param.search.peaks.min_height":      "Мин. высота пика",
    "analysis.param.search.peaks.min_distance":    "Мин. расстояние между пиками",
    "analysis.param.search.valleys.min_height":    "Мин. глубина впадины",
    "analysis.param.search.valleys.min_distance":  "Мин. расстояние между впадинами",
    "analysis.param.diff.window":                  "Окно сглаживания",
    "analysis.param.uncertainty.method":           "Метод оценки",
    "analysis.param.uncertainty.window":           "Окно усреднения",
    "analysis.param.uncertainty.level":            "Уровень доверия",
    "analysis.param.uncertainty.iterations":       "Число итераций",
    "analysis.param.uncertainty.y_err":            "Y-погрешность (вручную)",
    "analysis.param.fit.polynomial.degree.tooltip":
        "Степень аппроксимирующего полинома: 2 — парабола, 3 — кубическая, … до 6",

    "analysis.param.search.peaks.min_height.tooltip":
        "Минимальная высота пика (в единицах Y). 0 — без ограничения "
        "(находятся пики с любым Y, включая отрицательные).",
    "analysis.param.search.valleys.min_height.tooltip":
        "Минимальная глубина впадины (в единицах Y). 0 — без ограничения.",
    "analysis.param.search.peaks.min_distance.tooltip":
        "Минимальное расстояние между соседними пиками в точках индекса. "
        "1 — без ограничения.",
    "analysis.param.search.valleys.min_distance.tooltip":
        "Минимальное расстояние"
        " между соседними впадинами в точках индекса. "
        "1 — без ограничения.",

    "analysis.param.diff.window.tooltip":
        "Окно сглаживания производной. 0 или 1 — без сглаживания, >1 — скользящее среднее указанного размера",
    "analysis.param.uncertainty.method.tooltip":
        "Метод оценки погрешности: СКО, стандартная ошибка, доверительный интервал или бутстрап",
    "analysis.param.uncertainty.window.tooltip":
        "Размер локального окна усреднения. 0 — оценка по всей кривой",
    "analysis.param.uncertainty.level.tooltip":
        "Доверительный уровень (например, 0.95 для 95 %)",
    "analysis.param.uncertainty.iterations.tooltip":
        "Число бутстрап-итераций (10–5000)",
    "analysis.param.uncertainty.y_err.tooltip":
        "Фиксированное значение Y-погрешности для метода «Вручную»",

    "analysis.param.uncertainty.method.std":       "Стандартное отклонение (СКО)",
    "analysis.param.uncertainty.method.sem":       "Стандартная ошибка среднего",
    "analysis.param.uncertainty.method.ci95":      "Доверительный интервал 95 %",
    "analysis.param.uncertainty.method.bootstrap": "Бутстрап",
    "analysis.param.uncertainty.method.manual":    "Вручную (фиксированная)",
}


def tr_analysis(key: str, default: str = "") -> str:
    """Локализовать строку. Источник — русский текст (fallback)."""
    from PyQt5.QtWidgets import QApplication
    fallback = default or _RU_TITLES.get(key, key)
    return QApplication.translate("analysis", fallback)