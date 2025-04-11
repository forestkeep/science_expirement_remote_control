# Copyright © 2025 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

import logging
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QCheckBox, QHBoxLayout,QLabel,
                             QListWidget, QSizePolicy, QVBoxLayout, QWidget)

logger = logging.getLogger(__name__)

class customQListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        
    def add_parameters(self, parameters: str|list):
        if isinstance(parameters, str):
            parameters = [parameters]

        for parameter in parameters:
            if not any(self.item(i).text() == parameter for i in range(self.count())):
                self.addItem(parameter)

    def remove_parameters(self, parameters: str|list):
        if isinstance(parameters, str):
            parameters = [parameters]

        for parameter in parameters:
            for index in range(self.count()):
                if self.item(index).text() == parameter:
                    self.takeItem(index)

    def get_last_item_parameter(self, default="Select parameter"):
        item = self.currentItem()
        return item.text() if item is not None else default

class paramSelector(QWidget):

    def __init__(self):
        super().__init__()
        self.setLayout(self.setupDataSourceSelectors())

    def createHoverSelector(self, label_text) -> list:
        layout = QVBoxLayout()
        label = QLabel(label_text)
        listWidget = customQListWidget()
        listWidget.setSelectionMode(QListWidget.SingleSelection)

        hover_widget = QWidget()
        hover_widget.setLayout(layout)

        hover_widget.setAttribute(Qt.WA_Hover, True)

        layout.addWidget(label)
        layout.addWidget(listWidget)

        return [layout, hover_widget, listWidget]
    
    def setupDataSourceSelectors(self):
        main_lay = QVBoxLayout()
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

        dataSourceLayout.addWidget(self.y_first_param_hover)
        dataSourceLayout.addWidget(self.x_param_hover)
        dataSourceLayout.addWidget(self.y_second_param_hover)

        item = self.x_param_selector.item(0)
        
        self.x_param_selector.setCurrentItem( item )
        self.y_first_param_selector.setCurrentItem( item )
        self.y_second_param_selector.setCurrentItem( item )

        self.second_check_box = QCheckBox("Add second axis")
        self.check_miltiple = QCheckBox("Multiple selection")

        self.hor_check_lay = QHBoxLayout()
        self.hor_check_lay.addWidget(self.check_miltiple)
        self.hor_check_lay.addWidget(self.second_check_box)

        main_lay.addLayout(dataSourceLayout)
        main_lay.addLayout(self.hor_check_lay)

        self.y_second_param_hover.setVisible(False)

        self.second_check_box.stateChanged.connect(self.second_check_box_changed)
        self.check_miltiple.stateChanged.connect(self.check_miltiple_changed)

        return main_lay
    
    def check_miltiple_changed(self):
        if self.check_miltiple.isChecked() == True:
            self.y_first_param_selector.setSelectionMode(QListWidget.MultiSelection)
            self.y_second_param_selector.setSelectionMode(QListWidget.MultiSelection)
        else:
            self.y_first_param_selector.setSelectionMode(QListWidget.SingleSelection)
            self.y_second_param_selector.setSelectionMode(QListWidget.SingleSelection)
            self.y_second_param_selector.clearSelection()
            self.y_first_param_selector.clearSelection()
    
    def second_check_box_changed(self):
        if self.second_check_box.isChecked():
            self.y_second_param_hover.setVisible(True)
        else:
            self.y_second_param_hover.setVisible(False)

class paramController( QObject):
    parameters_updated = pyqtSignal(str, list, list)
    def __init__(self, paramSelector: paramSelector) -> None:
        super().__init__()
        self.paramSelector = paramSelector
        self.paramSelector.x_param_selector.itemPressed.connect(self.x_param_changed)
        self.paramSelector.y_first_param_selector.itemPressed.connect(self.y_first_param_changed)
        self.paramSelector.y_second_param_selector.itemPressed.connect(self.y_second_param_changed)
        self.paramSelector.check_miltiple.stateChanged.connect(self.update_multiple)
        self.paramSelector.second_check_box.stateChanged.connect(self.second_check_box_changed)

        self.curent_x_parameter = None
        self.curent_y_first_parameters = []
        self.curent_y_second_parameters = []

        self.__x_parameters = set()
        self.__y_first_parameters = set()
        self.__y_second_parameters = set()

    def x_param_changed(self):
        self.curent_x_parameter = self.paramSelector.x_param_selector.currentItem().text()
        self.parameters_updated.emit(self.curent_x_parameter, self.curent_y_first_parameters, self.curent_y_second_parameters)

    def y_first_param_changed(self):
        self.manage_y_selectors(self.paramSelector.y_first_param_selector, self.curent_y_first_parameters)
        self.parameters_updated.emit(self.curent_x_parameter, self.curent_y_first_parameters, self.curent_y_second_parameters)

    def y_second_param_changed(self):
        self.manage_y_selectors(self.paramSelector.y_second_param_selector, self.curent_y_second_parameters)
        self.parameters_updated.emit(self.curent_x_parameter, self.curent_y_first_parameters, self.curent_y_second_parameters)

    def manage_y_selectors(self, list_widget, buf_list):
        if self.paramSelector.check_miltiple.isChecked():
            buf_text = list_widget.currentItem().text()
            if buf_text in buf_list:
                buf_list.remove(buf_text)
            else:
                buf_list.append(buf_text)
        else:
            buf_list.clear()
            buf_item = list_widget.currentItem()
            if buf_item is not None:
                buf_list.append(list_widget.currentItem().text())

    def second_check_box_changed(self):
        if self.paramSelector.second_check_box.isChecked():
            self.curent_y_second_parameters = [item.text() for item in self.paramSelector.y_second_param_selector.selectedItems()]
        else:
            self.curent_y_second_parameters.clear()

        self.parameters_updated.emit(self.curent_x_parameter, self.curent_y_first_parameters, self.curent_y_second_parameters)
            
    def add_parameters(self, new_parameters):
        self.__x_parameters.update(new_parameters)
        self.__y_first_parameters.update(new_parameters)
        self.__y_second_parameters.update(new_parameters)

        self.paramSelector.y_first_param_selector.add_parameters(new_parameters)
        self.paramSelector.y_second_param_selector.add_parameters(new_parameters)
        self.paramSelector.x_param_selector.add_parameters(new_parameters)

    def clear_y_axis(self):
        self.paramSelector.y_second_param_selector.clearSelection()
        self.paramSelector.y_first_param_selector.clearSelection()
        self.curent_y_first_parameters = []
        self.curent_y_second_parameters = []
   
    def update_multiple(self):
        if not self.paramSelector.check_miltiple.isChecked():
            self.clear_y_axis()

        self.parameters_updated.emit(self.curent_x_parameter, self.curent_y_first_parameters, self.curent_y_second_parameters)

    def set_default(self):
        self.curent_x_parameter = None
        self.curent_y_first_parameters = []
        self.curent_y_second_parameters = []
        
        self.paramSelector.x_param_selector.clear()
        self.paramSelector.y_first_param_selector.clear()
        self.paramSelector.y_second_param_selector.clear()

        self.parameters_updated.emit(self.curent_x_parameter, self.curent_y_first_parameters, self.curent_y_second_parameters)

    def get_parameters(self):
        return self.curent_x_parameter, self.curent_y_first_parameters, self.curent_y_second_parameters

if __name__ == '__main__':
    import sys

    def print_param(x_list, y_first_list, y_second_list):
        print("parameters updated")
        print(x_list, y_first_list, y_second_list)

    app = QApplication(sys.argv)
    main_win = paramSelector()
    my_class = paramController(main_win)
    my_class.add_parameters(["a", "b", "c", "d", "e", "f", "g", "b", "a"])
    my_class.parameters_updated.connect(print_param)
    main_win.show()
    sys.exit(app.exec_())