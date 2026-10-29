"""Тонкие адаптеры: конверсия моделей — в самих моделях."""
from __future__ import annotations

import logging
from datetime import datetime

import numpy as np
from PyQt5 import QtGui

from ..core.curve_data import LineStyle
from ..ui.customPlotWidget import PatchedPlotWidget, axisStyle
from .models import (
    DataManager, FieldSettings, OscillogramData, ParameterData, Plot,
    Session, SessionParameters,SessionUIState
)
from .utils import string_to_qfont, string_to_color

logger = logging.getLogger(__name__)

def _serialize_inf_line(line):
    pen = getattr(line, "pen", None)
    label = getattr(line, "label", None)
    label_text = getattr(label, "text", "") if label else ""
    label_opts = dict(getattr(line, "labelOpts", {}) or {})
    return {
        "angle": getattr(line, "angle", 90),
        "pos": line.value(),
        "pen": {
            "color": pen.color().name() if pen else "#ffffff",
            "width": pen.width() if pen else 1,
            "style": int(pen.style()) if pen else 0,
        },
        "label": label_text,
        "labelOpts": label_opts,
    }


def _create_inf_line_no_signal(desc, graph_view):
    from graphs.ui.custom_inf_line import RemovableInfiniteLine
    import pyqtgraph as pg
    from PyQt5 import QtCore
    pen_desc = desc.get("pen", {})
    pen = pg.mkPen(
        color=pen_desc.get("color", "#ffffff"),
        width=pen_desc.get("width", 1),
        style=pen_desc.get("style", QtCore.Qt.SolidLine),
    )
    line = RemovableInfiniteLine(
        movable=True,
        angle=desc.get("angle", 90),
        pen=pen,
        hoverPen=(0, 200, 0),
        label=desc.get("label", ""),
        labelOpts=desc.get("labelOpts", {}),
        pos=desc.get("pos", 0),
    )
    line.removeRequested.connect(graph_view.remove_inf_line)
    graph_view.inf_lines.append(line)
    graph_view.addItem(line)
    return line



class ProjectToHDF5Adapter:
    def convert_project(self, core_project) -> "ProjectFile":
        from .models import ProjectFile
        from .migrations import CURRENT_SCHEMA_VERSION
        pf = ProjectFile(
            name=None,
            description=None,
            version_app=core_project.version_app,
            creation_date=datetime.now(),
            schema_version=CURRENT_SCHEMA_VERSION,
        )
        pf.aliases = core_project.alias_manager.get_all_aliases()
        for session_id, core_session in core_project.graph_sessions.items():
            pf.sessions[session_id] = self.convert_session(core_session)

        if hasattr(core_project, "session_selector"):
            pf.session_order = [s['id'] for s in core_project.session_selector.sessions]
        active_widget = core_project.graphics_win.stack.currentWidget()
        for sid, sess in core_project.graph_sessions.items():
            if sess is active_widget:
                pf.active_session_id = sid
                break
        return pf

    def convert_session(self, core_session) -> Session:
        parameters = SessionParameters(
            name=core_session.session_name,
            description=core_session.description,
            uuid=core_session.uuid,
            experiment_date=getattr(core_session, "experiment_date", None),
            operator=getattr(core_session, "operator", "") or "",
            comment=getattr(core_session, "comment", "") or "",
        )

        plots = {}
        for name, core_plot in core_session.graph_main.get_curves().items():
            try:
                plots[name.replace("\\", "_").replace("/", "_")] = Plot.from_core(core_plot)
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                logger.warning("convert_session: plot %r failed: %s", name, exc)

        artifacts = []
        ctrl = getattr(core_session, "analysis_controller", None)
        if ctrl is not None:
            artifacts = list(ctrl.store.all())

        helpers = []
        hm = getattr(core_session, "helper_manager", None)
        if hm is not None:
            helpers = [
                {
                    "helper_type": h.helper_type,
                    "params": dict(h.params or {}),
                    "visible": bool(h.visible),
                }
                for h in hm.get_helpers()
            ]

        field_settings = core_session.get_field_settings()

        ui_state = SessionUIState()
        ui_state.active_tab = getattr(core_session, "active_tab_index", 0)
        if hasattr(core_session, "tree_class") and core_session.tree_class is not None:
            ui_state.show_only_active_curves = (
                core_session.tree_class.visibility_button.isChecked()
            )

        inspector = getattr(core_session, "inspector", None)
        if inspector is not None:
            if inspector.stack.currentWidget() is inspector.curve_inspector:
                ui_state.inspector_current_widget = "curve"
                ui_state.inspector_curve_tab = (
                    inspector.curve_inspector.tabs.currentIndex()
                )
            else:
                ui_state.inspector_current_widget = "no_selection"
                ui_state.inspector_no_selection_tab = (
                    inspector.no_selection_tabs.currentIndex()
                )

            tools_tab = getattr(inspector.curve_inspector, "tools_tab", None)
            if tools_tab is not None:
                ui_state.active_analysis_tool = (
                    tools_tab.tool_combo.currentData() or ""
                )

        ui_state.main_inf_lines = [
            _serialize_inf_line(line)
            for line in core_session.graph_main.graphView.inf_lines
        ]
        if hasattr(core_session, "graph_wave"):
            ui_state.osc_inf_lines = [
                _serialize_inf_line(line)
                for line in core_session.graph_wave.graphView.inf_lines
            ]
            if getattr(core_session.graph_wave, "graphView_loop", None) is not None:
                ui_state.osc_loop_inf_lines = [
                    _serialize_inf_line(line)
                    for line in core_session.graph_wave.graphView_loop.inf_lines
                ]

        ui_state.applied_preset_name = getattr(
            field_settings.graph_field, "applied_preset_name", "—"
        )
        ui_state.edit_all_axes = bool(
            getattr(field_settings.graph_field, "edit_all_axes", True)
        )

        session = Session(
            name=core_session.session_name,
            description=core_session.description,
            parameters=parameters,
            field_settings=field_settings,
            data_manager=self._convert_data_manager(core_session.data_manager),
            plots=plots,
            analysis_artifacts=artifacts,
            helpers=helpers,
            ui_state=ui_state,
        )

        return session

    def _convert_data_manager(self, core_manager) -> DataManager:
        dm = DataManager()
        all_data = core_manager.get_all_data()
        for key, md in all_data["osc"].data.items():
            dm.oscillogram_data[key] = OscillogramData(
                name=key, device=md.device or "", channel=md.ch or "",
                parameter=md.param or "",
                time_values=np.asarray(md.num_or_time, dtype=float),
                data_values=np.asarray(md.par_val, dtype=float),
            )
        for key, md in all_data["main"].data.items():
            dm.parameter_data[key] = ParameterData(
                name=key, device=md.device or "", channel=md.ch or "",
                parameter=md.param or "",
                time_values=np.asarray(md.num_or_time, dtype=float),
                data_values=np.asarray(md.par_val, dtype=float),
            )
        return dm


class HDF5ToProjectAdapter:
    def convert(self, project, core_session) -> None:
        for original, alias in project.aliases.items():
            core_session.alias_manager.set_alias(original, alias)
        for _, session_model in project.sessions.items():
            self._convert_session(session_model, core_session)

        if project.session_order:
            by_id = {s['id']: s for s in core_session.session_selector.sessions}
            ordered = [by_id[sid] for sid in project.session_order if sid in by_id]
            for s in core_session.session_selector.sessions:
                if s not in ordered:
                    ordered.append(s)
            core_session.session_selector.sessions = ordered
            core_session.session_selector.update_view()

        if project.active_session_id and project.active_session_id in core_session.graph_sessions:
            core_session.change_session(project.active_session_id)

    def _convert_session(self, session: Session, core_session) -> None:
        parameters = session.parameters
        if parameters is None or not parameters.uuid:
            logger.warning("session %r has no uuid, skipped", session.name)
            return

        dm = session.data_manager
        use_timestamp = dm is not None and "time" in dm.parameter_data
        session_id = core_session.start_new_session(
            session_name=session.name,
            use_timestamps=use_timestamp,
            uuid=parameters.uuid,
        )
        if not session_id:
            return

        core_session.update_session_description(session_id, session.description or "")
        sess = core_session.graph_sessions[session_id]
        core_manager = sess.data_manager
        self._convert_data_manager(core_manager, dm)
        core_manager.mark_stopped_silently()

        ui = session.ui_state

        sess.operator = parameters.operator
        sess.comment = parameters.comment
        sess.active_tab_index = ui.active_tab

        sess.tabWidget.setCurrentIndex(ui.active_tab)

        if hasattr(sess, "tree_class") and sess.tree_class is not None:
            sess.tree_class.visibility_button.setChecked(
                ui.show_only_active_curves
            )
            sess.tree_class.update_visible()

        inspector = getattr(sess, "inspector", None)
        if inspector is not None:
            if ui.inspector_current_widget == "curve":
                inspector.stack.setCurrentWidget(inspector.curve_inspector)
                inspector.curve_inspector.tabs.setCurrentIndex(
                    ui.inspector_curve_tab
                )
            else:
                inspector.stack.setCurrentWidget(inspector.no_selection_tabs)
                inspector.no_selection_tabs.setCurrentIndex(
                    ui.inspector_no_selection_tab
                )

            if ui.active_analysis_tool:
                tools_tab = inspector.curve_inspector.tools_tab
                idx = tools_tab.tool_combo.findData(ui.active_analysis_tool)
                if idx >= 0:
                    tools_tab.tool_combo.setCurrentIndex(idx)

            graph_settings = getattr(inspector, "graph_settings", None)
            if graph_settings is not None:
                graph_settings.edit_all_axes_check.setChecked(
                    bool(ui.edit_all_axes)
                )

        sess.graph_main.graphView.applied_preset_name = (
            ui.applied_preset_name or "—"
        )

        for desc in ui.main_inf_lines:
            _create_inf_line_no_signal(desc, sess.graph_main.graphView)

        if hasattr(sess, "graph_wave"):
            for desc in ui.osc_inf_lines:
                _create_inf_line_no_signal(desc, sess.graph_wave.graphView)
            if getattr(sess.graph_wave, "graphView_loop", None) is not None:
                for desc in ui.osc_loop_inf_lines:
                    _create_inf_line_no_signal(
                        desc, sess.graph_wave.graphView_loop
                    )

        if parameters.experiment_date is not None:
            sess.experiment_date = parameters.experiment_date

        selection_x = None
        selection_y1, selection_y2 = [], []

        for plot in (session.plots or {}).values():
            axis = plot.axis
            if axis not in (1, 2):
                continue
            try:
                curve = plot.to_core(core_session.alias_manager, sess.filter_class)
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                logger.warning("plot %r restore failed: %s", plot.name, exc)
                continue
            curve.number_axis = axis
            sess.graph_main.add_curve(
                curve, type_axis="left" if axis == 1 else "right"
            )
            if not plot.is_draw:
                curve.delete_curve_from_graph()
                continue
            if plot.is_gen:
                continue
            x_alias = core_session.alias_manager.get_alias(plot.x_name)
            y_alias = core_session.alias_manager.get_alias(plot.y_name)
            if selection_x is None:
                selection_x = x_alias
            if axis == 1:
                if y_alias not in selection_y1:
                    selection_y1.append(y_alias)
            else:
                if y_alias not in selection_y2:
                    selection_y2.append(y_alias)

        fs = session.field_settings
        gf = fs.graph_field if fs is not None else None
        if gf is not None:
            if selection_y2:
                gf.is_second_axis_enabled = True
            if len(selection_y1) > 1:
                gf.is_multiple_y1_enabled = True
                gf.is_multiple_selection_enabled = True
            if len(selection_y2) > 1:
                gf.is_multiple_y2_enabled = True

        ctrl = sess.select_controller
        ctrl._last_emitted_state = (None, (), ())
        if fs is not None:
            sess.apply_field_settings(fs)
        ctrl.curent_x_parameter = selection_x
        ctrl.curent_y_first_parameters = list(selection_y1)
        ctrl.curent_y_second_parameters = list(selection_y2)
        ctrl._enforce_invariants()
        ctrl._sync_view_from_model()
        ctrl._last_emitted_state = (
            selection_x,
            tuple(selection_y1),
            tuple(selection_y2),
        )

        hm = getattr(sess, "helper_manager", None)
        if hm is not None:
            hm.remove_all()
            for helper in session.helpers or []:
                helper_type = helper.get("helper_type")
                if not helper_type:
                    continue
                try:
                    instance = hm.add_helper(
                        helper_type, dict(helper.get("params") or {})
                    )
                except (KeyError, ValueError, AttributeError) as exc:
                    logger.warning("helper %r restore failed: %s", helper_type, exc)
                    continue
                if instance is not None and not helper.get("visible", True):
                    hm.set_visible(instance.id, False)

        ctrl_analysis = getattr(sess, "analysis_controller", None)
        if ctrl_analysis is not None and session.analysis_artifacts:
            from graphs.analysis.commands import ApplyAnalysisCommand
            for artifact in session.analysis_artifacts:
                try:
                    sess.undo_manager.push(
                        ApplyAnalysisCommand(ctrl_analysis, artifact),
                        execute=True,
                    )
                except (KeyError, ValueError, AttributeError) as exc:
                    logger.warning(
                        "artifact %r restore failed: %s",
                        getattr(artifact, "id", "?"),
                        exc,
                    )

    def _convert_data_manager(self, core_manager, model: DataManager) -> None:
        if model is None:
            return

        def prep(items):
            l3, l2, l1 = {}, {}, {}
            for item in items:
                pairs = [item.data_values, item.time_values]
                if item.device:
                    l3.setdefault(item.device, {}).setdefault(item.channel or "", {})[item.parameter] = pairs
                elif item.channel:
                    l2.setdefault(item.channel, {})[item.parameter] = pairs
                else:
                    l1[item.parameter] = pairs
            return l3, l2, l1

        osc = list(model.oscillogram_data.values())
        if osc:
            for d in prep(osc):
                if d:
                    core_manager.add_measurement_data(d, "osc")
        par = list(model.parameter_data.values())
        if par:
            for d in prep(par):
                if d:
                    core_manager.add_measurement_data(d)

    def apply_graph_settings(self, graph_widget: PatchedPlotWidget,
                             settings: FieldSettings) -> None:
        if settings is None or settings.graph_field is None:
            return
        gs = settings.graph_field

        graph_widget.applied_preset_name = getattr(gs, "applied_preset_name", "—")

        graph_widget.setTitle(gs.title or "")
        graph_widget.setCustomBackgroundColor(color=QtGui.QColor(gs.background_color))

        bottom = graph_widget.plotItem.getAxis("bottom")
        left = graph_widget.plotItem.getAxis("left")
        grid_color = QtGui.QColor(gs.grid_color)
        try:
            grid_alpha = int(round(float(gs.grid_alpha) * 255))
        except (TypeError, ValueError):
            grid_alpha = 128
        bottom.setPen(grid_color)
        left.setPen(grid_color)

        x_on = bool(getattr(gs, "x_grid_enabled", gs.grid_enabled))
        y_on = bool(getattr(gs, "y_grid_enabled", gs.grid_enabled))
        bottom.setGrid(grid_alpha if x_on else False)
        left.setGrid(grid_alpha if y_on else False)
        graph_widget.is_grid_shown = bool(x_on or y_on)

        common = axisStyle(
            text_font=string_to_qfont(gs.common_axis_style.text_font),
            tick_font=string_to_qfont(gs.common_axis_style.tick_font),
            color=string_to_color(gs.common_axis_style.color),
        )
        graph_widget.common_style = common

        log_x = log_y = False
        for axis_name, axis_settings in gs.axes.items():
            if axis_name == "bottom":
                log_x = bool(axis_settings.log_mode)
            elif axis_name == "left":
                log_y = bool(axis_settings.log_mode)
            ctrl = graph_widget.axises.get(axis_name)
            if ctrl is None:
                continue
            ctrl.settings.label = axis_settings.label or ""
            ctrl.settings.is_visible = axis_settings.is_visible
            ctrl.settings.is_inverted = axis_settings.is_inverted
            if axis_settings.is_visible:
                ctrl.show()
            else:
                ctrl.hide()
            if axis_name == "bottom":
                graph_widget.invert_x_axis(axis_settings.is_inverted)
            elif axis_name == "left":
                graph_widget.invert_y_axis(axis_settings.is_inverted)
            elif axis_name == "right":
                graph_widget.invert_y2_axis(axis_settings.is_inverted)
            custom = axisStyle(
                text_font=string_to_qfont(axis_settings.custom_style.text_font),
                tick_font=string_to_qfont(axis_settings.custom_style.tick_font),
                color=string_to_color(axis_settings.custom_style.color),
            )
            if axis_settings.is_style_customized:
                ctrl.set_custom_style(custom)
            else:
                ctrl.set_common_style(common)
            if not axis_settings.auto_range and axis_settings.range:
                ctrl.setRange(*axis_settings.range)

        try:
            graph_widget.plotItem.setLogMode(x=log_x, y=log_y)
        except (AttributeError, ValueError):
            pass

        if hasattr(graph_widget, "legend"):
            graph_widget.legend.setVisible(gs.legend_enabled)
            graph_widget.legend2.setVisible(gs.legend_enabled)
            if gs.legend_pos:
                graph_widget.legend.setPos(*gs.legend_pos)
            if gs.legend2_pos:
                graph_widget.legend2.setPos(*gs.legend2_pos)
            graph_widget.set_legend_color(gs.legend_text_color)
            if gs.legend_font:
                f = string_to_qfont(gs.legend_font)
                if f is not None:
                    graph_widget.set_legend_font(f)
            if hasattr(graph_widget, "set_legend_symbol_size"):
                graph_widget.set_legend_symbol_size(
                    int(getattr(gs, "legend_symbol_size", 12))
                )

        graph_widget.setAntialiasing(gs.antialiasing)
        if hasattr(graph_widget, "style_changed"):
            try:
                graph_widget.style_changed.emit()
            except (TypeError, RuntimeError):
                pass