import sys
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QComboBox, QVBoxLayout, QFrame
import qdarktheme


class DraggableLabel(QLabel):
    def __init__(self, text, parent):
        super().__init__(text, parent)
        self.setFixedWidth(100)
        self.setAlignment(Qt.AlignCenter)
        self.drag_start_position = None

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.create_copy(event.pos())

        if event.buttons() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if self.drag_start_position is None:
            return
        if event.buttons() == Qt.LeftButton:
            diff = QPoint(event.pos() - self.drag_start_position)
            self.move(self.pos() + diff)

    def mouseReleaseEvent(self, event):
        self.drag_start_position = None

    def create_copy(self, pos):
        new_label = DraggableLabel(self.text(), self.parentWidget())
        new_label.setStyleSheet(self.styleSheet())
        # смещение новой копии от исходного лейбла
        new_label.move(self.pos() + QPoint(20, 20))
        new_label.show()


class WidgetWithComboBoxes(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)

        self.setObjectName("device")

        self.setMouseTracking(True)
        self.dragging = False
        self.last_pos = None

        layout = QVBoxLayout()

        self.label = QLabel(title)
        layout.addWidget(self.label)

        self.combo1 = QComboBox()
        self.combo1.addItems(['Item 1', 'Item 2', 'Item 3'])
        layout.addWidget(self.combo1)

        self.combo2 = QComboBox()
        self.combo2.addItems(['Option A', 'Option B', 'Option C'])
        layout.addWidget(self.combo2)

        self.setLayout(layout)
        self.drag_start_position = None

        self.frame = QFrame(self)
        # Установка размера рамки равным размеру QLabel
        self.frame.setGeometry(0, 0, 100, 100)
        self.frame.setFrameShape(QFrame.Box)  # Задаем форму рамки
        self.frame.setStyleSheet("background-color: lightgreen;")

        self.label.raise_()
        self.combo1.raise_()
        self.combo2.raise_()
        self.is_check = False

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.create_copy(event.pos())

        if event.buttons() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.frame.setStyleSheet(
                "background-color: rgba(250, 250, 250, 50);")
            self.is_check = True

    def mouseMoveEvent(self, event):
        if self.drag_start_position is None:
            return
        if event.buttons() == Qt.LeftButton:
            diff = QPoint(event.pos() - self.drag_start_position)
            self.move(self.pos() + diff)

    def mouseReleaseEvent(self, event):
        self.drag_start_position = None

    def mouseDoubleClickEvent(self, event):
        self.frame.setLineWidth(5)

    def enterEvent(self, event):
        self.frame.setStyleSheet("background-color: rgba(250, 250, 250, 20);")

    def leaveEvent(self, event):
        if not self.is_check:
            self.frame.setStyleSheet(
                "background-color: rgba(250, 250, 250, 0);")
            self.frame.setLineWidth(0)
        else:
            self.frame.setStyleSheet(
                "background-color: rgba(250, 250, 250, 50);")

    def create_copy(self, pos):
        new_label = WidgetWithComboBoxes(
            self.label.text(), self.parentWidget())
        new_label.setStyleSheet(self.styleSheet())
        # смещение новой копии от исходного лейбла
        new_label.move(self.pos() + QPoint(20, 20))
        new_label.show()

    def set_default_style(self):
        self.is_check = False
        self.frame.setStyleSheet("background-color: rgba(250, 250, 250, 0);")
        self.frame.setLineWidth(0)


class Example(QWidget):
    def __init__(self):
        super().__init__()
        '''
        label1 = DraggableLabel('Label 1', self)
        label1.setStyleSheet("background-color: lightblue;")

        label2 = DraggableLabel('Label 2', self)
        label2.move(150, 0)
        label2.setStyleSheet("background-color: lightgreen;")

        label3 = DraggableLabel('Label 3', self)
        label3.move(300, 0)
        label3.setStyleSheet("background-color: lightcoral;")
        '''
        widget1 = WidgetWithComboBoxes('Widget 1', self)
        widget1.move(0, 100)
        widget2 = WidgetWithComboBoxes('Widget 2', self)
        widget2.move(150, 100)
        widget3 = WidgetWithComboBoxes('Widget 3', self)
        widget3.move(300, 100)

        self.setGeometry(300, 300, 400, 200)
        self.setWindowTitle('Перемещение и копирование лейблов')
        self.show()

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            all_child_widgets = self.findChildren(QWidget)
            for widget in all_child_widgets:
                if widget.objectName() == "device":
                    widget.set_default_style()


if __name__ == '__main__':

    app = QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    ex = Example()
    sys.exit(app.exec_())
