from typing import Dict, Any
import json
import h5py
from .models import GraphFieldSettings, AxisSettings, AxisStyle
from PyQt5 import QtGui

def extract_plot_widget_settings(plot_widget) -> GraphFieldSettings:
    """Извлекает настройки из PatchedPlotWidget для сохранения"""
    settings = GraphFieldSettings()
    
    # Основные настройки графика
    settings.title = plot_widget.titleLabel.text if hasattr(plot_widget, 'titleLabel') else ""
    
    # Цвет фона
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

    # Цвет сетки — с оси, где она включена (или с нижней по умолчанию)
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
    
    # Общий стиль осей
    if hasattr(plot_widget, 'common_style'):
        settings.common_axis_style = AxisStyle.from_qfont_color(
            plot_widget.common_style.text_font,
            plot_widget.common_style.tick_font,
            plot_widget.common_style.color
        )
    
    # Настройки отдельных осей
    if hasattr(plot_widget, 'axises'):
        for axis_name, axis_controller in plot_widget.axises.items():
            axis_settings = AxisSettings()
            
            # Базовые настройки оси
            axis_settings.label = axis_controller.settings.label
            axis_settings.is_style_customized = axis_controller.settings.is_style_customized
            axis_settings.is_inverted = axis_controller.settings.is_inverted
            axis_settings.is_visible = axis_controller.axis.isVisible()
            
            # Лог-режим и автодиапазон
            if axis_name in ['bottom', 'top']:
                axis_settings.log_mode = plot_widget.plotItem.ctrl.logXCheck.isChecked()
            elif axis_name in ['left', 'right']:
                axis_settings.log_mode = plot_widget.plotItem.ctrl.logYCheck.isChecked()
            
            # Диапазон оси
            viewbox = plot_widget.plotItem.vb if axis_name in ['left', 'bottom'] else plot_widget.second_graphView
            if axis_name in ['left', 'right']:
                axis_settings.auto_range = viewbox.autoRangeEnabled()[1]  # Y-axis
                if not axis_settings.auto_range:
                    axis_settings.range = viewbox.viewRange()[1]  # Y-range
            elif axis_name in ['bottom', 'top']:
                axis_settings.auto_range = viewbox.autoRangeEnabled()[0]  # X-axis
                if not axis_settings.auto_range:
                    axis_settings.range = viewbox.viewRange()[0]  # X-range
            
            # Кастомный стиль оси
            if hasattr(axis_controller, 'custom_style'):
                axis_settings.custom_style = AxisStyle.from_qfont_color(
                    axis_controller.custom_style.text_font,
                    axis_controller.custom_style.tick_font,
                    axis_controller.custom_style.color
                )
            
            # Текущий тип стиля
            axis_settings.current_style_type = "custom" if axis_settings.is_style_customized else "common"
            
            settings.axes[axis_name] = axis_settings
    
    # Настройки легенды
    if hasattr(plot_widget, 'legend'):
        try:
            settings.legend_enabled = plot_widget.legend.isVisible()
        except Exception:
            pass

        # --- СОХРАНЕНИЕ ПОЗИЦИЙ ЛЕГЕНД ---
        if plot_widget.legend is not None:
            pos = plot_widget.legend.pos()
            settings.legend_pos = (pos.x(), pos.y())
        if hasattr(plot_widget, 'legend2') and plot_widget.legend2 is not None:
            pos2 = plot_widget.legend2.pos()
            settings.legend2_pos = (pos2.x(), pos2.y())
        # ---------------------------------

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
    
    return settings

def settings_to_dict(settings: GraphFieldSettings) -> Dict[str, Any]:
    """Преобразование настроек в словарь для сериализации"""
    return {
        'title': settings.title,
        'background_color': settings.background_color,
        'grid_enabled': settings.grid_enabled,
        'x_grid_enabled': getattr(settings, 'x_grid_enabled', settings.grid_enabled),
        'y_grid_enabled': getattr(settings, 'y_grid_enabled', settings.grid_enabled),
        'grid_color': settings.grid_color,
        'grid_alpha': settings.grid_alpha,
        'legend_pos': settings.legend_pos,
        'legend2_pos': settings.legend2_pos,
        'common_axis_style': {
            'text_font': settings.common_axis_style.text_font,
            'tick_font': settings.common_axis_style.tick_font,
            'color': settings.common_axis_style.color
        },
        'axes': {name: {
            'label': axis.label,
            'is_style_customized': axis.is_style_customized,
            'is_inverted': axis.is_inverted,
            'is_visible': axis.is_visible,
            'log_mode': axis.log_mode,
            'auto_range': axis.auto_range,
            'range': axis.range,
            'custom_style': {
                'text_font': axis.custom_style.text_font,
                'tick_font': axis.custom_style.tick_font,
                'color': axis.custom_style.color
            }
        } for name, axis in settings.axes.items()},
        'legend_enabled': settings.legend_enabled,
        'legend_text_color': settings.legend_text_color,
        'legend_font': settings.legend_font,
        'antialiasing': settings.antialiasing,
        'is_second_axis_enabled': settings.is_second_axis_enabled,
        # legacy-поле: продолжаем писать Y1, чтобы старые файлы читались
        'is_multiple_selection_enabled': settings.is_multiple_selection_enabled,
        'is_multiple_y1_enabled': getattr(
            settings, 'is_multiple_y1_enabled',
            settings.is_multiple_selection_enabled,
        ),
        'is_multiple_y2_enabled': getattr(
            settings, 'is_multiple_y2_enabled', False,
        ),
    }

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
    
def save_dict_to_hdf5_with_subgroups(group, data_dict):
    """Сохраняет словарь в HDF5-группу, создавая подгруппы для вложенных словарей."""
    for key, value in data_dict.items():
        if value is None:
            value = ''

        if isinstance(value, dict):
            try:
                subgroup = group.create_group(key)
            except (TypeError, ValueError, OSError) as exc:
                logger.warning(
                    "save_dict_to_hdf5_with_subgroups: cannot create "
                    "subgroup %r: %s", key, exc,
                )
                try:
                    group.attrs[key] = json.dumps(value)
                except (TypeError, ValueError):
                    group.attrs[key] = str(value)
                continue
            save_dict_to_hdf5_with_subgroups(subgroup, value)
        else:
            try:
                if isinstance(value, (list, tuple)):
                    group.attrs[key] = json.dumps(value)
                else:
                    group.attrs[key] = value
            except (TypeError, ValueError) as exc:
                logger.warning(
                    "save_dict_to_hdf5_with_subgroups: cannot write "
                    "attr %r: %s", key, exc,
                )
                group.attrs[key] = str(value)

def load_dict_from_hdf5_group(group):
    """Загружает словарь из HDF5 группы, восстанавливая вложенные словари из подгрупп"""
    result = {}
    
    # Читаем атрибуты группы
    for key, value in group.attrs.items():
        if isinstance(value, str) and value == '':
            result[key] = None
        elif isinstance(value, str):
            # Пытаемся распарсить JSON для списков/кортежей
            try:
                result[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                result[key] = value
        else:
            result[key] = value
    
    # Читаем подгруппы
    for key in group:
        subgroup = group[key]
        if isinstance(subgroup, h5py.Group):
            result[key] = load_dict_from_hdf5_group(subgroup)
    
    return result

def dict_to_graph_field_settings(data_dict: Dict[str, Any]) -> GraphFieldSettings:
    """Преобразование словаря в объект GraphFieldSettings"""
    # Создаем базовый объект
    settings = GraphFieldSettings()
    
    # Заполняем простые поля
    settings.title = data_dict.get('title', '')
    settings.background_color = data_dict.get('background_color', '#FFFFFF')
    settings.grid_enabled = data_dict.get('grid_enabled', True)
    settings.x_grid_enabled = bool(data_dict.get('x_grid_enabled', settings.grid_enabled))
    settings.y_grid_enabled = bool(data_dict.get('y_grid_enabled', settings.grid_enabled))
    settings.grid_color = data_dict.get('grid_color', '#CCCCCC')
    settings.grid_alpha = data_dict.get('grid_alpha', 0.5)
    settings.legend_enabled = data_dict.get('legend_enabled', True)
    settings.legend_text_color = data_dict.get('legend_text_color', '#000000')
    settings.legend_font = data_dict.get('legend_font', 'Arial,10,-1,5,50,0,0,0,0,0')
    settings.antialiasing = data_dict.get('antialiasing', True)
    settings.is_second_axis_enabled = data_dict.get('is_second_axis_enabled', False)
    # legacy-поле читаем всегда — от него зависит fallback для новых полей
    settings.is_multiple_selection_enabled = data_dict.get(
        'is_multiple_selection_enabled', False
    )
    settings.is_multiple_y1_enabled = bool(data_dict.get(
        'is_multiple_y1_enabled',
        settings.is_multiple_selection_enabled,     # старый файл → Y1
    ))
    settings.is_multiple_y2_enabled = bool(data_dict.get(
        'is_multiple_y2_enabled',
        False,                                      # старый файл → Y2 single
    ))
    
    # Обрабатываем common_axis_style
    common_axis_style_data = data_dict.get('common_axis_style', {})
    settings.common_axis_style = AxisStyle(
        text_font=common_axis_style_data.get('text_font', 'Arial,13,-1,5,50,0,0,0,0,0'),
        tick_font=common_axis_style_data.get('tick_font', 'Arial,10,-1,5,50,0,0,0,0,0'),
        color=common_axis_style_data.get('color', '#000000')
    )
    
    # Обрабатываем axes
    axes_data = data_dict.get('axes', {})
    settings.axes = {}
    
    for axis_name, axis_data in axes_data.items():
        # Обрабатываем custom_style для оси
        custom_style_data = axis_data.get('custom_style', {})
        custom_style = AxisStyle(
            text_font=custom_style_data.get('text_font', 'Arial,13,-1,5,50,0,0,0,0,0'),
            tick_font=custom_style_data.get('tick_font', 'Arial,10,-1,5,50,0,0,0,0,0'),
            color=custom_style_data.get('color', '#000000')
        )
        
        # Обрабатываем range (может быть списком/кортежем)
        range_data = axis_data.get('range')
        if range_data is None:
            range_tuple = None
        elif (not isinstance(range_data, (list, tuple))
                or len(range_data) != 2):
            logger.warning(
                "dict_to_graph_field_settings: invalid range for axis %r: %r",
                axis_name, range_data,
            )
            range_tuple = None
        else:
            try:
                range_tuple = (float(range_data[0]), float(range_data[1]))
            except (TypeError, ValueError):
                logger.warning(
                    "dict_to_graph_field_settings: non-numeric range "
                    "for axis %r: %r", axis_name, range_data,
                )
                range_tuple = None
        
        # Создаем настройки оси
        axis_settings = AxisSettings(
            label=axis_data.get('label', ''),
            is_style_customized=axis_data.get('is_style_customized', False),
            is_inverted=axis_data.get('is_inverted', False),
            is_visible=axis_data.get('is_visible', True),
            log_mode=axis_data.get('log_mode', False),
            auto_range=axis_data.get('auto_range', True),
            range=range_tuple,
            custom_style=custom_style
        )
        
        settings.axes[axis_name] = axis_settings
    
    return settings

