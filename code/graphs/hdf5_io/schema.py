"""Декларативные схемы HDF5-сериализации — единый источник правды.

Добавление нового поля модели = одна строка в соответствующей SPEC
плюс одно поле в dataclass'е. `HDF5Plot`, `HDF5Session`, `HDF5File`
читают/пишут строго по спеке и не знают о полях моделей напрямую.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .models import (
    AxisSettings, AxisStyle, CurveTreeItemData, FilterEntry,
    GraphFieldSettings, GraphStyle, LinearData, OscilloscopeFieldSettings,
    Plot, ProjectFile, Session, SessionParameters, Statistics,
    UncertaintyEntry,
)


@dataclass(frozen=True)
class Attr:
    name: str
    type: str = "str"
    default: Any = None
    hdf5_name: Optional[str] = None
    is_dataset: bool = False
    nested_schema: Optional["Schema"] = None

    def hdf5_key(self) -> str:
        return self.hdf5_name or self.name


@dataclass
class Schema:
    target: type
    attrs: list[Attr] = field(default_factory=list)

    def by_name(self) -> dict[str, Attr]:
        return {a.name: a for a in self.attrs}

    def hdf5_names(self) -> set[str]:
        return {a.hdf5_key() for a in self.attrs}


# ---------------------------------------------------------------------------
# Схемы моделей
# ---------------------------------------------------------------------------
GRAPH_STYLE_SPEC = Schema(GraphStyle, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("color", "color", "#ffffff"),
    Attr("line_style", "pen_style", None),
    Attr("line_width", "int", 1),
    Attr("symbol", "str_or_none", None),
    Attr("symbol_size", "int", 1),
    Attr("symbol_color", "color", "#ffffff"),
    Attr("fill_color", "color", "#ffffff"),
])

STATISTICS_SPEC = Schema(Statistics, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("mean", "float", 0.0),
    Attr("median", "float", 0.0),
    Attr("mode", "float", 0.0),
    Attr("std_dev", "float", 0.0),
    Attr("count", "int", 0),
    Attr("min_x", "float", 0.0),
    Attr("max_x", "float", 0.0),
    Attr("min_y", "float", 0.0),
    Attr("max_y", "float", 0.0),
])

FILTER_ENTRY_SPEC = Schema(FilterEntry, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("filter_type", "str", ""),
    Attr("params", "json", {}),
    Attr("enabled", "bool", True),
])

CURVE_TREE_ITEM_DATA_SPEC = Schema(CurveTreeItemData, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("font_info", "str", "Italic,10"),
    Attr("color_info", "color", "#ff30ea"),
    Attr("col_font_info", "str", "15"),
    Attr("parameters", "json", {}),
])

LINEAR_DATA_SPEC = Schema(LinearData, [
    Attr("device", "str", ""),
    Attr("channel", "str", ""),
    Attr("curve_name", "str", ""),
    Attr("is_name_customized", "bool", False),
    Attr("number", "int_or_none", None),
    Attr("number_axis", "int_or_none", None),
    Attr("is_draw", "bool", False),
    Attr("is_curve_selected", "bool", False),
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("tip", "str", "linear"),
    Attr("raw_data_x", "ndarray", None, is_dataset=True),
    Attr("raw_data_y", "ndarray", None, is_dataset=True),
    Attr("filtered_x_data", "ndarray", None, is_dataset=True),
    Attr("filtered_y_data", "ndarray", None, is_dataset=True),
])

UNCERTAINTY_ENTRY_SPEC = Schema(UncertaintyEntry, [
    Attr("id", "str", ""),
    Attr("method", "str", "std"),
    Attr("params", "json", {}),
    Attr("active", "bool", True),
    Attr("style", "json", {}),
    Attr("x_err", "ndarray", None, is_dataset=True),
    Attr("y_err", "ndarray", None, is_dataset=True),
])

SESSION_PARAMETERS_SPEC = Schema(SessionParameters, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("uuid", "str", ""),
    Attr("experiment_date", "datetime", None),
    Attr("operator", "str", ""),
    Attr("comment", "str", ""),
])

SESSION_SPEC = Schema(Session, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("active_tab", "int", 0),
    Attr("show_only_active_curves", "bool", False),
    Attr("inspector_current_widget", "str", "no_selection"),
    Attr("inspector_curve_tab", "int", 0),
    Attr("inspector_no_selection_tab", "int", 0),
    Attr("active_analysis_tool", "str", ""),
    Attr("main_inf_lines", "json", []),
    Attr("osc_inf_lines", "json", []),
    Attr("osc_loop_inf_lines", "json", []),
])

PLOT_SPEC = Schema(Plot, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("status", "str", "active"),
    Attr("is_draw", "bool", False),
    Attr("is_gen", "bool", False),
    Attr("is_curve_selected", "bool", False),
    Attr("x_name", "str", ""),
    Attr("y_name", "str", ""),
    Attr("axis", "int_axis", 1),
    Attr("formula", "str", ""),
    Attr("source_curve_ids", "json", []),
])

PROJECT_FILE_SPEC = Schema(ProjectFile, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("version_app", "str", "undefined"),
    Attr("creation_date", "datetime", None),
    Attr("schema_version", "int", 0),
    Attr("session_order", "json", []),
    Attr("active_session_id", "str", ""),
])

# схема для группы «uncertainty» — там нет отдельной dataclass'ы, но
# default_style удобно хранить отдельным «псевдо-полем».
@dataclass
class UncertaintyStyleHolder:
    default_style: dict = field(default_factory=dict)
    extras: dict = field(default_factory=dict)

UNCERTAINTY_STYLE_SPEC = Schema(UncertaintyStyleHolder, [
    Attr("default_style", "json", {}),
])

AXIS_STYLE_SPEC = Schema(AxisStyle, [
    Attr("text_font", "str", "Arial,13,-1,5,50,0,0,0,0,0"),
    Attr("tick_font", "str", "Arial,10,-1,5,50,0,0,0,0,0"),
    Attr("color", "color", "#000000"),
])