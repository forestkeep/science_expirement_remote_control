from typing import Dict, Optional
from datetime import datetime
from .hdf5_entities.file import HDF5File
from .models import ProjectFile
from .load_strategies.base import BaseLoadStrategy
from .load_strategies.full_load_strategy import FullLoadStrategy
from .adapters import ProjectToHDF5Adapter, HDF5ToProjectAdapter
import logging

logger = logging.getLogger(__name__)

class HDF5Facade:
    """Фасад для работы с HDF5 файлами проектов."""
    
    def __init__(self, core_to_hdf5_adapter=None, hdf5_to_core_adapter=None, 
                 default_load_strategy: Optional[BaseLoadStrategy] = None):
        """
        Инициализирует фасад с адаптерами.
        
        Args:
            core_to_hdf5_adapter: Адаптер для преобразования объектов ядра в модели HDF5
            hdf5_to_core_adapter: Адаптер для преобразования моделей HDF5 в объекты ядра
            default_load_strategy: Стратегия загрузки по умолчанию
        """
        self.core_to_hdf5 = core_to_hdf5_adapter or ProjectToHDF5Adapter()
        self.hdf5_to_core = hdf5_to_core_adapter or HDF5ToProjectAdapter()
        self.default_load_strategy = default_load_strategy or FullLoadStrategy()
        self._active_files: Dict[str, HDF5File] = {}
    
    def save_project(self, core_project, file_path: str):
        """
        Сохраняет проект ядра в файл.
        
        Args:
            core_project: Объект проекта из ядра приложения
            file_path: Путь к файлу
        """
        project_file = self.core_to_hdf5.convert_project(core_project)
        
        with HDF5File(file_path, 'a') as h5_file:
            h5_file.write_file_attributes(project_file)
            h5_file.write_aliases(project_file.aliases)
            
            for session_id, session in project_file.sessions.items():
                h5_file.write_session(session, session_id=session_id)
    
    def load_project(self, file_path: str, core_project_class, 
                    load_strategy: Optional[BaseLoadStrategy] = None):
        """
        Загружает проект из файла в объект ядра.
        
        Args:
            file_path: Путь к файлу проекта
            core_project_class: Класс проекта ядра приложения
            load_strategy: Стратегия загрузки
            
        Returns:
            Объект проекта ядра
        """
        strategy = load_strategy or self.default_load_strategy
        
        with HDF5File(file_path, 'r', strategy) as h5_file:
            file_attrs = h5_file.read_file_attributes()

            project_file = ProjectFile(
                name=file_attrs.get('name', ''),
                description=file_attrs.get('description', ''),
                version=file_attrs.get('version', '1.0'),
                creation_date=datetime.fromisoformat(file_attrs.get('creation_date', datetime.now().isoformat()))
            )
            logger.info(f"Project {project_file.name} loaded from {file_path}")

            project_file.aliases = h5_file.read_aliases()

            #logger.info(f"Aliases loaded")
            
            session_uuids = h5_file.get_session_uuids()

            for session_id in session_uuids:
                if session_id == "aliases":
                    continue
                logger.info(f"Start loading session {session_id}")
                session = h5_file.read_session(session_id)
                project_file.sessions[session_id] = session
            
            return self.hdf5_to_core.convert(project_file, core_project_class)