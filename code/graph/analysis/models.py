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


@dataclass
class AttachedPayload:
    kind: str = "attached"
    x: Any = None
    y: Any = None
    y_label: str = ""
    panel_title: str = ""


@dataclass
class DomainPayload:
    kind: str = "domain"
    x: Any = None
    y: Any = None
    x_label: str = ""
    y_label: str = ""
    tab_title: str = ""


@dataclass
class AnnotationPayload:
    kind: str = "annotation"
    points: List[Dict[str, Any]] = field(default_factory=list)
    label: str = ""


@dataclass
class UncertaintyPayload:
    kind: str = "uncertainty"
    x_err: Any = None
    y_err: Any = None
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)


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
    handle: Any = None            # renderer handle (не сериализуется)
    leader_curve_id: Optional[str] = None

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
# Локализация. Русский текст — источник перевода для QApplication.translate.
# При наличии .qm файла перевод подхватится автоматически, иначе вернётся
# русский текст по умолчанию.
# ---------------------------------------------------------------------
_RU_TITLES = {
    # --- Интерполяция (показываются первыми в выпадающем списке) ---
    "analysis.tool.fit.linear.title":        "Линейная интерполяция",
    "analysis.tool.fit.linear.tooltip":      "Прямая y = k·x + b",
    "analysis.tool.fit.polynomial.title":    "Полиномиальная интерполяция",
    "analysis.tool.fit.polynomial.tooltip":  "Полином степени 2–6",
    "analysis.tool.fit.gaussian.title":      "Гауссова интерполяция",
    "analysis.tool.fit.gaussian.tooltip":    "Колоколообразная кривая (пики)",
    "analysis.tool.fit.lorentz.title":       "Лоренцева интерполяция",
    "analysis.tool.fit.lorentz.tooltip":     "Лоренцева кривая (пики)",

    # --- Поиск ---
    "analysis.tool.search.peaks.title":      "Поиск максимумов",
    "analysis.tool.search.peaks.tooltip":    "Локальные максимумы",
    "analysis.tool.search.valleys.title":    "Поиск минимумов",
    "analysis.tool.search.valleys.tooltip":  "Локальные минимумы",

    # --- Дифференциальные ---
    "analysis.tool.diff.derivative.title":   "Производная",
    "analysis.tool.diff.derivative.tooltip": "Численная производная dY/dX",
    "analysis.tool.diff.integral.title":     "Интеграл",
    "analysis.tool.diff.integral.tooltip":   "Численный интеграл ∫Y dX",

    # --- Спектральные ---
    "analysis.tool.spectral.fft.title":      "Спектр (FFT)",
    "analysis.tool.spectral.fft.tooltip":    "Быстрое преобразование Фурье",
    "analysis.tool.spectral.autocorr.title": "Автокорреляция",
    "analysis.tool.spectral.autocorr.tooltip":"Автокорреляционная функция",

    # --- Статистика ---
    "analysis.tool.uncertainty.estimate.title":   "Погрешности точек",
    "analysis.tool.uncertainty.estimate.tooltip": "Полосы погрешностей (error bars) на точках кривой",

    # --- Параметры ---
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

    # Подписи для выбора метода
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