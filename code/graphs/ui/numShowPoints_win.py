from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QRadioButton, QSpinBox, QApplication,
    QLabel, QVBoxLayout, QGroupBox, QButtonGroup, QCheckBox
)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import Qt


class numShowPointsClass(QWidget):
    numPointsChanged = pyqtSignal(int)
    showingAllPoints = pyqtSignal(bool)
    connectLinesChanged = pyqtSignal(bool)
    showMarkersChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        group = QGroupBox(QApplication.translate("GraphWindow", "Отображение точек"))
        hbox = QHBoxLayout(group)
        hbox.setContentsMargins(6, 6, 6, 6)
        hbox.setSpacing(10)

        self.radio_all = QRadioButton(QApplication.translate("GraphWindow", "Все точки"))
        self.radio_all.setChecked(True)
        
        self.radio_window = QRadioButton(QApplication.translate("GraphWindow", "Окно:"))
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self.radio_all, 0)
        self._mode_group.addButton(self.radio_window, 1)

        self.countbox = QSpinBox()
        self.countbox.setRange(1, 2_147_483_647)
        self.countbox.setValue(10)
        self.countbox.setEnabled(False)
        self.countbox.setSuffix(QApplication.translate("GraphWindow", " точек"))

        # Вертикальный layout для связанных элементов
        vbox_window = QVBoxLayout()
        vbox_window.setContentsMargins(0, 0, 0, 0)
        vbox_window.setSpacing(2)
        vbox_window.addWidget(self.radio_window)
        vbox_window.addWidget(self.countbox)

        self.check_lines = QCheckBox(QApplication.translate("GraphWindow", "Соединять линиями"))
        self.check_lines.setChecked(True)
        self.check_lines.toggled.connect(lambda state: self.connectLinesChanged.emit(bool(state)))

        self.check_markers = QCheckBox(QApplication.translate("GraphWindow", "Показывать маркеры"))
        self.check_markers.setChecked(False)
        self.check_markers.toggled.connect(lambda state: self.showMarkersChanged.emit(bool(state)))

        # Размещаем элементы в горизонтальный ряд
        hbox.addWidget(self.radio_all, alignment=Qt.AlignTop)
        hbox.addLayout(vbox_window)
        hbox.addWidget(self.check_lines, alignment=Qt.AlignTop)
        hbox.addWidget(self.check_markers, alignment=Qt.AlignTop)
        hbox.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(group)

        self.setLayout(outer)

        self.radio_all.toggled.connect(self._on_mode_toggled)
        self.countbox.valueChanged.connect(self._on_value_changed)

    def _on_mode_toggled(self, show_all_checked: bool) -> None:
        self.countbox.setEnabled(not show_all_checked)
        if show_all_checked:
            self.showingAllPoints.emit(True)
        else:
            self.showingAllPoints.emit(False)
            self.numPointsChanged.emit(max(1, int(self.countbox.value())))

    def _on_value_changed(self, value: int) -> None:
        if self.radio_all.isChecked():
            return
        value = max(1, int(value))
        if value != self.countbox.value():
            self.countbox.blockSignals(True)
            self.countbox.setValue(value)
            self.countbox.blockSignals(False)
            self.numPointsChanged.emit(value)

    def getValue(self) -> int:
        return self.countbox.value()

    def setValue(self, value: int) -> None:
        self.countbox.setValue(max(1, int(value)))

    @property
    def checkbox(self):
        return self.radio_all

    
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    widget = numShowPointsClass()
    widget.numPointsChanged.connect(lambda v: print("numPointsChanged", v))
    widget.showingAllPoints.connect(lambda s: print("showingAllPoints", s))
    widget.show()
    sys.exit(app.exec_())