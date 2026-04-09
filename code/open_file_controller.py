import os
import h5py
import logging

logger = logging.getLogger(__name__)

class FileTypeChecker:
    SUPPORTED_EXTENSIONS = ['.ns', '.hdf5', '.h5']  # .h5 – частое сокращение для HDF5
    # Сигнатура HDF5 (первые 8 байт)
    HDF5_SIGNATURE = b'\x89HDF\r\n\x1a\n'

    def __init__(self, file_path: str):
        self.original_path = file_path
        self.file_path = file_path
        self._type = None
        self._exists = None

    def _find_file_with_extensions(self) -> str | None:
        """
        Если файл по точному пути не найден, пробуем добавить поддерживаемые расширения.
        Возвращает полный путь к найденному файлу или None.
        """
        # Сначала проверим, существует ли точно такой путь
        if os.path.isfile(self.original_path):
            return self.original_path

        # Разделим путь на директорию и базовое имя (без расширения)
        directory = os.path.dirname(self.original_path)
        basename = os.path.basename(self.original_path)

        # Если в basename уже есть точка, возможно расширение есть, но файл всё равно не найден
        # Всё равно попробуем добавить наши расширения
        for ext in self.SUPPORTED_EXTENSIONS:
            candidate = os.path.join(directory, basename + ext)
            if os.path.isfile(candidate):
                return candidate
        return None

    def exists(self) -> bool:
        """Проверяет существование файла, автоматически подбирая расширение при необходимости."""
        if self._exists is None:
            found = self._find_file_with_extensions()
            if found:
                self.file_path = found   # обновляем путь на реальный
                self._exists = True
            else:
                self._exists = False
        return self._exists

    def is_readable(self) -> bool:
        """Проверяет, доступен ли файл для чтения."""
        return self.exists() and os.access(self.file_path, os.R_OK)

    def _check_hdf5_by_content(self) -> bool:
        """
        Проверяет сигнатуру HDF5 в начале файла.
        Возвращает True, если файл является валидным HDF5.
        """
        if not self.is_readable():
            return False
        try:
            with open(self.file_path, 'rb') as f:
                header = f.read(len(self.HDF5_SIGNATURE))
                return header == self.HDF5_SIGNATURE
        except (IOError, OSError):
            return False

    def _check_hdf5_by_h5py(self) -> bool:
        """
        Альтернативная проверка с использованием библиотеки h5py.
        Более надёжная, но требует установки h5py и может быть медленной.
        """
        if not self.is_readable():
            return False
        try:
            with h5py.File(self.file_path, 'r') as _:
                return True
        except (OSError, IOError, h5py.FileIOError, ValueError):
            return False

    def is_hdf5(self) -> bool:
        """Определяет, является ли файл HDF5."""
        if not self.exists():
            return False
        # Сначала проверяем расширение (быстрая эвристика)
        if self.file_path.lower().endswith('.hdf5') or self.file_path.lower().endswith('.h5'):
            # Если расширение подходит, проверяем содержимое
            return self._check_hdf5_by_content() or self._check_hdf5_by_h5py()
        return False

    def is_ns(self) -> bool:
        """Определяет, является ли файл формата .ns."""
        if not self.exists():
            logger.info(f"Файл не существует: {self.file_path}")
            return False
        # Проверяем расширение. Для .ns можно добавить проверку сигнатуры,
        # если известен формат. Здесь предполагаем, что расширения достаточно.
        if self.file_path.lower().endswith('.ns'):
            # Дополнительная проверка: файл не должен быть HDF5,
            # так как .ns может быть обычным текстовым или бинарным.
            return not self.is_hdf5()
        return False

    def detect_type(self) -> str:
        """
        Определяет тип файла. Возвращает:
        - 'ns' для .ns
        - 'hdf5' для .hdf5
        - None, если тип не распознан или файл не существует
        """
        if self._type is not None:
            return self._type

        if not self.exists():
            self._type = None
            return None

        if self.is_hdf5():
            self._type = 'hdf5'
        elif self.is_ns():
            self._type = 'ns'
        else:
            self._type = None
        return self._type

    def get_type(self) -> str:
        """Алиас для detect_type() – возвращает определённый тип."""
        return self.detect_type()

    def is_supported(self) -> bool:
        """Проверяет, является ли файл поддерживаемым типом (.ns или .hdf5)."""
        return self.detect_type() is not None

    def validate(self) -> tuple[bool, str]:
        """
        Комплексная проверка: существование, читаемость, поддерживаемость.
        Возвращает (статус, сообщение).
        """
        if not self.exists():
            logger.info(f"Файл не существует: {self.file_path}")
            return False, f"Файл не существует: {self.file_path}"
        if not self.is_readable():
            return False, f"Файл недоступен для чтения: {self.file_path}"

        file_type = self.detect_type()
        if file_type is None:
            return False, f"Неподдерживаемый тип файла (ожидается .ns или .hdf5): {self.file_path}"
        return True, f"Файл распознан как тип '{file_type}'"