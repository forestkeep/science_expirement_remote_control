from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSizePolicy, QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

class ToolButton(QPushButton):
    def __init__(self, is_change_style=True, parent=None):
        super().__init__(parent)
        self.is_change_style = is_change_style

class tool_bar_widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(1)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        self.buttons = []
        
        self.button_size = self.calculate_button_size()
        
        self.active_style = """
            QPushButton {
                background-color: #4a9df8;
                color: white;
                border-radius: 3px;
            }

        """
        
        self.normal_style = """
            QPushButton {
                background-color: #2d2d2d;
                color: white;
                border-radius: 3px;
            }
        """

    def calculate_button_size(self):
        """Вычисляет размер кнопки на основе DPI экрана"""
        screen = QApplication.primaryScreen()
        if screen:
            dpi = screen.logicalDotsPerInchX()
        else:
            dpi = 96
            
        base_size= 0.20
        size = int(base_size * dpi)
        return max(20, min(size, 40))

    def add_tool_button(self, callback, is_change_style=True, tooltip=None, icon_path=None):
        """Добавляет новую кнопку на панель инструментов"""
        button = ToolButton(is_change_style, self)
        button.setFixedSize(self.button_size, self.button_size)
        
        if icon_path:
            icon_size = int(self.button_size * 0.8)
            button.setIcon(QIcon(icon_path))
            button.setIconSize(QSize(icon_size, icon_size))
            
        if tooltip:
            button.setToolTip(tooltip)
            
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        button.setStyleSheet(self.normal_style)
        
        button.is_active = False
        
        def handle_click():
            button.is_active = not button.is_active
            if button.is_change_style:
                button.setStyleSheet(self.active_style if button.is_active else self.normal_style)
            callback(button.is_active)
        
        button.clicked.connect(handle_click)
        
        self.layout.addWidget(button)
        self.buttons.append(button)
        return button