from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer, QPoint
import sys

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
            "background-color: rgba(255, 200, 255, 50); "
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
        self.adjustSize()  # Обновляем размер виджета, чтобы соответствовать размеру лейбла

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


class MainWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.notification = None

    def show_tooltip(self, message, show_while_not_click=False, timeout=3000):
        if self.notification is None:
            self.notification = NotificationWidget(parent=self)

        self.notification.set_message(message)

        note_size = self.notification.sizeHint()
        pos = QPoint(self.width() - note_size.width() - 10, self.height() - note_size.height() - 10)

        self.notification.move(pos)  # Перемещаем уведомление перед показом

        if show_while_not_click:
            self.notification.show()
        else:
            self.notification.show_with_animation(timeout=timeout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_widget = MainWidget()
    main_widget.setGeometry(100, 100, 400, 300)
    main_widget.show()

    # Показать уведомление
    main_widget.show_tooltip("Это уведомление!", show_while_not_click=True)

    sys.exit(app.exec_())