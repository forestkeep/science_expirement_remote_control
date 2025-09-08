"""
Стратегия загрузки только метаданных.
Пропускает загрузку больших массивов данных для экономии памяти.
"""
from .base import BaseLoadStrategy

class MetadataLoadStrategy(BaseLoadStrategy):
    """Загружает только метаданные, пропускает большие массивы данных."""
    
    def load_dataset(self, dataset):
        """
        Загружает dataset только если он небольшой, иначе возвращает None.
        
        Args:
            dataset: HDF5 dataset для загрузки
            
        Returns:
            Данные если dataset небольшой, иначе None
        """
        pass
    
    def should_load_dataset(self, dataset_name):
        """
        Определяет, нужно ли загружать dataset по его имени.
        Большие datasets (сырые данные, массивы значений) пропускаются.
        
        Args:
            dataset_name: Имя dataset
            
        Returns:
            True для метаданных, False для больших массивов
        """
        pass