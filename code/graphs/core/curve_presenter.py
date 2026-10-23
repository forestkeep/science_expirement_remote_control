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

from graphs.core.curve_data_store import CurveDataStore
from graphs.core.selection_model import SelectionModel

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
        """Применить стиль к элементу, не перестраивая путь данных без необходимости."""
        pen = self.to_pen()
        current_pen = plot_data_item.opts.get('pen')
        if current_pen is None or current_pen != pen:
            plot_data_item.setPen(pen)

        if self.symbol is not None:
            if plot_data_item.opts.get('symbol') != self.symbol:
                plot_data_item.setSymbol(self.symbol)
            plot_data_item.setSymbolSize(self.symbol_size)
            plot_data_item.setSymbolPen(self.to_symbol_pen())
            plot_data_item.setSymbolBrush(self.to_brush())
        elif plot_data_item.opts.get('symbol') is not None:
            plot_data_item.setSymbol(None)

        if plot_data_item.opts.get('pxMode') != self.px_mode:
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

        self._last_rendered_version: int = -1

        self.i_am_click_now = False
        self.higlighted_flag = False
        self.preselection_style: Optional[LineStyle] = None

        # --- видимое окно точек ---
        self.num_showing_points = 10
        self.is_all_points_showing = True

        # store → refresh plot data
        self.store.on_data_changed(self._on_data_changed)
        self.store.on_meta_changed(self._on_meta_changed)

        if self._selection_model is not None:
            self._selection_model.selection_changed.connect(self._on_model_selection_changed)

        self._last_legend_name = self.store.legend.current_name

        self._refresh_scheduled: bool = False
        self._detached: bool = False

    # -- visible window -------------------------------------------------
    def set_num_points(self, value: int) -> None:
        value = max(1, int(value))
        if value == self.num_showing_points:
            return
        self.num_showing_points = value
        self._do_refresh() 

    def _selection_style(self) -> LineStyle:
        """Стиль выделения, наследующий dash и символы у saved_style.

        Меняются только цвет пера, толщина и цвет символов. Символ, его размер
        и тип линии остаются исходными, поэтому стоимость кадра при
        панорамировании не растёт по сравнению с невыделенной кривой.
        """
        base = self.saved_style or LineStyle()
        return LineStyle(
            color=_SELECTION_COLOR,
            line_style=base.line_style,
            line_width=max(2, int(base.line_width) + 4),
            symbol=base.symbol,
            symbol_size=base.symbol_size,
            symbol_color=_SELECTION_COLOR,
            fill_color=base.fill_color,
        )

    def _on_data_changed(self) -> None:
        if self._detached or self._refresh_scheduled:
            return
        self._refresh_scheduled = True
        QtCore.QTimer.singleShot(16, self._do_refresh)

    def _do_refresh(self) -> None:
        self._refresh_scheduled = False
        if self._detached:
            return
        self.refresh()

    def _on_meta_changed(self) -> None:
        if self._detached:
            return
        current_name = self.store.legend.current_name
        if current_name == self._last_legend_name:
            return
        self._last_legend_name = current_name
        for info in self.plot_items.values():
            self._apply_legend_name(info, current_name)

    def show_all_points(self, state: bool) -> None:
        state = bool(state)
        if state == self.is_all_points_showing:
            return
        self.is_all_points_showing = state
        self._do_refresh() 

    def _apply_style_to_all(self, style: LineStyle, update_tree: bool = True) -> None:
        for info in self.plot_items.values():
            style.apply_to_curve(info['item'])
        if update_tree and self.tree_item is not None:
            color = style.to_pen().color().name()
            self.tree_item.setForeground(1, pg.mkBrush(color=color))

    def _refresh_selection_style(self) -> None:
        selected = self.is_curve_selected
        if selected == getattr(self, "_last_selection_state", None):
            return
        self._last_selection_state = selected
        if not selected:
            if self.saved_style is not None:
                self._apply_style_to_all(self.saved_style, update_tree=True)
            return
        self._apply_style_to_all(self._selection_style(), update_tree=True)
    

    def attach_selection_model(self, model: Optional[SelectionModel]) -> None:
        """Подключить модель выделения и сбросить кэш состояния выделения."""
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
        self._last_selection_state = None
        if model is not None:
            model.selection_changed.connect(self._on_model_selection_changed)
        self._refresh_selection_style()

    def detach(self) -> None:
        self._detached = True
        self._refresh_scheduled = False
        self.store.off_data_changed(self._on_data_changed)
        self.store.off_meta_changed(self._on_meta_changed)
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

    

    # -- plots ----------------------------------------------------------
    def create_plot_item(self):
        """Создать пустой PlotDataItem; данные устанавливаются в refresh()."""
        style = self.saved_style or LineStyle()
        item = pg.PlotDataItem(
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
        """Добавить кривую на график, форсируя первичную отрисовку данных
        и восстановление полос погрешностей (если они есть в store).
        """
        new_item = self.create_plot_item()
        graph_field.addItem(new_item)
        if legend_field.getLabel(new_item) is None:
            legend_field.addItem(new_item, self.store.legend.current_name)

        self.plot_items[graph_field] = {
            'item': new_item, 'legend': legend_field, 'axis': number_axis, 'error_bars': []
        }
        self.number_axis = number_axis

        self._apply_style_to_all(
            self._selection_style() if self.is_curve_selected else (self.saved_style or LineStyle()),
            update_tree=False,
        )
        self.is_draw = True
        self._last_rendered_version = -1
        self._do_refresh()

        # ВАЖНО: восстановить error bars ПОСЛЕ появления plot_items.
        # Сценарии: загрузка проекта, show_curve (после hide), undo/redo удаления.
        try:
            records = self.store.active_uncertainty_records()
            if records:
                self.set_error_bars(records)
        except Exception:
            logger.exception("add_to_graph: set_error_bars failed")

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
        """Убрать кривую и её error bars с графика без detach()."""
        logger.info(f"delete_curve_from_graph {self.store.curve_name}")
        if not self.is_draw:
            return
        self.is_draw = False
        for graph_field, info in list(self.plot_items.items()):
            for eb in info.get('error_bars') or []:
                try:
                    graph_field.removeItem(eb)
                except Exception:
                    pass
            try:
                graph_field.removeItem(info['item'])
            finally:
                info['legend'].removeItem(self.store.legend.current_name)
        self.plot_items.clear()

    def refresh(self) -> None:
        version = self.store.data_version
        if version == self._last_rendered_version:
            return                       # данные не менялись — setData не нужен
        x = self.store.filtered_x_data
        y = self.store.filtered_y_data
        if not self.is_all_points_showing and len(x) > self.num_showing_points:
            x = x[-self.num_showing_points:]
            y = y[-self.num_showing_points:]
        for info in self.plot_items.values():
            info['item'].setData(x, y)
        self._last_rendered_version = version

    def _apply_legend_name(self, info: dict, name: str) -> None:
        """Привести подпись элемента в легенде к *name*.

        Использует LegendItem.getLabel(item) — не зависит от
        legend.previous_name, поэтому корректно работает в любом
        порядке вызовов (change_name / reset_name / set_legend_name).
        """
        legend = info.get('legend')
        item = info.get('item')
        if legend is None or item is None:
            return
        try:
            current_label = legend.getLabel(item)
        except Exception:
            current_label = None
        if current_label == name:
            return
        try:
            if current_label is not None:
                legend.removeItem(item)
            legend.addItem(item, name)
        except Exception:
            logger.exception("CurvePresenter: legend rename failed")

    # -- style ----------------------------------------------------------
    

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
        """Подсветить кривую без пересборки пути (только перо/символы)."""
        if self.higlighted_flag:
            return
        self.higlighted_flag = True
        self.preselection_style = (
            self._selection_style() if self.is_curve_selected else self.saved_style
        )
        pen = pg.mkPen(color=(150, 150, 150, 90), width=5)
        brush = pg.mkBrush(150, 150, 150, 90)
        for info in self.plot_items.values():
            item = info['item']
            item.setPen(pen)
            item.setSymbolPen(pen)
            item.setSymbolBrush(brush)

    def unhiglight_curve(self) -> None:
        """Снять подсветку, пересчитав актуальный стиль по текущему состоянию.

        Стиль вычисляется заново по is_curve_selected / saved_style, а не
        восстанавливается из preselection_style. Это исключает сценарий,
        когда во время hover выделение изменилось (или preselection_style
        был выставлен из clicked_style) и после hover на кривую попадает
        dash-перо — а с ним и медленное панорамирование.
        """
        if not self.higlighted_flag:
            return
        self.higlighted_flag = False
        self.preselection_style = None
        if self.is_curve_selected:
            self._apply_style_to_all(self._selection_style(), update_tree=False)
        elif self.saved_style is not None:
            self._apply_style_to_all(self.saved_style, update_tree=False)

    # -- legend ---------------------------------------------------------
    def set_legend_name(self, name: str) -> None:
        """Публичный API: задать пользовательское имя и обновить легенду.

        Переписано, чтобы не зависеть от legend.previous_name.
        """
        self.store.legend.set_custom(name)
        self._last_legend_name = name
        for info in self.plot_items.values():
            self._apply_legend_name(info, name)

    # -- error bars -----------------------------------------------------
    def set_error_bars(self, records: list) -> None:
        """Отрисовка полос погрешностей согласно стилю каждой записи.

        Режимы (rec.style["mode"]):
          - 'bars'   — вертикальные столбики + горизонтальные риски;
          - 'caps'   — только горизонтальные риски;
          - 'shaded' — полупрозрачная заливка между y±yerr;
          - 'line'   — огибающие линии y+yerr и y−yerr.

        Стиль (rec.style):
          - color: "auto" (цвет кривой) | "#rrggbb";
          - width: 1..10 px;
          - alpha: 0..255;
          - cap_size: 0..40 px.
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

        x = np.asarray(self.store.filtered_x_data, dtype=float)
        y = np.asarray(self.store.filtered_y_data, dtype=float)
        if x.size == 0 or y.size == 0:
            return

        for viewbox, info in self.plot_items.items():
            bars = []
            for rec in records:
                try:
                    for item in self._build_error_items(viewbox, rec, x, y):
                        viewbox.addItem(item)
                        bars.append(item)
                except Exception:
                    logger.exception("set_error_bars failed")
            info["error_bars"] = bars

    def _build_error_items(self, viewbox, rec, x, y) -> list:
        """Собрать графические элементы для одной записи погрешности."""
        import numpy as np
        from graphs.analysis.uncertainty import normalize_uncertainty_style

        style = normalize_uncertainty_style(getattr(rec, "style", None) or {})
        mode = style["mode"]
        width = int(style["width"])
        alpha = int(style["alpha"])
        cap_size = int(style["cap_size"])

        color = style.get("color", "auto")
        if not color or color == "auto":
            color = self.saved_style.color if self.saved_style is not None else "#cccccc"
        try:
            color_obj = pg.mkColor(color)
            color_obj.setAlpha(alpha)
        except Exception:
            color_obj = pg.mkColor(200, 200, 200, alpha)

        # ОТДЕЛЬНО: pen и brush из QColor (ScatterPlotItem принимает brush,
        # а не QPen; иначе pyqtgraph падает в _mkBrush).
        pen = pg.mkPen(color=color_obj, width=width)
        brush = pg.mkBrush(color_obj)

        yerr_raw = getattr(rec, "y_err", None)
        if yerr_raw is None:
            return []
        yerr = np.asarray(yerr_raw, dtype=float)
        if yerr.size != y.size:
            return []

        items = []

        if mode == "line":
            items.append(pg.PlotDataItem(x, y + yerr, pen=pen))
            items.append(pg.PlotDataItem(x, y - yerr, pen=pen))
            return items

        if mode == "shaded":
            fill_color = pg.mkColor(color_obj)
            fill_color.setAlpha(max(20, min(140, alpha // 2)))
            fill_brush = pg.mkBrush(fill_color)
            upper = pg.PlotDataItem(x, y + yerr, pen=pg.mkPen(None))
            lower = pg.PlotDataItem(x, y - yerr, pen=pg.mkPen(None))
            fill = pg.FillBetweenItem(upper, lower, brush=fill_brush)
            return [upper, lower, fill]

        if mode == "bars":
            xs, ys = [], []
            for xi, yi, ei in zip(x, y, yerr):
                if not np.isfinite(ei) or ei <= 0:
                    continue
                xs.extend([xi, xi, float('nan')])
                ys.extend([yi - ei, yi + ei, float('nan')])
            if xs:
                items.append(pg.PlotDataItem(
                    np.asarray(xs), np.asarray(ys),
                    pen=pen, connect='finite',
                ))

        if cap_size > 0:
            size = max(2, cap_size)
            items.append(pg.ScatterPlotItem(
                x=x, y=y + yerr, symbol='_', size=size,
                pen=pen, brush=brush, pxMode=True,
            ))
            items.append(pg.ScatterPlotItem(
                x=x, y=y - yerr, symbol='_', size=size,
                pen=pen, brush=brush, pxMode=True,
            ))

        return items

_SELECTION_COLOR = (100, 100, 100)
def make_selection_style() -> LineStyle:
    """Стиль выделения для артефактов анализа и fallback-совместимости.

    Не использовать в CurvePresenter для основной кривой: в горячем пути
    применяется CurvePresenter._selection_style(), наследующий символы и
    dash у saved_style. Здесь dash и крупный символ допустимы, потому что
    у артефактов мало точек.
    """
    return LineStyle(
        color=(180, 150, 150), line_style=QtCore.Qt.DashLine, line_width=4,
        symbol="+", symbol_size=10,
        symbol_color=(150, 150, 150), fill_color='w',
    )