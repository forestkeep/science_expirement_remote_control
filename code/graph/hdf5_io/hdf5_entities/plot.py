import h5py
import numpy as np
from datetime import datetime
from .base import BaseHDF5Entity
from ..models import Plot, StyleSettings, Statistics, HistoryEntry, LinearData, CurveTreeItemData

class HDF5Plot(BaseHDF5Entity):
    """Представление графика в HDF5."""
    
    def write(self, plot: Plot):
        """Записывает график в HDF5."""
        # Записываем основные атрибуты
        attributes = {
            'name': plot.name,
            'description': plot.description if plot.description else "",
            'status': plot.status,
            'is_draw': plot.is_draw,
            'x_name': plot.x_name,
            'y_name': plot.y_name,
            'current_highlight': plot.current_highlight,
            'plot_obj_info': plot.plot_obj_info,
            'parent_graph_field_info': plot.parent_graph_field_info,
            'legend_field_info': plot.legend_field_info,
            'axis': plot.axis
        }
        self._write_attributes(attributes)
        
        # Записываем стиль
        if 'style' not in self._hdf5_object:
            self._hdf5_object.create_group('style')
        style_group = self._hdf5_object['style']
        
        style_attrs = {
            'name': plot.style.name,
            'description': plot.style.description if plot.style.description else "",
            'color': plot.style.color,
            'line_width': plot.style.line_width,
            'line_style': plot.style.line_style
        }
        for key, value in style_attrs.items():
            style_group.attrs[key] = value
        
        # Записываем статистику
        if 'statistics' not in self._hdf5_object:
            self._hdf5_object.create_group('statistics')
        stats_group = self._hdf5_object['statistics']
        
        stats_attrs = {
            'name': plot.statistics.name,
            'description': plot.statistics.description if plot.statistics.description else "",
            'mean': plot.statistics.mean,
            'median': plot.statistics.median,
            'mode': plot.statistics.mode,
            'std_dev': plot.statistics.std_dev,
            'count': plot.statistics.count,
            'min_x': plot.statistics.min_x,
            'max_x': plot.statistics.max_x,
            'min_y': plot.statistics.min_y,
            'max_y': plot.statistics.max_y
        }
        for key, value in stats_attrs.items():
            stats_group.attrs[key] = value
        
        # Записываем историю
        if 'history' in self._hdf5_object:
            del self._hdf5_object['history']
        if plot.history:
            history_group = self._hdf5_object.create_group('history')
            
            for i, entry in enumerate(plot.history):
                entry_group = history_group.create_group(f'entry_{i}')
                entry_attrs = {
                    'name': entry.name,
                    'description': entry.description if entry.description else "",
                    'timestamp': entry.timestamp.isoformat(),
                    'action': entry.action
                }
                for key, value in entry_attrs.items():
                    entry_group.attrs[key] = value
                
                # Записываем параметры как атрибуты
                for param_key, param_value in entry.parameters.items():
                    entry_group.attrs[f'param_{param_key}'] = str(param_value)
        
        
        # Записываем linear_data
        if 'linear_data' in self._hdf5_object:
            del self._hdf5_object['linear_data']
        linear_data_group = self._hdf5_object.create_group('linear_data')
        
        # Записываем атрибуты linear_data
        linear_attrs = {
            
            'device': plot.linear_data.device if plot.linear_data.device else "",
            'channel': plot.linear_data.channel if plot.linear_data.channel else "",
            'curve_name': plot.linear_data.curve_name if plot.linear_data.curve_name else "",
            'number': plot.linear_data.number if plot.linear_data.number is not None else -1,
            'number_axis': plot.linear_data.number_axis if plot.linear_data.number_axis is not None else -1,
            
            # Несериализуемые объекты заменены на текстовые представления
            'saved_pen_info': plot.linear_data.saved_pen_info,
            'is_draw': 1 if plot.linear_data.is_draw else 0, 
            'current_highlight': 1 if plot.linear_data.current_highlight else 0,

            'name': plot.linear_data.name,
            'description': plot.linear_data.description if plot.linear_data.description else "",
            'tip': plot.linear_data.tip,
        }
        for key, value in linear_attrs.items():
            linear_data_group.attrs[key] = value

        linear_data_group.create_dataset('raw_data_x', data=plot.linear_data.raw_data_x,dtype=float, compression='gzip')
        linear_data_group.create_dataset('raw_data_y', data=plot.linear_data.raw_data_y,dtype=float, compression='gzip')
        linear_data_group.create_dataset('filtered_x_data', data=plot.linear_data.filtered_x_data,dtype=float, compression='gzip')
        linear_data_group.create_dataset('filtered_y_data', data=plot.linear_data.filtered_y_data,dtype=float, compression='gzip')

   
        # Записываем tree_item_data
        if 'tree_item_data' in linear_data_group:
            del linear_data_group['tree_item_data']
        tree_item_group = linear_data_group.create_group('tree_item_data')
        
        tree_item_attrs = {
            'name': plot.linear_data.tree_item_data.name,
            'description': plot.linear_data.tree_item_data.description if plot.linear_data.tree_item_data.description else "",
            'font_info': plot.linear_data.tree_item_data.font_info,
            'color_info': plot.linear_data.tree_item_data.color_info,
            'col_font_info': plot.linear_data.tree_item_data.col_font_info
        }
        for key, value in tree_item_attrs.items():
            tree_item_group.attrs[key] = value
        
        # Записываем параметры tree_item
        if 'parameters' in tree_item_group:
            del tree_item_group['parameters']
        if plot.linear_data.tree_item_data.parameters:
            params_group = tree_item_group.create_group('parameters')
            for key, value in plot.linear_data.tree_item_data.parameters.items():
                params_group.attrs[key] = str(value)
           
    
    def read(self) -> Plot:
        """Читает график из HDF5 и возвращает объект Plot."""
        # Читаем основные атрибуты
        name = self._hdf5_object.attrs.get('name', '')
        description = self._hdf5_object.attrs.get('description', '')
        status = self._hdf5_object.attrs.get('status', 'active')
        is_draw = bool(self._hdf5_object.attrs.get('is_draw', False))
        current_highlight = bool(self._hdf5_object.attrs.get('current_highlight', False))
        plot_obj_info = self._hdf5_object.attrs.get('plot_obj_info', 'PlotObject')
        parent_graph_field_info = self._hdf5_object.attrs.get('parent_graph_field_info', 'ViewBox')
        legend_field_info = self._hdf5_object.attrs.get('legend_field_info', 'LegendItem')
        x_name = self._hdf5_object.attrs.get('x_name', 'X_default')
        y_name = self._hdf5_object.attrs.get('y_name', 'Y_default')
        axis = self._hdf5_object.attrs.get('axis', 1)
        
        # Читаем стиль
        style = StyleSettings()
        if 'style' in self._hdf5_object:
            style_group = self._hdf5_object['style']
            style.name = style_group.attrs.get('name', '')
            style.description = style_group.attrs.get('description', '')
            style.color = style_group.attrs.get('color', '#FF0000')
            style.line_width = float(style_group.attrs.get('line_width', 1.0))
            style.line_style = style_group.attrs.get('line_style', 'solid')
        
        # Читаем статистику
        statistics = Statistics()
        if 'statistics' in self._hdf5_object:
            stats_group = self._hdf5_object['statistics']
            statistics.name = stats_group.attrs.get('name', '')
            statistics.description = stats_group.attrs.get('description', '')
            statistics.mean = float(stats_group.attrs.get('mean', 0.0))
            statistics.median = float(stats_group.attrs.get('median', 0.0))
            statistics.mode = float(stats_group.attrs.get('mode', 0.0))
            statistics.std_dev = float(stats_group.attrs.get('std_dev', 0.0))
            statistics.count = int(stats_group.attrs.get('count', 0))
            statistics.min_x = float(stats_group.attrs.get('min_x', 0.0))
            statistics.max_x = float(stats_group.attrs.get('max_x', 0.0))
            statistics.min_y = float(stats_group.attrs.get('min_y', 0.0))
            statistics.max_y = float(stats_group.attrs.get('max_y', 0.0))
        
        # Читаем историю
        history = []
        if 'history' in self._hdf5_object:
            history_group = self._hdf5_object['history']
            for entry_name in history_group:
                entry_group = history_group[entry_name]
                entry = HistoryEntry()
                entry.name = entry_group.attrs.get('name', '')
                entry.description = entry_group.attrs.get('description', '')
                timestamp_str = entry_group.attrs.get('timestamp', '')
                if timestamp_str:
                    entry.timestamp = datetime.fromisoformat(timestamp_str)
                entry.action = entry_group.attrs.get('action', '')
                
                # Читаем параметры
                entry.parameters = {}
                for attr_name in entry_group.attrs:
                    if attr_name.startswith('param_'):
                        param_name = attr_name[6:]  # Убираем префикс 'param_'
                        entry.parameters[param_name] = entry_group.attrs[attr_name]
                
                history.append(entry)
        
        # Читаем linear_data
        linear_data = LinearData()
        if 'linear_data' in self._hdf5_object:
            linear_data_group = self._hdf5_object['linear_data']
            linear_data.device = linear_data_group.attrs.get('device', '')
            linear_data.channel = linear_data_group.attrs.get('channel', '')
            linear_data.curve_name = linear_data_group.attrs.get('curve_name', '')
            number = linear_data_group.attrs.get('number', -1)
            linear_data.number = number if number != -1 else None
            number_axis = linear_data_group.attrs.get('number_axis', -1)
            linear_data.number_axis = number_axis if number_axis != -1 else None
            linear_data.saved_pen_info = linear_data_group.attrs.get('saved_pen_info', 'color:#FF0000,width:1.0')
            linear_data.is_draw = bool(linear_data_group.attrs.get('is_draw', False))
            linear_data.current_highlight = bool(linear_data_group.attrs.get('current_highlight', False))
            linear_data.name = linear_data_group.attrs.get('name', '')
            linear_data.description = linear_data_group.attrs.get('description', '')
            linear_data.tip = linear_data_group.attrs.get('tip', 'linear')
            
            # Читаем datasets
            if 'raw_data_x' in linear_data_group:
                linear_data.raw_data_x = linear_data_group['raw_data_x'][:]
            if 'raw_data_y' in linear_data_group:
                linear_data.raw_data_y = linear_data_group['raw_data_y'][:]
            if 'filtered_x_data' in linear_data_group:
                linear_data.filtered_x_data = linear_data_group['filtered_x_data'][:]
            if 'filtered_y_data' in linear_data_group:
                linear_data.filtered_y_data = linear_data_group['filtered_y_data'][:]
            
            # Читаем tree_item_data
            if 'tree_item_data' in linear_data_group:
                tree_item_group = linear_data_group['tree_item_data']
                tree_item_data = CurveTreeItemData()
                tree_item_data.name = tree_item_group.attrs.get('name', '')
                tree_item_data.description = tree_item_group.attrs.get('description', '')
                tree_item_data.font_info = tree_item_group.attrs.get('font_info', 'Italic,10')
                tree_item_data.color_info = tree_item_group.attrs.get('color_info', '#ff30ea')
                tree_item_data.col_font_info = tree_item_group.attrs.get('col_font_info', '15')
                
                # Читаем параметры tree_item
                if 'parameters' in tree_item_group:
                    params_group = tree_item_group['parameters']
                    tree_item_data.parameters = {}
                    for attr_name in params_group.attrs:
                        tree_item_data.parameters[attr_name] = params_group.attrs[attr_name]
                
                linear_data.tree_item_data = tree_item_data
        
        # Создаем и возвращаем объект Plot
        plot = Plot(
            name=name,
            description=description,
            status=status,
            style=style,
            statistics=statistics,
            history=history,
            linear_data=linear_data,
            x_name = x_name,
            y_name = y_name,
            plot_obj_info=plot_obj_info,
            parent_graph_field_info=parent_graph_field_info,
            legend_field_info=legend_field_info,
            is_draw=is_draw,
            current_highlight=current_highlight,
            axis=axis
        )
        
        return plot