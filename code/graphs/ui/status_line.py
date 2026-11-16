from PyQt5.QtWidgets import QStatusBar, QProgressBar
from datetime import datetime

class StatusBar(QStatusBar):
    def __init__(self, parent=None, show_time: bool = True):
        super().__init__(parent)
        self.show_time = bool(show_time)
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setVisible(False)
        self.addPermanentWidget(self._progress_bar)

    def _with_time(self, text: str) -> str:
        text = text or ""
        if not self.show_time or not text:
            return text
        return f"[{datetime.now().strftime('%H:%M:%S')}] {text}"

    def set_status(self, text: str, timeout: int = 0):
        message = self._with_time(text)
        if timeout > 0:
            self.showMessage(message, timeout)
        else:
            self.showMessage(message)

    def clear_status(self):
        self.clearMessage()

    def set_permanent(self, text: str):
        self.showMessage(self._with_time(text))

    def clear_permanent(self):
        self.showMessage("")

    def show_progress(self, minimum: int = 0, maximum: int = 100):
        self._progress_bar.setMinimum(minimum)
        self._progress_bar.setMaximum(maximum)
        self._progress_bar.setValue(minimum)
        self._progress_bar.setVisible(True)
        return self._progress_bar

    def hide_progress(self):
        self._progress_bar.setVisible(False)

    def set_progress_value(self, value: int):
        self._progress_bar.setValue(value)

    def set_style(self, color: str = "#000", background: str = "#EEE", font_size: int = 12):
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