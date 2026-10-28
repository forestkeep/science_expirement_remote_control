
from .utils import string_to_qfont, string_to_color
import logging
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QApplication

import numpy as np
from datetime import datetime

from ..core.dataManager import graphDataManager, relationData, measTimeData
from ..core.curve_data import linearData, LineStyle
from ..ui.customPlotWidget import PatchedPlotWidget, axisStyle
from ..core.filters_instance_class import FilterCommand

from .models import (ProjectFile, Session, SessionParameters, FieldSettings, DataManager,Plot, OscillogramData,
                    ParameterData, GraphStyle, Statistics, CurveTreeItemData, GraphData, LinearData, FilterEntry,
                    UncertaintyEntry)


logger = logging.getLogger(__name__)

class ProjectToHDF5Adapter:
    """Адаптер для преобразования объектов ядра в модели HDF5."""
    
    def convert_project(self, core_project) -> ProjectFile: #sessionController
        """
        Преобразует объект проекта ядра в ProjectFile.
        
        Args:
            core_project: Объект проекта из ядра приложения
            
        Returns:
            ProjectFile: Модель проекта для HDF5
        """
        project_file = ProjectFile(
            name=None,
            description=None,
            version_app=core_project.version_app,
            creation_date=datetime.now()
        )

        self.convert_alias_manager(project_file, core_project.alias_manager)
        
        for session_id, core_session in core_project.graph_sessions.items():
            session = self.convert_session(core_session)
            project_file.sessions[session_id] = session
            
        return project_file
    
    def convert_alias_manager(self, project_file, alias_manager):
        project_file.aliases = alias_manager.get_all_aliases()
    
    def convert_session(self, core_session) -> Session:
        data_manager = self._convert_data_manager(core_session.data_manager)

        parameters = SessionParameters(
            name=core_session.session_name,
            description=core_session.description,
            uuid=core_session.uuid,
            experiment_date=None,
            operator=None,
            comment=None,
        )

        field_settings = core_session.get_field_settings()

        plots = {}
        failed_plots: list[str] = []
        for plot_name, core_plot in core_session.graph_main.get_curves().items():
            try:
                plot = self.convert_plot(core_plot)
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                failed_plots.append(
                    f"{plot_name} ({type(exc).__name__}: {exc})"
                )
                continue
            plots[plot_name.replace('\\', '_').replace('/', '_')] = plot
        if failed_plots:
            logger.warning(
                "convert_session: %d plot(s) failed: %s",
                len(failed_plots), ", ".join(failed_plots),
            )

        helpers: list[dict] = []
        hm = getattr(core_session, "helper_manager", None)
        if hm is not None:
            for h in hm.get_helpers():
                helpers.append({
                    "helper_type": h.helper_type,
                    "params": dict(h.params or {}),
                    "visible": bool(h.visible),
                })

        return Session(
            name=core_session.session_name,
            description=core_session.description,
            parameters=parameters,
            field_settings=field_settings,
            data_manager=data_manager,
            plots=plots,
            helpers=helpers,
        )

    def _convert_data_manager(self, core_manager: graphDataManager) -> DataManager:
        """Собрать DataManager из данных ядра для записи в HDF5."""
        logger.info("Converting data manager")
        dm = DataManager()
        all_data = core_manager.get_all_data()

        for key, md in all_data["osc"].data.items():
            dm.oscillogram_data[key] = OscillogramData(
                name=key,
                device=md.device or "",
                channel=md.ch or "",
                parameter=md.param or "",
                time_values=np.asarray(md.num_or_time, dtype=float),
                data_values=np.asarray(md.par_val, dtype=float),
            )

        for key, md in all_data["main"].data.items():
            dm.parameter_data[key] = ParameterData(
                name=key,
                device=md.device or "",
                channel=md.ch or "",
                parameter=md.param or "",
                time_values=np.asarray(md.num_or_time, dtype=float),
                data_values=np.asarray(md.par_val, dtype=float),
            )

        return dm
    
    def convert_plot(self, core_plot) -> Plot:
        style_settings = self.from_graph_item(graph_item=core_plot)

        core_plot.ensure_stats_fresh()

        stats = Statistics(
            mean=core_plot.tree_item.parameters.get('mean', 0.0),
            median=core_plot.tree_item.parameters.get('median', 0.0),
            std_dev=core_plot.tree_item.parameters.get('std', 0.0),
        )

        note_description = core_plot.tree_item.get_description() or ""

        tree_item_data = CurveTreeItemData(
            parameters=core_plot.tree_item.parameters.copy(),
            font_info=(
                f"Italic,{core_plot.tree_item.font.pointSize()}"
                if hasattr(core_plot.tree_item, 'font') else "Italic,10"
            ),
            color_info=(
                core_plot.tree_item.foreground(1).color().name()
                if core_plot.tree_item.foreground(1) else "#ff30ea"
            ),
            col_font_info=(
                f"{core_plot.tree_item.col_font.pointSize()}"
                if hasattr(core_plot.tree_item, 'col_font') else "15"
            ),
            description=note_description,
        )

        graph_data = GraphData(
            raw_data_x=core_plot.raw_data_x,
            raw_data_y=core_plot.raw_data_y,
            filtered_x_data=core_plot.filtered_x_data,
            filtered_y_data=core_plot.filtered_y_data,
            device=core_plot.device,
            channel=core_plot.ch,
            x_name=core_plot.rel_data.x_root_name,
            y_name=core_plot.rel_data.y_root_name,
            curve_name=core_plot.curve_name,
            is_name_customized=core_plot.is_name_curve_customized,
            number=core_plot.number,
            number_axis=core_plot.number_axis,
            is_draw=core_plot.is_draw,
            is_curve_selected=core_plot.is_curve_selected,
            tree_item_data=tree_item_data,
        )

        linear_data = LinearData(
            **graph_data.__dict__,
            tip=core_plot.tree_item.parameters.get('tip', 'linear'),
        )

        history = []
        for filter in core_plot.filters_history:
            history.append(FilterEntry(
                name="",
                description="",
                filter_type=filter.filter_type,
                params=filter.params,
                enabled=getattr(filter, "enabled", True),
            ))

        uncertainty_records = []
        uncertainty_style = {}
        store_ref = getattr(core_plot, "store", None)
        if store_ref is not None:
            uncertainty_style = dict(
                getattr(store_ref, "uncertainty_style", {}) or {}
            )
            active_ids = set(
                getattr(store_ref, "active_uncertainty_ids", set()) or set()
            )
            for rec in getattr(store_ref, "uncertainty_records", []) or []:
                uncertainty_records.append(UncertaintyEntry(
                    id=str(getattr(rec, "id", "")),
                    method=str(getattr(rec, "method", "std")),
                    params=dict(getattr(rec, "params", {}) or {}),
                    x_err=getattr(rec, "x_err", None),
                    y_err=getattr(rec, "y_err", None),
                    active=(getattr(rec, "id", None) in active_ids),
                    style=dict(getattr(rec, "style", {}) or {}),
                ))

        return Plot(
            status="active",
            style=style_settings,
            statistics=stats,
            history=history,
            linear_data=linear_data,
            is_draw=core_plot.is_draw,
            is_curve_selected=core_plot.is_curve_selected,
            is_gen=bool(getattr(core_plot.rel_data, "is_gen", False)),
            name=core_plot.curve_name if hasattr(core_plot, 'curve_name') else "",
            x_name=core_plot.rel_data.x_root_name,
            y_name=core_plot.rel_data.y_root_name,
            axis=core_plot.number_axis,
            uncertainty_records=uncertainty_records,
            uncertainty_style=uncertainty_style,
        )
    
    def from_graph_item(self, graph_item) -> GraphStyle:
        style_graph = graph_item.saved_style or LineStyle()

        styles = {
            QtCore.Qt.SolidLine:       "Solid",
            QtCore.Qt.DashLine:        "Dash",
            QtCore.Qt.DotLine:         "Dot",
            QtCore.Qt.DashDotLine:     "DashDot",
            QtCore.Qt.DashDotDotLine:  "DashDotDot",
        }

        sym = style_graph.symbol
        if sym is None:
            sym = ""

        return GraphStyle(
            color=style_graph.color or "#ffffff",
            line_style=styles.get(style_graph.line_style, "Solid"),
            line_width=int(style_graph.line_width or 1),
            symbol=sym,
            symbol_size=int(style_graph.symbol_size or 1),
            symbol_color=style_graph.symbol_color or "#ffffff",
            fill_color=style_graph.fill_color or "#ffffff",
        )
    
class HDF5ToProjectAdapter:
    """Адаптер для преобразования HDF5-моделей в данные ядра"""
    
    def convert(self, project: ProjectFile, core_session):
        for original_name, alias in project.aliases.items():
            core_session.alias_manager.set_alias(original_name, alias)

        for session_name, session_model in project.sessions.items():
            self._convert_session(session_model, core_session)

    def _convert_session(self, session: Session, core_session):
        """Восстановить сессию без лишних сигналов и повторных пересборок данных."""
        logger.info(f"Converting session {session.name}")

        parameters = session.parameters
        if parameters is None or not parameters.uuid:
            logger.warning(
                "convert_session: session %r has no uuid, skipped", session.name
            )
            return

        uuid = parameters.uuid
        dm = session.data_manager
        use_timestamp = dm is not None and 'time' in dm.parameter_data

        session_id = core_session.start_new_session(
            session_name=session.name, use_timestamps=use_timestamp, uuid=uuid
        )
        if not session_id:
            logger.warning(
                f"Failed to start session {session.name=} {uuid=}, "
                f"convert session skipped"
            )
            return

        core_session.update_session_description(session_id, session.description or "")

        sess = core_session.graph_sessions[session_id]
        core_manager = sess.data_manager
        select_ctrl = sess.select_controller

        # --- 1. Данные ---
        self._convert_data_manager(core_manager, dm)
        core_manager.mark_stopped_silently()

        # --- 2. Кривые ---
        selection_x_param = None
        selection_y_first_params: list = []
        selection_y_second_params: list = []

        failed_curves: list[str] = []
        for plot in session.plots.values():
            axis = plot.axis
            if axis not in (1, 2):
                logger.warning(
                    "convert_session: unknown axis %r for plot %r",
                    axis, plot.name,
                )
                continue

            try:
                curve_obj = self.restore_curve_from_model(
                    plot_model=plot,
                    alias_manager=core_session.alias_manager,
                    filter_instance=sess.filter_class,
                )
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                failed_curves.append(
                    f"{plot.name} ({type(exc).__name__}: {exc})"
                )
                continue

            curve_obj.number_axis = axis
            sess.graph_main.add_curve(
                curve_obj, type_axis="left" if axis == 1 else "right"
            )

            if not plot.is_draw:
                curve_obj.delete_curve_from_graph()
                continue

            if getattr(plot, "is_gen", False):
                continue

            x_alias = core_session.alias_manager.get_alias(plot.x_name)
            y_alias = core_session.alias_manager.get_alias(plot.y_name)

            if selection_x_param is None:
                selection_x_param = x_alias
            elif selection_x_param != x_alias:
                logger.warning(
                    f"Conflict selection x parameter {plot.x_name} "
                    f"(have {selection_x_param})"
                )
                continue

            if axis == 1:
                if y_alias not in selection_y_first_params:
                    selection_y_first_params.append(y_alias)
            else:
                if y_alias not in selection_y_second_params:
                    selection_y_second_params.append(y_alias)

        if failed_curves:
            logger.warning(
                "convert_session: failed to restore %d curve(s): %s",
                len(failed_curves), ", ".join(failed_curves),
            )

        # --- 3. Скорректировать field_settings под фактический выбор ---------
        field_settings = session.field_settings
        gf = field_settings.graph_field if field_settings is not None else None
        if gf is None:
            logger.warning(
                "convert_session: session %r has no field_settings.graph_field",
                session.name,
            )
        else:
            if selection_y_second_params:
                gf.is_second_axis_enabled = True
            if len(selection_y_first_params) > 1:
                gf.is_multiple_y1_enabled = True
                gf.is_multiple_selection_enabled = True
            if len(selection_y_second_params) > 1:
                gf.is_multiple_y2_enabled = True

        # --- 4. «Замораживаем» состояние модели ---
        select_ctrl._last_emitted_state = (
            select_ctrl.curent_x_parameter,
            tuple(select_ctrl.curent_y_first_parameters),
            tuple(select_ctrl.curent_y_second_parameters),
        )

        if field_settings is not None:
            sess.apply_field_settings(field_settings)

        # --- 5. Установить selection-модель ---
        select_ctrl.curent_x_parameter = selection_x_param
        select_ctrl.curent_y_first_parameters = list(selection_y_first_params)
        select_ctrl.curent_y_second_parameters = list(selection_y_second_params)
        select_ctrl._enforce_invariants()
        select_ctrl._sync_view_from_model()

        select_ctrl._last_emitted_state = (
            select_ctrl.curent_x_parameter,
            tuple(select_ctrl.curent_y_first_parameters),
            tuple(select_ctrl.curent_y_second_parameters),
        )

        # --- 6. Хелперы ---
        hm = getattr(sess, "helper_manager", None)
        if hm is not None:
            hm.remove_all()
            helpers_failed: list[str] = []
            for h_data in getattr(session, "helpers", []) or []:
                helper_type = h_data.get("helper_type", "")
                if not helper_type:
                    continue
                try:
                    new_helper = hm.add_helper(
                        helper_type, dict(h_data.get("params") or {})
                    )
                except (KeyError, ValueError, AttributeError) as exc:
                    helpers_failed.append(
                        f"{helper_type} ({type(exc).__name__}: {exc})"
                    )
                    continue
                if new_helper is not None and not h_data.get("visible", True):
                    hm.set_visible(new_helper.id, False)
            if helpers_failed:
                logger.warning(
                    "convert_session: failed to restore %d helper(s): %s",
                    len(helpers_failed), ", ".join(helpers_failed),
                )

        # --- 7. Артефакты анализа ---
        if hasattr(sess, "analysis_controller") and session.analysis_artifacts:
            from graphs.analysis.commands import ApplyAnalysisCommand
            artifacts_failed: list[str] = []
            for art in session.analysis_artifacts:
                try:
                    cmd = ApplyAnalysisCommand(sess.analysis_controller, art)
                    sess.undo_manager.push(cmd, execute=True)
                except (KeyError, ValueError, AttributeError) as exc:
                    artifacts_failed.append(
                        f"{getattr(art, 'id', '?')} "
                        f"({type(exc).__name__}: {exc})"
                    )
            if artifacts_failed:
                logger.warning(
                    "convert_session: failed to restore %d artifact(s): %s",
                    len(artifacts_failed), ", ".join(artifacts_failed),
                )


    def apply_graph_settings(self, graph_widget: PatchedPlotWidget,
                         settings: FieldSettings) -> None:
        """Применяет настройки к графику."""
        if settings is None or settings.graph_field is None:
            logger.warning("apply_graph_settings: empty settings, skipped")
            return

        graph_settings = settings.graph_field

        graph_widget.setTitle(graph_settings.title or "")
        graph_widget.setCustomBackgroundColor(
            color=QtGui.QColor(graph_settings.background_color)
        )

        # --- Сетка: X / Y независимо, alpha отдельно от цвета ---
        bottom_axis = graph_widget.plotItem.getAxis("bottom")
        left_axis = graph_widget.plotItem.getAxis("left")
        grid_color = QtGui.QColor(graph_settings.grid_color)
        try:
            grid_alpha = int(round(float(graph_settings.grid_alpha) * 255))
        except (TypeError, ValueError):
            grid_alpha = 128

        bottom_axis.setPen(grid_color)
        left_axis.setPen(grid_color)

        x_on = bool(getattr(graph_settings, "x_grid_enabled",
                            graph_settings.grid_enabled))
        y_on = bool(getattr(graph_settings, "y_grid_enabled",
                            graph_settings.grid_enabled))

        bottom_axis.setGrid(grid_alpha if x_on else False)
        left_axis.setGrid(grid_alpha if y_on else False)

        graph_widget.is_grid_shown = bool(x_on or y_on)

        common_style = axisStyle(
            text_font=string_to_qfont(graph_settings.common_axis_style.text_font),
            tick_font=string_to_qfont(graph_settings.common_axis_style.tick_font),
            color=string_to_color(graph_settings.common_axis_style.color),
        )
        graph_widget.common_style = common_style

        log_x = False
        log_y = False
        for axis_name, axis_settings in graph_settings.axes.items():
            if axis_name == "bottom":
                log_x = bool(axis_settings.log_mode)
            elif axis_name == "left":
                log_y = bool(axis_settings.log_mode)

            if axis_name not in graph_widget.axises:
                continue

            axis_controller = graph_widget.axises[axis_name]

            axis_controller.settings.label = axis_settings.label or ""
            axis_controller.settings.is_visible = axis_settings.is_visible
            axis_controller.settings.is_inverted = axis_settings.is_inverted

            if axis_settings.is_visible:
                axis_controller.show()
            else:
                axis_controller.hide()

            if axis_name == 'bottom':
                graph_widget.invert_x_axis(axis_settings.is_inverted)
            elif axis_name == 'left':
                graph_widget.invert_y_axis(axis_settings.is_inverted)
            elif axis_name == 'right':
                graph_widget.invert_y2_axis(axis_settings.is_inverted)

            custom_style = axisStyle(
                text_font=string_to_qfont(axis_settings.custom_style.text_font),
                tick_font=string_to_qfont(axis_settings.custom_style.tick_font),
                color=string_to_color(axis_settings.custom_style.color),
            )
            if axis_settings.is_style_customized:
                axis_controller.set_custom_style(custom_style)
            else:
                axis_controller.set_common_style(common_style)

            if not axis_settings.auto_range and axis_settings.range:
                axis_controller.setRange(*axis_settings.range)

        try:
            graph_widget.plotItem.setLogMode(x=log_x, y=log_y)
        except (AttributeError, ValueError) as exc:
            logger.debug("apply_graph_settings: setLogMode failed: %s", exc)

        if hasattr(graph_widget, 'legend'):
            graph_widget.legend.setVisible(graph_settings.legend_enabled)
            graph_widget.legend2.setVisible(graph_settings.legend_enabled)

            if getattr(graph_settings, "legend_pos", None) is not None:
                pos = graph_settings.legend_pos
                if (isinstance(pos, (tuple, list)) and len(pos) == 2):
                    graph_widget.legend.setPos(pos[0], pos[1])
            if getattr(graph_settings, "legend2_pos", None) is not None:
                pos2 = graph_settings.legend2_pos
                if (isinstance(pos2, (tuple, list)) and len(pos2) == 2):
                    graph_widget.legend2.setPos(pos2[0], pos2[1])

            if hasattr(graph_widget, 'set_legend_color'):
                graph_widget.set_legend_color(graph_settings.legend_text_color)

            if hasattr(graph_widget, 'set_legend_font') and graph_settings.legend_font:
                font = string_to_qfont(graph_settings.legend_font)
                if font is not None:
                    graph_widget.set_legend_font(font)

        graph_widget.setAntialiasing(graph_settings.antialiasing)
        if hasattr(graph_widget, "style_changed"):
            try:
                graph_widget.style_changed.emit()
            except (TypeError, RuntimeError) as exc:
                logger.debug(
                    "apply_graph_settings: style_changed.emit failed: %s", exc
                )

    def prepare_data_dict(self, data_items):
            level_3 = {}
            level_2 = {}
            level_1 = {}
            
            for item in data_items:
                data_pairs = [item.data_values, item.time_values]
                
                if item.device:
                    if item.device not in level_3:
                        level_3[item.device] = {}
                    if item.channel:
                        if item.channel not in level_3[item.device]:
                            level_3[item.device][item.channel] = {}
                        level_3[item.device][item.channel][item.parameter] = data_pairs
                    else:
                        level_2[item.device] = {item.parameter: data_pairs}
                elif item.channel:
                    if item.channel not in level_2:
                        level_2[item.channel] = {}
                    level_2[item.channel][item.parameter] = data_pairs
                else:
                    level_1[item.parameter] = data_pairs
                    
            return level_3, level_2, level_1

    def _convert_data_manager(self, core_manager: graphDataManager, model: DataManager):
        """Преобразует данные измерений и осциллограмм"""
        logger.info("Converting data manager")
        osc_data = list(model.oscillogram_data.values())
        if osc_data:
            osc_l3, osc_l2, osc_l1 = self.prepare_data_dict(osc_data)
            for data_dict in [osc_l3, osc_l2, osc_l1]:
                if data_dict:
                    core_manager.add_measurement_data(data_dict, "osc")

        param_data = list(model.parameter_data.values())
        if param_data:
            param_l3, param_l2, param_l1 = self.prepare_data_dict(param_data)
            for data_dict in [param_l3, param_l2, param_l1]:
                if data_dict:
                    core_manager.add_measurement_data(data_dict)

    def restore_curve_from_model(self, plot_model: Plot,
                             alias_manager, filter_instance) -> linearData:
        """Восстановить linearData из Plot. Битые поля — с warning, не с except."""
        logger.info("Restoring curve from model")

        def _strip_prefix(full: str, dev: str, ch: str) -> str:
            prefix = (dev or "") + (ch or "")
            if prefix and full and full.startswith(prefix):
                return full[len(prefix):]
            return full or ""

        linear_data = plot_model.linear_data
        if linear_data is None:
            raise ValueError(
                f"restore_curve_from_model: plot {plot_model.name!r} "
                f"has no linear_data"
            )

        x_dev = linear_data.device or ""
        x_ch = linear_data.channel or ""
        y_dev = x_dev
        y_ch = x_ch

        x_param_only = _strip_prefix(plot_model.x_name or "", x_dev, x_ch)
        y_param_only = _strip_prefix(plot_model.y_name or "", y_dev, y_ch)

        is_gen = bool(getattr(plot_model, "is_gen", False))

        x_meas = measTimeData(
            device=x_dev, ch=x_ch, param=x_param_only,
            par_val=linear_data.raw_data_x,
            num_or_time=np.arange(len(linear_data.raw_data_x)),
        )
        y_meas = measTimeData(
            device=y_dev, ch=y_ch, param=y_param_only,
            par_val=linear_data.raw_data_y,
            num_or_time=np.arange(len(linear_data.raw_data_y)),
        )
        rel_data = relationData(x_meas, y_meas, is_gen=is_gen)

        new_data = linearData(data=rel_data, alias_manager=alias_manager)

        new_data.device = linear_data.device
        new_data.channel = linear_data.channel
        new_data.number = linear_data.number

        new_data.store.raw_data_x = np.asarray(linear_data.raw_data_x)
        new_data.store.raw_data_y = np.asarray(linear_data.raw_data_y)
        new_data.store.filtered_x_data = np.asarray(linear_data.filtered_x_data)
        new_data.store.filtered_y_data = np.asarray(linear_data.filtered_y_data)

        style = self.transform_line_style(plot_model.style)
        new_data.presenter.saved_style = style
        new_data.presenter.preselection_style = style

        for f in plot_model.history:
            new_data.store.filters_history.append(
                FilterCommand(
                    filter_type=f.filter_type,
                    params=f.params,
                    filters_instance=filter_instance,
                    enabled=getattr(f, "enabled", True),
                )
            )
        new_data.store._filtered_dirty = False

        if linear_data.is_name_customized:
            new_data.change_name(linear_data.curve_name)
        else:
            new_data.reset_name()

        # Описание — через .get, без страховки try/except
        tree_item_data = linear_data.tree_item_data
        desc = (getattr(tree_item_data, "description", "") or "") \
            if tree_item_data is not None else ""
        if desc:
            block_name = QApplication.translate("GraphWindow", "Разное")
            key = QApplication.translate("GraphWindow", "Описание")
            if not new_data.tree_item.update_block_data(block_name, {key: desc}):
                new_data.tree_item.add_new_block(block_name, {key: desc})

        # Погрешности — записи опциональны, поля читаем через .get
        from graphs.analysis.uncertainty import UncertaintyRecord
        store = new_data.store
        store.uncertainty_style = dict(
            getattr(plot_model, "uncertainty_style", {}) or {}
        )
        for entry in getattr(plot_model, "uncertainty_records", []) or []:
            kwargs = dict(
                method=getattr(entry, "method", "std") or "std",
                params=dict(getattr(entry, "params", {}) or {}),
                x_err=getattr(entry, "x_err", None),
                y_err=getattr(entry, "y_err", None),
                style=dict(getattr(entry, "style", {}) or {}),
            )
            if getattr(entry, "id", ""):
                kwargs["id"] = entry.id
            rec = UncertaintyRecord(**kwargs)
            store.uncertainty_records.append(rec)
            if getattr(entry, "active", True):
                store.active_uncertainty_ids.add(rec.id)
            else:
                store.active_uncertainty_ids.discard(rec.id)
        if store.uncertainty_records and hasattr(new_data.presenter, "set_error_bars"):
            new_data.presenter.set_error_bars(store.active_uncertainty_records())

        return new_data
    
    def transform_line_style(self, style: GraphStyle) -> LineStyle:
        styles = {
            "Solid":       QtCore.Qt.SolidLine,
            "Dash":        QtCore.Qt.DashLine,
            "Dot":         QtCore.Qt.DotLine,
            "DashDot":     QtCore.Qt.DashDotLine,
            "DashDotDot":  QtCore.Qt.DashDotDotLine,
        }
        sym = style.symbol
        if sym in (None, "", "None"):
            sym = None

        return LineStyle(
            color=style.color or "#ffffff",
            line_style=styles.get(style.line_style, QtCore.Qt.SolidLine),
            line_width=int(style.line_width or 1),
            symbol=sym,
            symbol_size=int(style.symbol_size or 1),
            symbol_color=style.symbol_color or "#ffffff",
            fill_color=style.fill_color or "#ffffff",
        )
