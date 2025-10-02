# hdf5_entities/session.py
import h5py
from typing import Dict, Optional
import datetime
from .base import BaseHDF5Entity
from ..models import Session, SessionParameters, FieldSettings, DataManager, Plot, GraphFieldSettings, OscilloscopeFieldSettings, OscillogramData, ParameterData
from .plot import HDF5Plot
from ..utils import settings_to_dict, save_dict_to_hdf5_with_subgroups, load_dict_from_hdf5_group, dict_to_graph_field_settings
from ..load_strategies.base import BaseLoadStrategy



def print_nested(data, indent=0):
    for key, value in data.items():
        if isinstance(value, dict):
            print(' ' * indent + f'{key}:')
            print_nested(value, indent + 2)
        else:
            print(' ' * indent + f'{key}: {value}')


class HDF5Session(BaseHDF5Entity):
    """Представление сессии в HDF5."""
    
    def __init__(self, hdf5_object: h5py.Group, load_strategy: Optional[BaseLoadStrategy] = None):
        super().__init__(hdf5_object)
        self.load_strategy = load_strategy
    
    def write(self, session: Session):
        """Записывает сессию в HDF5."""
        # Записываем основные атрибуты сессии
        attributes = {
            'name': session.name,
            'description': session.description
        }
        self._write_attributes(attributes)
        
        # Записываем параметры сессии
        if 'parameters' not in self._hdf5_object:
            self._hdf5_object.create_group('parameters')
        params_group = self._hdf5_object['parameters']
        
        params_attrs = {
            'name': session.parameters.name,
            'description': session.parameters.description,
            'uuid': session.parameters.uuid,
            'experiment_date': session.parameters.experiment_date.isoformat() if session.parameters.experiment_date else None,
            'operator': session.parameters.operator,
            'comment': session.parameters.comment
        }
        for key, value in params_attrs.items():
            if value is not None:
                params_group.attrs[key] = value
        
        # Записываем настройки полей
        if 'field_settings' not in self._hdf5_object:
            self._hdf5_object.create_group('field_settings')
        field_settings_group = self._hdf5_object['field_settings']
        
        # Настройки поля графиков
        if 'graph_field' not in field_settings_group:
            field_settings_group.create_group('graph_field')
        graph_field_group = field_settings_group['graph_field']
        
        graph_field_attrs = settings_to_dict(session.field_settings.graph_field)
        save_dict_to_hdf5_with_subgroups(graph_field_group, graph_field_attrs)
        
        # Настройки поля осциллограмм (аналогично)
        if 'oscilloscope_field' not in field_settings_group:
            field_settings_group.create_group('oscilloscope_field')
        oscilloscope_field_group = field_settings_group['oscilloscope_field']
        
        oscilloscope_field_attrs = settings_to_dict(session.field_settings.oscilloscope_field)

        save_dict_to_hdf5_with_subgroups(oscilloscope_field_group, oscilloscope_field_attrs)
        
        # Записываем менеджер данных
        if 'data_manager' not in self._hdf5_object:
            self._hdf5_object.create_group('data_manager')
        data_manager_group = self._hdf5_object['data_manager']
        
        # Данные осциллограмм
        if 'oscillogram_data' not in data_manager_group:
            data_manager_group.create_group('oscillogram_data')
        oscillogram_data_group = data_manager_group['oscillogram_data']
        
        for data_name, data in session.data_manager.oscillogram_data.items():
            if data_name in oscillogram_data_group:
                del oscillogram_data_group[data_name]
            data_entity_group = oscillogram_data_group.create_group(data_name)
            
            # Используем HDF5OscillogramData для записи
            from .oscillogram_data import HDF5OscillogramData
            data_entity = HDF5OscillogramData(data_entity_group)
            data_entity.write(data)

        # Данные параметров
        if 'parameters_data' not in data_manager_group:
            data_manager_group.create_group('parameters_data')
        parameters_data_group = data_manager_group['parameters_data']
        
        for data_name, data in session.data_manager.parameter_data.items():
            if data_name in parameters_data_group:
                del parameters_data_group[data_name]
            data_entity_group = parameters_data_group.create_group(data_name)
            
            # Используем HDF5OscillogramData для записи
            from .oscillogram_data import HDF5OscillogramData
            data_entity = HDF5OscillogramData(data_entity_group)
            data_entity.write(data)
        
        
        # Записываем графики
        if 'plots' not in self._hdf5_object:
            self._hdf5_object.create_group('plots')
        plots_group = self._hdf5_object['plots']
        
        for plot_name, plot in session.plots.items():
            if plot_name in plots_group:
                del plots_group[plot_name]
            plot_entity_group = plots_group.create_group(plot_name)
            plot_entity = HDF5Plot(plot_entity_group)
            plot_entity.write(plot)
    
    def read(self) -> Session:
        """Читает сессию из HDF5 и возвращает объект Session."""
        # Читаем основные атрибуты сессии
        name = self._hdf5_object.attrs.get('name', '')
        description = self._hdf5_object.attrs.get('description', '')

        print("----------------------Чтение--------------------------")
        print(f"{name=} {description=}")
        
        # Читаем параметры сессии
        parameters = SessionParameters()
        if 'parameters' in self._hdf5_object:
            params_group = self._hdf5_object['parameters']
            print(f"{params_group=}")
            for param in params_group.attrs:
                print(param, params_group.attrs[param])
            parameters.name = params_group.attrs['name']
            parameters.description = params_group.attrs.get('description', '')
            parameters.uuid = params_group.attrs['uuid']
            exp_date_str = params_group.attrs.get('experiment_date', '')
            if exp_date_str:
                parameters.experiment_date = datetime.fromisoformat(exp_date_str)
            parameters.operator = params_group.attrs.get('operator', '')
            parameters.comment = params_group.attrs.get('comment', '')
        print("-----------------------Конец чтения--------------------------")
        # Читаем настройки полей
        field_settings = self.read_field_settings()
        
        # Читаем менеджер данных
        data_manager = DataManager()
        if 'data_manager' in self._hdf5_object:
            data_manager_group = self._hdf5_object['data_manager']
            
            # Читаем данные осциллограмм
            if 'oscillogram_data' in data_manager_group:
                oscillogram_data_group = data_manager_group['oscillogram_data']
                for data_name in oscillogram_data_group:
                    data_entity_group = oscillogram_data_group[data_name]
                    data = OscillogramData()
                    data.device = data_entity_group.attrs.get('device', '')
                    data.channel = data_entity_group.attrs.get('channel', '')
                    data.parameter = data_entity_group.attrs.get('parameter', '')
                    if 'time_values' in data_entity_group:
                        data.time_values = data_entity_group['time_values'][:]
                    if 'data_values' in data_entity_group:
                        data.data_values = data_entity_group['data_values'][:]
                    data_manager.oscillogram_data[data_name] = data
            
            # Читаем данные параметров
            if 'parameters_data' in data_manager_group:
                parameters_data_group = data_manager_group['parameters_data']
                for data_name in parameters_data_group:
                    data_entity_group = parameters_data_group[data_name]
                    data = ParameterData()
                    data.device = data_entity_group.attrs.get('device', '')
                    data.channel = data_entity_group.attrs.get('channel', '')
                    data.parameter = data_entity_group.attrs.get('parameter', '')
                    if 'time_values' in data_entity_group:
                        data.time_values = data_entity_group['time_values'][:]
                    if 'data_values' in data_entity_group:
                        data.data_values = data_entity_group['data_values'][:]
                    data_manager.parameter_data[data_name] = data

        
        # Читаем графики
        plots = {}
        if 'plots' in self._hdf5_object:
            plots_group = self._hdf5_object['plots']
            for plot_name in plots_group:
                plot_entity_group = plots_group[plot_name]
                plot_entity = HDF5Plot(plot_entity_group)
                plot = plot_entity.read()
                plots[plot_name] = plot
        
        # Создаем и возвращаем объект сессии
        session = Session(
            name=name,
            description=description,
            parameters=parameters,
            field_settings=field_settings,
            data_manager=data_manager,
            plots=plots
        )
        
        return session
    
    def read_field_settings(self) -> FieldSettings:
        field_settings = FieldSettings()
        if 'field_settings' in self._hdf5_object:
            field_settings_group = self._hdf5_object['field_settings']
            
            # Читаем настройки поля графиков (новая версия)
            if 'graph_field' in field_settings_group:
                graph_field_group = field_settings_group['graph_field']
                
                # Загружаем данные из HDF5 группы в словарь
                graph_field_data = load_dict_from_hdf5_group(graph_field_group)
                #print_nested(graph_field_data)
                # Преобразуем словарь в объект GraphFieldSettings
                graph_field_settings = dict_to_graph_field_settings(graph_field_data)
                field_settings.graph_field = graph_field_settings
            
            # Читаем настройки поля осциллограмм (старая версия - оставляем как есть)
            if 'oscilloscope_field' in field_settings_group:
                oscilloscope_field_group = field_settings_group['oscilloscope_field']
                oscilloscope_field = OscilloscopeFieldSettings()
                oscilloscope_field.name = oscilloscope_field_group.attrs.get('name', '')
                oscilloscope_field.description = oscilloscope_field_group.attrs.get('description', '')
                oscilloscope_field.title = oscilloscope_field_group.attrs.get('title', '')
                oscilloscope_field.background_color = oscilloscope_field_group.attrs.get('background_color', '#FFFFFF')
                oscilloscope_field.foreground_color = oscilloscope_field_group.attrs.get('foreground_color', '#000000')
                oscilloscope_field.grid_enabled = bool(oscilloscope_field_group.attrs.get('grid_enabled', True))
                oscilloscope_field.grid_color = oscilloscope_field_group.attrs.get('grid_color', '#CCCCCC')
                oscilloscope_field.grid_alpha = float(oscilloscope_field_group.attrs.get('grid_alpha', 0.5))
                oscilloscope_field.x_label = oscilloscope_field_group.attrs.get('x_label', 'X Axis')
                oscilloscope_field.y_label = oscilloscope_field_group.attrs.get('y_label', 'Y Axis')
                oscilloscope_field.x_log_mode = bool(oscilloscope_field_group.attrs.get('x_log_mode', False))
                oscilloscope_field.y_log_mode = bool(oscilloscope_field_group.attrs.get('y_log_mode', False))
                oscilloscope_field.x_auto_range = bool(oscilloscope_field_group.attrs.get('x_auto_range', True))
                oscilloscope_field.y_auto_range = bool(oscilloscope_field_group.attrs.get('y_auto_range', True))
                
                x_range = oscilloscope_field_group.attrs.get('x_range', None)
                y_range = oscilloscope_field_group.attrs.get('y_range', None)
                oscilloscope_field.x_range = tuple(x_range) if x_range is not None else None
                oscilloscope_field.y_range = tuple(y_range) if y_range is not None else None
                
                oscilloscope_field.legend_enabled = bool(oscilloscope_field_group.attrs.get('legend_enabled', True))
                oscilloscope_field.antialiasing = bool(oscilloscope_field_group.attrs.get('antialiasing', True))
                field_settings.oscilloscope_field = oscilloscope_field
        
        return field_settings