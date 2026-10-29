from typing import Dict, Any
import json
import h5py
from .models import GraphFieldSettings, AxisSettings, AxisStyle
from PyQt5 import QtGui

def extract_plot_widget_settings(plot_widget) -> GraphFieldSettings:
    settings = GraphFieldSettings()
    settings.title = plot_widget.titleLabel.text if hasattr(plot_widget, 'titleLabel') else ""

    bg_brush = plot_widget.backgroundBrush()
    if bg_brush and bg_brush.color():
        settings.background_color = color_to_string(bg_brush.color())

    def _grid_state(axis):
        if axis is None:
            return False, 0
        g = getattr(axis, "grid", False)
        if g is False or g is None:
            return False, 0
        try:
            gi = int(g)
        except (TypeError, ValueError):
            return False, 0
        return gi > 0, gi

    bottom_axis = plot_widget.plotItem.getAxis("bottom")
    left_axis = plot_widget.plotItem.getAxis("left")

    x_on, x_alpha = _grid_state(bottom_axis)
    y_on, y_alpha = _grid_state(left_axis)

    settings.x_grid_enabled = x_on
    settings.y_grid_enabled = y_on
    settings.grid_enabled = bool(x_on or y_on)
    alpha = max(x_alpha, y_alpha)
    settings.grid_alpha = alpha / 255.0 if alpha > 0 else 0.0

    grid_src = None
    if x_on:
        grid_src = bottom_axis
    elif y_on:
        grid_src = left_axis
    else:
        grid_src = bottom_axis or left_axis
    try:
        if grid_src is not None:
            settings.grid_color = color_to_string(grid_src.pen().color())
    except Exception:
        pass

    if hasattr(plot_widget, 'common_style'):
        settings.common_axis_style = AxisStyle.from_qfont_color(
            plot_widget.common_style.text_font,
            plot_widget.common_style.tick_font,
            plot_widget.common_style.color
        )

    if hasattr(plot_widget, 'axises'):
        for axis_name, axis_controller in plot_widget.axises.items():
            axis_settings = AxisSettings()

            axis_settings.label = axis_controller.settings.label
            axis_settings.is_style_customized = axis_controller.settings.is_style_customized
            axis_settings.is_inverted = axis_controller.settings.is_inverted
            axis_settings.is_visible = axis_controller.axis.isVisible()

            if axis_name in ['bottom', 'top']:
                axis_settings.log_mode = plot_widget.plotItem.ctrl.logXCheck.isChecked()
            elif axis_name in ['left', 'right']:
                axis_settings.log_mode = plot_widget.plotItem.ctrl.logYCheck.isChecked()

            viewbox = plot_widget.plotItem.vb if axis_name in ['left', 'bottom'] else plot_widget.second_graphView
            if axis_name in ['left', 'right']:
                axis_settings.auto_range = viewbox.autoRangeEnabled()[1]
                if not axis_settings.auto_range:
                    axis_settings.range = viewbox.viewRange()[1]
            elif axis_name in ['bottom', 'top']:
                axis_settings.auto_range = viewbox.autoRangeEnabled()[0]
                if not axis_settings.auto_range:
                    axis_settings.range = viewbox.viewRange()[0]

            if hasattr(axis_controller, 'custom_style'):
                axis_settings.custom_style = AxisStyle.from_qfont_color(
                    axis_controller.custom_style.text_font,
                    axis_controller.custom_style.tick_font,
                    axis_controller.custom_style.color
                )

            axis_settings.current_style_type = "custom" if axis_settings.is_style_customized else "common"

            settings.axes[axis_name] = axis_settings

    if hasattr(plot_widget, 'legend'):
        try:
            settings.legend_enabled = plot_widget.legend.isVisible()
        except Exception:
            pass

        if plot_widget.legend is not None:
            pos = plot_widget.legend.pos()
            settings.legend_pos = (pos.x(), pos.y())
        if hasattr(plot_widget, 'legend2') and plot_widget.legend2 is not None:
            pos2 = plot_widget.legend2.pos()
            settings.legend2_pos = (pos2.x(), pos2.y())

        lc = getattr(plot_widget, "legend_color", None)
        if lc is not None:
            try:
                settings.legend_text_color = color_to_string(lc)
            except Exception:
                pass

        lf = getattr(plot_widget, "legend_font", None)
        if lf is not None:
            try:
                settings.legend_font = lf.toString()
            except Exception:
                pass

        settings.legend_symbol_size = int(
            getattr(plot_widget, "legend_symbol_size", 8)
        )

    settings.applied_preset_name = getattr(plot_widget, 'applied_preset_name', '—')
    return settings


def string_to_qfont(font_string: str):
    """Конвертация строки в QFont (требует PyQt)"""
    try:
        font = QtGui.QFont()
        font.fromString(font_string)
        return font
    except ImportError:
        return font_string

def color_to_string(color) -> str:
    """Конвертация цвета в строку"""
    if hasattr(color, 'name'):
        return color.name()
    elif isinstance(color, tuple):
        return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
    elif isinstance(color, str) and color.startswith('#'):
        return color
    return str(color)

def string_to_color(color_string: str):
    """Конвертация строки в цвет (требует PyQt)"""
    try:
        from PyQt5 import QtGui
        return QtGui.QColor(color_string)
    except ImportError:
        return color_string
