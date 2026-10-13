# Copyright © 2025 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
from graph.core.curve_data import linearData
from graph.core.dataManager import relationData
from PyQt5.QtWidgets import QApplication
import logging

logger = logging.getLogger(__name__)


class graphSelectAdapter:
    def __init__(self, graph, selector, data_manager, tree_class, type_data, main_class):
        self.graph = graph
        self.selector = selector
        self.data_manager = data_manager
        self.tree_class = tree_class
        self.type_data = type_data
        self.main_class = main_class

        self.selector.parameters_updated.connect(self.parameters_choised)
        self.selector.multiple_checked.connect(self.multiple_changed)
        self.selector.state_second_axis_changed.connect(self.state_second_axis_changed)
        self.selector.numPointsChanged.connect(self._on_num_points_changed)
        self.selector.showingAllPoints.connect(self._on_showing_all_points)

        self.data_manager.list_parameters_updated.connect(self.update_params)
        self.data_manager.val_parameters_added.connect(self.data_updated)
        self.data_manager.stop_current_session.connect(self.stop_session)

        self.tree_class.curve_deleted.connect(self.destroy_curve)
        self.tree_class.curve_shown.connect(self.show_curve)
        self.tree_class.curve_hide.connect(self.hide_curve)
        self.tree_class.curve_reset.connect(self.reset_filters)
        self.tree_class.curve_created.connect(self.curve_created)

    # --- видимое окно ---
    def _on_num_points_changed(self, value: int) -> None:
        self.graph.set_num_points(int(value))

    def _on_showing_all_points(self, state: bool) -> None:
        self.graph.show_all_points(bool(state))

    def hide_curve(self, curve_data_obj: linearData):
        curve_data_obj.delete_curve_from_graph()

        if curve_data_obj.rel_data.is_gen:
            # генерируемые кривые не участвуют в селекторе — снимать выделение не с чего
            return

        y_name = curve_data_obj.rel_data.y_root_name
        axis = curve_data_obj.number_axis
        if axis == 2:
            first, second = [], [y_name]
        elif axis == 1:
            first, second = [y_name], []
        else:
            logger.warning(f"hide_curve: unknown axis {axis} for {y_name}")
            return

        self.selector.clear_selections("", first, second, is_signal=True)

    def stop_session(self):
        """
        Остановка эксперимента.

        Перед остановкой подтягиваем финальные данные во все созданные кривые
        (включая скрытые), чтобы при последующем их отображении в REVIEW-режиме
        на графике появились актуальные данные, а не срез на момент скрытия.
        Состав отображаемого при этом не меняется.

        После остановки принудительно включаем показ всех точек: в REVIEW
        видимое окно не нужно, данные уже не растут.
        """
        self._refresh_all_curves_data()
        self.graph.stop_session()
        self.selector.stop_session()
        # Гарантированный сброс видимого окна независимо от UI-сигналов.
        self.graph.show_all_points(True)

    def _refresh_all_curves_data(self):
        """
        Обновляет raw/filtered данные всех кривых текущей сессии из data_manager.

        - не добавляет и не удаляет plot_items: скрытые кривые остаются скрытыми,
        видимые получают свежие данные через presenter.refresh();
        - генерируемые кривые (rel_data.is_gen) пропускаем — у них нет источника
        в data_manager;
        - фильтры пересобираются автоматически внутри CurveDataStore.set_data()
        (через filters_history). В live-режиме история фильтров пуста, так что
        этот шаг для активной сессии фактически no-op.
        """
        curves = self.graph.get_curves()
        if not curves:
            return

        for root_name, curve in list(curves.items()):
            try:
                if getattr(curve.rel_data, "is_gen", False):
                    continue

                x_name = curve.rel_data.x_root_name
                y_name = curve.rel_data.y_root_name
                axis = curve.number_axis or 1

                first, second = ([y_name], []) if axis == 1 else ([], [y_name])
                data_first, data_second = self.data_manager.get_relation_data(
                    x_name, first, second, self.type_data
                )
                relations = data_first + data_second
                if not relations:
                    logger.warning(
                        f"_refresh_all_curves_data: no data for {root_name} "
                        f"({x_name}/{y_name}, axis={axis})"
                    )
                    continue

                # setData внутри store:
                #   - копирует свежие raw_data_x/y,
                #   - пересобирает filtered_* из filters_history,
                #   - уведомляет подписчиков (presenter.refresh обновит plot_items
                #     только у видимых кривых; у скрытых словарь plot_items пуст).
                curve.setData(relations[0])

            except Exception:
                logger.exception(
                    f"_refresh_all_curves_data: failed to refresh curve {root_name}"
                )

    def destroy_curve(self, curve_data_obj: linearData):
        if curve_data_obj.is_draw:
            self.hide_curve(curve_data_obj)
        self.graph.destroy_curve(curve_data_obj)

    def show_curve(self, curve_data_obj: linearData):
        paramx, _, _ = self.selector.get_parameters()
        curve_x = curve_data_obj.rel_data.x_root_name

        # X селектора не задан — не блокируем; при заданном требуем совпадения
        if paramx and paramx != curve_x:
            self.main_class.show_tooltip(
                message=QApplication.translate("GraphWindow", "Кривая принадлежит другому пространству")
            )
            return

        y_name = curve_data_obj.rel_data.y_root_name

        if curve_data_obj.rel_data.is_gen:
            if curve_data_obj.number_axis == 1:
                curve_data_obj.add_to_graph(
                    graph_field=self.graph.graphView,
                    legend_field=self.graph.graphView.legend,
                    number_axis=1,
                )
            elif curve_data_obj.number_axis == 2:
                curve_data_obj.add_to_graph(
                    graph_field=self.graph.graphView.second_graphView,
                    legend_field=self.graph.graphView.legend2,
                    number_axis=2,
                )
            else:
                logger.warning(f"show_curve: gen curve without axis {y_name}")
            return

        axis = curve_data_obj.number_axis
        if axis == 1:
            self.selector.set_selections("", [y_name], [], is_signal=True)
        elif axis == 2:
            self.selector.set_selections("", [], [y_name], is_signal=True)
        else:
            logger.warning(f"show_curve: unknown axis {axis} for {y_name}")

    def reset_filters(self, curve_data_obj: linearData):
        self.graph.reset_filters(curve_data_obj)

    def curve_created(self, data: relationData, formula: str = None, description: str = None):
        status = self.graph.create_and_place_curve(data=data)
        if not status:
            logger.warning(f"Кривая {data.root_name=} уже существует")
            return
        curve = self.graph.get_curve(data.root_name)
        if curve is None:
            return
        blocks = {}
        if formula:
            blocks[QApplication.translate("GraphWindow", "Формула")] = formula
        if description:
            blocks[QApplication.translate("GraphWindow", "Описание")] = description
        if blocks:
            curve.tree_item.add_new_block(
                QApplication.translate("GraphWindow", "Разное"), blocks
            )

    def numPointsChanged(self, value):
        self.graph.set_num_points(value)

    def showingAllPoints(self, state):
        self.graph.show_all_points(state)

    def state_second_axis_changed(self, state):
        self.graph.set_second_axis(state)

    def multiple_changed(self, state):
        self.graph.set_multiple_mode(state)

    def update_params(self, parameters):
        list_parameters = parameters[self.type_data]
        self.selector.add_parameters(list_parameters)

    def data_updated(self, parameters):
        paramx, paramy1, paramy2 = self.selector.get_parameters()
        datax = ''
        datay1, datay2 = {}, {}
        if parameters[self.type_data].get(paramx):
            datax = paramx
        for param in paramy1:
            if parameters[self.type_data].get(param):
                datay1[param] = parameters[self.type_data][param]
        for param in paramy2:
            if parameters[self.type_data].get(param):
                datay2[param] = parameters[self.type_data][param]
        data_first_axis, data_second_axis = self.data_manager.get_relation_data(
            datax, datay1, datay2, self.type_data
        )
        self.graph.update_data(data_first_axis, data_second_axis, is_updated=True)

    def parameters_choised(self, param_x, param_y1, param_y2):
        logger.info(f"parameters_choised {param_x} {param_y1} {param_y2}")

        if param_x == "numbers":
            param_y1 = [p for p in param_y1 if p != "numbers"]
            param_y2 = [p for p in param_y2 if p != "numbers"]

        # X не выбран — ни одна кривая не может быть построена; очищаем график.
        if not param_x:
            self.graph.update_data([], [])
            return

        # Здесь param_y1/param_y2 могут быть пустыми: это корректный сценарий
        # «пользователь снял выделение с последнего Y-параметра». get_relation_data
        # вернёт ([], []), а manageGraph.update_data удалит с графика все ранее
        # показанные кривые, которых нет в новом списке.
        data_first_axis, data_second_axis = self.data_manager.get_relation_data(
            param_x, param_y1, param_y2, self.type_data
        )
        self.graph.update_data(data_first_axis, data_second_axis)
