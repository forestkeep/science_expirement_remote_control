import h5py
import numpy as np
from .base import BaseHDF5Entity
from ..models import OscillogramData

class HDF5OscillogramData(BaseHDF5Entity):
    """Представление данных осциллограмм в HDF5."""
    
    def write(self, data: OscillogramData):
        """Записывает данные осциллограммы в HDF5."""
        # Записываем атрибуты
        attributes = {
            'name': data.name,
            'description': data.description,
            'device': data.device,
            'channel': data.channel,
            'parameter': data.parameter
        }
        self._write_attributes(attributes)
        
        # Записываем datasets
        if 'time_values' in self._hdf5_object:
            del self._hdf5_object['time_values']
        if 'data_values' in self._hdf5_object:
            del self._hdf5_object['data_values']
            
        self._hdf5_object.create_dataset('time_values', data=data.time_values,dtype=float, compression='gzip')
        self._hdf5_object.create_dataset('data_values', data=data.data_values,dtype=float, compression='gzip')
    
    def read(self) -> OscillogramData:
        """Читает данные осциллограммы из HDF5."""
        # Читаем атрибуты
        attrs = self._read_attributes()
        
        # Читаем datasets
        time_values = np.array(self._hdf5_object['time_values'])
        data_values = np.array(self._hdf5_object['data_values'])
        
        return OscillogramData(
            name=attrs.get('name', ''),
            description=attrs.get('description', ''),
            device=attrs.get('device', ''),
            channel=attrs.get('channel', ''),
            parameter=attrs.get('parameter', ''),
            time_values=time_values,
            data_values=data_values
        )