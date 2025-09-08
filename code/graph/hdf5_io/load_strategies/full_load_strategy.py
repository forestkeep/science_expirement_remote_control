"""
Стратегия полной загрузки всех данных.
Используется когда нужно загрузить все данные без исключений.
"""
from .base import BaseLoadStrategy

class FullLoadStrategy(BaseLoadStrategy):
    """Загружает все данные без исключений."""
    
    def load_dataset(self, dataset):
        """
        Загружает dataset полностью.
        
        Args:
            dataset: HDF5 dataset для загрузки
            
        Returns:
            Все данные из dataset
        """
        pass
    
    def should_load_dataset(self, dataset_name):
        """
        Всегда возвращает True - загружать все datasets.
        
        Args:
            dataset_name: Имя dataset
            
        Returns:
            Всегда True
        """
        pass