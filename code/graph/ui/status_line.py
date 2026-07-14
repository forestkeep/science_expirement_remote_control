import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget


from PyQt5.QtWidgets import QStatusBar, QLabel, QProgressBar, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer

from PyQt5.QtWidgets import QStatusBar, QProgressBar, QWidget
from PyQt5.QtCore import Qt

class StatusBar(QStatusBar):
    """
    Улучшенная строка состояния с методами для постоянного/временного текста
    и прогресс-баром. Постоянный текст автоматически восстанавливается после
    временных сообщений.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Прогресс-бар (постоянно справа)
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setVisible(False)
        self.addPermanentWidget(self._progress_bar)

    def set_status(self, text: str, timeout: int = 0):
        """
        Показать временное сообщение.
        Если timeout > 0, сообщение исчезнет через указанное число миллисекунд,
        и восстановится постоянный текст (если был задан).
        При timeout=0 сообщение остаётся до явной очистки (clear_status).
        """
        if timeout > 0:
            self.showMessage(text, timeout)
        else:
            self.showMessage(text)   # остаётся, пока не будет очищено вручную

    def clear_status(self):
        """
        Убрать текущее временное сообщение и вернуть постоянный текст.
        Постоянный текст остаётся неизменным.
        """
        self.clearMessage()

    def set_permanent(self, text: str):
        """
        Задать постоянный текст (normal message). Он будет показываться,
        когда нет временных сообщений.
        """
        self.showMessage(text)       # без таймаута -> normal message

    def clear_permanent(self):
        """
        Полностью очистить постоянный текст.
        Если в данный момент показывается временное сообщение, оно тоже сбросится.
        """
        self.showMessage("")         # сбрасывает normal message

    def show_progress(self, minimum: int = 0, maximum: int = 100):
        """Показать прогресс-бар и вернуть ссылку на него для обновления."""
        self._progress_bar.setMinimum(minimum)
        self._progress_bar.setMaximum(maximum)
        self._progress_bar.setValue(minimum)
        self._progress_bar.setVisible(True)
        return self._progress_bar

    def hide_progress(self):
        """Скрыть прогресс-бар."""
        self._progress_bar.setVisible(False)

    def set_progress_value(self, value: int):
        """Установить текущее значение прогресс-бара."""
        self._progress_bar.setValue(value)

    def set_style(self, color: str = "#000", background: str = "#EEE", font_size: int = 12):
        """Настроить цвета и шрифт строки состояния."""
        self.setStyleSheet(f"""
            QStatusBar {{
                color: {color};
                background-color: {background};
                font-size: {font_size}px;
            }}
            QStatusBar::item {{
                border: none;
            }}
        """)
class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Пример StatusBar")
        self.setGeometry(100, 100, 600, 200)

        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        btn1 = QPushButton("Временное сообщение (3 сек.)")
        btn1.clicked.connect(lambda: self.status_bar.set_status("Загрузка...", 3000))

        btn2 = QPushButton("Постоянный текст")
        btn2.clicked.connect(lambda: self.status_bar.set_permanent("Готово"))

        btn3 = QPushButton("Показать прогресс")
        btn3.clicked.connect(self.show_progress_example)

        btn4 = QPushButton("Скрыть прогресс")
        btn4.clicked.connect(self.status_bar.hide_progress)

        btn5 = QPushButton("Очистить")
        btn5.clicked.connect(self.status_bar.clear_status)

        layout.addWidget(btn1)
        layout.addWidget(btn2)
        layout.addWidget(btn3)
        layout.addWidget(btn4)
        layout.addWidget(btn5)

        self.status_bar.set_style(color="#333", background="#f0f0f0", font_size=12)
        self.status_bar.set_permanent("Приложение запущено")

    def show_progress_example(self):
        bar = self.status_bar.show_progress(0, 100)
        # Имитация прогресса
        for i in range(0, 101, 5):
            QTimer.singleShot(i * 10, lambda val=i: self.status_bar.set_progress_value(val))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())