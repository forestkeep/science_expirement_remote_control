# hdf5_entities/file.py
import h5py
from datetime import datetime
from typing import Dict, Optional
from .base import BaseHDF5Entity
from ..models import ProjectFile, Session
from .session import HDF5Session
from ..load_strategies.base import BaseLoadStrategy

class HDF5File(BaseHDF5Entity):
    """Представление HDF5 файла."""
    
    def __init__(self, file_path: str, mode: str = 'a', load_strategy: Optional[BaseLoadStrategy] = None):
        self.file_path = file_path
        self.mode = mode
        self._h5file = h5py.File(file_path, mode)
        self.load_strategy = load_strategy
        super().__init__(self._h5file)
    
    def close(self):
        """Закрывает файл."""
        self._h5file.close()
    
    def write_file_attributes(self, project_file: ProjectFile):
        """Записывает атрибуты файла."""
        attributes = {
            'version app': project_file.version,
            'creation_date': project_file.creation_date.isoformat(),
            #'name': "rtr",
            #'description': "qqqq",
            #'type' : "graphics"
        }
        self._write_attributes(attributes)
    
    def read_file_attributes(self) -> Dict:
        """Читает атрибуты файла и возвращает словарь."""
        return self._read_attributes()
    
    def write_session(self, session: Session, session_id: Optional[str] = None):
        """Записывает сессию в файл."""
        #ses_name = session.name.replace('\\', '_').replace('/', '_')
        uuid = session.parameters.uuid
        if uuid in self._h5file:
            del self._h5file[uuid]
        session_group = self._h5file.create_group(uuid)
        session_entity = HDF5Session(session_group)
        session_entity.write(session)

    def write_aliases(self, aliases: Dict[str, str]):
        if 'aliases' in self._h5file:
            del self._h5file['aliases']

        alias_group = self._h5file.create_group('aliases')
        for original_name, alias in aliases.items():
            alias_group.attrs[original_name] = alias

    def read_aliases(self) -> Dict[str, str]:
        """Читает псевднимы из файла и возвращает словарь."""
        if 'aliases' not in self._h5file:
            return {}
        
        alias_group = self._h5file['aliases']
        return dict(alias_group.attrs)

    
        
    def read_session(self, session_name: str) -> Session:
        """Читает сессию из файла."""
        if session_name not in self._h5file:
            raise KeyError(f"Session '{session_name}' not found in file.")
        
        session_group = self._h5file[session_name]
        session_entity = HDF5Session(session_group, self.load_strategy)
        return session_entity.read()
    
    def get_session_uuids(self) -> list:
        """Возвращает список uuid сессий в файле."""
        return list(self._h5file.keys())
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()