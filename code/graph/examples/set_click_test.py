import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

from PyQt5.QtWidgets import QApplication, QMainWindow

class MyApp:
    def __init__(self):
        app = QApplication(sys.argv)
        self.app = QApplication(sys.argv)
        self.window = QMainWindow()
        self.window.setWindowTitle('Пример графика с перехватом кликов')

        self.graph_widget = pg.PlotWidget(title="График с кликами")
        self.window.setCentralWidget(self.graph_widget)

        x = np.linspace(0, 10, 100)
        y = np.sin(x)

        self.plot_obj = self.graph_widget.plot(
            x, y,
            pen={'color': 'b', 'width': 2},
            symbol='o'
        )

        self.plot_obj.setCurveClickable(True, width=10)
        self.plot_obj.sigPointsClicked.connect(self.on_points_clicked)

        self.window.show()
        sys.exit(self.app.exec_())

    def on_points_clicked(self, plot, points):
        for point in points:
            pos = point.pos()
            print(f'Clicked on point at: x={pos.x()}, y={pos.y()}')

if __name__ == "__main__":
    MyApp()