"""Empty-state overlay: показывается, когда в сессии ещё нет ни одной кривой."""
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy,
)


class EmptyStateButton(QPushButton):
    """Кнопка с крупной иконкой-эмодзи, заголовком и подзаголовком.

    Рисуется вручную в paintEvent: даёт полный контроль над внешним видом
    (иконка слева, две строки текста справа) и не требует файлов иконок.
    """

    def __init__(self, icon: str, title: str, subtitle: str = "",
                 accent: str = "#5b9bd5", parent=None):
        super().__init__(parent)
        self.setFixedSize(440, 80)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        self.setStyleSheet("background: transparent; border: none;")
        self._icon = icon
        self._title = title
        self._subtitle = subtitle
        self._accent = QColor(accent)
        self._hover = False
        self._pressed = False

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(3, 3, -3, -3)

        bg = QColor(self._accent)
        bg.setAlpha(120 if self._pressed else (80 if self._hover else 40))
        p.setBrush(bg)

        border = QColor(self._accent)
        border.setAlpha(230 if self._hover else 130)
        pen = QPen(border)
        pen.setWidthF(1.5)
        p.setPen(pen)
        p.drawRoundedRect(rect, 14, 14)

        icon_rect = QRect(rect.left() + 18, rect.top() + 14, 52, 52)
        icon_font = QFont()
        icon_font.setPointSize(26)
        p.setFont(icon_font)
        p.setPen(QColor("#eef4ff"))
        p.drawText(icon_rect, Qt.AlignCenter, self._icon)

        title_rect = QRect(rect.left() + 84, rect.top() + 14,
                           rect.width() - 100, 26)
        tf = QFont()
        tf.setPointSize(12)
        tf.setBold(True)
        p.setFont(tf)
        p.setPen(QColor("#eef4ff"))
        p.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, self._title)

        if self._subtitle:
            sr = QRect(rect.left() + 84, rect.top() + 42,
                       rect.width() - 100, 24)
            sf = QFont()
            sf.setPointSize(9)
            p.setFont(sf)
            p.setPen(QColor("#a8b8d0"))
            p.drawText(sr, Qt.AlignLeft | Qt.AlignVCenter, self._subtitle)
        p.end()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self._pressed = True
        self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(e)


class EmptyStateWidget(QWidget):
    """Оверлей «сессия пуста». Шлёт 4 сигнала наружу, сам ничего не знает."""

    load_hdf5_requested = pyqtSignal()
    import_excel_requested = pyqtSignal()
    start_live_demo_requested = pyqtSignal()
    start_static_demo_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #070707;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 40, 40, 40)
        outer.setSpacing(0)
        outer.addStretch(1)

        title = QLabel("Начните работу с графиком")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 26px; font-weight: bold; color: #eef4ff; "
            "background: transparent;")
        outer.addWidget(title)

        subtitle = QLabel(
            "Загрузите сохранённый проект, импортируйте измерения из Excel "
            "или запустите демонстрационную сессию — чтобы сразу увидеть, "
            "как всё работает."
        )
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "font-size: 13px; color: #a8b8d0; background: transparent; "
            "margin-top: 8px;")
        outer.addWidget(subtitle)

        outer.addSpacing(28)

        self.btn_load = EmptyStateButton(
            "📂", "Загрузить проект",
            "Открыть .hdf5 файл с сохранёнными сессиями",
            accent="#5b9bd5")
        self.btn_load.clicked.connect(self.load_hdf5_requested.emit)

        self.btn_import = EmptyStateButton(
            "📊", "Импортировать данные",
            "Загрузить измерения из Excel (.xlsx)",
            accent="#5b9bd5")
        self.btn_import.clicked.connect(self.import_excel_requested.emit)

        self.btn_live = EmptyStateButton(
            "▶", "Демо: live-сессия",
            "2 прибора × 3 канала, по 100 точек каждую секунду",
            accent="#f0a000")
        self.btn_live.clicked.connect(self.start_live_demo_requested.emit)

        self.btn_static = EmptyStateButton(
            "📋", "Демо: готовые данные",
            "2 прибора × 3 канала, 10 000 точек сразу",
            accent="#4caf50")
        self.btn_static.clicked.connect(self.start_static_demo_requested.emit)

        for btn in (self.btn_load, self.btn_import,
                    self.btn_live, self.btn_static):
            outer.addSpacing(12)
            outer.addWidget(btn, alignment=Qt.AlignHCenter)

        outer.addStretch(2)

        footer = QLabel("Все эти действия также доступны в меню «Файл»")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(
            "font-size: 11px; color: #7080a0; background: transparent; "
            "margin-top: 12px;")
        outer.addWidget(footer)