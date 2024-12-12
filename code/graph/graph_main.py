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
    from curve_data import linearData
    from colors import cold_colors, warm_colors, GColors
except:
    from graph.calc_values_for_graph import ArrayProcessor
    from graph.Message_graph import messageDialog
    from graph.curve_data import linearData
    from graph.colors import cold_colors, warm_colors, GColors


def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Метод {func.__name__} - {end_time - start_time} с")
        return result

    return wrapper


class graphMain:

    def __init__(self, tablet_page, main_class):
        self.page = tablet_page
        self.is_show_warning = True
        self.key_to_update_plot = True
        self.x = []
        self.y = {}
        self.x2 = []
        self.y2 = {}
        self.dict_param = {}
    
        self.main_class = main_class

        self.curve1 = {}
        self.curve2 = {}
        self.curve2_dots = {}

        self.old_params = []

        self.is_time_column = True
        
        self.legend = pg.LegendItem(size=(80, 60), offset=(10, 10))
        self.legend2 = pg.LegendItem(size=(80, 60), offset=(50, 10))

        self.legends_main = []
        self.legends_second = []

        self.y_main_axis_label = ""
        self.x_axis_label = ""
        self.y_second_axis_label = ""

        self.stack_curve = {}

        self.colors_class = GColors()
        self.color_warm_gen = self.colors_class.get_random_warm_color()
        self.color_cold_gen = self.colors_class.get_random_cold_color()

        self.initUI()

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

    def import_data(self, *args, **kwargs):

        if self.main_class.experiment_controller is not None:
            if self.main_class.experiment_controller.is_experiment_running():
                self.main_class.show_tooltip("Дождитесь окончания эксперимента", timeout = 3000)
                return
        
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


                df = pd.read_excel(fileName, engine='openpyxl')
                if 'time' not in df.columns:
                    self.is_time_column = False

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
        '''
        self.y_first_param_selector.itemPressed.connect(
            lambda: self.update_plot()
        )
        self.y_second_param_selector.itemPressed.connect(
            lambda: self.update_plot()
        )
        self.x_param_selector.itemPressed.connect(lambda: self.update_plot())
        self.second_check_box.stateChanged.connect(lambda: self.update_plot())
        '''
        #===============================================
        self.y_first_param_selector.itemPressed.connect( lambda: self.update_plot( self.y_first_param_selector ) )
        self.y_second_param_selector.itemPressed.connect( lambda: self.update_plot( self.y_second_param_selector ) )
        self.x_param_selector.itemPressed.connect( lambda: self.update_plot( self.x_param_selector ) )
        self.second_check_box.stateChanged.connect( lambda: self.update_plot( self.second_check_box ) )

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
        #hover_widget.enterEvent = lambda event: self.onHoverShowList(event, listWidget)
        #hover_widget.leaveEvent = lambda event: self.onHoverHideList(event, listWidget)

        # Добавляем виджеты в layout
        layout.addWidget(label)
        layout.addWidget(listWidget)

        return [layout, hover_widget, listWidget]

    def setupSettingsLayout(self):
        
        self.multiple_checkbox = QCheckBox()

        self.multiple_checkbox.stateChanged.connect(self.update_multiple)

        self.tooltip = QLabel("X:0,Y:0")
        self.horizontalSpacer = QSpacerItem(
            15, 15, QSizePolicy.Expanding, QSizePolicy.Minimum
        )
        settingsLayout = QHBoxLayout()
        settingsLayout.addWidget(self.multiple_checkbox)
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
            new_param = list(set(new_name_parameters) - set(self.old_params))

            self.dict_param = new
            for param in new_param:
                self.old_params.append(param)

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
        self.old_params = []
        self.y.clear()
        self.y2.clear()
        for item in self.graphView.items():
            if isinstance(item, pg.PlotDataItem):
                self.graphView.removeItem(item)
        self.p2.clear()

        self.dict_param = {}

        self.key_to_update_plot = True

    def remove_parameter(self, parameter, qlistwidget):
            for index in range(qlistwidget.count()):
                if qlistwidget.item(index).text() == parameter:
                    qlistwidget.takeItem(index)
                    #print(f"удалили {parameter} из {qlistwidget}")
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
        
        self.x_param_selector.clear()
        self.y_first_param_selector.clear()
        self.y_second_param_selector.clear()
        if box_x not in self.list_param:
            self.list_param.append(box_x)
        if box_y not in self.list_param:
            self.list_param.append(box_y)
        if box_y2 not in self.list_param:
            self.list_param.append(box_y2)

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
    
    def update_data_old(self):
        string_x = self.get_last_item_parameter(self.x_param_selector)
        string_y = self.get_last_item_parameter(self.y_first_param_selector)
        string_y2 = self.get_last_item_parameter(self.y_second_param_selector)

        current_items_y = list(item.text() for item in self.y_first_param_selector.selectedItems())
        current_items_y2 = list(item.text() for item in self.y_second_param_selector.selectedItems())

        print(f"{string_y=} {current_items_y=}")

        if string_y not in current_items_y and string_y != "Select parameter":
                if string_y in self.y.keys():
                    self.y.pop(string_y)
                    self.graphView.removeItem(self.curve1[string_y])
                    self.curve1.pop(string_y)
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
                self.y[string_y] = self.dict_param[device_y][ch_y][parameter_y]
                
            elif string_y == "time" and string_x != "time":
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                self.x_axis_label = parameter_x
                self.y_main_axis_label = "time"
                self.y["time"] = self.dict_param[device_x][ch_x]["time"]
                self.x = self.dict_param[device_x][ch_x][parameter_x]
                
            elif string_x == string_y:
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                self.x = self.dict_param[device_x][ch_x][parameter_x]
                self.y[string_x] = self.dict_param[device_x][ch_x][parameter_x]
                self.y_main_axis_label = parameter_x
                self.x_axis_label = parameter_x
            else:
                device_y, ch_y, parameter_y = self.decode_name_parameters(string_y)
                device_x, ch_x, parameter_x = self.decode_name_parameters(string_x)
                x_param = self.dict_param[device_x][ch_x][parameter_x]
                y_param = self.dict_param[device_y][ch_y][parameter_y]
                if self.is_time_column:

                    x_time = self.dict_param[device_x][ch_x]["time"]
                    y_time = self.dict_param[device_y][ch_y]["time"]
                    calculator_param = ArrayProcessor()
                    
                    self.x, bufy, _ = calculator_param.combine_interpolate_arrays(
                        arr_time_x1=x_time,
                        arr_time_x2=y_time,
                        values_y1=x_param,
                        values_y2=y_param,
                                        )
                        
                    self.y[string_y] = bufy
                    
                else:
                    self.x = x_param
                    self.y[string_y] = y_param
                
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
                        arr_time_x1=x_time,
                        arr_time_x2=y_time,
                        values_y1=x_param,
                        values_y2=y_param,
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

    def set_filters(self, filter_func):
        print(filter_func)

    def update_data(self, obj):

        string_x = self.get_last_item_parameter(self.x_param_selector)
        string_y = self.get_last_item_parameter(self.y_first_param_selector)
        string_y2 = self.get_last_item_parameter(self.y_second_param_selector)
   
        #блок очистки полей

        if string_x != "Select parameter":
            self.remove_parameter("Select parameter", self.x_param_selector)

        if string_y != "Select parameter":
            self.remove_parameter("Select parameter", self.y_first_param_selector)

        if string_y2 != "Select parameter":
            self.remove_parameter("Select parameter", self.y_second_param_selector)
        #==========================================================================
        #блок проверки параметров


        block_parameters = ("time", "Select parameter")
        check_main = True
        check_second = True
        
        if string_x in block_parameters and string_y in block_parameters:
            check_main = False

        if string_x in block_parameters and string_y2 in block_parameters and self.second_check_box.isChecked():
            check_second = False

        if not check_second and not check_main:
            return
        

        #==========================================================================

        if obj is None:
            return
        elif obj is self.x_param_selector:
            pass

        elif obj is self.y_first_param_selector and check_main:
                if self.multiple_checkbox.isChecked():
                    current_items_y = list(item.text() for item in self.y_first_param_selector.selectedItems())
                    if string_y not in current_items_y and string_y != "Select parameter":
                        if self.stack_curve.get(string_y + string_x) is not None:
                            self.stack_curve[string_y + string_x].is_draw = False
                            self.stack_curve[string_y + string_x].delete_curve_from_graph()
                            self.y_second_param_selector.addItem(string_y)
                            print(f"отменяем отрисовку {string_y + string_x} в блоке 1")
                            return
                else:
                    #отменить отрисовку всех кривых в блоке 1 кроме текущей
                    for data_curve in self.stack_curve.values():
                        if data_curve.is_draw and data_curve.parent_graph_field is self.graphView:
                            data_curve.is_draw = False
                            data_curve.delete_curve_from_graph()
                            self.y_second_param_selector.addItem(data_curve.y_name)
                    
                if self.stack_curve.get(string_y + string_x) is not None:
                    print(f"задаем отрисовку {string_y + string_x} в блоке 1")
                    self.stack_curve[string_y + string_x].place_curve_on_graph(graph_field  = self.graphView,
                                                                                legend_field = self.legend)
                    self.stack_curve[string_y + string_x].is_draw = True
                else:
                    print(f"создаем кривую {string_y + string_x} в блоке 1")
                    x1, y1, x1_name, y1_name, name_device1, name_ch1 = self.calc_curve_parameter(string_x, string_y)
                    self.manage_curve(y1, x1, name_device1, name_ch1, y1_name, x1_name, self.graphView, self.legend)

                self.remove_parameter(string_y, self.y_second_param_selector)

        elif obj is self.y_second_param_selector or obj is self.second_check_box:
            if not self.second_check_box.isChecked() or not check_second:
                return
            
            if self.multiple_checkbox.isChecked():
                current_items_y2 = list(item.text() for item in self.y_second_param_selector.selectedItems())
                if string_y2 not in current_items_y2 and string_y2 != "Select parameter":
                    if self.stack_curve.get(string_y2 + string_x) is not None:
                        self.stack_curve[string_y2 + string_x].is_draw = False
                        self.stack_curve[string_y2 + string_x].delete_curve_from_graph()
                        self.y_first_param_selector.addItem(string_y2)
                        print(f"отменяем отрисовку {string_y2 + string_x} в блоке 2")
                        return
            else:
                #отменить отрисовку всех кривых в блоке 2 кроме текущей
                for data_curve in self.stack_curve.values():
                    if data_curve.is_draw and data_curve.parent_graph_field is self.p2:
                        data_curve.is_draw = False
                        data_curve.delete_curve_from_graph()
                        self.y_first_param_selector.addItem(data_curve.y_name)
            
            if self.stack_curve.get(string_y2 + string_x) is not None:
                print(f"задаем отрисовку {string_y2 + string_x} в блоке 2")

                self.stack_curve[string_y2 + string_x].place_curve_on_graph(graph_field  = self.p2,
                                                                            legend_field = self.legend2)
                self.stack_curve[string_y2 + string_x].is_draw = True

            else:
                print(f"создаем кривую {string_y2 + string_x} в блоке 2")
                x2, y2, x2_name, y2_name, name_device2, name_ch2 = self.calc_curve_parameter(string_x, string_y2)
                self.manage_curve(y2, x2, name_device2, name_ch2, y2_name, x2_name, self.p2, self.legend2)

            self.remove_parameter(string_y2, self.y_first_param_selector)#удаляем этот параметр из второго селектора

        for key, curve in self.stack_curve.items():
            pass
            #print(key, curve.is_draw)
        print("//////////")

        
        #==========================================================================
        #блок расчета и создание объектов кривых


            
        #==========================================================================
        self.x_axis_label = string_x
        self.y_main_axis_label = string_y
        self.y_second_axis_label = string_y2
        if self.multiple_checkbox.isChecked():
            self.y_main_axis_label = ""
            self.y_second_axis_label = ""
    def deselect_item(self, text, list_widget):
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            if item.text() == text:
                list_widget.setItemSelected(item, False)
                break
    def calc_curve_parameter(self, string_x, string_y):
        device_y, ch_y, parameter_y = self.decode_name_parameters_new(string_y)
        device_x, ch_x, parameter_x = self.decode_name_parameters_new(string_x)
        if (string_x == "time"and string_y != "time" and string_y != "Select parameter"):
                x1_name = string_x
                y1_name = string_y
                x1 = self.dict_param[device_y][ch_y]["time"]
                y1 = self.dict_param[device_y][ch_y][parameter_y]
                name_device1 = device_y
                name_ch1 = ch_y
                
        elif string_y == "time" and string_x != "time":
            x1_name = string_x
            y1_name = string_y
            x1 = self.dict_param[device_x][ch_x][parameter_x]
            y1 = self.dict_param[device_x][ch_x]["time"]
            name_device1 = device_x
            name_ch1 = ch_x
            
        elif string_x == string_y:
            x1_name = string_x
            y1_name = string_y
            x1 = self.dict_param[device_x][ch_x][parameter_x]
            y1 = self.dict_param[device_y][ch_y][parameter_y]
            name_device1 = device_y
            name_ch1 = ch_y
            
        else:
            x_param = self.dict_param[device_x][ch_x][parameter_x]
            y_param = self.dict_param[device_y][ch_y][parameter_y]
            if self.is_time_column:

                x_time = self.dict_param[device_x][ch_x]["time"]
                y_time = self.dict_param[device_y][ch_y]["time"]
                calculator_param = ArrayProcessor()
                
                buf_x, bufy, _  = calculator_param.combine_interpolate_arrays(
                                                                            arr_time_x1 = x_time,
                                                                            arr_time_x2 = y_time,
                                                                            values_y1   = x_param,
                                                                            values_y2   = y_param,
                                                                                )
                x1 = buf_x
                y1 = bufy
            else:
                x1 = x_param
                y1 = y_param

            x1_name = string_x
            y1_name = string_y
            name_device1 = device_y
            name_ch1 = ch_y

        return x1, y1, x1_name, y1_name, name_device1, name_ch1

    def manage_curve(self, y_data, x_data, name_device, name_ch, y_name, x_name, graph_field, legend_field):
        if self.stack_curve.get(y_name + x_name) is None:
            new_data = linearData(raw_x   = x_data,
                                    raw_y   = y_data,
                                    device  = name_device,
                                    ch      = name_ch,
                                    y_name  = y_name,
                                    x_name  = x_name
                                    )
            self.stack_curve[y_name + x_name] = new_data
            
        self.stack_curve[y_name + x_name].is_draw = True
        self.stack_curve[y_name + x_name].parent_graph_field = graph_field
        self.stack_curve[y_name + x_name].legend_field = legend_field

    def check_and_show_warning(self):
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

    def update_draw(self):

        #==================================
        self.legend.clear()
        self.legend2.clear()

        self.graphView.setLabel("left", self.y_main_axis_label, color=self.color_line_main)
        self.graphView.setLabel("bottom", self.x_axis_label, color="#ffffff")
        for obj in self.stack_curve.values():
            if obj.is_draw:
                if obj.plot_obj == None:
                    buf_color = next(self.color_warm_gen)
                    if obj.saved_pen == None:
                        buf_pen = {
                            "color": buf_color,
                            "width": 1,
                            "antialias": True,  
                            "symbol": "o",
                        }
                    else:
                        buf_pen = obj.saved_pen

                    graph = pg.PlotDataItem(obj.filtered_x_data, 
                                            obj.filtered_y_data, 
                                            pen  = buf_pen,
                                            name = obj.legend_name,
                                            symbolPen=buf_color,
                                            symbolBrush=buf_color,
                                            symbol='o',
                                            )

                    obj.set_plot_obj(plot_obj = graph,
                                     pen      = buf_pen)
                print(f"рисуем в {obj.parent_graph_field=}")
                obj.parent_graph_field.addItem(obj.plot_obj)
                obj.legend_field.addItem(
                        obj.plot_obj, obj.legend_name
                )

            else:
                if obj.plot_obj != None:
                    print(f"удаляем {obj.plot_obj} из {obj.parent_graph_field=}")
                    obj.parent_graph_field.removeItem(obj.plot_obj)
                    #obj.plot_obj = None
        #=============================================================

    def update_draw_old(self):

        keys_y = set(self.y.keys())
        keys_y2 = set(self.y2.keys())

        print(f"{keys_y=}")

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
           
                self.curve1[key] = pg.PlotDataItem(
                    x=self.x[:min_length],
                    y=data[:min_length],
                    pen=pen,
                    symbol='o',
                    symbolPen=cold_colors[i],
                    symbolBrush=cold_colors[i]
                )

                self.graphView.addItem(self.curve1[key])

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

    def update_plot(self, obj = None):
        if self.key_to_update_plot:
            self.update_data( obj )
            self.update_draw()

    def create_name_param(self, main_dict):
        if "time" in main_dict.keys():
            output_list = ["time"]
        else:
            output_list = []

        for device, channels in main_dict.items():
            for channel, values in channels.items():
                if "time" in values.keys() and "time" not in output_list:
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
    
    def decode_name_parameters_new(self, string_y):
        if string_y.upper() == "TIME" or string_y.upper() == "SELECT PARAMETER":
            return False, False, string_y
        
        buf_y = string_y.split("(")
        if len(buf_y) > 1:
            parameter_y = buf_y[0]
            # print(f"{buf_y=}")
            device_y = buf_y[1].split(" ")[0]
            ch_y = buf_y[1].split(" ")[1][:-1]
        else:
            print(f"ошибка при декодиировании имени параметра {buf_y}")
            return False, False, string_y

        return device_y, ch_y, parameter_y

    def closeEvent(self, event):  # эта функция вызывается при закрытии окна
        self.graph_win_close_signal.emit(1)

    def retranslateUi(self, GraphWindow):
        _translate = QApplication.translate
        self.import_button.setText( _translate("GraphWindow", "Импортировать..") )
        self.data_name_label.setText( _translate("GraphWindow","Экспериментальные данные") )
        self.multiple_checkbox.setText( _translate("GraphWindow","Множественное построение") )
        
'''


new={'АКИП-2404_1': {'ch-1_meas': {'voltage': [0.0002342], 'time': [7.37]}, 'ch-2_meas': {'voltage': [0.01], 'time': [9.76]}}}


new={'device1': {'ch_1': {'time': [0, 0, 10], 'D': [9, 6, 9]}}


'''