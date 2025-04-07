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

from PyQt5.QtCore import QRect
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QApplication, QToolTip, QWidget


class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.rects = [
            {"rect": QRect(10, 10, 100, 50), "text": "Прямоугольник 1"},
            {"rect": QRect(150, 20, 100, 50), "text": "Прямоугольник 2"}
        ]

    def paintEvent(self, event):
        painter = QPainter(self)
        for r in self.rects:
            painter.drawRect(r["rect"])

    def mousePressEvent(self, event):
        for r in self.rects:
            if r["rect"].contains(event.pos()):
                QToolTip.showText(event.globalPos(), r["text"], self)
                return

    def mouseReleaseEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        for r in self.rects:
            if r["rect"].contains(event.pos()):
                QToolTip.showText(event.globalPos(), r["text"], self)
                return
        QToolTip.hideText()

app = QApplication([])
window = MyWidget()
window.show()
app.exec_()