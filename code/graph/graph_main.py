# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

import time

import pandas as pd
import pyqtgraph as pg
import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QPushButton,
    QFileDialog
)

try:
    from calc_values_for_graph import ArrayProcessor
    from Message_graph import messageDialog
except:
    from graph.calc_values_for_graph import ArrayProcessor
    from graph.Message_graph import messageDialog

cold_colors = [
    "#0000ff",  # Синий
    "#00bfff",  # Скай-блю
    "#1e90ff",  # Доллар-блю
    "#00ffff",  # Цвет морской волны
    "#6495ed",  # Кобальт
    "#4682b4",  # Стальной синий
    "#4169e1",  # Королевский синий
    "#7b68ee",  # Светло-фиолетовый
    "#6a5acd",  # Сине-фиолетовый
    "#00ced1",  # Темный бирюзовый
    "#5f9ea0",  # Дюк-бирюзовый
    "#48d1cc",  # Бирюзовый
    "#00fa9a",  # Средний зеленый
    "#98fb98",  # Светло-зеленый
    "#3cb371",  # Мятный
    "#00ff7f",  # Весенний зеленый
    "#20b2aa",  # Средний аквамариновый
    "#4682b4",  # Стальной синий
    "#7fffd4",  # Аквамарин
    "#add8e6"   # Светло-голубой
]

warm_colors = [
    "#ff0000",  # Красный
    "#ff4500",  # Оранжево-красный
    "#ff7f50",  # Коралловый
    "#ff6347",  # Помидор
    "#ff8c00",  # Темный оранжевый
    "#ffa500",  # Оранжевый
    "#ffd700",  # Золотой
    "#ff1493",  # Ярко-розовый
    "#db7093",  # Вересковый
    "#ff69b4",  # Жарко-розовый
    "#ffb6c1",  # Светло-розовый
    "#ff8c00",  # Темный оранжевый
    "#cd5c5c",  # Испанская красная
    "#f08080",  # Светло-красный
    "#e9967a",  # Светло-коричневый
    "#ff7f00",  # Ярко-оранжевый
    "#ff4500",  # Оранжево-красный
    "#ff6347",  # Помидор
    "#fa8072",  # Светлый коралловый
    "#ff1493"   # Ярко-розовый
]


def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Метод {func.__name__} - {end_time - start_time} с")
        return result

    return wrapper


class graphMain:

    def __init__(self, tablet_page):
        self.page = tablet_page
        self.is_show_warning = True
        self.key_to_update_plot = True
        self.x = []
        self.y = {}
        self.x2 = []
        self.y2 = {}
        self.dict_param = {}

        self.curve1 = {}
        self.curve2 = {}
        self.curve2_dots = {}

        self.is_time_column = True
        
        self.legend = pg.LegendItem(size=(80, 60), offset=(10, 10))
        self.legend2 = pg.LegendItem(size=(80, 60), offset=(50, 10))

        self.legends_main = []
        self.legends_second = []

        self.y_main_axis_label = ""
        self.x_axis_label = ""
        self.y_second_axis_label = ""

        self.initUI()

    @time_decorator
    def initUI(self):
        self.tab1Layout = QVBoxLayout()
        # Add all data source selectors and graph area to tab1Layout
        self.settingsLayout = self.setupSettingsLayout()
        self.dataSourceLayout = self.setupDataSourceSelectors()
        
        self.graphView = self.setupGraphView()

        self.graphView.plotItem.getAxis("left").linkToView(
            self.graphView.plotItem.getViewBox()
        )
        self.graphView.plotItem.getAxis("bottom").linkToView(
            self.graphView.plotItem.getViewBox()
        )
        
        import_lay = QHBoxLayout()
        self.import_button = QPushButton()
        self.selector = QSpacerItem(
            15, 15, QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        import_lay.addWidget(self.import_button)
        import_lay.addItem(self.selector)


        data_name_layout = QHBoxLayout()
        self.data_name_label = QLabel()
        data_name_layout.addWidget(self.data_name_label)
        data_name_layout.addItem(self.selector)
        # Add the layouts to the first tab
        self.tab1Layout.addLayout(data_name_layout)
        self.tab1Layout.addLayout(self.dataSourceLayout)
        self.tab1Layout.addLayout(self.settingsLayout)
        self.tab1Layout.addWidget(self.graphView)
        self.tab1Layout.addLayout(import_lay)
        self.page.setLayout(self.tab1Layout)
        
        self.import_button.clicked.connect(self.import_data)

        self.retranslateUi(self.page)

    @time_decorator
    def import_data(self, *args, **kwargs):
        
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, ans = QFileDialog.getOpenFileName(
            caption=QApplication.translate("GraphWindow","укажите путь импорта"),
            directory="",
            filter="Книга Excel (*.xlsx)",
            options=options,
        )
        
        if fileName:
            if ans == "Книга Excel (*.xlsx)":
                # Считываем все листы из книги Excel
                #xls = pd.ExcelFile(fileName, engine='openpyxl')
                #dfs = {sheet_name: xls.parse(sheet_name) for sheet_name in xls.sheet_names}


                df = pd.read_excel(fileName, engine='openpyxl')
                #for sheet_name, df in dfs.items():
                #    if 'time' not in df.columns:
                #       self.is_time_column = False
                #       print(f"Отсутствует столбец 'time' в листе {sheet_name}")

                if 'time' not in df.columns:
                    self.is_time_column = False
                    #raise ValueError("Отсутствует обязательный столбец 'time'")

                df = df.dropna(axis=1, how='all')#удаление пустых столбцов

                result = {}
                errors_col = []

                for col in df.columns:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='raise')
                    except ValueError:
                        errors_col.append(col)
                        continue
                    
                if errors_col != []:
                    res = ', '.join(errors_col)
                    text = QApplication.translate("GraphWindow", "В столбцах {res} обнаружены данные, которые не получается преобразовать в числа.\nПри построение эти точки будут пропущены.")
                    text = text.format(res = res)
                    message = messageDialog(
                        title = QApplication.translate("GraphWindow","Сообщение"),
                        text= text
                    )
                    message.exec_()
                    
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    col_ = col.replace('(', '[').replace(')', ']')
                    result[col_] = np.array( df[col].tolist() )
                    
                dev = {'d': {'c': result}}

                self.data_name_label.setText(fileName)

                self.set_default()
                self.update_dict_param(dev)
                return result

    def setupDataSourceSelectors(self):
        # Data source selectors layout
        dataSourceLayout = QHBoxLayout()

        #sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # Создание селекторов
        x_buf = self.createHoverSelector("X-Axis:")
        y_first_buf = self.createHoverSelector("Y main Axis:")
        y_second_buf = self.createHoverSelector("Y second Axis:")
        
        self.x_param_selector = x_buf[2]
        self.y_first_param_selector = y_first_buf[2]
        self.y_second_param_selector = y_second_buf[2]
        
        self.x_param_selector.setMaximumSize(800, 75)
        self.y_first_param_selector.setMaximumSize(800, 75)
        self.y_second_param_selector.setMaximumSize(800, 75)
        
        self.x_param_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.y_first_param_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.y_second_param_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.x_param_hover = x_buf[1]
        self.y_first_param_hover = y_first_buf[1]
        self.y_second_param_hover = y_second_buf[1]

        self.second_check_box = QCheckBox("Add second axis")
        self.y_second_Layout = QVBoxLayout()
        self.y_second_Layout.addWidget(QLabel("Y second Axis:"))
        self.y_second_Layout.addWidget(self.y_second_param_selector)
        self.y_second_Layout.addWidget(self.second_check_box)
        
        dataSourceLayout.addWidget(self.y_first_param_hover)
        dataSourceLayout.addWidget(self.x_param_hover)
        dataSourceLayout.addLayout(self.y_second_Layout)

        self.x_param_selector.addItems(["Select parameter"])
        self.y_first_param_selector.addItems(["Select parameter"])
        self.y_second_param_selector.addItems(["Select parameter"])
        
        item = self.x_param_selector.item(0)
        
        self.x_param_selector.setCurrentItem( item )
        self.y_first_param_selector.setCurrentItem( item )
        self.y_second_param_selector.setCurrentItem( item )

        self.y_first_param_selector.itemSelectionChanged.connect(
            lambda: self.update_plot()
        )
        self.y_second_param_selector.itemSelectionChanged.connect(
            lambda: self.update_plot()
        )
        self.x_param_selector.itemSelectionChanged.connect(lambda: self.update_plot())
        self.second_check_box.stateChanged.connect(lambda: self.update_plot())

        return dataSourceLayout

    def createHoverSelector(self, label_text) -> list:
        layout = QVBoxLayout()
        label = QLabel(label_text)
        listWidget = QListWidget()
        #listWidget.setVisible(True)
        listWidget.setSelectionMode(QListWidget.SingleSelection)

        # Создаем виджет-обертку
        hover_widget = QWidget()
        hover_widget.setLayout(layout)
        #hover_widget.setStyleSheet("background-color: transparent;")  # Прозрачный фон
        hover_widget.setAttribute(Qt.WA_Hover, True)
        hover_widget.enterEvent = lambda event: self.onHoverShowList(event, listWidget)
        hover_widget.leaveEvent = lambda event: self.onHoverHideList(event, listWidget)

        # Добавляем виджеты в layout
        layout.addWidget(label)
        layout.addWidget(listWidget)

        return [layout, hover_widget, listWidget]

    def onHoverShowList(self, event, listWidget):
        pass
        #listWidget.setVisible(True)

    def onHoverHideList(self, event, listWidget):
        pass
        #listWidget.setVisible(False)

    def setupSettingsLayout(self):
        
        self.multiple_checkbox = QCheckBox()
        self.line_graph_button = QPushButton("set color line main")
        self.line_graph_button.clicked.connect(lambda: self.push_line_color_graph("m"))

        self.line_graph_button_second = QPushButton("set color line second")
        self.line_graph_button_second.clicked.connect(
            lambda: self.push_line_color_graph("s")
        )
        
        self.multiple_checkbox.stateChanged.connect(self.update_multiple)

        self.tooltip = QLabel("X:0,Y:0")
        self.horizontalSpacer = QSpacerItem(
            15, 15, QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        settingsLayout = QHBoxLayout()
        settingsLayout.addWidget(self.multiple_checkbox)
        #settingsLayout.addWidget(self.line_graph_button_second)
        settingsLayout.addItem(self.horizontalSpacer)
        settingsLayout.addWidget(self.tooltip)

        return settingsLayout
    
    def update_multiple(self):
        if self.multiple_checkbox.isChecked() == True:
            self.y_first_param_selector.setSelectionMode(QListWidget.MultiSelection)
            self.y_second_param_selector.setSelectionMode(QListWidget.MultiSelection)
            
        else:
            self.y_first_param_selector.setSelectionMode(QListWidget.SingleSelection)
            self.y_second_param_selector.setSelectionMode(QListWidget.SingleSelection)
            
        self.y.clear()
        self.y2.clear()
        
        self.y_second_param_selector.clearSelection()
        self.y_first_param_selector.clearSelection()
        
        self.update_draw()

    def setupGraphView(self):
        graphView = pg.PlotWidget(title="")

        self.color_line_main = "#55aa00"
        self.color_line_second = "#ff0000"

        graphView.scene().sigMouseMoved.connect(self.showToolTip)
        graphView.plotItem.getAxis("left").linkToView(graphView.plotItem.getViewBox())
        graphView.plotItem.getAxis("bottom").linkToView(graphView.plotItem.getViewBox())

        self.p1 = graphView.plotItem

        self.p2 = pg.ViewBox()
        self.p1.showAxis("right")
        self.p1.scene().addItem(self.p2)
        self.p1.getAxis("right").linkToView(self.p2)
        self.p2.setXLink(self.p1)
        self.p1.getAxis("right").setLabel("axis2", color="#000fff")

        self.p1.vb.sigResized.connect(self.updateViews)
        
        self.legend.setParentItem(self.p1)
        self.legend2.setParentItem(self.p2)

        my_font = QFont("Times", 13)
        self.p1.getAxis("right").label.setFont(my_font)
        graphView.getAxis("bottom").label.setFont(my_font)
        graphView.getAxis("left").label.setFont(my_font)

        return graphView

    def push_line_color_graph(self, which_axis):
        dlg = QColorDialog(self.page)
        if dlg.exec_():
            if which_axis == "m":
                self.color_line_main = dlg.currentColor().name()
            else:
                self.color_line_second = dlg.currentColor().name()

            self.update_plot()

    def showToolTip(self, event):
        pos = event 
        if len(self.y) > 0 and len(self.x) > 0:
            self.graphView.removeItem(self.tooltip)
            x_val = round(
                self.graphView.plotItem.vb.mapSceneToView(pos).x(), 1
            ) 
            y_val = round(
                self.graphView.plotItem.vb.mapSceneToView(pos).y(), 1
            ) 
            text = f'<p style="font-size:{10}pt">X:{x_val} Y:{y_val}</p>'
            # Устанавливаем текст подсказки
            self.tooltip.setText(text)

    def update_dict_param(self, new: dict):
        if new:
            new_param = []
            new_name_parameters = self.create_name_param(new)
            old_name_parameters = self.create_name_param(self.dict_param)
            for name in new_name_parameters:
                if name not in old_name_parameters:
                    new_param.append(name)

            '''
            for devices, channels in new.items():
                for ch, values in channels.items():
                    for param, value in values.items():
                        if type(value) == list:
                            print(f"{value=}")
                            value = np.array(value)
            '''
            self.dict_param = new
            self.update_param_in_comboxes(new_param)
            self.update_plot()

    def set_default(self):
        self.key_to_update_plot = False

        self.x_param_selector.clear()
        self.y_first_param_selector.clear()
        self.x_param_selector.clear()
        self.y_first_param_selector.clear()
        self.y_second_param_selector.clear()
        self.x_param_selector.addItems(["Select parameter"])
        self.y_first_param_selector.addItems(["Select parameter"])
        self.y_second_param_selector.addItems(["Select parameter"])
        self.x = []
        self.y.clear()
        self.y2.clear()
        for item in self.graphView.items():
            if isinstance(item, pg.PlotDataItem):
                self.graphView.removeItem(item)
        self.p2.clear()

        self.dict_param = {}

        old_name_parameters = []

        self.key_to_update_plot = True

    def remove_parameter(self, parameter, qlistwidget):
            for index in range(qlistwidget.count()):
                if qlistwidget.item(index).text() == parameter:
                    qlistwidget.takeItem(index)
                    break

    def update_param_in_comboxes(self, new_param = None):
        self.key_to_update_plot = False
        if new_param is not None:
            self.x_param_selector.addItems(new_param)
            self.y_first_param_selector.addItems(new_param)
            self.y_second_param_selector.addItems(new_param)
            self.key_to_update_plot = True
            return
        
        self.list_param = self.create_name_param(self.dict_param)
        box_x = self.x_param_selector.currentItem()
        box_y = self.y_first_param_selector.currentItem()
        box_y2 = self.y_second_param_selector.currentItem()

        if box_x is not None:
            box_x = box_x.text()
        if box_y2 is not None:
            box_y2 = box_y2.text()
        if box_y is not None:
            box_y = box_y.text()
        
        # print(f"{box_x=} {box_y=}")
        self.x_param_selector.clear()
        self.y_first_param_selector.clear()
        self.y_second_param_selector.clear()
        if box_x not in self.list_param:
            self.list_param.append(box_x)
        if box_y not in self.list_param:
            self.list_param.append(box_y)
        if box_y not in self.list_param:
            self.list_param.append(box_y2)
        # print(f"{self.list_param=}")
        self.x_param_selector.addItems(self.list_param)
        self.y_first_param_selector.addItems(self.list_param)
        self.y_second_param_selector.addItems(self.list_param)
        self.x_param_selector.setCurrentItem(QListWidgetItem(box_x))
        self.y_first_param_selector.setCurrentItem(QListWidgetItem(box_y))
        self.y_second_param_selector.setCurrentItem(QListWidgetItem(box_y2))
        self.key_to_update_plot = True

    def updateViews(self):

        self.p2.setGeometry(self.p1.vb.sceneBoundingRect())
        self.p2.linkedViewChanged(self.p1.vb, self.p2.XAxis)

    def get_last_item_parameter(self, selector, default="Select parameter"):
        item = selector.currentItem()
        return item.text() if item is not None else default
    
    def update_data(self):
        string_x = self.get_last_item_parameter(self.x_param_selector)
        string_y = self.get_last_item_parameter(self.y_first_param_selector)
        string_y2 = self.get_last_item_parameter(self.y_second_param_selector)

        
        current_items_y = list(item.text() for item in self.y_first_param_selector.selectedItems())
        current_items_y2 = list(item.text() for item in self.y_second_param_selector.selectedItems())

        if string_y not in current_items_y and string_y != "Select parameter":
                device_y, ch_y, key_y = self.decode_name_parameters(string_y)
                if key_y in self.y.keys():
                    self.y.pop(key_y)
                    self.graphView.removeItem(self.curve1[key_y])
                    self.curve1.pop(key_y)
                    return
                else:
                    string_y = "Select parameter"

        if string_y2 not in current_items_y2 and string_y2 != "Select parameter":
                device_y2, ch_y2, key_y2 = self.decode_name_parameters(string_y2)
                if key_y2 in self.y2.keys():
                    self.y2.pop(key_y2)
                    self.p2.removeItem(self.curve2[key_y2])
                    self.p2.removeItem(self.curve2_dots[key_y2])
                    self.curve2.pop(key_y2)
                    self.curve2_dots.pop(key_y2)
                    return
                else:
                    string_y2 = "Select parameter"


        if string_x != "Select parameter":
            self.remove_parameter("Select parameter", self.x_param_selector)

        if string_y != "Select parameter":
            self.remove_parameter("Select parameter", self.y_first_param_selector)

        if string_y2 != "Select parameter":
            self.remove_parameter("Select parameter", self.y_second_param_selector)

        check_main = True
        
        if not self.multiple_checkbox.isChecked():
            self.y.clear()
            self.y2.clear()

        if string_x == "Select parameter" or string_y == "Select parameter":
            check_main = False
            if self.second_check_box.isChecked():
                if string_x == "Select parameter" or string_y2 == "Select parameter":
                    return
            else:
                return

        if string_x == "time" and string_y == "time":
            check_main = False
            if self.second_check_box.isChecked():
                if string_x == "time" or string_y2 == "time":
                    return
            else:
                return

        if check_main == True:
            if self.y is self.y2:
                self.y = {}
                self.x = []
                self.y_main_axis_label = ""
            if (
                string_x == "time"
                and string_y != "time"
                and string_y != "Select parameter"
            ):
                device_y, ch_y, parameter_y = self.decode_name_parameters(string_y)
                self.y_main_axis_label = parameter_y
                self.x_axis_label = "time"
                self.x = self.dict_param[device_y][ch_y]["time"]
                self.y[parameter_y] = self.dict_param[device_y][ch_y][parameter_y]
                
            elif string_y == "time" and string_x != "time":
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                self.x_axis_label = parameter_x
                self.y_main_axis_label = "time"
                self.y["time"] = self.dict_param[device_x][ch_x]["time"]
                self.x = self.dict_param[device_x][ch_x][parameter_x]
                
            elif string_x == string_y:
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                self.x = self.dict_param[device_x][ch_x][parameter_x]
                self.y[parameter_x] = self.dict_param[device_x][ch_x][parameter_x]
                self.y_main_axis_label = parameter_x
                self.x_axis_label = parameter_x
            else:

                device_y, ch_y, parameter_y = self.decode_name_parameters(string_y)
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                print(self.dict_param)
                x_param = self.dict_param[device_x][ch_x][parameter_x]
                y_param = self.dict_param[device_y][ch_y][parameter_y]
                if self.is_time_column:

                    x_time = self.dict_param[device_x][ch_x]["time"]
                    y_time = self.dict_param[device_y][ch_y]["time"]
                    calculator_param = ArrayProcessor()
                    
                    self.x, bufy, _ = calculator_param.combine_interpolate_arrays(
                        arr_time_x=x_time,
                        arr_time_y=y_time,
                        values_x=x_param,
                        values_y=y_param,
                                        )
                        
                    self.y[parameter_y] = bufy
                    
                else:
                    self.x = x_param
                    self.y[parameter_y] = y_param
                
                self.y_main_axis_label = parameter_y
                self.x_axis_label = parameter_x

        if self.second_check_box.isChecked():
            if (
                string_x == "time" and string_y2 == "time"
            ) or string_y2 == "Select parameter":
                self.y_second_axis_label = ""
                self.x2 = []
                self.y2.clear()
            elif (
                string_x == "time"
                and string_y2 != "time"
                and string_y2 != "Select parameter"
            ):
                
                device_y2, ch_y2, parameter_y2 = self.decode_name_parameters(string_y2)
                self.y_second_axis_label = parameter_y2
                self.x_axis_label = "time"
                self.x2 = self.dict_param[device_y2][ch_y2]["time"]
                self.y2[parameter_y2] = self.dict_param[device_y2][ch_y2][parameter_y2]

            elif string_y2 == "time" and string_x != "time":
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                self.x_axis_label = parameter_x
                self.y_second_axis_label = "time"
                self.y2["time"] = self.dict_param[device_x][ch_x]["time"]
                self.x2 = self.dict_param[device_x][ch_x][parameter_x]
            elif string_x == string_y2 and string_y2 != "time":
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                self.x2 = self.dict_param[device_x][ch_x][parameter_x]
                self.y2[parameter_x] = self.x2
                self.y_second_axis_label = parameter_x
                self.x_axis_label = parameter_x
            else:
                device_y2, ch_y2, parameter_y2 = self.decode_name_parameters(string_y2)
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                x_param = self.dict_param[device_x][ch_x][parameter_x]
                y_param = self.dict_param[device_y2][ch_y2][parameter_y2]
                if self.is_time_column:
                    x_time = self.dict_param[device_x][ch_x]["time"]
                    y_time = self.dict_param[device_y2][ch_y2]["time"]
                    calculator_param = ArrayProcessor()
                    self.x2, bufy2, _ = calculator_param.combine_interpolate_arrays(
                        arr_time_x=x_time,
                        arr_time_y=y_time,
                        values_x=x_param,
                        values_y=y_param,
                    )
                    self.y2[parameter_y2] = bufy2
                else:
                    self.x2 = x_param
                    self.y2[parameter_y2] = y_param
                    
                self.y_second_axis_label = parameter_y2
                self.x_axis_label = parameter_x

        else:
            self.y_second_axis_label = ""
            self.x2 = self.x2[:0]
            self.y2.clear()


        if len(self.y.keys()) > 1:
            #если множественное построение, то лейбл не ставим
            self.y_main_axis_label = ""

        if len(self.y2.keys()) > 1:
            #если множественное построение, то лейбл не ставим
            self.y_second_axis_label = ""

        if self.is_show_warning == True:
            points_num = 10000
            self.is_show_warning = False
            if len(self.x) > points_num:
                text = QApplication.translate("GraphWindow", "Число точек превысило {points_num}, расчет зависимости одного параметра от другого может занимать некоторое время.\n Особенно, на слабых компьютерах. Рекомендуется выводить графики в зависимости от времени.")
                text = text.format(points_num = points_num)
                message = messageDialog(
                    title=QApplication.translate("GraphWindow","Сообщение"),
                    text=text
                )
                message.exec_()

    @time_decorator
    def update_draw(self):

        keys_y = set(self.y.keys())
        keys_y2 = set(self.y2.keys())

        to_remove1 = [key for key in self.curve1 if key not in keys_y]
        to_remove2 = [key for key in self.curve2 if key not in keys_y2]


        for key in to_remove1:
            self.graphView.removeItem(self.curve1[key])
            del self.curve1[key]

        for key in to_remove2:
            self.p2.removeItem(self.curve2[key])
            self.p2.removeItem(self.curve2_dots[key])
            del self.curve2[key]
            del self.curve2_dots[key]

        # Обновление легенд
        self.legend.clear()
        self.legend2.clear()

        self.graphView.setLabel("left", self.y_main_axis_label, color=self.color_line_main)
        self.graphView.setLabel("bottom", self.x_axis_label, color="#ffffff")

        # Обновление curve1
        for i, (key, data) in enumerate(self.y.items()):
            min_length = min(len(self.x), len(data))

            if key in self.curve1:
                self.curve1[key].setData( self.x[:min_length], data[:min_length] )
            else:
                pen = pg.mkPen(color=cold_colors[i], width=2, style=pg.QtCore.Qt.SolidLine)
                self.curve1[key] = self.graphView.plot(x = self.x[:min_length], y = data[:min_length], pen=pen, symbol='o', 
                                                    symbolPen=cold_colors[i], symbolBrush=cold_colors[i])
            self.legend.addItem(self.curve1[key], f"{key}")

        # Обновление curve2, если чекбокс отмечен
        if self.second_check_box.isChecked():
            self.p1.getAxis("right").setLabel(self.y_second_axis_label, color=self.color_line_second)
            self.p1.getAxis("right").setStyle(showValues=True)

            for i, (key, data) in enumerate(self.y2.items()):
                min_length = min(len(self.x2), len(data))

                if key not in self.curve2:
                    pen = pg.mkPen(color=warm_colors[i], width=2, style=pg.QtCore.Qt.DashLine)
                    brush = pg.mkBrush(color=warm_colors[i])
                    self.curve2[key] = pg.PlotCurveItem(pen=pen)
                    self.curve2_dots[key] = pg.ScatterPlotItem(pen=pen, symbol='x', size=10)
                    self.p2.addItem(self.curve2[key])
                    self.p2.addItem(self.curve2_dots[key])
                    self.curve2_dots[key].setBrush(brush)
                    
                self.curve2[key].setData(self.x2[:min_length], data[:min_length])
                self.curve2_dots[key].setData(self.x2[:min_length], data[:min_length])
                self.legend2.addItem(self.curve2[key], f"{key}")
        else:
            self.p1.getAxis("right").setStyle(showValues=False)
            self.p1.getAxis("right").setLabel("")

    def update_plot(self):
        if self.key_to_update_plot:
            self.update_data()
            self.update_draw()

    def create_name_param(self, main_dict):
        if "time" in main_dict.keys():
            output_list = ["time"]
        else:
            output_list = []

        for device, channels in main_dict.items():
            for channel, values in channels.items():
                if "time" in values.keys():
                    output_list.append("time")
                for key, value in values.items():
                    # print(key)
                    if key != "time" and ("WAVECH" not in key.upper()):
                        output_list.append(f"{key}({device} {channel})")

        return output_list

    def decode_name_parameters(self, string_y):
        buf_y = string_y.split("(")
        if len(buf_y) > 1:
            parameter_y = buf_y[0]
            # print(f"{buf_y=}")
            device_y = buf_y[1].split(" ")[0]
            ch_y = buf_y[1].split(" ")[1][:-1]
        else:
            print(f"ошибка при декодиировании имени параметра {buf_y}")
            return 1,1,1

        return device_y, ch_y, parameter_y

    def closeEvent(self, event):  # эта функция вызывается при закрытии окна
        self.graph_win_close_signal.emit(1)

    def retranslateUi(self, GraphWindow):
        _translate = QApplication.translate
        self.import_button.setText( _translate("GraphWindow", "Импортировать..") )
        self.data_name_label.setText( _translate("GraphWindow","Экспериментальные данные") )
        self.multiple_checkbox.setText( _translate("GraphWindow","Множественное построение") )
        
