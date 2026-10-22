import h5py
from typing import Any, Dict

class BaseHDF5Entity:
    """Базовый класс для всех HDF5-сущностей."""
    
    def __init__(self, hdf5_object: h5py.Group):
        self._hdf5_object = hdf5_object
    
    def _write_attributes(self, attributes: Dict[str, Any]):
        """Записывает атрибуты в HDF5-объект."""
        for key, value in attributes.items():
            if value is not None:
                if isinstance(value, (list, dict)):
                    self._hdf5_object.attrs[key] = str(value)
                else:
                    self._hdf5_object.attrs[key] = value
    
    def _read_attributes(self) -> Dict[str, Any]:
        """Читает атрибуты из HDF5-объекта."""
        return dict(self._hdf5_object.attrs)
    
    @property
    def name(self) -> str:
        """Возвращает имя объекта в HDF5."""
        return self._hdf5_object.name.split('/')[-1]
    
    @property
    def path(self) -> str:
        """Возвращает полный путь к объекту в HDF5."""
        return self._hdf5_object.name