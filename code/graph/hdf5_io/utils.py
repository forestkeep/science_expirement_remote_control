from pyqtgraph import PlotWidget
from typing import Dict, Any, Tuple, Optional
from .models import GraphFieldSettings, OscilloscopeFieldSettings

def extract_plot_widget_settings(plot_widget: PlotWidget) -> Dict[str, Any]:
    """Извлекает настройки из PlotWidget для сохранения"""
    settings = {}
    
    # Основные настройки
    settings['title'] = plot_widget.titleLabel.text if hasattr(plot_widget, 'titleLabel') else ""
    
    # Цвета
    viewbox = plot_widget.getViewBox()
    #settings['background_color'] = viewbox.backgroundBrush().color().name()
    
    # Настройки сетки
    #settings['grid_enabled'] = plot_widget.showGrid()[0]  # x grid
    settings['grid_color'] = "#CCCCCC"  # Нужно извлечь реальный цвет
    
    # Настройки осей
    x_axis = plot_widget.getAxis('bottom')
    y_axis = plot_widget.getAxis('left')
    
    settings['x_label'] = x_axis.labelText
    settings['y_label'] = y_axis.labelText
    settings['x_log_mode'] = x_axis.logMode
    settings['y_log_mode'] = y_axis.logMode
    
    # Диапазон осей
    viewbox = plot_widget.getViewBox()
    settings['x_range'] = viewbox.viewRange()[0] if viewbox.viewRange() else None
    settings['y_range'] = viewbox.viewRange()[1] if viewbox.viewRange() else None
    
    # Настройки легенды
    if hasattr(plot_widget, 'legend'):
        settings['legend_enabled'] = plot_widget.legend.isVisible()
        # Позиция легенды нужно определить дополнительно
    
    # Дополнительные настройки
    #settings['antialiasing'] = viewbox.antialias
    settings['mouse_enabled'] = viewbox.mouseEnabled
    settings['menu_enabled'] = viewbox.menuEnabled
    
    return settings

def apply_plot_widget_settings(plot_widget: PlotWidget, settings: Dict[str, Any]):
    """Применяет настройки к PlotWidget при загрузке"""
    # Основные настройки
    if 'title' in settings:
        plot_widget.setTitle(settings['title'])
    
    # Цвета
    if 'background_color' in settings:
        plot_widget.setBackground(settings['background_color'])
    
    # Сетка
    if 'grid_enabled' in settings:
        plot_widget.showGrid(
            x=settings['grid_enabled'], 
            y=settings['grid_enabled'],
            alpha=settings.get('grid_alpha', 0.5)
        )
    
    # Оси
    if 'x_label' in settings:
        plot_widget.setLabel('bottom', settings['x_label'])
    if 'y_label' in settings:
        plot_widget.setLabel('left', settings['y_label'])
    
    if 'x_log_mode' in settings:
        plot_widget.setLogMode(x=settings['x_log_mode'])
    if 'y_log_mode' in settings:
        plot_widget.setLogMode(y=settings['y_log_mode'])
    
    # Диапазон
    if 'x_range' in settings and settings['x_range']:
        plot_widget.setXRange(*settings['x_range'])
    if 'y_range' in settings and settings['y_range']:
        plot_widget.setYRange(*settings['y_range'])
    
    # Легенда
    if 'legend_enabled' in settings:
        if settings['legend_enabled'] and not hasattr(plot_widget, 'legend'):
            plot_widget.addLegend()
        elif hasattr(plot_widget, 'legend'):
            plot_widget.legend.setVisible(settings['legend_enabled'])
    
    # Дополнительные настройки
    viewbox = plot_widget.getViewBox()
    if 'antialiasing' in settings:
        viewbox.setAntialiasing(settings['antialiasing'])
    if 'mouse_enabled' in settings:
        viewbox.setMouseEnabled(settings['mouse_enabled'])
    if 'menu_enabled' in settings:
        viewbox.setMenuEnabled(settings['menu_enabled'])