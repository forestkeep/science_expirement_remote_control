from PyQt5.QtWidgets import QWidget, QLabel, QToolTip
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QWidget, QApplication, QLabel

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
        print(33333)
        for r in self.rects:
            if r["rect"].contains(event.pos()):
                print(event.pos())
                QToolTip.showText(event.globalPos(), r["text"], self)
                return

    def mouseReleaseEvent(self, event):
        print(22222)

    def mouseMoveEvent(self, event):
        print(event.pos())
        for r in self.rects:
            if r["rect"].contains(event.pos()):
                print(event.pos())
                QToolTip.showText(event.globalPos(), r["text"], self)
                return
        QToolTip.hideText()

# Пример использования
app = QApplication([])
window = MyWidget()
window.show()
app.exec_()