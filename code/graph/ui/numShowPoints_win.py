from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QRadioButton, QSpinBox, QApplication,
    QLabel, QVBoxLayout, QGroupBox, QButtonGroup,
)
from PyQt5.QtCore import pyqtSignal


class numShowPointsClass(QWidget):
    """Виджет выбора видимого окна точек.

    Эмитит:
      - numPointsChanged(value)  — при изменении числа точек
      - showingAllPoints(state)  — при переключении режима «все / окно»

    Внутреннее состояние — только UI-слой, источником правды остаётся
    manageGraph.
    """
    numPointsChanged = pyqtSignal(int)
    showingAllPoints = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        group = QGroupBox(
            QApplication.translate("GraphWindow", "Отображение точек")
        )
        vbox = QVBoxLayout(group)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(4)

        self.radio_all = QRadioButton(
            QApplication.translate("GraphWindow", "Все точки")
        )
        self.radio_all.setChecked(True)

        self.radio_window = QRadioButton(
            QApplication.translate("GraphWindow", "Окно:")
        )

        # Явная группа исключает любые auto-exclusive сюрпризы при вложенных layouts
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self.radio_all, 0)
        self._mode_group.addButton(self.radio_window, 1)

        self.countbox = QSpinBox()
        self.countbox.setRange(1, 2_147_483_647)
        self.countbox.setValue(10)
        self.countbox.setEnabled(False)   # по умолчанию активен режим «все»
        self.countbox.setSuffix(
            QApplication.translate("GraphWindow", " точек")
        )

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.radio_window)
        row.addWidget(self.countbox)
        row.addStretch()

        vbox.addWidget(self.radio_all)
        vbox.addLayout(row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(group)
        self.setLayout(outer)

        self.radio_all.toggled.connect(self._on_mode_toggled)
        self.countbox.valueChanged.connect(self._on_value_changed)

    # ------------------------------------------------------------------
    def _on_mode_toggled(self, show_all_checked: bool) -> None:
        self.countbox.setEnabled(not show_all_checked)
        if show_all_checked:
            self.showingAllPoints.emit(True)
        else:
            self.showingAllPoints.emit(False)
            # применим текущее значение сразу, чтобы не ждать ручного клика
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

    # ------------------------------------------------------------------
    # Публичный API (совместимость с прежним numShowPointsClass)
    # ------------------------------------------------------------------
    def getValue(self) -> int:
        return self.countbox.value()

    def setValue(self, value: int) -> None:
        self.countbox.setValue(max(1, int(value)))

    @property
    def checkbox(self):
        """Старый API: чекбокс «show all» → radio_all."""
        return self.radio_all


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    widget = numShowPointsClass()
    widget.numPointsChanged.connect(lambda v: print("numPointsChanged", v))
    widget.showingAllPoints.connect(lambda s: print("showingAllPoints", s))
    widget.show()
    sys.exit(app.exec_())