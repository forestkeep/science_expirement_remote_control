# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

from PyQt5.QtCore import QPropertyAnimation, Qt, QTimer
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout


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
