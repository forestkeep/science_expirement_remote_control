from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from graphs.analysis.models import (
    AnalysisArtifact, AnnotationPayload, AttachedPayload, DomainPayload,
    OverlayPayload, UncertaintyPayload,
)
from .models import (
    AxisSettings, AxisStyle, CurveTreeItemData, DataManager, FieldSettings,
    FilterEntry, GraphFieldSettings, GraphStyle, LinearData,
    OscilloscopeFieldSettings, OscillogramData, ParameterData, Plot,
    ProjectFile, Session, SessionParameters, SessionUIState, Statistics,
    UncertaintyEntry,
)


@dataclass(frozen=True)
class Attr:
    name: str
    type: str = "str"
    default: Any = None
    hdf5_name: Optional[str] = None
    is_dataset: bool = False
    is_list: bool = False
    nested_schema: Optional["Schema"] = None
    mapping_schema: Optional["Schema"] = None

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


# =====================================================================
# Кривые / статистика / фильтры / uncertainty
# =====================================================================
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


# =====================================================================
# Uncertainty style holder
# =====================================================================
@dataclass
class UncertaintyStyleHolder:
    default_style: dict = field(default_factory=dict)
    extras: dict = field(default_factory=dict)


UNCERTAINTY_STYLE_SPEC = Schema(UncertaintyStyleHolder, [
    Attr("default_style", "json", {}),
])


# =====================================================================
# Field settings (бывший utils-механизм, теперь spec-driven)
# =====================================================================
AXIS_STYLE_SPEC = Schema(AxisStyle, [
    Attr("text_font", "str", "Arial,13,-1,5,50,0,0,0,0,0"),
    Attr("tick_font", "str", "Arial,10,-1,5,50,0,0,0,0,0"),
    Attr("color", "color", "#000000"),
])

AXIS_SETTINGS_SPEC = Schema(AxisSettings, [
    Attr("label", "str", ""),
    Attr("is_style_customized", "bool", False),
    Attr("is_inverted", "bool", False),
    Attr("is_visible", "bool", True),
    Attr("log_mode", "bool", False),
    Attr("auto_range", "bool", True),
    Attr("range", "tuple_float", None),
    Attr("custom_style", nested_schema=AXIS_STYLE_SPEC),
])

GRAPH_FIELD_SETTINGS_SPEC = Schema(GraphFieldSettings, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("title", "str", ""),
    Attr("background_color", "color", "#070707"),
    Attr("grid_enabled", "bool", True),
    Attr("x_grid_enabled", "bool", True),
    Attr("y_grid_enabled", "bool", True),
    Attr("grid_color", "color", "#CCCCCC"),
    Attr("grid_alpha", "float", 0.5),
    Attr("common_axis_style", nested_schema=AXIS_STYLE_SPEC),
    Attr("axes", mapping_schema=AXIS_SETTINGS_SPEC),
    Attr("legend_enabled", "bool", True),
    Attr("legend_text_color", "color", "#DD1010"),
    Attr("legend_font", "str", "Arial,10,-1,5,50,0,0,0,0,0"),
    Attr("legend_pos", "tuple_float", (10.0, 10.0)),
    Attr("legend2_pos", "tuple_float", (50.0, 10.0)),
    Attr("antialiasing", "bool", True),
    Attr("is_second_axis_enabled", "bool", False),
    Attr("is_multiple_selection_enabled", "bool", False),
    Attr("is_multiple_y1_enabled", "bool", False),
    Attr("is_multiple_y2_enabled", "bool", False),
    Attr("applied_preset_name", "str", "—"),
    Attr("edit_all_axes", "bool", True),
])

OSCILLOSCOPE_FIELD_SETTINGS_SPEC = Schema(OscilloscopeFieldSettings, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("title", "str", ""),
    Attr("background_color", "color", "#000000"),
    Attr("grid_enabled", "bool", True),
    Attr("grid_color", "color", "#FFFFFF"),
    Attr("grid_alpha", "float", 0.5),
    Attr("common_axis_style", nested_schema=AXIS_STYLE_SPEC),
    Attr("axes", mapping_schema=AXIS_SETTINGS_SPEC),
    Attr("legend_enabled", "bool", True),
    Attr("legend_text_color", "color", "#F00B0B"),
    Attr("legend_font", "str", "Arial,10,-1,5,50,0,0,0,0,0"),
    Attr("antialiasing", "bool", True),
])

FIELD_SETTINGS_SPEC = Schema(FieldSettings, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("graph_field", nested_schema=GRAPH_FIELD_SETTINGS_SPEC),
    Attr("oscilloscope_field", nested_schema=OSCILLOSCOPE_FIELD_SETTINGS_SPEC),
])


# =====================================================================
# Session / UI state / project file
# =====================================================================
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
])

SESSION_UI_STATE_SPEC = Schema(SessionUIState, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("active_tab", "int", 0),
    Attr("show_only_active_curves", "bool", False),
    Attr("inspector_current_widget", "str", "no_selection"),
    Attr("inspector_curve_tab", "int", 0),
    Attr("inspector_no_selection_tab", "int", 0),
    Attr("active_analysis_tool", "str", ""),
    Attr("main_inf_lines", "json", [], is_list=True),
    Attr("osc_inf_lines", "json", [], is_list=True),
    Attr("osc_loop_inf_lines", "json", [], is_list=True),
    Attr("applied_preset_name", "str", "—"),
    Attr("edit_all_axes", "bool", True),
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


# =====================================================================
# Data manager (бывший BaseHDF5Entity/HDF5OscillogramData)
# =====================================================================
OSCILLOGRAM_DATA_SPEC = Schema(OscillogramData, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("device", "str", ""),
    Attr("channel", "str", ""),
    Attr("parameter", "str", ""),
    Attr("time_values", "ndarray", None, is_dataset=True),
    Attr("data_values", "ndarray", None, is_dataset=True),
])

PARAMETER_DATA_SPEC = Schema(ParameterData, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("device", "str", ""),
    Attr("channel", "str", ""),
    Attr("parameter", "str", ""),
    Attr("time_values", "ndarray", None, is_dataset=True),
    Attr("data_values", "ndarray", None, is_dataset=True),
])

DATA_MANAGER_SPEC = Schema(DataManager, [
    Attr("name", "str", ""),
    Attr("description", "str", ""),
    Attr("oscillogram_data", mapping_schema=OSCILLOGRAM_DATA_SPEC),
    Attr("parameter_data", mapping_schema=PARAMETER_DATA_SPEC,
         hdf5_name="parameters_data"),
])


# =====================================================================
# Analysis payloads / artifact
# =====================================================================
OVERLAY_PAYLOAD_SPEC = Schema(OverlayPayload, [
    Attr("kind", "str", "overlay"),
    Attr("x", "ndarray", None, is_dataset=True, is_list=True),
    Attr("y", "ndarray", None, is_dataset=True, is_list=True),
    Attr("style_hint", "json", {}),
])

ATTACHED_PAYLOAD_SPEC = Schema(AttachedPayload, [
    Attr("kind", "str", "attached"),
    Attr("x", "ndarray", None, is_dataset=True, is_list=True),
    Attr("y", "ndarray", None, is_dataset=True, is_list=True),
    Attr("y_label", "str", ""),
    Attr("panel_title", "str", ""),
])

DOMAIN_PAYLOAD_SPEC = Schema(DomainPayload, [
    Attr("kind", "str", "domain"),
    Attr("x", "ndarray", None, is_dataset=True, is_list=True),
    Attr("y", "ndarray", None, is_dataset=True, is_list=True),
    Attr("x_label", "str", ""),
    Attr("y_label", "str", ""),
    Attr("tab_title", "str", ""),
])

ANNOTATION_PAYLOAD_SPEC = Schema(AnnotationPayload, [
    Attr("kind", "str", "annotation"),
    Attr("points", "json", [], is_list=True),
    Attr("label", "str", ""),
])

UNCERTAINTY_PAYLOAD_SPEC = Schema(UncertaintyPayload, [
    Attr("kind", "str", "uncertainty"),
    Attr("x_err", "ndarray", None, is_dataset=True),
    Attr("y_err", "ndarray", None, is_dataset=True),
    Attr("method", "str", ""),
    Attr("params", "json", {}),
])

ANALYSIS_ARTIFACT_SPEC = Schema(AnalysisArtifact, [
    Attr("id", "str", ""),
    Attr("tool_id", "str", ""),
    Attr("source_curve_ids", "json", []),
    Attr("params", "json", {}),
    Attr("placement_type", "str", "overlay"),
    Attr("visibility", "bool", True),
    Attr("order_index", "int", 0),
    Attr("created_at", "datetime", None),
    Attr("preset_id", "str_or_none", None),
    Attr("active_uncertainty_id", "str_or_none", None),
    Attr("description", "str", ""),
    Attr("leader_curve_id", "str_or_none", None),
])