# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

# graph/core/curve_data.py
"""Facade classes for curves.

``linearData`` and ``oscData`` compose a ``CurveDataStore`` (pure data)
with a ``CurvePresenter`` (visuals) and expose the historical public API.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from graph.core.curve_data_store import CurveDataStore, legendName
from graph.core.curve_presenter import CurvePresenter, LineStyle
from graph.core.dataManager import relationData
from graph.core.filters_instance_class import FilterCommand
from graph.core.selection_model import SelectionModel
from graph.core.statistics_calc import StatisticsCalculator, STATISTICS_DESCRIPTIONS
from graph.ui.tree_curves import CurveTreeItem

logger = logging.getLogger(__name__)

__all__ = ["linearData", "oscData", "hystLoop", "LineStyle", "legendName"]


# ====================================================================
# Facade: linearData
# ====================================================================
class linearData:
    """Backwards-compatible curve object composed of store + presenter."""

    def __init__(self, data: relationData, alias_manager,
                 selection_model: Optional[SelectionModel] = None) -> None:
        self.alias_manager = alias_manager
        self.store = CurveDataStore(data)
        self.presenter = CurvePresenter(self.store, selection_model=selection_model)

        # alias initial
        x_alias = alias_manager.get_alias(data.x_root_name)
        y_alias = alias_manager.get_alias(data.y_root_name)
        self.store.update_aliases(x_alias, y_alias)

        alias_manager.aliases_updated.connect(self._alias_changed)

        # tree_item belongs to the facade (needs the facade as curve_data_obj)
        self.presenter.tree_item = CurveTreeItem(curve_data_obj=self)
        self.presenter.tree_item.set_name(self.store.curve_name)

        # now that tree_item exists, hook stats recalculation
        self.store.on_changed(self._on_store_changed)
        self.recalc_stats_param()

    # ------------------------------------------------------------------
    # Data delegation
    # ------------------------------------------------------------------
    @property
    def rel_data(self): return self.store.rel_data

    @property
    def raw_data_x(self): return self.store.raw_data_x

    @property
    def raw_data_y(self): return self.store.raw_data_y

    @property
    def filtered_x_data(self): return self.store.filtered_x_data

    @filtered_x_data.setter
    def filtered_x_data(self, value): self.store.filtered_x_data = value

    @property
    def filtered_y_data(self): return self.store.filtered_y_data

    @filtered_y_data.setter
    def filtered_y_data(self, value): self.store.filtered_y_data = value

    @property
    def filters_history(self): return self.store.filters_history

    @property
    def curve_name(self): return self.store.curve_name

    @property
    def legend(self): return self.store.legend

    @property
    def is_name_curve_customized(self): return self.store.is_name_curve_customized

    @property
    def device(self): return self.store.device
    @device.setter
    def device(self, v): self.store.device = v

    @property
    def ch(self): return self.store.ch
    @ch.setter
    def ch(self, v): self.store.ch = v

    @property
    def channel(self): return self.store.ch
    @channel.setter
    def channel(self, v): self.store.ch = v

    @property
    def number(self): return self.store.number
    @number.setter
    def number(self, v): self.store.number = v

    # ------------------------------------------------------------------
    # Presentation delegation
    # ------------------------------------------------------------------
    @property
    def plot_items(self): return self.presenter.plot_items

    @property
    def tree_item(self): return self.presenter.tree_item
    @tree_item.setter
    def tree_item(self, v): self.presenter.tree_item = v

    @property
    def is_draw(self): return self.presenter.is_draw
    @is_draw.setter
    def is_draw(self, v): self.presenter.is_draw = v

    @property
    def is_curve_selected(self): return self.presenter.is_curve_selected
    @is_curve_selected.setter
    def is_curve_selected(self, v): self.presenter.is_curve_selected = v

    @property
    def number_axis(self): return self.presenter.number_axis
    @number_axis.setter
    def number_axis(self, v): self.presenter.number_axis = v

    @property
    def i_am_click_now(self): return self.presenter.i_am_click_now
    @i_am_click_now.setter
    def i_am_click_now(self, v): self.presenter.i_am_click_now = v

    @property
    def saved_style(self): return self.presenter.saved_style
    @saved_style.setter
    def saved_style(self, v): self.presenter.saved_style = v

    @property
    def clicked_style(self): return self.presenter.clicked_style

    @property
    def higlighted_flag(self): return self.presenter.higlighted_flag

    # ------------------------------------------------------------------
    # Actions: presentation
    # ------------------------------------------------------------------
    def add_to_graph(self, graph_field, legend_field, number_axis):
        self.presenter.add_to_graph(graph_field, legend_field, number_axis)

    def remove_from_graph(self, viewbox):
        self.presenter.remove_from_graph(viewbox)

    def remove_all_from_graphs(self):
        self.presenter.remove_all_from_graphs()

    def delete_curve_from_graph(self):
        self.presenter.delete_curve_from_graph()

    def update_all_plots_data(self):
        self.presenter.refresh()

    def change_style(self, new_style: LineStyle):
        self.presenter.change_style(new_style)
        self._notify_analysis_style_changed()

    def apply_style_to_all(self, style: LineStyle):
        self.presenter.apply_style_to_all(style)
        self._notify_analysis_style_changed()

    def _notify_analysis_style_changed(self):
        """Сообщить AnalysisController, что кривая сменила стиль.

        Вызывается из change_style / apply_style_to_all — то есть из всех
        путей изменения стиля: ChangeCurveStyleCommand, GraphCustomizer,
        вкладка «Стиль» в инспекторе.
        """
        session = getattr(self, "_main_class", None)
        if session is None:
            return
        ctrl = getattr(session, "analysis_controller", None)
        if ctrl is None:
            return
        try:
            ctrl.on_source_style_changed(self.store.rel_data.root_name)
        except Exception:
            logger.exception("_notify_analysis_style_changed failed")

    def on_plot_clicked(self, obj=None):
        self.presenter.on_plot_clicked(obj)

    def higlight_curve(self):
        self.presenter.higlight_curve()

    def unhiglight_curve(self):
        self.presenter.unhiglight_curve()

    def set_selection_callback(self, callback):
        """Legacy API; kept for compatibility. Model is now authoritative."""
        # do nothing: selection flows through SelectionModel

    def set_legend_name(self, name: str):
        self.presenter.set_legend_name(name)

    def attach_selection_model(self, model):
        self.presenter.attach_selection_model(model)

    def detach(self):
        try:
            self.alias_manager.aliases_updated.disconnect(self._alias_changed)
        except (TypeError, RuntimeError):
            pass
        self.presenter.detach()

    # ------------------------------------------------------------------
    # Actions: data
    # ------------------------------------------------------------------
    def change_name(self, name: str):
        self.store.change_name(name)

    def reset_name(self):
        self.store.reset_name()

    def setData(self, data: relationData):
        self.store.set_data(data)

    def set_raw_point(self, index: int, x=None, y=None):
        return self.store.set_raw_point(index, x=x, y=y)

    def set_filter(self, fc: FilterCommand):
        message = self.store.set_filter(fc)
        self._append_history_entry(fc, message)

    def delete_filter(self, fc: FilterCommand):
        self.store.delete_filter(fc)
        self._rebuild_history_block()

    def clear_filters(self):
        self.store.clear_filters()
        if self.tree_item is not None:
            self.tree_item.clear_history_block()

    def data_reset(self) -> bool:
        return self.store.data_reset()

    def stop_session(self):
        self.store.stop_session()
        self.recalc_stats_param()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def recalc_stats_param(self):
        if len(self.store.filtered_y_data) == 0:
            return
        y_series = pd.Series(self.store.filtered_y_data)
        stats = StatisticsCalculator._compute_column_statistics(
            y_series, list(STATISTICS_DESCRIPTIONS.keys())
        )
        params = {
            "min_x": np.nanmin(self.store.filtered_x_data) if len(self.store.filtered_x_data) else None,
            "max_x": np.nanmax(self.store.filtered_x_data) if len(self.store.filtered_x_data) else None,
            "name": self.store.curve_name,
            "tip": "linear",
        }
        params.update(stats)
        params["min_y"] = stats["min"]
        params["max_y"] = stats["max"]

        if self.tree_item is not None:
            self.tree_item.update_parameters(params)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_store_changed(self):
        try:
            self.recalc_stats_param()
        except Exception:
            logger.exception("linearData: stats recalculation failed")

    # ------------------------------------------------------------------
    # Visible window delegation
    # ------------------------------------------------------------------
    def set_num_points(self, value: int) -> None:
        self.presenter.set_num_points(value)

    def show_all_points(self, state: bool) -> None:
        self.presenter.show_all_points(state)

    def _alias_changed(self, original_name, old_alias, alias):
        new_x = self.store.rel_data.x_current_name
        new_y = self.store.rel_data.y_current_name
        if original_name == self.store.rel_data.x_root_name:
            new_x = alias
        if original_name == self.store.rel_data.y_root_name:
            new_y = alias
        self.store.update_aliases(new_x, new_y)

    def _append_history_entry(self, fc: FilterCommand, message: str):
        if self.tree_item is None:
            return
        self.tree_item.update_history_block(
            data={datetime.now().strftime("%H:%M:%S"): message},
            filter_command=fc,
        )

    def _rebuild_history_block(self):
        if self.tree_item is None:
            return
        self.tree_item.clear_history_block()
        for f in self.store.filters_history:
            self.tree_item.update_history_block(
                data={f.filter_type: str(f.params)},
                filter_command=f,
            )


# ====================================================================
# Facade: oscData (used by graphOsc — a different, simpler pattern)
# ====================================================================
class oscData:
    """Facade for oscillogram curves used in graphOsc."""

    def __init__(self, data: relationData) -> None:
        self.store = CurveDataStore(data)
        self.presenter = CurvePresenter(self.store, selection_model=None)
        self.store.curve_name = data.root_name
        self.store.legend.set_custom(self.store.curve_name)

        # attributes expected by graphOsc
        self.plot_obj = None
        self.saved_pen = None
        self.current_highlight = False

    # Data delegation
    @property
    def rel_data(self): return self.store.rel_data
    @property
    def raw_data_x(self): return self.store.raw_data_x
    @property
    def raw_data_y(self): return self.store.raw_data_y
    @property
    def filtered_x_data(self): return self.store.filtered_x_data
    @filtered_x_data.setter
    def filtered_x_data(self, v): self.store.filtered_x_data = v
    @property
    def filtered_y_data(self): return self.store.filtered_y_data
    @filtered_y_data.setter
    def filtered_y_data(self, v): self.store.filtered_y_data = v
    @property
    def curve_name(self): return self.store.curve_name
    @property
    def legend(self): return self.store.legend

    # Presentation delegation (only what graphOsc uses)
    @property
    def is_draw(self): return self.presenter.is_draw
    @is_draw.setter
    def is_draw(self, v): self.presenter.is_draw = v

    @property
    def plot_items(self): return self.presenter.plot_items

    @property
    def saved_style(self): return self.presenter.saved_style
    @saved_style.setter
    def saved_style(self, v): self.presenter.saved_style = v

    # graphOsc API
    def set_plot_obj(self, plot_obj, pen):
        self.plot_obj = plot_obj
        self.saved_pen = pen


# ====================================================================
# hystLoop — standalone, no longer inherits from graphData
# ====================================================================
class hystLoop:
    """Hysteresis loop. Independent of the curve/presenter architecture."""

    Q2 = 1.67

    def __init__(self, raw_x, raw_y, time_scale, resistance, wire_square):
        self.raw_data_x = np.asarray(raw_x)
        self.raw_data_y = np.asarray(raw_y)
        self.filtered_x_data = self.raw_data_x.copy()
        self.filtered_y_data = self.raw_data_y.copy()

        self.time_raw_data = [i * time_scale for i in range(len(self.raw_data_x))]
        self.time_scale = time_scale
        self.filtered_time_data = list(self.time_raw_data)

        self.resistance = resistance
        self.wire_square = wire_square

        self.data_x = None
        self.data_y = None

        # compatibility with old UI usage
        self.current_highlight = False
        self.saved_pen = None
        self.plot_obj = None

    def calc_loop(self):
        arr1 = np.asarray(self.filtered_x_data)
        arr2 = np.asarray(self.filtered_y_data)
        R = 100 + self.resistance
        d = self.wire_square / 2 * (10 ** -6)
        A = R * (3.1415 * 2 * d * 2)
        C = 16
        X = arr2 / A + C
        Y = self.calculate_results(arr1)
        n = min(len(X), len(Y))
        return X[:n], Y[:n]

    def calculate_results(self, C):
        noise = self.threshold_median(C)
        D2 = np.mean(C)
        E2 = C - D2
        F2 = np.where(np.abs(E2) > noise, 1, 0)
        G2 = E2 * F2
        H2 = np.mean(G2)
        I2 = G2 - H2
        J2 = np.cumsum(I2)
        K2 = J2 - np.max(J2) / 2
        L2 = K2 + self.Q2
        return np.where(L2 <= 0, L2 / np.nanmin(L2), L2 / -np.nanmax(L2))

    def threshold_mean_std(self, data):
        return np.mean(data) + 2 * np.std(data)

    def threshold_median(self, data):
        Q1 = np.percentile(data, 40)
        Q3 = np.percentile(data, 60)
        return Q3 + 1.5 * (Q3 - Q1)

    def recalc_data(self):
        self.data_x, self.data_y = self.calc_loop()
        return self.data_x, self.data_y

    def get_xy_data(self):
        if self.data_x is None or self.data_y is None:
            self.data_x, self.data_y = self.calc_loop()
        return self.data_x, self.data_y

    # graphOsc API
    def set_plot_obj(self, plot_obj, pen, highlight=False):
        self.plot_obj = plot_obj
        self.saved_pen = pen
        self.current_highlight = highlight

    def clear_filters(self):
        self.filtered_x_data = self.raw_data_x.copy()
        self.filtered_y_data = self.raw_data_y.copy()