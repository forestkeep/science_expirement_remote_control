# code/app/sidebar.py
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QSizePolicy, QToolButton, QVBoxLayout, QWidget


class IconSidebar(QWidget):
    """Узкая вертикальная панель (~44 px) с иконками страниц."""

    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(44)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setObjectName("IconSidebar")
        self.setStyleSheet("""
            QWidget#IconSidebar {
                background-color: #2b2b2b;
                border-right: 1px solid #444;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                color: #cccccc;
                border-radius: 6px;
            }
            QToolButton:hover  { background-color: #3b3b3b; }
            QToolButton:checked { background-color: #4aa3f8; color: #000000; }
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 8, 4, 8)
        self._layout.setSpacing(6)
        self._layout.addStretch(1)          # растяжка в конце
        self._buttons: list[QToolButton] = []

    def add_page_button(self, icon_char: str, tooltip: str, index: int) -> QToolButton:
        btn = QToolButton(self)
        btn.setText(icon_char)
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setFixedSize(36, 36)
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        btn.setFont(QFont("Segoe UI Emoji", 16))
        btn.clicked.connect(lambda _=False, i=index: self.page_changed.emit(i))

        # вставляем перед растяжкой
        self._layout.insertWidget(self._layout.count() - 1, btn)
        self._buttons.append(btn)
        return btn

    def set_active(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)