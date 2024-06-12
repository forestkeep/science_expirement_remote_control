import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QGraphicsView, QLabel, QHBoxLayout, QSizePolicy, QPushButton
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtGui
import time
import random
from PyQt5.QtGui import QFont
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore    import *
from calc_values_for_graph import ArrayProcessor



class test_graph:
    def __init__(self):
        self.main_dict = {
                        'device1': {
                            'ch_1': {'time': self.get_time(), self.get_param(): self.get_values()}
                        },
                        'device2': {
                            'ch_1': {'time': self.get_time(), self.get_param(): self.get_values(), self.get_param(): self.get_values(), self.get_param(): self.get_values()},
                            'ch_2': {'time': self.get_time(), self.get_param(): self.get_values()},
                            'ch_3': {'time': self.get_time(), self.get_param(): self.get_values()}
                        },
                        'device3': {
                            'ch_1': {'time': self.get_time(), self.get_param(): self.get_values()},
                            'ch_2': {'time': self.get_time(), self.get_param(): self.get_values(), self.get_param(): self.get_values(), self.get_param(): self.get_values()}
                        }
                }
        
    def get_param(self):
        random_X = ["R", "L", "C", "PHAS", "V", "I", "D", "|Z|", "Q"]
        return random.choice(random_X)

    def get_values(self):
        return [random.randint(1, 10) for _ in range(1, 11)]
    
    def get_time(self):
        time_dict = [random.randint(1, 100) for _ in range(10)]
        time_dict.sort()
        return time_dict

class GraphWindow(QMainWindow):
    graph_win_close_signal = pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Online Graph")
        self.setGeometry(100, 100, 800, 600)
        self.initUI()

    def initUI(self):
        # Main widget and layout
        self.mainWidget = QWidget(self)
        self.setCentralWidget(self.mainWidget)
        self.mainLayout = QVBoxLayout()
        self.mainWidget.setLayout(self.mainLayout)

        # Data source selectors
        self.dataSourceLayout = QHBoxLayout()
        self.x_Layout = QVBoxLayout()
        self.y_Layout = QVBoxLayout()

        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.x_param_selector = QComboBox()
        self.x_param_selector.setSizePolicy(sizePolicy)
        self.x_device_selector = QComboBox()
        self.y_param_selector = QComboBox()
        self.y_param_selector.setSizePolicy(sizePolicy)
        self.y_device_selector = QComboBox()

        self.x_Layout.addWidget(QLabel("X-Axis:"))
        #self.x_Layout.addWidget(self.x_device_selector)
        self.x_Layout.addWidget(self.x_param_selector)

        self.y_Layout.addWidget(QLabel("Y-Axis:"))
        #self.y_Layout.addWidget(self.y_device_selector)
        self.y_Layout.addWidget(self.y_param_selector)

        self.line_graph_button = QPushButton("set color line")
        self.line_graph_button.setMinimumSize(10, 20)
        self.line_graph_button.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.line_graph_button.clicked.connect(lambda: self.push_line_color_graph())
        self.tooltip = QLabel("X:0,Y:0")
        self.horizontalSpacer = QSpacerItem(15, 15, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.settingsLayout = QHBoxLayout()
        self.settingsLayout.addWidget(self.line_graph_button)
        self.settingsLayout.addItem(self.horizontalSpacer)
        self.settingsLayout.addWidget(self.tooltip)


        self.dataSourceLayout.addLayout(self.y_Layout)
        self.dataSourceLayout.addLayout(self.x_Layout)

        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.test_graph())

        self.x =[]
        self.y =[]

        # Graph area
        self.graphView = pg.PlotWidget(title="") #QGraphicsView()

        self.color_line = "#55aa00"

        # Add to main layout
        self.mainLayout.addLayout(self.dataSourceLayout)
        self.mainLayout.addLayout(self.settingsLayout)
        self.mainLayout.addWidget(self.graphView)

        # Placeholder items for dropdown - this will be dynamically populated later
        self.x_param_selector.addItems(["Select parameter"])
        self.x_device_selector.addItems(["Select device"])
        self.y_param_selector.addItems(["Select parameter"])
        self.y_device_selector.addItems(["Select device"])

        self.y_param_selector.currentIndexChanged.connect(lambda: self.update_plot())
        self.x_param_selector.currentIndexChanged.connect(lambda: self.update_plot())

        self.graphView.scene().sigMouseMoved.connect(self.showToolTip)
        self.graphView.plotItem.getAxis('left').linkToView(self.graphView.plotItem.getViewBox())
        self.graphView.plotItem.getAxis('bottom').linkToView(self.graphView.plotItem.getViewBox())

        #self.timer.start(10000)

        self.key_to_update_plot = True

    def push_line_color_graph(self):
        dlg = QColorDialog(self)
        if dlg.exec_():
            self.color_line = dlg.currentColor().name()
            self.graphView.plot(self.x, self.y, pen = self.color_line)

    def showToolTip(self, event):
        pos = event  # Позиция курсора
        #print(self.graphView.removeItem(tooltip))
        #print(self.graphView.items())
        if self.y != [] and self.x != []:

            self.graphView.removeItem(self.tooltip)
            x_val = round(self.graphView.plotItem.vb.mapSceneToView(pos).x(), 1)  # Координата X
            y_val = round(self.graphView.plotItem.vb.mapSceneToView(pos).y(), 1)  # Координата Y
            text = f'<p style="font-size:{10}pt">X:{x_val} Y:{y_val}</p>'
            # Устанавливаем текст подсказки
            self.tooltip.setText(text)

    def test_graph(self):
        array_length = 100

        min_value = np.random.randint(1, 100)
        max_value = np.random.randint(min_value, 1000)

        # Создаем два массива случайных чисел из заданного диапазона
        self.x = np.random.randint(min_value, max_value, array_length)
        self.y = np.random.randint(min_value, max_value, array_length)
        self.x.sort()
        self.y.sort()
        self.update_plot()

    def update_dict_param(self, new: dict):
        if new:
            self.dict_param = new
            self.update_param_in_comboxes()
            self.update_plot()

    def set_default(self):
        self.key_to_update_plot = False
        self.x_param_selector.clear()
        self.y_param_selector.clear()
        self.x_param_selector.addItems(["Select parameter"])
        self.y_param_selector.addItems(["Select parameter"])
        self.graphView.plotItem.clear()
        self.key_to_update_plot = True

    def update_param_in_comboxes(self):
        self.key_to_update_plot = False
        self.list_param = self.create_name_param(self.dict_param)
        #print(f"{self.list_param=}")
        box_x = self.x_param_selector.currentText()
        box_y = self.y_param_selector.currentText()
        #print(f"{box_x=} {box_y=}")
        self.x_param_selector.clear()
        self.y_param_selector.clear()
        if box_x not in self.list_param:
            self.list_param.append(box_x)
        if box_y not in self.list_param:
            self.list_param.append(box_y)
        #print(f"{self.list_param=}")
        self.x_param_selector.addItems(self.list_param)
        self.y_param_selector.addItems(self.list_param)
        self.x_param_selector.setCurrentText(box_x)
        self.y_param_selector.setCurrentText(box_y)
        self.key_to_update_plot = True

    def update_plot(self):
        if self.key_to_update_plot:
            string_x = self.x_param_selector.currentText()
            string_y = self.y_param_selector.currentText()
            #print(f"{string_x=} {string_y=}")

            if string_x == "Select parameter" or string_y == "Select parameter":
                return
            
            if string_x == 'time' and string_y == 'time':
                #print(f"нельзя строить время от времени")
                return
            elif string_x == 'time' and string_y != 'time':
                device_y, ch_y, parameter_y = self.decode_name_parameters(string_y)
                y_axis_label = parameter_y
                x_axis_label = 'time'
                self.x = self.dict_param[device_y][ch_y]['time']
                self.y = self.dict_param[device_y][ch_y][parameter_y]

            elif string_y == 'time' and string_x != 'time':
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                x_axis_label = parameter_x
                y_axis_label = 'time'
                self.y = self.dict_param[device_x][ch_x]['time']
                self.x = self.dict_param[device_x][ch_x][parameter_x]
            elif string_x == string_y:
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                self.x = self.dict_param[device_x][ch_x][parameter_x]
                self.y = self.x
                y_axis_label = parameter_x
                x_axis_label = parameter_x
            else:
                device_y, ch_y, parameter_y = self.decode_name_parameters(string_y)
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                x_param = self.dict_param[device_x][ch_x][parameter_x]
                x_time = self.dict_param[device_x][ch_x]['time']
                y_param = self.dict_param[device_y][ch_y][parameter_y]
                y_time = self.dict_param[device_y][ch_y]['time']
                calculator_param = ArrayProcessor()
                self.x, self.y, _ = calculator_param.combine_interpolate_arrays(arr_time_x=x_time, arr_time_y=y_time,values_x=x_param, values_y=y_param)
                y_axis_label = parameter_y
                x_axis_label = parameter_x

            #print(f"{self.x=} {self.y=}")

            self.graphView.plotItem.clear()
            self.graphView.showGrid(x=True, y=True)
            self.graphView.plotItem.getAxis('left').linkToView(self.graphView.plotItem.getViewBox())
            self.graphView.plotItem.getAxis('bottom').linkToView(self.graphView.plotItem.getViewBox())

            self.graphView.setLabel('left', y_axis_label)
            self.graphView.setLabel('bottom', x_axis_label)
            self.graphView.plotItem.setTitle()
            self.graphView.plot(self.x, self.y, pen = {'color': self.color_line, 'width': 2, 'antialias': True, 'symbol': 'o'})

    def create_name_param(self, main_dict):
        output_list = ['time']

        for device, channels in main_dict.items():
            for channel, values in channels.items():
                #print(values.items())
                for key, value in values.items():
                    #print(key)
                    if key != 'time':
                        output_list.append(f'{key}({device} {channel})')

        return output_list
    
    def decode_name_parameters(self, string_y):
        buf_y = string_y.split("(")
        parameter_y = buf_y[0]
        device_y = buf_y[1].split(" ")[0]
        ch_y = buf_y[1].split(" ")[1][:-1]

        return device_y, ch_y, parameter_y

    def closeEvent(self, event):  # эта функция вызывается при закрытии окна
        self.graph_win_close_signal.emit(1)

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWindow = GraphWindow()
    mainWindow.show()

    test = test_graph()
    mainWindow.update_dict_param(test.main_dict)
    mainWindow.update_param_in_comboxes()
    sys.exit(app.exec_())