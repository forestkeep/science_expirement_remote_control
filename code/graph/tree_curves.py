import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
                             QMessageBox, QMenu, QAction, QDialog, QLineEdit, QColorDialog, QHeaderView)
from PyQt5.QtGui import QColor, QIcon, QFont, QBrush
from PyQt5.QtCore import Qt, QEvent
from datetime import datetime

class CurveTreeItem(QTreeWidgetItem):
    def __init__(self, curve_data_obj=None, parent=None, name=None):
        super().__init__(parent)

        self.setText(0, f"Кривая {name}")
        self.font = QFont()
        self.font.setItalic(True)
        self.font.setBold(True)
        self.font.setPointSize(12)
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
        self.addChild(QTreeWidgetItem([f"Тип: {self.parameters['tip']}"]))
        self.addChild(QTreeWidgetItem([f"Область определения: ({self.parameters['min_x']}, {self.parameters['max_x']})"]))
        self.addChild(QTreeWidgetItem([f"Область значений: ({self.parameters['min_y']}, {self.parameters['max_y']})"]))
        self.add_statistics(self.parameters["mean"], self.parameters["std"], 
                            self.parameters["mode"], self.parameters["median"], 
                            self.parameters["count"])

    def add_statistics(self, mean, std_dev, mode, median, count):
        stats_item = self.findChild("Статистические данные")
        if stats_item is None:
            stats_item = QTreeWidgetItem(self, ["Статистические данные"])
            stats_item.setFont(0, self.font)
            stats_item.setExpanded(True)

        stats_item.addChild(QTreeWidgetItem([f"Среднее: {mean}"]))
        stats_item.addChild(QTreeWidgetItem([f"Стандартное отклонение: {std_dev}"]))
        stats_item.addChild(QTreeWidgetItem([f"Мода: {mode}"]))
        stats_item.addChild(QTreeWidgetItem([f"Медиана: {median}"]))
        stats_item.addChild(QTreeWidgetItem([f"Число точек: {count}"]))

    def update_parameters(self, dict_parameters):
        for parameter_name, new_value in dict_parameters.items():
            if self.parameters.get(parameter_name, False) is not False:
                self.parameters[parameter_name] = new_value
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
        self.child(0).setText(0, f"ID: {self.parameters['id']}")
        self.child(1).setText(0, f"Тип: {self.parameters['tip']}")
        self.child(2).setText(0, f"Область определения: ({self.parameters['min_x']}, {self.parameters['max_x']})")
        self.child(3).setText(0, f"Область значений: ({self.parameters['min_y']}, {self.parameters['max_y']})")

        stats_item = self.findChild("Статистические данные")
        if stats_item:
            print(self.parameters)
            stats_item.child(0).setText(0, f"Среднее: {self.parameters['mean']}")
            stats_item.child(1).setText(0, f"Стандартное отклонение: {self.parameters['std']}")
            stats_item.child(2).setText(0, f"Мода: {self.parameters['mode']}")
            stats_item.child(3).setText(0, f"Медиана: {self.parameters['median']}")
            stats_item.child(4).setText(0, f"Число точек: {self.parameters['count']}")

    def findChild(self, title):
        for i in range(self.childCount()):
            if self.child(i).text(0) == title:
                return self.child(i)
        return None

class CurveDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать новую кривую")
        self.setFixedSize(300, 200)
        layout = QVBoxLayout(self)

        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Имя")
        layout.addWidget(self.name_input)

        self.formula_input = QLineEdit(self)
        self.formula_input.setPlaceholderText("Формула")
        layout.addWidget(self.formula_input)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("ОК", self)
        self.cancel_button = QPushButton("Отмена", self)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def get_curve_data(self):
        return self.name_input.text(), self.formula_input.text()


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
        # Ваш код обработки события ухода курсора
        self.par_class.on_item_entered(item = None)
        super().leaveEvent(event)

class treeWin(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(0,0)
        self.curves = []
        left_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        button_colors = [QColor(255, 0, 0)]
        self.buttons = []
        i = 0
        for color in button_colors:
            button = QPushButton()
            button.setStyleSheet(f"background-color: {color.name()}; border:none;")
            button.setMaximumSize(30, 30)
            button.setMinimumSize(0, 0)
            button_layout.addWidget(button)
            self.buttons.append(button)
            i += 1

        self.buttons[0].clicked.connect(self.open_curve_dialog)

        left_layout.addLayout(button_layout)

        self.visibility_button = QPushButton()
        self.visibility_button.setIcon(QIcon("eye.png"))
        self.visibility_button.setCheckable(True)
        self.visibility_button.clicked.connect(self.toggle_visibility)
        self.visibility_button.setToolTip("Показать активные кривые")
        self.visibility_button.setMinimumSize(0, 30)
        self.visibility_button.setMaximumSize(30, 30)
        button_layout.addWidget(self.visibility_button)

        self.tree_widget = customTreeWidget(self)
        self.tree_widget.setColumnCount(3)
        self.tree_widget.setSortingEnabled(True)
        self.tree_widget.setHeaderLabels(["Кривые", "Цвет", "Статус"])

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

    def toggle_visibility(self):
        if self.visibility_button.isChecked():
            self.visibility_button.setIcon(QIcon("eye_crossed.png"))
            self.visibility_button.setToolTip("Показать активные кривые")
            if self.curves:
                for curve in self.curves:
                    if not curve.is_draw():
                        curve.setHidden(True)
        else:
            self.visibility_button.setIcon(QIcon("eye.png"))
            self.visibility_button.setToolTip("Показать все кривые")
            if self.curves:
                for curve in self.curves:
                    curve.setHidden(False)

    def open_curve_dialog(self):
        dialog = CurveDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, formula = dialog.get_curve_data()
            curve_item = CurveTreeItem(name=name)
            self.add_curve(curve_item)

    def add_curve(self, curve_item: CurveTreeItem):
        self.tree_widget.addTopLevelItem(curve_item)
        curve_item.update_parameters({"ID": "CUR" + str(len(self.curves) + 1)})
        self.curves.append(curve_item)

    def create_curve(self):
        print("Создание кривой")

    def show_context_menu(self, position):
        item = self.tree_widget.itemAt(position)
        parent = item
        while True:
            root_item = parent
            parent = parent.parent()
            if parent  is None:
                break
        
        context_menu = QMenu(self)

        if item:
            color_action = QAction("Изменить цвет", self)
            #edit_action = QAction("Редактировать", self)
            #delete_action = QAction("Удалить график", self)
            context_menu.addAction(color_action)
            #context_menu.addAction(edit_action)
            #context_menu.addAction(delete_action)

            color_action.triggered.connect(lambda: self.change_color_curve(root_item))
            #edit_action.triggered.connect(lambda: self.edit_curve(root_item))
            #delete_action.triggered.connect(lambda: self.delete_curve(root_item))

        context_menu.exec_(self.tree_widget.viewport().mapToGlobal(position))

    def delete_curve(self, item=None):
        if item is None:
            selected_items = self.tree_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
            else:
                QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите элемент для удаления.")
                return
        
        if item in self.curves:
            self.curves.remove(item)

        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            index = self.tree_widget.indexOfTopLevelItem(item)
            if index != -1:
                self.tree_widget.takeTopLevelItem(index)

    def change_color_curve(self, item):
        color = choose_color()
        if color:
            item.change_color(color)
        else:
            pass




if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())

    
