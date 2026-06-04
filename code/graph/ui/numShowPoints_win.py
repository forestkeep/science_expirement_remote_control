from PyQt5.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QSpinBox, QApplication, QLabel, QVBoxLayout

from PyQt5.QtCore import pyqtSignal

class numShowPointsClass(QWidget):
    numPointsChanged = pyqtSignal(int)
    showingAllPoints = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
        
    def initUI(self):
        self.checkbox = QCheckBox("show all")
        self.countbox = QSpinBox()
        self.countbox.setRange(0, 2147483647)
        self.countbox.setValue(10)

        self.label = QLabel("Count showing points")

        self.vert_lay = QVBoxLayout()

        self.vert_lay.setContentsMargins(0, 0, 0, 0)

        lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.checkbox)
        lay.addWidget(self.countbox)
        self.setLayout(self.vert_lay)
        self.vert_lay.addWidget(self.label)
        self.vert_lay.addLayout(lay)

        self.countbox.valueChanged.connect(self.onValueChanged)
        self.checkbox.stateChanged.connect(self.onCheckboxStateChanged)

        self.checkbox.setChecked(True)

    def onValueChanged(self, value):
        self.setValue(value)
        self.numPointsChanged.emit(value)

    def onCheckboxStateChanged(self, state):
        self.showingAllPoints.emit(bool(state))
        if state:
            self.countbox.setEnabled(False)
        else:
            self.countbox.setEnabled(True)

    def getValue(self):
        return self.countbox.value()

    def setValue(self, value):
        self.countbox.setValue(value)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    widget = numShowPointsClass()
    widget.show()
    sys.exit(app.exec_())
