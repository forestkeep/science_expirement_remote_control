import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QCheckBox, QGridLayout
from PyQt5 import QtChart
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import Qt
from PyQt5.QtChart import QBarSet, QChart, QBarSeries, QLineSeries, QBarCategoryAxis, QChartView

class GraphApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Графики массивов")
        self.setGeometry(100, 100, 800, 600)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.layout = QGridLayout(self.central_widget)

        self.chart = QChart()
        self.chart_view = QChartView(self.chart)
        self.layout.addWidget(self.chart_view, 0, 1,6,6)

        self.series = []
        self.dataY = [np.arange(0, 100, 10), np.arange(40, 50, 1)]
        self.dataX = [np.arange(0, 500, 1), np.arange(100, 200, 5)]
        print(self.dataX)
        print(self.dataY)
        self.check_X = []
        self.check_Y = []
        for i in range(2):
            checkbox = QCheckBox(f"МассивУ {i+1}")
            self.check_X.append(checkbox)
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(lambda state, i=i: self.update_chart(i, state, 0))
            self.layout.addWidget(checkbox,7,i+4)

        for i in range(2):
            checkbox = QCheckBox(f"МассивX {i+1}")
            self.check_Y.append(checkbox)
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(lambda state, i=i: self.update_chart(i, state, 1))
            self.layout.addWidget(checkbox,i,0)
        #self.update_chart(0, Qt.Checked)

    def update_chart(self, index, state, axis):
        if state == Qt.Checked:
            print("проверяем чек боксы противоположной оси", index, axis)
            kX = 0
            kY = 0
            if axis == 0:
                print(222)
                for ch in self.check_X:
                    if kX != index:
                        ch.setChecked(False)
                    kX+=1
                kX = index
                for ch in self.check_Y:
                    if ch.checkState() == Qt.Checked:
                        #ch.setChecked(False)
                        break
                    kY+=1
                if kY > 1:
                    kY = 1
            else:
                print(111)
                for ch in self.check_Y:
                    if kY != index:
                        ch.setChecked(False)
                    kY+=1
                kY = index
                for ch in self.check_X:
                    if ch.checkState() == Qt.Checked:
                        break
                    kX+=1
                if kX > 1:
                    kX = 1
            
            print(kX, kY)
            for s in self.series:
                self.chart.removeSeries(s)
            self.series = []

            series = QLineSeries()
            for j in range(10):
                series.append(self.dataX[kX][j], self.dataY[kY][j])
            self.series.append(series)
            self.chart.addSeries(series)
                        #series.attachAxis(self.chart.axisX())
            self.chart.createDefaultAxes()
            self.chart_view.setChart(self.chart)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    graph_app = GraphApp()
    graph_app.show()
    sys.exit(app.exec_())