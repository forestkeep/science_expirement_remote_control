from pyqtgraph import PlotWidget
from typing import Dict, Any, Tuple, Optional
import json
import h5py
from .models import GraphFieldSettings, OscilloscopeFieldSettings, AxisSettings, AxisStyle
from graph.customPlotWidget import axisStyle
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

    settings.grid_enabled = plot_widget.is_grid_shown
    # Цвет сетки (берем цвет первой видимой оси)
    for axis_name in ['bottom', 'left']:
        axis = plot_widget.plotItem.getAxis(axis_name)
        if axis and axis.isVisible():
            settings.grid_color = color_to_string(axis.pen().color())
            break
    
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
        settings.legend_enabled = plot_widget.legend.isVisible()
        
        # Позиция легенды (упрощенная логика)
        legend_pos = plot_widget.legend.pos()
        view_size = plot_widget.size()
        if legend_pos.x() < view_size.width() / 2:
            horizontal_pos = "left"
        else:
            horizontal_pos = "right"
        
        if legend_pos.y() < view_size.height() / 2:
            vertical_pos = "top"
        else:
            vertical_pos = "bottom"
        
        settings.legend_position = f"{vertical_pos} {horizontal_pos}"
        
        # Цвет и шрифт легенды
        if plot_widget.legend.items:
            sample_item = plot_widget.legend.items[0][1]
            settings.legend_text_color = color_to_string(plot_widget.legend_color)
    
    return settings


def apply_plot_widget_settings(plot_widget, settings: GraphFieldSettings):
    """Применяет настройки к PatchedPlotWidget при загрузке"""
    
    # Основные настройки
    if settings.title:
        plot_widget.setTitle(settings.title)
    
    # Цвет фона
    if settings.background_color:
        plot_widget.setBackground(settings.background_color)
    
    # Сетка
    plot_widget.plotItem.showGrid(
        x=settings.grid_enabled, 
        y=settings.grid_enabled,
        alpha=settings.grid_alpha
    )
    
    # Применение цвета сетки
    if settings.grid_color:
        for axis_name in ['bottom', 'left']:
            axis = plot_widget.plotItem.getAxis(axis_name)
            if axis:
                axis.setPen(string_to_color(settings.grid_color))
    
    # Общий стиль осей
    if hasattr(plot_widget, 'common_style'):
        plot_widget.common_style.text_font = string_to_qfont(settings.common_axis_style.text_font)
        plot_widget.common_style.tick_font = string_to_qfont(settings.common_axis_style.tick_font)
        plot_widget.common_style.color = string_to_color(settings.common_axis_style.color)
    
    # Настройки отдельных осей
    for axis_name, axis_settings in settings.axes.items():
        if axis_name not in plot_widget.axises:
            continue
            
        axis_controller = plot_widget.axises[axis_name]
        
        # Базовые настройки
        axis_controller.settings.label = axis_settings.label
        axis_controller.settings.is_style_customized = axis_settings.is_style_customized
        axis_controller.settings.is_inverted = axis_settings.is_inverted
        
        # Видимость
        if axis_settings.is_visible:
            axis_controller.show()
        else:
            axis_controller.hide()
        
        # Лог-режим
        if axis_name in ['bottom', 'top']:
            plot_widget.plotItem.setLogMode(x=axis_settings.log_mode)
        elif axis_name in ['left', 'right']:
            plot_widget.plotItem.setLogMode(y=axis_settings.log_mode)
        
        # Диапазон
        viewbox = plot_widget.plotItem.vb if axis_name in ['left', 'bottom'] else plot_widget.second_graphView
        
        if axis_name in ['left', 'right']:
            if axis_settings.auto_range:
                viewbox.enableAutoRange(axis='y')
            elif axis_settings.range:
                viewbox.setYRange(*axis_settings.range)
        elif axis_name in ['bottom', 'top']:
            if axis_settings.auto_range:
                viewbox.enableAutoRange(axis='x')
            elif axis_settings.range:
                viewbox.setXRange(*axis_settings.range)
        
        # Инвертирование
        if axis_name == 'bottom':
            plot_widget.plotItem.vb.invertX(axis_settings.is_inverted)
            if hasattr(plot_widget, 'second_graphView'):
                plot_widget.second_graphView.invertX(axis_settings.is_inverted)
        elif axis_name == 'left':
            plot_widget.plotItem.vb.invertY(axis_settings.is_inverted)
        elif axis_name == 'right':
            if hasattr(plot_widget, 'second_graphView'):
                plot_widget.second_graphView.invertY(axis_settings.is_inverted)
        
        # Стиль оси
        if axis_settings.is_style_customized:
            # Применяем кастомный стиль
            custom_style = axisStyle(
                text_font=string_to_qfont(axis_settings.custom_style.text_font),
                tick_font=string_to_qfont(axis_settings.custom_style.tick_font),
                color=string_to_color(axis_settings.custom_style.color)
            )
            axis_controller.set_custom_style(custom_style)
        else:
            # Применяем общий стиль
            axis_controller.set_common_style(plot_widget.common_style)
    
    # Легенда
    if settings.legend_enabled:
        plot_widget.legend.show()
        # Позиция легенды (упрощенная реализация)
        if "top" in settings.legend_position:
            y_pos = 10
        else:
            y_pos = plot_widget.height() - 70
        
        if "left" in settings.legend_position:
            x_pos = 10
        else:
            x_pos = plot_widget.width() - 90
        
        plot_widget.legend.setPos(x_pos, y_pos)
        
        # Цвет и шрифт легенды
        legend_color = string_to_color(settings.legend_text_color)
        legend_font = string_to_qfont(settings.legend_font)
        plot_widget.set_legend_color(legend_color)
    else:
        plot_widget.legend.hide()
    
    # Вторая ось
    #plot_widget.set_second_axis(settings.second_axis_enabled)
    
    # Дополнительные настройки
    plot_widget.setAntialiasing(settings.antialiasing)
    plot_widget.plotItem.vb.setMouseEnabled(settings.mouse_enabled)
    plot_widget.plotItem.vb.setMenuEnabled(settings.menu_enabled)
    
    # Обновление отображения
    plot_widget.update()


# Вспомогательные функции для работы с осями

def get_axis_viewbox(plot_widget, axis_name: str):
    """Получает соответствующий ViewBox для оси"""
    if axis_name in ['left', 'bottom']:
        return plot_widget.plotItem.vb
    elif axis_name in ['right', 'top']:
        return getattr(plot_widget, 'second_graphView', None)
    return None


def sync_axis_styles(plot_widget):
    """Синхронизирует стили осей после применения настроек"""
    for axis_name, axis_controller in plot_widget.axises.items():
        if axis_controller.settings.is_style_customized:
            axis_controller.__apply_style()
        else:
            axis_controller.set_common_style(plot_widget.common_style)


def update_plot_ranges(plot_widget):
    """Обновляет диапазоны отображения после применения настроек"""
    plot_widget.plotItem.vb.autoRange()
    if hasattr(plot_widget, 'second_graphView'):
        plot_widget.second_graphView.autoRange()


def settings_to_dict(settings: GraphFieldSettings) -> Dict[str, Any]:
    """Преобразование настроек в словарь для сериализации"""
    return {
        'title': settings.title,
        'background_color': settings.background_color,
        'grid_enabled': settings.grid_enabled,
        'grid_color': settings.grid_color,
        'grid_alpha': settings.grid_alpha,
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
        "is_multiple_selection_enabled" : settings.is_multiple_selection_enabled    
    }


def settings_from_dict(data: Dict[str, Any]) -> GraphFieldSettings:
    """Создание настроек из словаря (десериализация)"""
    settings = GraphFieldSettings()
    
    # Основные настройки
    settings.title = data.get('title', "")
    settings.background_color = data.get('background_color', "#FFFFFF")
    settings.grid_enabled = data.get('grid_enabled', True)
    settings.grid_color = data.get('grid_color', "#CCCCCC")
    settings.grid_alpha = data.get('grid_alpha', 0.5)
    
    # Общий стиль осей
    common_style_data = data.get('common_axis_style', {})
    settings.common_axis_style = AxisStyle(
        text_font=common_style_data.get('text_font', "Arial,13,-1,5,50,0,0,0,0,0"),
        tick_font=common_style_data.get('tick_font', "Arial,10,-1,5,50,0,0,0,0,0"),
        color=common_style_data.get('color', "#000000")
    )
    
    # Настройки осей
    axes_data = data.get('axes', {})
    settings.axes = {}
    for axis_name, axis_data in axes_data.items():
        custom_style_data = axis_data.get('custom_style', {})
        axis_settings = AxisSettings(
            label=axis_data.get('label', ""),
            is_style_customized=axis_data.get('is_style_customized', False),
            is_inverted=axis_data.get('is_inverted', False),
            is_visible=axis_data.get('is_visible', True),
            log_mode=axis_data.get('log_mode', False),
            auto_range=axis_data.get('auto_range', True),
            range=axis_data.get('range'),
            custom_style=AxisStyle(
                text_font=custom_style_data.get('text_font', "Arial,13,-1,5,50,0,0,0,0,0"),
                tick_font=custom_style_data.get('tick_font', "Arial,10,-1,5,50,0,0,0,0,0"),
                color=custom_style_data.get('color', "#000000")
            )
        )
        # Устанавливаем текущий тип стиля на основе флага
        axis_settings.current_style_type = "custom" if axis_settings.is_style_customized else "common"
        settings.axes[axis_name] = axis_settings
    
    # Настройки легенды
    settings.legend_enabled = data.get('legend_enabled', True)
    settings.legend_text_color = data.get('legend_text_color', "#000000")
    settings.legend_font = data.get('legend_font', "Arial,10,-1,5,50,0,0,0,0,0")
    
    # Дополнительные настройки
    settings.antialiasing = data.get('antialiasing', True)
    settings.is_second_axis_enabled = data.get('is_second_axis_enabled', False)
    settings.is_multiple_selection_enabled = data.get('is_multiple_selection_enabled', False)
    
    return settings


def settings_to_json(settings: GraphFieldSettings) -> str:
    """Сериализация настроек в JSON строку"""
    return json.dumps(settings_to_dict(settings), indent=2)



def save_settings_to_hdf5(settings: GraphFieldSettings, hdf5_group):
    """Сохранение настроек в HDF5 группу"""
    settings_dict = settings_to_dict(settings)
    
    for key, value in settings_dict.items():
        if isinstance(value, (dict, list)):
            # Сложные структуры сохраняем как JSON строки
            hdf5_group.attrs[key] = json.dumps(value)
        elif value is not None:
            hdf5_group.attrs[key] = value


def load_settings_from_hdf5(hdf5_group) -> GraphFieldSettings:
    """Загрузка настроек из HDF5 группы"""
    data = {}
    
    for key in hdf5_group.attrs:
        value = hdf5_group.attrs[key]
        
        # Пытаемся распарсить JSON строки
        if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
            try:
                data[key] = json.loads(value)
            except json.JSONDecodeError:
                data[key] = value
        else:
            data[key] = value
    
    return settings_from_dict(data)


# Вспомогательные функции для работы со стилями осей

def apply_common_style_to_axis(axis_settings: AxisSettings, common_style: AxisStyle) -> None:
    """Применение общего стиля к настройкам оси"""
    axis_settings.is_style_customized = False
    axis_settings.current_style_type = "common"
    # Note: common_style применяется runtime, не сохраняется в axis_settings


def apply_custom_style_to_axis(axis_settings: AxisSettings, custom_style: AxisStyle) -> None:
    """Применение кастомного стиля к настройкам оси"""
    axis_settings.is_style_customized = True
    axis_settings.current_style_type = "custom"
    axis_settings.custom_style = custom_style


def get_current_axis_style(axis_settings: AxisSettings, common_style: AxisStyle) -> AxisStyle:
    """Получение текущего стиля оси (общего или кастомного)"""
    if axis_settings.current_style_type == "custom" and axis_settings.is_style_customized:
        return axis_settings.custom_style
    else:
        return common_style


def reset_axis_style(axis_settings: AxisSettings) -> None:
    """Сброс стиля оси к общему"""
    axis_settings.is_style_customized = False
    axis_settings.current_style_type = "common"


# Функции для преобразования шрифтов и цветов

def qfont_to_string(font) -> str:
    """Конвертация QFont в строку"""
    return font.toString() if hasattr(font, 'toString') else str(font)


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
    """Сохраняет словарь в HDF5 группу, создавая подгруппы для вложенных словарей"""
    for key, value in data_dict.items():
        if value is None:
            value = ''
        
        if isinstance(value, dict):
            # Создаем подгруппу для словаря
            try:
                subgroup = group.create_group(key)
                save_dict_to_hdf5_with_subgroups(subgroup, value)
            except Exception as e:
                # Fallback: сохраняем как JSON строку
                try:
                    group.attrs[key] = json.dumps(value)
                except:
                    group.attrs[key] = str(value)
        else:
            # Простые значения сохраняем как атрибуты
            try:
                if isinstance(value, (list, tuple)):
                    group.attrs[key] = json.dumps(value)
                else:
                    group.attrs[key] = value
            except Exception as e:
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
    settings.grid_color = data_dict.get('grid_color', '#CCCCCC')
    settings.grid_alpha = data_dict.get('grid_alpha', 0.5)
    settings.legend_enabled = data_dict.get('legend_enabled', True)
    settings.legend_text_color = data_dict.get('legend_text_color', '#000000')
    settings.legend_font = data_dict.get('legend_font', 'Arial,10,-1,5,50,0,0,0,0,0')
    settings.antialiasing = data_dict.get('antialiasing', True)
    settings.is_second_axis_enabled = data_dict.get('is_second_axis_enabled', False)
    settings.is_multiple_selection_enabled = data_dict.get('is_multiple_selection_enabled', False)
    
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
        if range_data is not None and isinstance(range_data, (list, tuple)) and len(range_data) == 2:
            range_tuple = (float(range_data[0]), float(range_data[1]))
        else:
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


def _str_to_font(font_family: str, font_size: int) -> QtGui.QFont:
    """Преобразует строку в QFont"""
    font = QtGui.QFont()
    font.setFamily(font_family)
    font.setPointSize(font_size)
    return font