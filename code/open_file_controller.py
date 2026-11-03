# code/open_file_controller.py
"""Классификация файла для UI: какой редактор открыть.
"""
import os

import h5py
import logging

logger = logging.getLogger(__name__)


class FileTypeChecker:
    SUPPORTED_EXTENSIONS = ['.ns', '.hdf5', '.h5']  # .h5 — сокращение HDF5
    # Сигнатура HDF5 (первые 8 байт)
    HDF5_SIGNATURE = b'\x89HDF\r\n\x1a\n'

    def __init__(self, file_path: str):
        self.original_path = file_path
        self.file_path = file_path
        self._type = None
        self._exists = None

    def _find_file_with_extensions(self) -> str | None:
        """Если файл по точному пути не найден, пробуем добавить расширения.

        Возвращает полный путь к найденному файлу или None.
        """
        if os.path.isfile(self.original_path):
            return self.original_path

        directory = os.path.dirname(self.original_path)
        basename = os.path.basename(self.original_path)

        for ext in self.SUPPORTED_EXTENSIONS:
            candidate = os.path.join(directory, basename + ext)
            if os.path.isfile(candidate):
                return candidate
        return None

    def exists(self) -> bool:
        if self._exists is None:
            found = self._find_file_with_extensions()
            if found:
                self.file_path = found
                self._exists = True
            else:
                self._exists = False
        return self._exists

    def is_readable(self) -> bool:
        return self.exists() and os.access(self.file_path, os.R_OK)

    def _check_hdf5_by_content(self) -> bool:
        """Проверяет сигнатуру HDF5 в начале файла.

        Достаточно 8 байт: файл, который h5py не откроет, всё равно
        упадёт в HDF5Facade.load_project, и open_project_file корректно
        это обработает. Читать h5py.File ради классификации не нужно —
        это лишний I/O на многомегабайтных проектах.
        """
        if not self.is_readable():
            return False
        try:
            with open(self.file_path, 'rb') as f:
                header = f.read(len(self.HDF5_SIGNATURE))
                return header == self.HDF5_SIGNATURE
        except (IOError, OSError):
            return False

    def is_hdf5(self) -> bool:
        if not self.exists():
            return False
        if self.file_path.lower().endswith('.hdf5') or self.file_path.lower().endswith('.h5'):
            return self._check_hdf5_by_content()
        return False

    def is_ns(self) -> bool:
        if not self.exists():
            logger.info("Файл не существует: %s", self.file_path)
            return False
        if self.file_path.lower().endswith('.ns'):
            # Защита от HDF5-файла, переименованного в .ns: содержимое
            # важнее расширения. Дальнейшая семантика (.ns-парсер) уже
            # проверяется в load_file с hint="installation_spec".
            return not self.is_hdf5()
        return False

    def detect_type(self) -> str:
        """'ns' | 'hdf5' | None."""
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
        """Алиас для detect_type()."""
        return self.detect_type()

    def is_supported(self) -> bool:
        return self.detect_type() is not None

    def validate(self) -> tuple[bool, str]:
        """Комплексная проверка: существование, читаемость, поддерживаемость."""
        if not self.exists():
            logger.info("Файл не существует: %s", self.file_path)
            return False, f"Файл не существует: {self.file_path}"
        if not self.is_readable():
            return False, f"Файл недоступен для чтения: {self.file_path}"

        file_type = self.detect_type()
        if file_type is None:
            return False, (
                f"Неподдерживаемый тип файла (ожидается .ns или .hdf5): "
                f"{self.file_path}"
            )
        return True, f"Файл распознан как тип '{file_type}'"