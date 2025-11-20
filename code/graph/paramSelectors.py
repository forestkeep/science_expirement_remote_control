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
try:
    from numShowPoints_win import numShowPointsClass
except:
    from graph.numShowPoints_win import numShowPointsClass
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

    def rename_parameter(self, parameter, new_parameter):
        for index in range(self.count()):
            if self.item(index):
                if self.item(index).text() == parameter:
                    self.item(index).setText(new_parameter)

    def remove_parameters(self, parameters: str|list):

        if isinstance(parameters, str):
            parameters = [parameters]

        for parameter in parameters:
            for index in range(self.count()):
                if self.item(index):
                    if self.item(index).text() == parameter:
                        self.takeItem(index)
    def __manage_selection(self, text: str, checked: bool):
        for index in range(self.count()):
            if self.item(index):
                if self.item(index).text() == text:
                    logger.info(f"manage_selection {text} {checked}")
                    self.setCurrentItem(self.item(index))
                    self.item(index).setSelected(checked)
                    self.itemClicked.emit(self.item(index))#программно вызываем соответсвующую логику событий, будто кликнули на элемент

    def clear_selection(self, text: str):
        self.__manage_selection(text, False)

    def set_selection(self, text: str):
        self.__manage_selection(text, True)

class paramSelector(QWidget):

    def __init__(self, alias_manager):
        super().__init__()
        self.alias_manager = alias_manager
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

        layout.setContentsMargins(0, 0, 0, 0)
        hover_widget.setContentsMargins(0, 0, 0, 0)

        return [layout, hover_widget, listWidget]
    
    def setupDataSourceSelectors(self):
        main_lay = QVBoxLayout()
        dataSourceLayout = QHBoxLayout()

        main_lay.setContentsMargins(0, 0, 0, 0)
        dataSourceLayout.setContentsMargins(0, 0, 0, 0)

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

        self.second_check_box = QCheckBox("Add second axis")
        self.check_miltiple = QCheckBox("Multiple selection")

        self.hor_check_lay = QHBoxLayout()
        self.hor_check_lay.addWidget(self.check_miltiple)
        self.hor_check_lay.addWidget(self.second_check_box)

        self.hor_check_lay.setContentsMargins(0, 0, 0, 0)

        self.numPointsselector = numShowPointsClass()

        self.hor_check_lay.addWidget(self.numPointsselector)

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
        logger.info(f"second_check_box_changed {self.second_check_box.isChecked()}")
        if self.second_check_box.isChecked():
            self.y_second_param_hover.setVisible(True)
        else:
            self.y_second_param_hover.setVisible(False)

    def set_second_check_box(self, state: bool):
        logger.info(f"set_second_check_box {state}")
        self.second_check_box.setChecked(state)

    def set_multiple_mode(self, state: bool):
        self.check_miltiple.setChecked(state)

class paramController( QObject):
    parameters_updated = pyqtSignal(str, list, list)
    multiple_checked = pyqtSignal(bool)
    state_second_axis_changed = pyqtSignal(bool)

    numPointsChanged = pyqtSignal(int)
    showingAllPoints = pyqtSignal(bool)

    def __init__(self, paramSelector: paramSelector, alias_manager) -> None:
        super().__init__()
        self.alias_manager = alias_manager
        self.paramSelector = paramSelector
        self.paramSelector.x_param_selector.itemClicked.connect(self.x_param_changed)
        self.paramSelector.y_first_param_selector.itemClicked.connect(self.y_first_param_changed)
        self.paramSelector.y_second_param_selector.itemClicked.connect(self.y_second_param_changed)
        self.paramSelector.check_miltiple.stateChanged.connect(self.update_multiple)
        self.paramSelector.second_check_box.stateChanged.connect(self.second_check_box_changed)

        self.paramSelector.numPointsselector.numPointsChanged.connect(self.numPointsChanged)
        self.paramSelector.numPointsselector.showingAllPoints.connect(self.showingAllPoints)

        self.alias_manager.aliases_updated.connect(self.alias_changed)


        self.curent_x_parameter = None
        self.curent_y_first_parameters = []
        self.curent_y_second_parameters = []

        self.previous_x_parameter = [None]
        self.previous_y_first_parameter = [None]
        self.previous_y_second_parameter = [None]

        self.__x_parameters = set()
        self.__y_first_parameters = set()
        self.__y_second_parameters = set()

    def alias_changed(self, original_name, old_alias, alias):
        #++++++++++++++previous+++++++++++++++++
        for index, name in enumerate(self.previous_x_parameter):
            if name == old_alias:
                self.previous_x_parameter[index] = alias

        for index, name in enumerate(self.previous_y_first_parameter):
            if name == old_alias:
                self.previous_y_first_parameter[index] = alias

        for index, name in enumerate(self.previous_y_second_parameter):
            if name == old_alias:
                self.previous_y_second_parameter[index] = alias

        #++++++++++++++curent+++++++++++++++++
        if self.curent_x_parameter == old_alias:
            self.curent_x_parameter = alias

        for index, name in enumerate(self.curent_y_first_parameters):
            if name == old_alias:
                self.curent_y_first_parameters[index] = alias

        for index, name in enumerate(self.curent_y_second_parameters):
            if name == old_alias:
                self.curent_y_second_parameters[index] = alias

        self.paramSelector.x_param_selector.rename_parameter(old_alias, alias)
        self.paramSelector.y_first_param_selector.rename_parameter(old_alias, alias)
        self.paramSelector.y_second_param_selector.rename_parameter(old_alias, alias)

    def x_param_changed(self):
        logger.debug(f"x_param_changed {self.curent_x_parameter=}")
        self.curent_x_parameter = self.paramSelector.x_param_selector.currentItem().text()
        self.parameters_updated.emit(self.curent_x_parameter, self.curent_y_first_parameters, self.curent_y_second_parameters)

    def y_first_param_changed(self):

        self.manage_y_selectors(selector = self.paramSelector.y_first_param_selector,
                                current_parameters = self.curent_y_first_parameters,
                                opposite_selector = self.paramSelector.y_second_param_selector,
                                previous_parameter = self.previous_y_first_parameter)
        
        logger.info(f"y_first_param_changed update current parameters {self.curent_y_first_parameters=}")
        self.parameters_updated.emit(self.curent_x_parameter, self.curent_y_first_parameters, self.curent_y_second_parameters)


    def y_second_param_changed(self):

        self.manage_y_selectors(selector = self.paramSelector.y_second_param_selector,
                                current_parameters = self.curent_y_second_parameters,
                                opposite_selector = self.paramSelector.y_first_param_selector,
                                previous_parameter = self.previous_y_second_parameter
                                )
        logger.info(f"y_second_param_changed update current parameters {self.curent_y_second_parameters=}")
        self.parameters_updated.emit(self.curent_x_parameter, self.curent_y_first_parameters, self.curent_y_second_parameters)

    def manage_y_selectors(self, selector, current_parameters, opposite_selector, previous_parameter):
        logger.debug(f"manage_y_selectors {current_parameters=}, {previous_parameter=}") 
        if self.paramSelector.check_miltiple.isChecked():
            buf_text = selector.currentItem().text()
            if buf_text in current_parameters:
                current_parameters.remove(buf_text)
                opposite_selector.add_parameters(buf_text)
            else:
                current_parameters.append(buf_text)
                opposite_selector.remove_parameters(buf_text)
        else:
            opposite_selector.add_parameters(current_parameters)
            current_parameters.clear()
            buf_item = selector.currentItem()
            if buf_item is not None:
                buf_text = buf_item.text()
                if buf_text == previous_parameter[0]:
                    buf_item.setSelected(False)
                    selector.setCurrentItem(None)
                    previous_parameter[0] = None
                    opposite_selector.add_parameters(buf_text)
                else:
                    previous_parameter[0] = buf_text
                    current_parameters.append(buf_text)
                    opposite_selector.remove_parameters(buf_text)

    def second_check_box_changed(self):
        self.curent_y_second_parameters.clear()

        state = self.paramSelector.second_check_box.isChecked()
        if not state:
            self.paramSelector.y_first_param_selector.add_parameters(self.__y_first_parameters)
        self.previous_y_second_parameter[0] = None
        self.paramSelector.y_second_param_selector.clearSelection()
        self.state_second_axis_changed.emit( state )
            
    def add_parameters(self, new_parameters: list):
        new_parameters = [self.alias_manager.get_alias(name) for name in new_parameters]
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
        is_multiple = True
        if not self.paramSelector.check_miltiple.isChecked():
            self.clear_y_axis()
            is_multiple = False
            self.paramSelector.y_second_param_selector.add_parameters(self.__y_first_parameters)
            self.paramSelector.y_first_param_selector.add_parameters(self.__y_second_parameters)
            self.previous_x_parameter = [None]
            self.previous_y_first_parameter = [None]
            self.previous_y_second_parameter = [None]

        self.multiple_checked.emit( is_multiple )

    def clear_selections(self, x_param: str, y_first_params: list, y_second_params: list):
        logger.debug(f"clear_selections {x_param=} {y_first_params=} {y_second_params=}")
        self.paramSelector.x_param_selector.clear_selection(x_param)
        for param in y_first_params:
            self.paramSelector.y_first_param_selector.clear_selection(param)
        for param in y_second_params:
            self.paramSelector.y_second_param_selector.clear_selection(param)

    def set_selections(self, x_param: str, y_first_params: list, y_second_params: list):
        self.paramSelector.x_param_selector.set_selection(x_param)
        for param in y_first_params:
            self.paramSelector.y_first_param_selector.set_selection(param)
        for param in y_second_params:
            self.paramSelector.y_second_param_selector.set_selection(param)

    def set_default(self):
        self.curent_x_parameter = None
        self.curent_y_first_parameters = []
        self.curent_y_second_parameters = []
        
        self.paramSelector.x_param_selector.clear()
        self.paramSelector.y_first_param_selector.clear()
        self.paramSelector.y_second_param_selector.clear()

        self.parameters_updated.emit(self.curent_x_parameter, self.curent_y_first_parameters, self.curent_y_second_parameters)

    def get_parameters(self):
        returned_x = self.alias_manager.get_original_name(self.curent_x_parameter)
        returned_y1 = [self.alias_manager.get_original_name(param) for param in self.curent_y_first_parameters]
        returned_y2 = [self.alias_manager.get_original_name(param) for param in self.curent_y_second_parameters]
        return returned_x, returned_y1, returned_y2
    
    def stop_session(self):
        self.paramSelector.numPointsselector.hide()

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