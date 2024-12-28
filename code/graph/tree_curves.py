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

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
                             QMessageBox, QMenu, QAction, QDialog, QLineEdit, QTextEdit, QColorDialog, QHeaderView)
from PyQt5.QtGui import QColor, QIcon, QFont, QBrush
from PyQt5.QtCore import Qt, pyqtSignal
try:
    from calc_values_for_graph import ArrayProcessor
except:
    from graph.calc_values_for_graph import ArrayProcessor
import numexpr as ne
import numpy as np

class CurveTreeItem(QTreeWidgetItem):
    def __init__(self, curve_data_obj=None, parent=None, name=None):
        super().__init__(parent)

        self.setText(0, f"Кривая {name}")
        self.font = QFont()
        self.font.setItalic(True)
        self.font.setBold(True)
        self.font.setPointSize(10)
        self.setFont(0, self.font)

        self.setForeground(1, QBrush(QColor("#ff30ea")))

        self.col_font = QFont()
        self.col_font.setBold(True)
        self.col_font.setPointSize(20)
        self.setFont(1, self.col_font)

        self.setText(1, "--●--")
        self.setForeground(1, QBrush(QColor("#ff30ea")))

        self.curve_data_obj = curve_data_obj

        self.parameters = {
            "min_x": None,
            "max_x": None,
            "min_y": None,
            "max_y": None,
            "name": name,
            "tip": None,
            "mean": None,
            "std": None,
            "id": None,
            "mode": None,
            "median": None,
            "count": None
        }

        self.add_basic_characteristics()

    def add_basic_characteristics(self):


        self.addChild(QTreeWidgetItem([f"ID: {self.parameters['id']}"]))
        
        text = QApplication.translate("GraphWindow", "Тип: {tip}")
        text = text.format(tip=self.parameters["tip"])
        self.addChild(QTreeWidgetItem([text]))

        text = QApplication.translate("GraphWindow", "Область определения: ({min_x}, {max_x})")
        text = text.format(min_x=self.parameters["min_x"], max_x=self.parameters["max_x"])
        self.addChild(QTreeWidgetItem([text]))

        text = QApplication.translate("GraphWindow", "Область значений: ({min_y}, {max_y})")
        text = text.format(min_y=self.parameters["min_y"], max_y=self.parameters["max_y"])
        self.addChild(QTreeWidgetItem([text]))

        self.add_statistics(self.parameters["mean"], self.parameters["std"], 
                            self.parameters["mode"], self.parameters["median"], 
                            self.parameters["count"])

    def add_statistics(self, mean, std_dev, mode, median, count):
        stats_item = self.findChild( QApplication.translate("GraphWindow","Статистические данные") )
        if stats_item is None:
            stats_item = QTreeWidgetItem(self, [ QApplication.translate("GraphWindow","Статистические данные" )])
            stats_item.setFont(0, self.font)
            stats_item.setExpanded(True)

            text = QApplication.translate("GraphWindow", "Среднее: {mean}")
            text = text.format(mean=self.parameters["mean"])
            stats_item.addChild(QTreeWidgetItem([text]))

            text = QApplication.translate("GraphWindow", "Стандартное отклонение: {std}")
            text = text.format(std=self.parameters["std"])
            stats_item.addChild(QTreeWidgetItem([text]))

            text = QApplication.translate("GraphWindow", "Мода: {mode}")
            text = text.format(mode=self.parameters["mode"])
            stats_item.addChild(QTreeWidgetItem([text]))

            text = QApplication.translate("GraphWindow", "Медиана: {median}")
            text = text.format(median=self.parameters["median"])
            stats_item.addChild(QTreeWidgetItem([text]))

            text = QApplication.translate("GraphWindow", "Число точек: {count}")
            text = text.format(count=self.parameters["count"])
            stats_item.addChild(QTreeWidgetItem([text]))

    def add_new_block(self, block_name, data):
        block_item = self.findChild(block_name)
        if block_item is None:
            block_item = QTreeWidgetItem(self, [block_name])
            block_item.setFont(0, self.font)
            block_item.setExpanded(True)

        for key, value in data.items():
            block_item.addChild(QTreeWidgetItem([f"{key}: {value}"]))

    def update_block_data(self, block_name, data) -> bool:
        block_item = self.findChild(block_name)
        if block_item:
            for i, (key, value) in enumerate(data.items()):
                if i < block_item.childCount():
                    block_item.child(i).setText(0, f"{key}: {value}")
                else:
                    # Если дочерних элементов недостаточно, добавляем новые
                    block_item.addChild(QTreeWidgetItem([f"{key}: {value}"]))
            return True
        return False

    def update_parameters(self, dict_parameters):
        for parameter_name, new_value in dict_parameters.items():
            if self.parameters.get(parameter_name, False) is not False:
                if isinstance(new_value, (int, float)):
                    val = np.format_float_scientific(new_value, precision=5, unique=True)
                else:
                    val = new_value
                self.parameters[parameter_name] = val
            else:
                print(f"ключ {parameter_name} не найден в параметрах отображения кривой")
        self.update_display()

    def this_choise(self):
        self.curve_data_obj.higlight_curve()

    def deselection(self):
        self.curve_data_obj.unhiglight_curve()

    def change_color(self, color):
        self.setForeground(1, QBrush(QColor(color)))
        self.curve_data_obj.change_color(color)

    def is_draw(self):
        return self.curve_data_obj.is_draw

    def update_display(self):
        self.setText(0, f"{self.parameters['name']}")
        text = QApplication.translate("GraphWindow", "ID: {id}")
        text = text.format(id=self.parameters["id"])
        self.child(0).setText(0, text)

        text = QApplication.translate("GraphWindow", "Тип: {tip}")
        text = text.format(tip=self.parameters["tip"])
        self.child(1).setText(0, text)

        text = QApplication.translate("GraphWindow", "Область определения: ({min_x}, {max_x})")
        text = text.format(min_x=self.parameters["min_x"], max_x=self.parameters["max_x"])
        self.child(2).setText(0, text)

        text = QApplication.translate("GraphWindow", "Область значений: ({min_y}, {max_y})")
        text = text.format(min_y=self.parameters["min_y"], max_y=self.parameters["max_y"])
        self.child(3).setText(0, text)

        stats_item = self.findChild( QApplication.translate("GraphWindow","Статистические данные") )
        if stats_item:
            text = QApplication.translate("GraphWindow", "Среднее: {mean}")
            text = text.format(mean=self.parameters["mean"])
            stats_item.child(0).setText(0, text)

            text = QApplication.translate("GraphWindow", "Стандартное отклонение: {std}")
            text = text.format(std=self.parameters["std"])
            stats_item.child(1).setText(0, text)

            text = QApplication.translate("GraphWindow", "Мода: {mode}")
            text = text.format(mode=self.parameters["mode"])
            stats_item.child(2).setText(0, text)

            text = QApplication.translate("GraphWindow", "Медиана: {median}")
            text = text.format(median=self.parameters["median"])
            stats_item.child(3).setText(0, text)

            text = QApplication.translate("GraphWindow", "Число точек: {count}")
            text = text.format(count=self.parameters["count"])
            stats_item.child(4).setText(0, text)

    def findChild(self, title):
        for i in range(self.childCount()):
            if self.child(i).text(0) == title:
                return self.child(i)
        return None

class CurveDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle( QApplication.translate("GraphWindow","Создать новую кривую"))
        self.setFixedSize(300, 200)
        layout = QVBoxLayout(self)

        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText( QApplication.translate("GraphWindow","Имя"))
        layout.addWidget(self.name_input)

        self.formula_input = QLineEdit(self)
        self.formula_input.setPlaceholderText( QApplication.translate("GraphWindow","Формула"))
        layout.addWidget(self.formula_input)

        self.description_input = QTextEdit(self)
        self.description_input.setPlaceholderText( QApplication.translate("GraphWindow","Описание"))
        layout.addWidget(self.description_input)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("ОК", self)
        self.cancel_button = QPushButton( QApplication.translate("GraphWindow","Отмена"), self)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def get_curve_data(self):
        return self.name_input.text(), self.formula_input.text(), self.description_input.toPlainText()

def choose_color():
    color = QColorDialog.getColor()
    if color.isValid():
        return color.name()
    return None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Приложение с графиком и древовидной структурой")
        self.setGeometry(100, 100, 800, 600)
        main_widget = treeWin()
        self.setCentralWidget(main_widget)

class customTreeWidget(QTreeWidget):
    def __init__(self, par_class):
        super().__init__()
        self.par_class = par_class
        self.setMouseTracking(True)
        #self.setStyleSheet("QTreeWidget::item:selected { background-color: transparent; }")#отключение подсветки фона
    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        if not item:
            item = None
        self.par_class.on_item_entered(item)
        super().mouseMoveEvent(event)
    def leaveEvent(self, event):
        self.par_class.on_item_entered(item = None)
        super().leaveEvent(event)

class treeWin(QWidget):
    curve_deleted = pyqtSignal( object )
    curve_shown = pyqtSignal( object )
    curve_hide = pyqtSignal( object )
    curve_reset = pyqtSignal( object )
    curve_created = pyqtSignal( object )
    def __init__(self, main_class = None):
        super().__init__()
        self.setMinimumSize(0,0)
        self.curves = []
        left_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        self.main_class = main_class

        self.buttons = []
        button = QPushButton("+")
        button.setMaximumSize(30, 30)
        button.setMinimumSize(0, 0)
        button_layout.addWidget(button)
        self.buttons.append(button)

        self.buttons[0].clicked.connect(self.open_curve_dialog)

        left_layout.addLayout(button_layout)

        self.visibility_button = QPushButton("eye")
        self.visibility_button.setIcon(QIcon("eye.png"))
        self.visibility_button.setCheckable(True)
        self.visibility_button.clicked.connect(self.toggle_visibility)
        self.visibility_button.setToolTip( QApplication.translate("GraphWindow","Показать активные кривые"))
        self.visibility_button.setMinimumSize(0, 30)
        self.visibility_button.setMaximumSize(30, 30)
        button_layout.addWidget(self.visibility_button)

        self.tree_widget = customTreeWidget(self)
        self.tree_widget.setColumnCount(3)
        self.tree_widget.setSortingEnabled(False)
        self.tree_widget.setHeaderLabels([QApplication.translate("GraphWindow","Кривые"),
                                          QApplication.translate("GraphWindow","Цвет"),
                                          QApplication.translate("GraphWindow", "Статус")])

        left_layout.addWidget(self.tree_widget)

        header = self.tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(left_layout)

        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)

    def on_item_entered(self, item):
        root_item = None
        if item:
            parent = item
            while True:
                root_item = parent
                parent = parent.parent()
                if parent  is None:
                    break

            root_item.this_choise()

        for cur in self.curves:
            if cur != item and cur != root_item:
                cur.deselection()

    def update_visible(self):
        if self.visibility_button.isChecked():
            if self.curves:
                for curve in self.curves:
                    if not curve.is_draw():
                        curve.setHidden(True)
                    else:
                        curve.setHidden(False)

    def toggle_visibility(self):
        if self.visibility_button.isChecked():
            self.visibility_button.setIcon(QIcon("eye_crossed.png"))
            self.visibility_button.setToolTip( QApplication.translate("GraphWindow","Показать активные кривые"))
            if self.curves:
                for curve in self.curves:
                    if not curve.is_draw():
                        curve.setHidden(True)
        else:
            self.visibility_button.setIcon(QIcon("eye.png"))
            self.visibility_button.setToolTip( QApplication.translate("GraphWindow","Показать все кривые"))
            if self.curves:
                for curve in self.curves:
                    curve.setHidden(False)

    def open_curve_dialog(self):
        dialog = CurveDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, formula, description = dialog.get_curve_data()

            context = {}
            choised_curves = {}
            is_consist_curve = False
            for curve in self.curves:
                if curve.parameters["id"] in formula:
                    is_consist_curve = True
                    context[curve.parameters["id"]] = curve
                    choised_curves[curve.parameters["id"]] = curve
            if not is_consist_curve:
                return
            
            names_x_parameters = set()
            x_name = ""
            for id, curve in choised_curves.items():
                if curve.curve_data_obj.x_name not in names_x_parameters and names_x_parameters:
                    print(f"Выбранные кривые построены в различных пространствах. {names_x_parameters}")
                    #TODO: вывести предупреждение пользователю и сообщить о конкретных кривых из разных пространств
                    return
                names_x_parameters.add(curve.curve_data_obj.x_name)
                x_name = curve.curve_data_obj.x_name

            context, all_x, status = self.preparation_arrays(context)
            if not status:
                print("ошибка в расчете, таймаут, авозможно, что-то с исходными данными")
                
            result = self.evaluate_expression(formula, context)

            curve_data = self.main_class.graph_main.create_curve(y_data = result, 
                                                    x_data = all_x[0],
                                                    name_device ="gene",
                                                    name_ch ="rate",
                                                    y_name =name,
                                                    x_name =x_name,
                                                    y_param_name =name,
                                                    x_param_name=x_name)

            self.curve_shown.emit(curve_data)
            self.curve_created.emit(curve_data)
            self.add_curve(curve_data.tree_item)
            curve_data.set_full_legend_name()
            curve_data.tree_item.update_block_data( QApplication.translate("GraphWindow","Разное"),
                                                    {QApplication.translate("GraphWindow","Формула"): formula,
                                                     QApplication.translate("GraphWindow","Описание"): description})

    def preparation_arrays(self, tree_curves: dict):
        keys = list(tree_curves.keys())
        all_x = []
        all_y = []
        for key in keys:
            curve_data = tree_curves[key].curve_data_obj
            x = curve_data.filtered_x_data
            y = curve_data.filtered_y_data
            
            all_x.append(x)
            all_y.append(y)

        all_x, all_y, status = ArrayProcessor.combine_all_arrays(all_x, all_y)
        
        for i, key in enumerate(keys):
            tree_curves[key] = all_y[i]

        return tree_curves, all_x, status

    def evaluate_expression(self, expression, context=None):
        result = None
        try:
            result = ne.evaluate(expression, context)
        except Exception as e:
            print(f'Ошибка: {str(e)}')

        return result

    def add_curve(self, curve_item: CurveTreeItem):
        self.tree_widget.addTopLevelItem(curve_item)
        curve_item.update_parameters({"id": "CUR" + str(len(self.curves) + 1)})
        self.curves.append(curve_item)

    def show_context_menu(self, position):
        item = self.tree_widget.itemAt(position)
        parent = item
        while True:
            root_item = parent
            parent = parent.parent()
            if parent  is None:
                break

        if root_item:
            context_menu = QMenu(self) 

            if root_item.curve_data_obj.is_draw:
                text_show = "Скрыть"
                show_action = QAction(text_show, self)
                context_menu.addAction(show_action)
                show_action.triggered.connect(lambda: self.hide_curve(root_item))
            else:
                text_show = "Отобразить"
                show_action = QAction(text_show, self)
                context_menu.addAction(show_action)
                show_action.triggered.connect(lambda: self.show_curve(root_item))

            color_action = QAction( QApplication.translate("GraphWindow","Изменить цвет"), self)
            delete_action = QAction( QApplication.translate("GraphWindow","Удалить график"), self)
            reset_data_action = QAction( QApplication.translate("GraphWindow","Сбросить фильтры"), self)
            context_menu.addAction(color_action)
            context_menu.addAction(delete_action)
            context_menu.addAction(reset_data_action)

            color_action.triggered.connect(lambda: self.change_color_curve(root_item))
            delete_action.triggered.connect(lambda: self.delete_curve(root_item))
            reset_data_action.triggered.connect(lambda: self.reset_filters(root_item))

            context_menu.exec_(self.tree_widget.viewport().mapToGlobal(position))
    def reset_filters(self, item=None):
        if item in self.curves:
            self.curve_reset.emit(item.curve_data_obj)

    def delete_curve(self, item=None):
        if item is None:
            selected_items = self.tree_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
            else:
                QMessageBox.warning(self, QApplication.translate("GraphWindow","Ошибка"),
                                          QApplication.translate("GraphWindow","Пожалуйста, выберите элемент для удаления."))
                return
            
        if item in self.curves:
            self.curve_deleted.emit(item.curve_data_obj)
            self.curves.remove(item)

        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            index = self.tree_widget.indexOfTopLevelItem(item)
            if index != -1:
                self.tree_widget.takeTopLevelItem(index)

    def show_curve(self, item=None):
        if item is None:
            selected_items = self.tree_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
            else:
                QMessageBox.warning(self, QApplication.translate("GraphWindow","Ошибка"),
                                          QApplication.translate("GraphWindow", "Пожалуйста, выберите элемент для отображения."))
                return
            
        if item in self.curves:
            self.curve_shown.emit(item.curve_data_obj)

    def hide_curve(self, item=None):
        if item is None:
            selected_items = self.tree_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
            else:
                QMessageBox.warning(self, QApplication.translate("GraphWindow","Ошибка"),
                                          QApplication.translate("GraphWindow", "Пожалуйста, выберите элемент для отображения."))
                return
        if item in self.curves:
            self.curve_hide.emit(item.curve_data_obj)

    def change_color_curve(self, item):
        color = choose_color()
        if color:
            item.change_color(color)
        else:
            pass

    def clear_all(self):
        for curve in self.curves:
            self.delete_curve(curve)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())

    
