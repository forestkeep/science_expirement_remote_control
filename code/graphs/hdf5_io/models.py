"""Модели данных HDF5-сериализации.

`BaseModel` содержит поле `extras` — сюда при чтении складываются
неизвестные атрибуты, при записи они возвращаются обратно. Это
обеспечивает forward/backward-совместимость без потери данных.

`Plot.from_core` / `Plot.to_core` — единственное место конверсии
между `linearData` и `Plot`; адаптеры превращаются в тонких делегатов.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PyQt5 import QtCore

from .migrations import CURRENT_SCHEMA_VERSION


@dataclass
class BaseModel:
    name: str = ""
    description: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphStyle(BaseModel):
    color: str = "#ffffff"
    line_style: Any = QtCore.Qt.SolidLine          # Qt.PenStyle — кодек сериализует
    line_width: int = 1
    symbol: Optional[str] = None
    symbol_size: int = 1
    symbol_color: str = "#ffffff"
    fill_color: str = "#ffffff"

    @classmethod
    def from_core(cls, style) -> "GraphStyle":
        if style is None:
            return cls()
        return cls(
            color=style.color or "#ffffff",
            line_style=style.line_style if style.line_style is not None
                       else QtCore.Qt.SolidLine,
            line_width=int(style.line_width or 1),
            symbol=style.symbol if style.symbol not in (None, "", "None") else None,
            symbol_size=int(style.symbol_size or 1),
            symbol_color=style.symbol_color or "#ffffff",
            fill_color=style.fill_color or "#ffffff",
        )


@dataclass
class Statistics(BaseModel):
    mean: float = 0.0
    median: float = 0.0
    std_dev: float = 0.0
    mode: float = 0.0
    count: int = 0
    min_x: float = 0.0
    max_x: float = 0.0
    min_y: float = 0.0
    max_y: float = 0.0


@dataclass
class FilterEntry(BaseModel):
    filter_type: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class UncertaintyEntry(BaseModel):
    id: str = ""
    method: str = "std"
    params: Dict[str, Any] = field(default_factory=dict)
    x_err: Optional[np.ndarray] = None
    y_err: Optional[np.ndarray] = None
    active: bool = True
    style: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CurveTreeItemData(BaseModel):
    parameters: Dict[str, Any] = field(default_factory=dict)
    font_info: str = "Italic,10"
    color_info: str = "#ff30ea"
    col_font_info: str = "15"

    @classmethod
    def from_core(cls, tree_item, description: str) -> "CurveTreeItemData":
        font_info = "Italic,10"
        col_font_info = "15"
        color_info = "#ff30ea"
        if tree_item is not None:
            if hasattr(tree_item, "font"):
                font_info = f"Italic,{tree_item.font.pointSize()}"
            if hasattr(tree_item, "col_font"):
                col_font_info = f"{tree_item.col_font.pointSize()}"
            fg = tree_item.foreground(1) if hasattr(tree_item, "foreground") else None
            if fg is not None:
                color_info = fg.color().name()
        return cls(
            name="",
            description=description or "",
            font_info=font_info,
            color_info=color_info,
            col_font_info=col_font_info,
            parameters=dict(getattr(tree_item, "parameters", {}) or {}),
        )


@dataclass
class LinearData(BaseModel):
    device: str = ""
    channel: str = ""
    curve_name: str = ""
    is_name_customized: bool = False
    number: Optional[int] = None
    number_axis: Optional[int] = None
    is_draw: bool = False
    is_curve_selected: bool = False
    raw_data_x: np.ndarray = field(default_factory=lambda: np.empty(0))
    raw_data_y: np.ndarray = field(default_factory=lambda: np.empty(0))
    filtered_x_data: np.ndarray = field(default_factory=lambda: np.empty(0))
    filtered_y_data: np.ndarray = field(default_factory=lambda: np.empty(0))
    tree_item_data: CurveTreeItemData = field(default_factory=CurveTreeItemData)
    tip: str = "linear"

    @classmethod
    def from_core(cls, core_plot) -> "LinearData":
        tree_item = getattr(core_plot, "tree_item", None)
        desc = tree_item.get_description() if tree_item is not None else ""
        params = dict(getattr(tree_item, "parameters", {}) or {}) if tree_item is not None else {}
        tip = params.get("tip") or "linear"
        return cls(
            device=core_plot.device or "",
            channel=core_plot.ch or "",
            curve_name=core_plot.curve_name or "",
            is_name_customized=bool(getattr(core_plot, "is_name_curve_customized", False)),
            number=getattr(core_plot, "number", None),
            number_axis=getattr(core_plot, "number_axis", None),
            is_draw=bool(core_plot.is_draw),
            is_curve_selected=bool(core_plot.is_curve_selected),
            raw_data_x=np.asarray(core_plot.raw_data_x),
            raw_data_y=np.asarray(core_plot.raw_data_y),
            filtered_x_data=np.asarray(core_plot.filtered_x_data),
            filtered_y_data=np.asarray(core_plot.filtered_y_data),
            tree_item_data=CurveTreeItemData.from_core(tree_item, desc or ""),
            tip=tip,
        )


@dataclass
class Plot(BaseModel):
    status: str = "active"
    style: GraphStyle = field(default_factory=GraphStyle)
    statistics: Statistics = field(default_factory=Statistics)
    history: List[FilterEntry] = field(default_factory=list)
    linear_data: LinearData = field(default_factory=LinearData)
    axis: int = 1
    is_draw: bool = False
    is_curve_selected: bool = False
    is_gen: bool = False
    x_name: str = ""
    y_name: str = ""
    uncertainty_records: List[UncertaintyEntry] = field(default_factory=list)
    uncertainty_style: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # core → model
    # ------------------------------------------------------------------
    @classmethod
    def from_core(cls, core_plot) -> "Plot":
        if hasattr(core_plot, "ensure_stats_fresh"):
            core_plot.ensure_stats_fresh()

        params = getattr(core_plot.tree_item, "parameters", {}) or {}
        stats = Statistics(
            mean=params.get("mean", 0.0) or 0.0,
            median=params.get("median", 0.0) or 0.0,
            std_dev=params.get("std", 0.0) or 0.0,
        )

        history = [
            FilterEntry(
                filter_type=f.filter_type,
                params=dict(f.params or {}),
                enabled=bool(getattr(f, "enabled", True)),
            )
            for f in core_plot.filters_history
        ]

        uncertainty_records = []
        uncertainty_style: Dict[str, Any] = {}
        store = getattr(core_plot, "store", None)
        if store is not None:
            uncertainty_style = dict(getattr(store, "uncertainty_style", {}) or {})
            active_ids = set(getattr(store, "active_uncertainty_ids", set()) or set())
            for rec in getattr(store, "uncertainty_records", []) or []:
                uncertainty_records.append(UncertaintyEntry(
                    id=str(getattr(rec, "id", "")),
                    method=str(getattr(rec, "method", "std")),
                    params=dict(getattr(rec, "params", {}) or {}),
                    x_err=getattr(rec, "x_err", None),
                    y_err=getattr(rec, "y_err", None),
                    active=(getattr(rec, "id", None) in active_ids),
                    style=dict(getattr(rec, "style", {}) or {}),
                ))

        rel = core_plot.rel_data
        return cls(
            name=core_plot.curve_name or "",
            description="",
            status="active",
            style=GraphStyle.from_core(core_plot.saved_style),
            statistics=stats,
            history=history,
            linear_data=LinearData.from_core(core_plot),
            axis=int(core_plot.number_axis or 1),
            is_draw=bool(core_plot.is_draw),
            is_curve_selected=bool(core_plot.is_curve_selected),
            is_gen=bool(getattr(rel, "is_gen", False)),
            x_name=rel.x_root_name,
            y_name=rel.y_root_name,
            uncertainty_records=uncertainty_records,
            uncertainty_style=uncertainty_style,
        )

    # ------------------------------------------------------------------
    # model → core
    # ------------------------------------------------------------------
    def to_core(self, alias_manager, filter_instance):
        from graphs.core.curve_data import linearData, LineStyle
        from graphs.core.dataManager import measTimeData, relationData
        from graphs.core.filters_instance_class import FilterCommand
        from graphs.analysis.uncertainty import UncertaintyRecord
        from PyQt5.QtWidgets import QApplication

        if self.linear_data is None:
            raise ValueError(f"plot {self.name!r} has no linear_data")

        ld = self.linear_data

        def _strip_prefix(full, dev, ch):
            prefix = (dev or "") + (ch or "")
            if prefix and full and full.startswith(prefix):
                return full[len(prefix):]
            return full or ""

        x_dev, x_ch = ld.device or "", ld.channel or ""
        y_dev, y_ch = x_dev, x_ch
        x_param = _strip_prefix(self.x_name or "", x_dev, x_ch)
        y_param = _strip_prefix(self.y_name or "", y_dev, y_ch)

        x_meas = measTimeData(
            device=x_dev, ch=x_ch, param=x_param,
            par_val=ld.raw_data_x,
            num_or_time=np.arange(len(ld.raw_data_x)),
        )
        y_meas = measTimeData(
            device=y_dev, ch=y_ch, param=y_param,
            par_val=ld.raw_data_y,
            num_or_time=np.arange(len(ld.raw_data_y)),
        )
        rel = relationData(x_meas, y_meas, is_gen=bool(self.is_gen))
        new_data = linearData(data=rel, alias_manager=alias_manager)

        new_data.device = ld.device
        new_data.channel = ld.channel
        new_data.number = ld.number

        new_data.store.raw_data_x = np.asarray(ld.raw_data_x)
        new_data.store.raw_data_y = np.asarray(ld.raw_data_y)
        new_data.store.filtered_x_data = np.asarray(ld.filtered_x_data)
        new_data.store.filtered_y_data = np.asarray(ld.filtered_y_data)
        new_data.store._filtered_dirty = False

        style = LineStyle.from_graph_style(self.style)
        new_data.presenter.saved_style = style
        new_data.presenter.preselection_style = style

        for f in self.history:
            new_data.store.filters_history.append(FilterCommand(
                filter_type=f.filter_type,
                params=dict(f.params or {}),
                filters_instance=filter_instance,
                enabled=bool(getattr(f, "enabled", True)),
            ))

        if ld.is_name_customized:
            new_data.change_name(ld.curve_name)
        else:
            new_data.reset_name()

        # tip: единый источник правды — LinearData.tip, но пишется и в
        # tree_item.parameters, чтобы старый код видел его там же.
        new_data.tree_item.parameters["tip"] = ld.tip
        if ld.tree_item_data is not None:
            new_data.tree_item.parameters.update(ld.tree_item_data.parameters or {})

        desc = (ld.tree_item_data.description if ld.tree_item_data else "") or ""
        if desc:
            block_name = QApplication.translate("GraphWindow", "Разное")
            key = QApplication.translate("GraphWindow", "Описание")
            if not new_data.tree_item.update_block_data(block_name, {key: desc}):
                new_data.tree_item.add_new_block(block_name, {key: desc})

        store = new_data.store
        store.uncertainty_style = dict(self.uncertainty_style or {})
        for entry in self.uncertainty_records or []:
            kwargs = dict(
                method=entry.method or "std",
                params=dict(entry.params or {}),
                x_err=entry.x_err,
                y_err=entry.y_err,
                style=dict(entry.style or {}),
            )
            if entry.id:
                kwargs["id"] = entry.id
            rec = UncertaintyRecord(**kwargs)
            store.uncertainty_records.append(rec)
            if entry.active:
                store.active_uncertainty_ids.add(rec.id)
        if store.uncertainty_records and hasattr(new_data.presenter, "set_error_bars"):
            new_data.presenter.set_error_bars(store.active_uncertainty_records())

        return new_data


# ---------------------------------------------------------------------------
# Вспомогательные модели
# ---------------------------------------------------------------------------
@dataclass
class AxisStyle:
    text_font: str = "Arial,13,-1,5,50,0,0,0,0,0"
    tick_font: str = "Arial,10,-1,5,50,0,0,0,0,0"
    color: str = "#000000"

    @classmethod
    def from_qfont_color(cls, text_font, tick_font, color) -> "AxisStyle":
        def f_to_s(f):
            return f.toString() if hasattr(f, "toString") else str(f)

        def c_to_s(c):
            if hasattr(c, "name"):
                return c.name()
            if isinstance(c, (tuple, list)):
                return f"#{int(c[0]):02x}{int(c[1]):02x}{int(c[2]):02x}"
            return str(c)

        return cls(f_to_s(text_font), f_to_s(tick_font), c_to_s(color))


@dataclass
class AxisSettings:
    label: str = ""
    is_style_customized: bool = False
    is_inverted: bool = False
    is_visible: bool = True
    log_mode: bool = False
    auto_range: bool = True
    range: Optional[Tuple[float, float]] = None
    custom_style: AxisStyle = field(default_factory=AxisStyle)
    current_style_type: str = field(default="common", init=False)


@dataclass
class GraphFieldSettings:
    title: str = ""
    background_color: str = "#070707"
    grid_enabled: bool = True
    x_grid_enabled: bool = True
    y_grid_enabled: bool = True
    grid_color: str = "#CCCCCC"
    grid_alpha: float = 0.5
    common_axis_style: AxisStyle = field(default_factory=AxisStyle)
    axes: Dict[str, AxisSettings] = field(default_factory=dict)
    legend_enabled: bool = True
    legend_text_color: str = "#DD1010"
    legend_font: str = "Arial,10,-1,5,50,0,0,0,0,0"
    legend_pos: Tuple[float, float] = (10.0, 10.0)
    legend2_pos: Tuple[float, float] = (50.0, 10.0)
    antialiasing: bool = True
    is_second_axis_enabled: bool = False
    is_multiple_selection_enabled: bool = False
    is_multiple_y1_enabled: bool = False
    is_multiple_y2_enabled: bool = False

    def __post_init__(self):
        if not self.axes:
            self.axes = {
                "left": AxisSettings(label="Y"),
                "bottom": AxisSettings(label="X"),
                "right": AxisSettings(label="Y2", is_visible=False),
            }


@dataclass
class OscilloscopeFieldSettings(BaseModel):
    title: str = ""
    background_color: str = "#000000"
    grid_enabled: bool = True
    grid_color: str = "#FFFFFF"
    grid_alpha: float = 0.5
    common_axis_style: AxisStyle = field(default_factory=AxisStyle)
    axes: Dict[str, AxisSettings] = field(default_factory=dict)
    legend_enabled: bool = True
    legend_text_color: str = "#F00B0B"
    legend_font: str = "Arial,10,-1,5,50,0,0,0,0,0"
    antialiasing: bool = True

    def __post_init__(self):
        if not self.axes:
            self.axes = {
                "left": AxisSettings(label="Y"),
                "bottom": AxisSettings(label="X"),
                "right": AxisSettings(label="Y2", is_visible=False),
            }


@dataclass
class FieldSettings(BaseModel):
    graph_field: GraphFieldSettings = field(default_factory=GraphFieldSettings)
    oscilloscope_field: OscilloscopeFieldSettings = field(default_factory=OscilloscopeFieldSettings)


@dataclass
class OscillogramData(BaseModel):
    device: str = ""
    channel: str = ""
    parameter: str = ""
    time_values: np.ndarray = field(default_factory=lambda: np.empty(0))
    data_values: np.ndarray = field(default_factory=lambda: np.empty(0))


@dataclass
class ParameterData(BaseModel):
    device: str = ""
    channel: str = ""
    parameter: str = ""
    time_values: np.ndarray = field(default_factory=lambda: np.empty(0))
    data_values: np.ndarray = field(default_factory=lambda: np.empty(0))


@dataclass
class DataManager(BaseModel):
    oscillogram_data: Dict[str, OscillogramData] = field(default_factory=dict)
    parameter_data: Dict[str, ParameterData] = field(default_factory=dict)


@dataclass
class SessionParameters(BaseModel):
    uuid: str = ""
    experiment_date: Optional[datetime] = None
    operator: str = ""
    comment: str = ""


@dataclass
class Session(BaseModel):
    parameters: SessionParameters = field(default_factory=SessionParameters)
    field_settings: FieldSettings = field(default_factory=FieldSettings)
    data_manager: DataManager = field(default_factory=DataManager)
    plots: Dict[str, Plot] = field(default_factory=dict)
    analysis_artifacts: list = field(default_factory=list)
    helpers: list = field(default_factory=list)


@dataclass
class ProjectFile(BaseModel):
    version_app: str = "undefined"
    creation_date: datetime = field(default_factory=datetime.now)
    schema_version: int = CURRENT_SCHEMA_VERSION
    sessions: Dict[str, Session] = field(default_factory=dict)
    aliases: Dict[str, str] = field(default_factory=dict)