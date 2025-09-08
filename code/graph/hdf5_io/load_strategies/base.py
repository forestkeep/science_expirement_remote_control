"""
Базовый класс для стратегий загрузки данных.
Определяет интерфейс для всех стратегий загрузки.
"""
class BaseLoadStrategy:
    """Базовый класс для стратегий загрузки данных из HDF5."""
    
    def load_dataset(self, dataset):
        """
        Загружает dataset в соответствии со стратегией.
        
        Args:
            dataset: HDF5 dataset для загрузки
            
        Returns:
            Загруженные данные или None (если пропускаем)
        """
        pass
    
    def load_attributes(self, group):
        """
        Загружает атрибуты группы.
        
        Args:
            group: HDF5 группа
            
        Returns:
            Словарь атрибутов
        """
        pass
    
    def should_load_dataset(self, dataset_name):
        """
        Определяет, нужно ли загружать dataset.
        
        Args:
            dataset_name: Имя dataset
            
        Returns:
            True если нужно загружать, False если пропустить
        """
        pass