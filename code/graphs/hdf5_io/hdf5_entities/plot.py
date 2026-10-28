"""Spec-driven HDF5-сущность одной кривой (Plot)."""
from __future__ import annotations

import logging

import h5py

from ..extras import read_attrs, write_attrs
from ..models import (
    CurveTreeItemData, FilterEntry, GraphStyle, LinearData, Plot,
    Statistics, UncertaintyEntry,
)
from ..schema import (
    CURVE_TREE_ITEM_DATA_SPEC, FILTER_ENTRY_SPEC, GRAPH_STYLE_SPEC,
    LINEAR_DATA_SPEC, PLOT_SPEC, STATISTICS_SPEC,
    UNCERTAINTY_ENTRY_SPEC, UNCERTAINTY_STYLE_SPEC, UncertaintyStyleHolder,
)

logger = logging.getLogger(__name__)


class HDF5Plot:
    def __init__(self, group: h5py.Group) -> None:
        self._group = group

    def write(self, plot: Plot) -> None:
        write_attrs(self._group, plot, PLOT_SPEC)

        if "style" in self._group:
            del self._group["style"]
        write_attrs(self._group.create_group("style"), plot.style, GRAPH_STYLE_SPEC)

        if "statistics" in self._group:
            del self._group["statistics"]
        write_attrs(
            self._group.create_group("statistics"), plot.statistics, STATISTICS_SPEC
        )

        if "history" in self._group:
            del self._group["history"]
        if plot.history:
            hg = self._group.create_group("history")
            for i, entry in enumerate(plot.history):
                write_attrs(hg.create_group(f"entry_{i}"), entry, FILTER_ENTRY_SPEC)

        if "uncertainty" in self._group:
            del self._group["uncertainty"]
        ug = self._group.create_group("uncertainty")
        holder = UncertaintyStyleHolder(
            default_style=dict(plot.uncertainty_style or {})
        )
        write_attrs(ug, holder, UNCERTAINTY_STYLE_SPEC)
        for i, entry in enumerate(plot.uncertainty_records or []):
            write_attrs(ug.create_group(f"u{i}"), entry, UNCERTAINTY_ENTRY_SPEC)

        if "linear_data" in self._group:
            del self._group["linear_data"]
        ld_group = self._group.create_group("linear_data")
        write_attrs(ld_group, plot.linear_data, LINEAR_DATA_SPEC)
        write_attrs(
            ld_group.create_group("tree_item_data"),
            plot.linear_data.tree_item_data, CURVE_TREE_ITEM_DATA_SPEC,
        )

    def read(self) -> Plot:
        values, extras = read_attrs(self._group, PLOT_SPEC)
        axis = values.get("axis", 1)

        plot = Plot(
            name=values.get("name", "") or "",
            description=values.get("description", "") or "",
            status=values.get("status", "active") or "active",
            is_draw=values.get("is_draw", False),
            is_gen=values.get("is_gen", False),
            is_curve_selected=values.get("is_curve_selected", False),
            x_name=values.get("x_name", "") or "",
            y_name=values.get("y_name", "") or "",
            axis=axis,
            extras=extras,
        )

        if "style" in self._group:
            s_values, s_extras = read_attrs(self._group["style"], GRAPH_STYLE_SPEC)
            plot.style = GraphStyle(**s_values, extras=s_extras)

        if "statistics" in self._group:
            s_values, s_extras = read_attrs(
                self._group["statistics"], STATISTICS_SPEC
            )
            plot.statistics = Statistics(**s_values, extras=s_extras)

        if "history" in self._group:
            hg = self._group["history"]
            for name in hg:
                e_values, e_extras = read_attrs(hg[name], FILTER_ENTRY_SPEC)
                if not e_values.get("params"):
                    e_values["params"] = self._read_legacy_params(hg[name])
                plot.history.append(FilterEntry(**e_values, extras=e_extras))

        if "uncertainty" in self._group:
            ug = self._group["uncertainty"]
            u_values, _ = read_attrs(ug, UNCERTAINTY_STYLE_SPEC)
            plot.uncertainty_style = dict(u_values.get("default_style") or {})
            for name in ug:
                if not name.startswith("u"):
                    continue
                e_values, e_extras = read_attrs(ug[name], UNCERTAINTY_ENTRY_SPEC)
                if not e_values.get("id"):
                    e_values["id"] = name
                plot.uncertainty_records.append(
                    UncertaintyEntry(**e_values, extras=e_extras)
                )

        if "linear_data" in self._group:
            ld_group = self._group["linear_data"]
            ld_values, ld_extras = read_attrs(ld_group, LINEAR_DATA_SPEC)
            ld_values["number_axis"] = axis
            plot.linear_data = LinearData(**ld_values, extras=ld_extras)

            if "tree_item_data" in ld_group:
                t_values, t_extras = read_attrs(
                    ld_group["tree_item_data"], CURVE_TREE_ITEM_DATA_SPEC
                )
                if not t_values.get("parameters"):
                    t_values["parameters"] = self._read_legacy_tree_params(
                        ld_group["tree_item_data"]
                    )
                plot.linear_data.tree_item_data = CurveTreeItemData(
                    **t_values, extras=t_extras
                )

            params = plot.linear_data.tree_item_data.parameters
            if "tip" not in params and plot.linear_data.tip:
                params["tip"] = plot.linear_data.tip
            if plot.linear_data.tip == "linear" and params.get("tip"):
                plot.linear_data.tip = params["tip"]
        else:
            plot.linear_data = LinearData(number_axis=axis)

        return plot

    def _read_legacy_params(self, entry_group) -> dict:
        from graphs.utils.parsing import to_best_number
        legacy = entry_group.get("params") if hasattr(entry_group, "get") else None
        if legacy is None:
            return {}
        return {k: to_best_number(legacy.attrs[k]) for k in legacy.attrs}

    def _read_legacy_tree_params(self, tree_group) -> dict:
        from graphs.utils.parsing import to_best_number
        legacy = tree_group.get("parameters") if hasattr(tree_group, "get") else None
        if legacy is None:
            return {}
        return {k: to_best_number(legacy.attrs[k]) for k in legacy.attrs}