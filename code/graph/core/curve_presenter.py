"""
Visual representation of a curve on one or more pyqtgraph viewboxes.
Owns plot_items, styles and visible window settings.
Selection state comes from a SelectionModel — this class only reads
and requests changes.
"""
from __future__ import annotations

import logging
from typing import Optional

import pyqtgraph as pg
from PyQt5 import QtCore

from graph.core.curve_data_store import CurveDataStore
from graph.core.selection_model import SelectionModel

logger = logging.getLogger(__name__)


class LineStyle:
    def __init__(self, color='w', line_style=QtCore.Qt.SolidLine, line_width=1,
                 symbol=None, symbol_size=5, symbol_color='w', fill_color='w'):
        self.color = color
        self.line_style = line_style
        self.line_width = line_width
        self.symbol = symbol
        self.symbol_size = symbol_size
        self.symbol_color = symbol_color
        self.fill_color = fill_color
        self.px_mode = True

    def to_pen(self):
        return pg.mkPen(color=self.color, width=self.line_width, style=self.line_style)

    def to_symbol_pen(self):
        return pg.mkPen(color=self.symbol_color)

    def to_brush(self):
        return pg.mkBrush(color=self.fill_color)

    def copy(self):
        return LineStyle(
            color=self.color, line_style=self.line_style, line_width=self.line_width,
            symbol=self.symbol, symbol_size=self.symbol_size,
            symbol_color=self.symbol_color, fill_color=self.fill_color,
        )

    def apply_to_curve(self, plot_data_item) -> None:
        plot_data_item.setPen(self.to_pen())
        if self.symbol is not None:
            plot_data_item.setSymbol(self.symbol)
            plot_data_item.setSymbolSize(self.symbol_size)
            plot_data_item.setSymbolPen(self.to_symbol_pen())
            plot_data_item.setSymbolBrush(self.to_brush())
        else:
            plot_data_item.setSymbol(None)
        plot_data_item.opts['pxMode'] = self.px_mode
        plot_data_item.updateItems()


class CurvePresenter:
    """Visual layer: plot items, styles, selection feedback, visible window."""

    def __init__(self, store: CurveDataStore,
                 selection_model: Optional[SelectionModel] = None) -> None:
        self.store = store
        self._selection_model: Optional[SelectionModel] = selection_model

        self.plot_items: dict = {}   # viewbox -> {'item', 'legend', 'axis'}
        self.saved_style: Optional[LineStyle] = None
        self.clicked_style = make_selection_style()

        self.is_draw = False
        self.number_axis: Optional[int] = None
        self.tree_item = None                 # set by linearData facade

        self.i_am_click_now = False
        self.higlighted_flag = False
        self.preselection_style: Optional[LineStyle] = None

        # --- видимое окно точек ---
        self.num_showing_points = 10
        self.is_all_points_showing = True

        # store → refresh plot data
        self.store.on_changed(self.refresh)

        if self._selection_model is not None:
            self._selection_model.selection_changed.connect(self._on_model_selection_changed)

    # -- visible window -------------------------------------------------
    def set_num_points(self, value: int) -> None:
        value = max(1, int(value))
        if value == self.num_showing_points:
            return
        self.num_showing_points = value
        # Всегда перерисовываем — если показываем все точки, refresh() просто
        # выставит полный массив (no-op), если окно — обрежет хвост.
        self.refresh()

    def show_all_points(self, state: bool) -> None:
        state = bool(state)
        if state == self.is_all_points_showing:
            return
        self.is_all_points_showing = state
        self.refresh()

    # -- selection plumbing ---------------------------------------------
    def attach_selection_model(self, model: Optional[SelectionModel]) -> None:
        if self._selection_model is model:
            return
        if self._selection_model is not None:
            try:
                self._selection_model.selection_changed.disconnect(
                    self._on_model_selection_changed
                )
            except (TypeError, RuntimeError):
                pass
        self._selection_model = model
        if model is not None:
            model.selection_changed.connect(self._on_model_selection_changed)
        self._refresh_selection_style()

    def detach(self) -> None:
        self.store.off_changed(self.refresh)
        if self._selection_model is not None:
            try:
                self._selection_model.selection_changed.disconnect(
                    self._on_model_selection_changed
                )
            except (TypeError, RuntimeError):
                pass
            self._selection_model = None

    @property
    def is_curve_selected(self) -> bool:
        if self._selection_model is None:
            return False
        return self._selection_model.is_selected(self)

    @is_curve_selected.setter
    def is_curve_selected(self, value: bool) -> None:
        if self._selection_model is None:
            return
        if value:
            self._selection_model.add(self)
        else:
            self._selection_model.remove(self)

    def _on_model_selection_changed(self, selected_list) -> None:
        self._refresh_selection_style()

    def _refresh_selection_style(self) -> None:
        style = self.clicked_style if self.is_curve_selected else self.saved_style
        if style is None:
            return
        self._apply_style_to_all(style)

    # -- plots ----------------------------------------------------------
    def create_plot_item(self):
        style = self.saved_style or LineStyle()
        item = pg.PlotDataItem(
            self.store.filtered_x_data, self.store.filtered_y_data,
            pen=style.to_pen(),
            name=self.store.legend.current_name,
            symbol=style.symbol,
            symbolPen=style.to_symbol_pen(),
            symbolBrush=style.to_brush(),
        )
        item.setClipToView(True)
        item.setDownsampling(auto=True, method='peak')
        item.setZValue(100)
        item.setCurveClickable(state=True, width=10)
        item.sigClicked.connect(self.on_plot_clicked)
        return item

    def add_to_graph(self, graph_field, legend_field, number_axis) -> None:
        new_item = self.create_plot_item()
        graph_field.addItem(new_item)
        if legend_field.getLabel(new_item) is None:
            legend_field.addItem(new_item, self.store.legend.current_name)

        self.plot_items[graph_field] = {
            'item': new_item, 'legend': legend_field, 'axis': number_axis, 'error_bars': []
        }
        self.number_axis = number_axis

        self._apply_style_to_all(
            self.clicked_style if self.is_curve_selected else (self.saved_style or LineStyle())
        )
        self.is_draw = True
        self.refresh()  # применить видимое окно

    def remove_from_graph(self, viewbox) -> None:
        info = self.plot_items.pop(viewbox, None)
        if info is None:
            return
        try:
            viewbox.removeItem(info['item'])
        finally:
            info['legend'].removeItem(self.store.legend.current_name)

    def remove_all_from_graphs(self) -> None:
        for viewbox in list(self.plot_items.keys()):
            self.remove_from_graph(viewbox)

    def delete_curve_from_graph(self) -> None:
        logger.info(f"delete_curve_from_graph {self.store.curve_name}")
        if not self.is_draw:
            return
        self.is_draw = False
        for graph_field, info in list(self.plot_items.items()):
            try:
                graph_field.removeItem(info['item'])
            finally:
                info['legend'].removeItem(self.store.legend.current_name)
        self.plot_items.clear()

    def refresh(self) -> None:
        """Sync plot data with store, applying visible window if needed."""
        x = self.store.filtered_x_data
        y = self.store.filtered_y_data
        if not self.is_all_points_showing and len(x) > self.num_showing_points:
            x = x[-self.num_showing_points:]
            y = y[-self.num_showing_points:]
        for info in self.plot_items.values():
            info['item'].setData(x, y)

    # -- style ----------------------------------------------------------
    def _apply_style_to_all(self, style: LineStyle) -> None:
        for info in self.plot_items.values():
            style.apply_to_curve(info['item'])
        if self.tree_item is not None:
            color = style.to_pen().color().name()
            self.tree_item.setForeground(1, pg.mkBrush(color=color))

    def apply_style_to_all(self, style: LineStyle) -> None:
        self._apply_style_to_all(style)

    def change_style(self, new_style: LineStyle) -> None:
        self.saved_style = new_style
        if not self.is_curve_selected:
            self._apply_style_to_all(new_style)

    # -- mouse / highlight ----------------------------------------------
    def on_plot_clicked(self, obj=None) -> None:
        self.i_am_click_now = True
        if self._selection_model is None:
            return
        if self._selection_model.is_selected(self):
            self._selection_model.remove(self)
        else:
            self._selection_model.add(self)

    def higlight_curve(self) -> None:
        if self.higlighted_flag:
            return
        self.higlighted_flag = True
        self.preselection_style = (
            self.clicked_style if self.is_curve_selected else self.saved_style
        )
        pen = pg.mkPen(color=(150, 150, 150, 90), width=5)
        for info in self.plot_items.values():
            info['item'].setPen(pen)
            info['item'].setSymbolBrush(color=(150, 150, 150, 90))
            info['item'].setSymbolPen(pen)

    def unhiglight_curve(self) -> None:
        if not self.higlighted_flag:
            return
        self.higlighted_flag = False
        if self.preselection_style is not None:
            self._apply_style_to_all(self.preselection_style)

    # -- legend ---------------------------------------------------------
    def set_legend_name(self, name: str) -> None:
        self.store.legend.set_custom(name)
        for info in self.plot_items.values():
            info['legend'].removeItem(self.store.legend.previous_name)
            info['legend'].addItem(info['item'], self.store.legend.current_name)

    # -- error bars -----------------------------------------------------
    def set_error_bars(self, records: list) -> None:
        """Отрисовка полос погрешностей (error bars).

        Перо берётся в цвет кривой, чтобы полосы были видимы на тёмном фоне
        и визуально привязаны к источнику. Все прежние ErrorBarItem снимаются.
        """
        import numpy as np

        # Убрать старые полосы
        for viewbox, info in list(self.plot_items.items()):
            for eb in info.get("error_bars", []) or []:
                try:
                    viewbox.removeItem(eb)
                except Exception:
                    pass
            info["error_bars"] = []

        if not records:
            return

        x = self.store.filtered_x_data
        y = self.store.filtered_y_data
        if len(x) == 0 or len(y) == 0:
            return

        color = None
        if self.saved_style is not None:
            color = self.saved_style.color
        pen = pg.mkPen(color=color or (220, 220, 220), width=1)

        for viewbox, info in self.plot_items.items():
            bars = []
            for rec in records:
                try:
                    yerr = np.asarray(rec.y_err) if rec.y_err is not None else None
                    if yerr is None or yerr.size != y.size:
                        continue
                    eb = pg.ErrorBarItem(
                        x=x, y=y,
                        top=yerr, bottom=yerr,
                        beam=0.5, pen=pen,
                    )
                    viewbox.addItem(eb)
                    bars.append(eb)
                except Exception:
                    logger.exception("set_error_bars failed")
            info["error_bars"] = bars
            
def make_selection_style() -> LineStyle:
    """Единый стиль выделения основной кривой и всех её потомков (анализа).

    Именно этот стиль применяется и к CurvePresenter.clicked_style,
    и к артефактам анализа при подсветке источника.
    """
    return LineStyle(
        color=(180, 150, 150), line_style=QtCore.Qt.DashLine, line_width=4,
        symbol="+", symbol_size=10,
        symbol_color=(150, 150, 150), fill_color='w',
    )