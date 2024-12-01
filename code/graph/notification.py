from PyQt5.QtCore import QTimer, QPropertyAnimation,  Qt, QTimer
from PyQt5.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel
)

class NotificationWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout()
        self.label = QLabel("", self)
        self.label.setStyleSheet(
            "color: yellow; "
            "font-weight: bold; "
            "background-color: rgba(255, 0, 255, 50); "
            "padding: 10px; "
            "border: none;"
        )
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.timeout = 2000

    def mousePressEvent(self, event):
        self.hide()

    def set_message(self, message):
        self.label.setText(message)
        self.adjustSize() 

    def show_with_animation(self, timeout):
        self.timeout = timeout

        self.setWindowOpacity(0)
        self.show()
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(700)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.finished.connect(self.hide_after_delay)
        self.animation.start()

    def hide_after_delay(self):
        QTimer.singleShot(self.timeout, self.hide)
