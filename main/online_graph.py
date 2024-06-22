import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QGraphicsView, QLabel, QHBoxLayout, QSizePolicy, QPushButton
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg
import numpy as np
from interface.Message import messageDialog
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
        return [random.randint(1, 100) for _ in range(1000)]
    
    def get_time(self):
        start_range = 1
        end_range = 10
        list_size = 1000
        all_values = list(range(start_range, end_range*list_size))
        random.shuffle(all_values)
        # Берем первые list_size элементов
        time_dict = all_values[:list_size]
        time_dict.sort()
        print(f"{time_dict=}")
        return time_dict

class GraphWindow(QMainWindow):
    graph_win_close_signal = pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Online Graph")
        self.setGeometry(100, 100, 800, 600)
        self.is_show_warning = True
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
        self.y_main_Layout = QVBoxLayout()
        self.y_second_Layout = QVBoxLayout()

        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.x_param_selector = QComboBox()
        self.x_param_selector.setSizePolicy(sizePolicy)
        self.x_device_selector = QComboBox()

        self.y_first_param_selector = QComboBox()
        self.y_first_param_selector.setSizePolicy(sizePolicy)
        self.y_first_device_selector = QComboBox()

        self.y_second_param_selector = QComboBox()
        self.y_second_param_selector.setSizePolicy(sizePolicy)
        self.y_second_device_selector = QComboBox()

        self.x_Layout.addWidget(QLabel("X-Axis:"))
        #self.x_Layout.addWidget(self.x_device_selector)
        self.x_Layout.addWidget(self.x_param_selector)
        self.y_second_axis_label = "Y second Axis:"
        self.y_main_Layout.addWidget(QLabel("Y main Axis:"))
        #self.y_Layout.addWidget(self.y_device_selector)
        self.y_main_Layout.addWidget(self.y_first_param_selector)

        self.second_check_box = QCheckBox('Add second axis')
        self.second_y_axis_layout = QHBoxLayout()

        self.second_y_axis_layout.addWidget(QLabel(self.y_second_axis_label))
        self.second_y_axis_layout.addWidget(self.second_check_box)
        self.y_second_Layout.addLayout(self.second_y_axis_layout)
        #self.y_Layout.addWidget(self.y_device_selector)
        self.y_second_Layout.addWidget(self.y_second_param_selector)

        self.line_graph_button = QPushButton("set color line main")
        self.line_graph_button.setMinimumSize(10, 20)
        self.line_graph_button.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.line_graph_button.clicked.connect(lambda: self.push_line_color_graph('m'))

        self.line_graph_button_second = QPushButton("set color line second")
        self.line_graph_button_second.setMinimumSize(10, 20)
        self.line_graph_button_second.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.line_graph_button_second.clicked.connect(lambda: self.push_line_color_graph('s'))
        self.tooltip = QLabel("X:0,Y:0")
        self.horizontalSpacer = QSpacerItem(15, 15, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.settingsLayout = QHBoxLayout()
        self.settingsLayout.addWidget(self.line_graph_button)
        self.settingsLayout.addWidget(self.line_graph_button_second)
        self.settingsLayout.addItem(self.horizontalSpacer)
        self.settingsLayout.addWidget(self.tooltip)


        self.dataSourceLayout.addLayout(self.y_main_Layout)
        self.dataSourceLayout.addLayout(self.x_Layout)
        self.dataSourceLayout.addLayout(self.y_second_Layout)

        self.x =[]
        self.y =[]

        self.y_main_axis_label = ''
        self.x_axis_label = ''

        # Graph area
        self.graphView = pg.PlotWidget(title="") #QGraphicsView()

        self.color_line_main = "#55aa00"
        self.color_line_second = "#ff0000"

        # Add to main layout
        self.mainLayout.addLayout(self.dataSourceLayout)
        self.mainLayout.addLayout(self.settingsLayout)
        self.mainLayout.addWidget(self.graphView)

        # Placeholder items for dropdown - this will be dynamically populated later
        self.x_param_selector.addItems(["Select parameter"])
        self.x_device_selector.addItems(["Select device"])
        self.y_first_param_selector.addItems(["Select parameter"])
        self.y_first_device_selector.addItems(["Select device"])
        self.y_second_param_selector.addItems(["Select parameter"])
        self.y_second_device_selector.addItems(["Select device"])

        self.y_first_param_selector.currentIndexChanged.connect(lambda: self.update_plot())
        self.y_second_param_selector.currentIndexChanged.connect(lambda: self.update_plot())
        self.x_param_selector.currentIndexChanged.connect(lambda: self.update_plot())
        self.second_check_box.stateChanged.connect(lambda: self.update_plot())

        self.graphView.scene().sigMouseMoved.connect(self.showToolTip)
        self.graphView.plotItem.getAxis('left').linkToView(self.graphView.plotItem.getViewBox())
        self.graphView.plotItem.getAxis('bottom').linkToView(self.graphView.plotItem.getViewBox())


        self.p1 = self.graphView.plotItem
        #self.p1.setLabels(left='axis 1')

        ## create a new ViewBox, link the right axis to its coordinate system
        
        self.p2 = pg.ViewBox()
        self.p1.showAxis('right')
        self.p1.scene().addItem(self.p2)
        self.p1.getAxis('right').linkToView(self.p2)
        self.p2.setXLink(self.p1)
        self.p1.getAxis('right').setLabel('axis2', color='#000fff')

        self.p1.vb.sigResized.connect(self.updateViews)

        self.curve2 = pg.PlotCurveItem(pen=pg.mkPen(color=self.color_line_second, width=1))
        #self.curve2.setData(x=[1,2,3,3,5,6], y=[10,20,40,80,40,20])
        self.p2.addItem(self.curve2)

        my_font = QFont("Times", 13)
        self.p1.getAxis("right").label.setFont(my_font)
        self.graphView.getAxis("bottom").label.setFont(my_font)
        self.graphView.getAxis("left").label.setFont(my_font)

        self.key_to_update_plot = True

    def time_decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            print(f"Метод {func.__name__} - {end_time - start_time} с")
            return result
        return wrapper

    def push_line_color_graph(self, which_axis):
        dlg = QColorDialog(self)
        if dlg.exec_():
            if which_axis == 'm':
                self.color_line_main = dlg.currentColor().name()
            else:
                self.color_line_second = dlg.currentColor().name()
            
            self.update_plot()


    def showToolTip(self, event):
        pos = event  # Позиция курсора
        #print(self.graphView.removeItem(tooltip))
        #print(self.graphView.items())
        if len(self.y) > 1 and len(self.x) > 0:

            self.graphView.removeItem(self.tooltip)
            x_val = round(self.graphView.plotItem.vb.mapSceneToView(pos).x(), 1)  # Координата X
            y_val = round(self.graphView.plotItem.vb.mapSceneToView(pos).y(), 1)  # Координата Y
            text = f'<p style="font-size:{10}pt">X:{x_val} Y:{y_val}</p>'
            # Устанавливаем текст подсказки
            self.tooltip.setText(text)

    def update_dict_param(self, new: dict):
        if new:
            self.dict_param = new
            self.update_param_in_comboxes()
            self.update_plot()

    def set_default(self):
        self.key_to_update_plot = False
        self.x_param_selector.clear()
        self.y_first_param_selector.clear()
        self.x_param_selector.addItems(["Select parameter"])
        self.y_first_param_selector.addItems(["Select parameter"])
        self.graphView.plotItem.clear()
        self.key_to_update_plot = True

    def update_param_in_comboxes(self):
        self.key_to_update_plot = False
        self.list_param = self.create_name_param(self.dict_param)
        #print(f"{self.list_param=}")
        box_x = self.x_param_selector.currentText()
        box_y = self.y_first_param_selector.currentText()
        box_y2 = self.y_second_param_selector.currentText()
        #print(f"{box_x=} {box_y=}")
        self.x_param_selector.clear()
        self.y_first_param_selector.clear()
        self.y_second_param_selector.clear()
        if box_x not in self.list_param:
            self.list_param.append(box_x)
        if box_y not in self.list_param:
            self.list_param.append(box_y)
        if box_y not in self.list_param:
            self.list_param.append(box_y2)
        #print(f"{self.list_param=}")
        self.x_param_selector.addItems(self.list_param)
        self.y_first_param_selector.addItems(self.list_param)
        self.y_second_param_selector.addItems(self.list_param)
        self.x_param_selector.setCurrentText(box_x)
        self.y_first_param_selector.setCurrentText(box_y)
        self.y_second_param_selector.setCurrentText(box_y2)
        self.key_to_update_plot = True

    def updateViews(self):
        ## view has resized; update auxiliary views to match

        self.p2.setGeometry(self.p1.vb.sceneBoundingRect())
        #p3.setGeometry(p1.vb.sceneBoundingRect())
        
        ## need to re-update linked axes since this was called
        ## incorrectly while views had different shapes.
        ## (probably this should be handled in ViewBox.resizeEvent)
        self.p2.linkedViewChanged(self.p1.vb, self.p2.XAxis)
        #p3.linkedViewChanged(p1.vb, p3.XAxis)


    @time_decorator
    def update_data(self):
            string_x = self.x_param_selector.currentText()
            string_y = self.y_first_param_selector.currentText()
            string_y2 = self.y_second_param_selector.currentText()
            #print(f"{string_x=} {string_y=}")
            check_main = True

            if string_x == "Select parameter" or string_y == "Select parameter":
                check_main = False
                if self.second_check_box.isChecked(): 
                    if string_x == "Select parameter" or string_y2 == "Select parameter":
                        return
                else:
                    return
            
            if string_x == 'time' and string_y == 'time':
                check_main = False
                if self.second_check_box.isChecked(): 
                    if string_x == 'time' or string_y2 == 'time':
                        return
                else:
                    return
                
            if check_main == True:
                if string_x == 'time' and string_y != 'time' and string_y != "Select parameter":
                    device_y, ch_y, parameter_y = self.decode_name_parameters(string_y)
                    self.y_main_axis_label = parameter_y
                    self.x_axis_label = 'time'
                    self.x = self.dict_param[device_y][ch_y]['time']
                    self.y = self.dict_param[device_y][ch_y][parameter_y]
                elif string_y == 'time' and string_x != 'time':
                    device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                    self.x_axis_label = parameter_x
                    self.y_main_axis_label = 'time'
                    self.y = self.dict_param[device_x][ch_x]['time']
                    self.x = self.dict_param[device_x][ch_x][parameter_x]
                elif string_x == string_y:
                    device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                    self.x = self.dict_param[device_x][ch_x][parameter_x]
                    self.y = self.x
                    self.y_main_axis_label = parameter_x
                    self.x_axis_label = parameter_x
                else:

                    device_y, ch_y, parameter_y = self.decode_name_parameters(string_y)
                    device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                    x_param = self.dict_param[device_x][ch_x][parameter_x]
                    x_time = self.dict_param[device_x][ch_x]['time']
                    y_param = self.dict_param[device_y][ch_y][parameter_y]
                    y_time = self.dict_param[device_y][ch_y]['time']
                    #TODO: добавить функционал определения, какие из новых данных изменились, если текущие данные для вывода не менялись, то проверить, есть ли сохраненные. Если есть, то вывести их, если нет, то посчитать и сохранить.
                    #таким образом избавиться от повторных вычислений
                    calculator_param = ArrayProcessor()
                    #print(9999999999999999999999999999999999999999999999999999)
                    #print(f"{x_param=} {y_param=}")

                    self.x, self.y, _ = calculator_param.combine_interpolate_arrays(arr_time_x=x_time, arr_time_y=y_time,values_x=x_param, values_y=y_param)

                    #print(f"{self.x=}")
                    #print(1111111111111111111111111111111111111111111111111111)
                    self.y_main_axis_label = parameter_y
                    self.x_axis_label = parameter_x
            
            if self.second_check_box.isChecked():
                if (string_x == 'time' and string_y2 == 'time') or string_y2 == "Select parameter":
                    self.y_second_axis_label = ''
                    self.x2 = []
                    self.y2 = []
                elif string_x == 'time' and string_y2 != 'time' and string_y2 != "Select parameter":
                    device_y2, ch_y2, parameter_y2 = self.decode_name_parameters(string_y2)
                    self.y_second_axis_label = parameter_y2
                    self.x_axis_label = 'time'
                    self.x2 = self.dict_param[device_y2][ch_y2]['time']
                    self.y2 = self.dict_param[device_y2][ch_y2][parameter_y2]
                elif string_y2 == 'time' and string_x != 'time':
                    device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                    self.x_axis_label = parameter_x
                    self.y_second_axis_label = 'time'
                    self.y2 = self.dict_param[device_x][ch_x]['time']
                    self.x2 = self.dict_param[device_x][ch_x][parameter_x]
                elif string_x == string_y2 and string_y2 != "time":
                    device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                    self.x2 = self.dict_param[device_x][ch_x][parameter_x]
                    self.y2 = self.x2
                    self.y_second_axis_label = parameter_x
                    self.x_axis_label = parameter_x
                else:
                    device_y2, ch_y2, parameter_y2 = self.decode_name_parameters(string_y2)
                    device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                    x_param = self.dict_param[device_x][ch_x][parameter_x]
                    x_time = self.dict_param[device_x][ch_x]['time']
                    y_param = self.dict_param[device_y2][ch_y2][parameter_y2]
                    y_time = self.dict_param[device_y2][ch_y2]['time']
                    calculator_param = ArrayProcessor()
                    self.x2, self.y2, _ = calculator_param.combine_interpolate_arrays(arr_time_x=x_time, arr_time_y=y_time,values_x=x_param, values_y=y_param)
                    self.y_second_axis_label = parameter_y2
                    self.x_axis_label = parameter_x

                if not check_main:
                        self.x = self.x2
                        self.y = self.y2
                        self.y_main_axis_label = self.y_second_axis_label

                #print(f"{len(self.x2)=}")
                self.curve2.setData(x=self.x2, y=self.y2)

            if self.is_show_warning == True:
                    self.is_show_warning = False
                    if len(self.x) > 3000:
                        message = messageDialog(title="Сообщение", text = "Число точек превысило 3000, расчет зависимости одного параметра от другого может занимать некоторое время.\n Особенно, на слабых компьютерах. Рекомендуется выводить графики в зависимости от времени.")
                        message.exec_()

    def update_draw(self):
            self.graphView.plotItem.clear()
            self.graphView.plotItem.getAxis('left').linkToView(self.graphView.plotItem.getViewBox())
            self.graphView.plotItem.getAxis('bottom').linkToView(self.graphView.plotItem.getViewBox())
            self.graphView.setLabel('left', self.y_main_axis_label, color=self.color_line_main)
            self.graphView.setLabel('bottom', self.x_axis_label, color='#ffffff')


            self.graphView.plot(self.x, self.y, pen = {'color': self.color_line_main, 'width': 1, 'antialias': True, 'symbol': 'o'})
            self.graphView.getAxis('left').setGrid(True)
            self.graphView.getAxis('bottom').setGrid(True)
            self.graphView.getAxis('left').setGrid(False)

            if self.second_check_box.isChecked():
                self.p1.getAxis('right').setLabel(self.y_second_axis_label, color=self.color_line_second)
                self.p1.getAxis('right').setStyle(showValues=True)
                #self.curve2.setData(x=[1,2,3,3,5,6], y=[10,20,40,80,40,20])
                self.curve2.setPen(pg.mkPen(color=self.color_line_second, width=1))
                self.p2.addItem(self.curve2)
            else:
                self.p1.getAxis('right').setStyle(showValues=False)
                self.p1.getAxis('right').setLabel("")
                #self.p2.removeItem(self.curve2)

    def update_plot(self):
        if self.key_to_update_plot:
            self.update_data()
            self.update_draw()

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
        #print(f"{buf_y=}")
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