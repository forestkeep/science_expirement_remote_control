import re
import logging
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

logger = logging.getLogger(__name__)


class IconGenerator:
    """
    Генерирует иконки для каналов, используя цвет из ColorManager.
    Кэширует результат по (device_key, is_measure, channel_number, size).
    """
    def __init__(self, color_manager):
        self.color_manager = color_manager
        self._cache = {}  # key -> QIcon

    # ---------- вспомогательный метод парсинга ----------
    @staticmethod
    def _parse_channel_string(s: str):
        """
        Пытается извлечь из строки вида 'WPS300s_1 ch-1_act'
        название прибора, номер канала и тип.
        Возвращает (device_name, channel_number, ch_type) или None.
        """
        if not isinstance(s, str):
            return None
        # допустимые типы
        match = re.match(r'^(.+)\s+ch-(\d+)_(act|meas)$', s, re.IGNORECASE)
        if match:
            device = match.group(1)
            number = int(match.group(2))
            ch_type = match.group(3).lower()
            return device, number, ch_type
        return None

    # ---------- изменённый get_icon ----------
    def get_icon(self, device_key, ch_type=None, channel_number=None, size: int = 32) -> QIcon:
        """
        Возвращает QIcon для канала.

        Параметры:
        -----------
        device_key : str или объект
            Если передана строка, МОЖЕТ содержать полную информацию
            в формате "ИмяПрибора ch-<номер>_<тип>", например:
                "WPS300s_1 ch-1_act"
            Если это обычный идентификатор (не строка или не соответствует формату),
            используется как есть.
        ch_type : str, optional
            Тип канала: 'meas' (измерение) или 'act' (действие).
            Если не задан, будет извлечён из device_key (если это строка нужного формата).
        channel_number : int, optional
            Номер канала.
            Если не задан, будет извлечён из device_key (если это строка нужного формата).
        size : int
            Размер иконки в пикселях (по умолчанию 32).

        Поведение:
        ----------
        1. Если ch_type и/или channel_number не переданы (None),
           а device_key является строкой подходящего формата,
           значения извлекаются из неё.
        2. Явно переданные ch_type / channel_number всегда имеют
           приоритет над извлечёнными из строки.
        3. Идентификатор прибора (для получения цвета) всегда
           берётся из строки (если она распознана) либо используется
           device_key без изменений.
        """
        final_device = device_key
        final_type = ch_type
        final_number = channel_number

        if isinstance(device_key, str) and (ch_type is None or channel_number is None):
            parsed = self._parse_channel_string(device_key)
            if parsed:
                dev_name, num, typ = parsed
                final_device = dev_name
                if ch_type is None:
                    final_type = typ
                if channel_number is None:
                    final_number = num

        if final_type is None or final_number is None:
            logger.error(
                "Не удалось определить ch_type или channel_number. "
                "Укажите их явно или передайте device_key в формате "
                "'Прибор ch-<номер>_<тип>'."
            )
            if final_type is None:
                final_type = "meas"
            if final_number is None:
                final_number = 1

        color_str = self.color_manager.get_color(final_device)
        if color_str is None:
            logger.warning(f"Цвет для device_key={final_device} не найден, использую серый")
            color_str = "rgba(128, 128, 128, 255)"

        cache_key = (color_str, final_type, final_number, size)
        if cache_key in self._cache:
            return self._cache[cache_key]

        pixmap = self._generate_pixmap(color_str, final_type, final_number, size)
        icon = QIcon(pixmap)
        self._cache[cache_key] = icon
        return icon

    def _generate_pixmap(self, color_str: str, ch_type: str, number: int, size: int) -> QPixmap:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor()
        if color_str.startswith("rgba("):
            parts = color_str[5:-1].split(",")
            if len(parts) == 4:
                r, g, b, a = [int(p.strip()) for p in parts]
                color = QColor(r, g, b, a)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)

        margin = 3
        rect = pixmap.rect().adjusted(margin, margin, -margin, -margin)

        if ch_type.lower() == "meas":
            painter.drawEllipse(rect)
        elif ch_type.lower() == "act":
            painter.drawRoundedRect(rect, 4, 4)
        else:
            logger.warning(f"неопознанное значение ch_type: {ch_type}")
            painter.drawEllipse(rect)

        brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        text_color = Qt.black if brightness > 128 else Qt.white
        painter.setPen(text_color)

        font_size = size // 2.2 if number < 10 else size // 2.8
        font = QFont('Segoe UI', int(font_size), QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, str(number))

        painter.end()
        return pixmap

    def clear_cache(self):
        """Очищает кэш"""
        self._cache.clear()