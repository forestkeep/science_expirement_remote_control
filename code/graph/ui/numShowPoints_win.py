from PyQt5.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QSpinBox, QApplication, QLabel, QVBoxLayout
from PyQt5.QtCore import pyqtSignal


class numShowPointsClass(QWidget):
    """Виджет выбора видимого окна точек.

    Эмитит ровно одно событие на каждое действие пользователя:
      - numPointsChanged(value)  — при изменении числа точек
      - showingAllPoints(state)  — при переключении чекбокса «показать все»

    Внутреннее состояние (значение спиннера и чекбокса) остаётся только UI-слоем,
    источником правды для графа является manageGraph.
    """
    numPointsChanged = pyqtSignal(int)
    showingAllPoints = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.checkbox = QCheckBox("show all")
        self.countbox = QSpinBox()
        self.countbox.setRange(1, 2_147_483_647)
        self.countbox.setValue(10)
        self.countbox.setEnabled(False)   # по умолчанию show all активен

        self.label = QLabel("Count showing points")

        self.vert_lay = QVBoxLayout()
        self.vert_lay.setContentsMargins(0, 0, 0, 0)

        lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.checkbox)
        lay.addWidget(self.countbox)

        self.vert_lay.addWidget(self.label)
        self.vert_lay.addLayout(lay)
        self.setLayout(self.vert_lay)

        self.checkbox.setChecked(True)
        self.countbox.valueChanged.connect(self._on_value_changed)
        self.checkbox.stateChanged.connect(self._on_checkbox_changed)

    # ------------------------------------------------------------------
    # Обработчики пользователя
    # ------------------------------------------------------------------
    def _on_value_changed(self, value: int) -> None:
        # Значение 0 недопустимо — выравниваем сами, чтобы не отдавать мусор в граф
        value = max(1, int(value))
        if value != self.countbox.value():
            self.countbox.blockSignals(True)
            self.countbox.setValue(value)
            self.countbox.blockSignals(False)
        self.numPointsChanged.emit(value)

    def _on_checkbox_changed(self, state: int) -> None:
        show_all = (state != 0)  # Qt.Unchecked == 0
        self.countbox.setEnabled(not show_all)
        self.showingAllPoints.emit(show_all)

    # ------------------------------------------------------------------
    # Публичный API (без сигналов — чтобы не порождать циклы)
    # ------------------------------------------------------------------
    def getValue(self) -> int:
        return self.countbox.value()

    def setValue(self, value: int) -> None:
        self.countbox.setValue(max(1, int(value)))


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    widget = numShowPointsClass()
    widget.numPointsChanged.connect(lambda v: print("numPointsChanged", v))
    widget.showingAllPoints.connect(lambda s: print("showingAllPoints", s))
    widget.show()
    sys.exit(app.exec_())
