from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QStatusBar, QProgressBar, QLabel, QPushButton,
)
from datetime import datetime
class StatusBar(QStatusBar):
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, parent=None, show_time: bool = True):
        super().__init__(parent)
        self.show_time = bool(show_time)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setVisible(False)
        self.addPermanentWidget(self._progress_bar)

        self._cursor_label = QLabel("")
        self._cursor_label.setMinimumWidth(220)
        self._cursor_label.setAlignment(self._cursor_label.alignment() | 0x0002)
        self._cursor_label.setStyleSheet(
            "color: #888; font-family: Consolas, Menlo, monospace; font-size: 11px;"
        )
        self.addPermanentWidget(self._cursor_label)

        self._build_live_controls()

    def _build_live_controls(self) -> None:
        self._live_label = QLabel("")
        self._live_label.setStyleSheet(
            "color: #ff4444; font-weight: bold; font-size: 11px; padding: 0 6px;"
        )
        self.addPermanentWidget(self._live_label)

        self._pause_btn = QPushButton("⏸")
        self._pause_btn.setFixedSize(28, 22)
        self._pause_btn.setToolTip("Пауза / Возобновить эксперимент")
        self._pause_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #555;"
            " border-radius: 3px; color: #eee; font-size: 12px; }"
            "QPushButton:hover { background: #333; }"
            "QPushButton:pressed { background: #222; }"
        )
        self._pause_btn.clicked.connect(lambda: self.pause_requested.emit())
        self.addPermanentWidget(self._pause_btn)

        self._stop_btn = QPushButton("⏹")
        self._stop_btn.setFixedSize(28, 22)
        self._stop_btn.setToolTip("Остановить эксперимент")
        self._stop_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #555;"
            " border-radius: 3px; color: #ff6666; font-size: 12px; }"
            "QPushButton:hover { background: #442222; }"
            "QPushButton:pressed { background: #331111; }"
        )
        self._stop_btn.clicked.connect(lambda: self.stop_requested.emit())
        self.addPermanentWidget(self._stop_btn)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(600)
        self._pulse_timer.timeout.connect(self._on_pulse)
        self._pulse_on = True

        self._set_live_visible(False)

    def _set_live_visible(self, visible: bool) -> None:
        self._live_label.setVisible(visible)
        self._pause_btn.setVisible(visible)
        self._stop_btn.setVisible(visible)
        if visible:
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
            self._live_label.setStyleSheet(
                "color: #ff4444; font-weight: bold; font-size: 11px; padding: 0 6px;"
            )
            self._pulse_on = True

    def _on_pulse(self) -> None:
        self._pulse_on = not self._pulse_on
        if self._pulse_on:
            self._live_label.setStyleSheet(
                "color: #ff4444; font-weight: bold; font-size: 11px; padding: 0 6px;"
            )
        else:
            self._live_label.setStyleSheet(
                "color: #882222; font-weight: bold; font-size: 11px; padding: 0 6px;"
            )

    def set_live_mode(self, is_live: bool, is_paused: bool = False) -> None:
        if not is_live:
            self._set_live_visible(False)
            self._live_label.setText("")
            return

        self._set_live_visible(True)

        if is_paused:
            self._live_label.setText("PAUSED")
            self._live_label.setStyleSheet(
                "color: #ffaa00; font-weight: bold; font-size: 11px; padding: 0 6px;"
            )
            self._pause_btn.setText("▶")
            self._pause_btn.setToolTip("Возобновить эксперимент")
            self._pulse_timer.stop()
        else:
            self._live_label.setText("LIVE")
            self._live_label.setStyleSheet(
                "color: #ff4444; font-weight: bold; font-size: 11px; padding: 0 6px;"
            )
            self._pause_btn.setText("⏸")
            self._pause_btn.setToolTip("Приостановить эксперимент")
            if not self._pulse_timer.isActive():
                self._pulse_timer.start()

    def _with_time(self, text: str) -> str:
        text = text or ""
        if not self.show_time or not text:
            return text
        return f"[{datetime.now().strftime('%H:%M:%S')}] {text}"

    def set_status(self, text: str, timeout: int = 0) -> None:
        message = self._with_time(text)
        if timeout > 0:
            self.showMessage(message, timeout)
        else:
            self.showMessage(message)

    def clear_status(self) -> None:
        self.clearMessage()

    def set_permanent(self, text: str) -> None:
        self.showMessage(self._with_time(text))

    def clear_permanent(self) -> None:
        self.showMessage("")

    def set_cursor_position(self, x: float, y: float) -> None:
        try:
            text = f"X: {x:.6g}   Y: {y:.6g}"
        except (TypeError, ValueError):
            text = ""
        if self._cursor_label.text() != text:
            self._cursor_label.setText(text)

    def clear_cursor_position(self) -> None:
        if self._cursor_label.text():
            self._cursor_label.setText("")

    def show_progress(self, minimum: int = 0, maximum: int = 100):
        self._progress_bar.setMinimum(minimum)
        self._progress_bar.setMaximum(maximum)
        self._progress_bar.setValue(minimum)
        self._progress_bar.setVisible(True)
        return self._progress_bar

    def hide_progress(self) -> None:
        self._progress_bar.setVisible(False)

    def set_progress_value(self, value: int) -> None:
        self._progress_bar.setValue(value)

    def set_style(self, color: str = "#000", background: str = "#EEE", font_size: int = 12) -> None:
        self.setStyleSheet(
            f"""
            QStatusBar {{
                color: {color};
                background-color: {background};
                font-size: {font_size}px;
            }}
            QStatusBar::item {{
                border: none;
            }}
            """
        )