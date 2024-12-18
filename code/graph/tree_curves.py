import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
                             QMessageBox, QMenu, QAction)
from PyQt5.QtGui import QColor, QIcon, QFont
from PyQt5.QtCore import Qt
from datetime import datetime


class CurveTreeItem(QTreeWidgetItem):
    def __init__(self, curve_data_obj = None,  parent = None, name = None):
        super().__init__(parent)
        self.setText(0, f"Кривая {name}")
        self.font = QFont()
        self.font.setItalic(True)
        self.font.setBold(True)
        self.font.setPointSize(12)
        self.setFont(0, self.font)

        self.curve_data_obj = curve_data_obj

        self.parameters = {
            "min_x": False,
            "max_x": False,
            "min_y": False,
            "max_y": False,
            "name": False,
            "tip": False,
            "mean": False,
            "std": False,
            "ID": False
            }

        # Добавить основные характеристики
        self.add_basic_characteristics()

    def add_basic_characteristics(self):
        self.addChild(QTreeWidgetItem([f"ID: {self.parameters['ID']}", "c"]))
        self.addChild(QTreeWidgetItem([f"Тип: {self.parameters['tip']}", "Коэффициенты: [1, 2, 3]"]))
        self.addChild(QTreeWidgetItem([f"Область определения: ({self.parameters['min_x']}, {self.parameters['max_x']})"]))
        self.addChild(QTreeWidgetItem([f"Область значений: ({self.parameters['min_y']}, {self.parameters['max_y']})"]))
        self.add_statistics(2.5, 1.0)

        '''
        self.add_filter("Сглаживание", "Порядок 3")
        self.add_filter("Нормализация", "")
        self.add_statistics(2.5, 1.0)
        self.add_change_history("Применен фильтр сглаживания")
        self.add_change_history("Изменение параметров")
        self.add_notes("Кривая была получена из эксперимента X.")
        '''

    def update_parameters(self, dict_parameters) :
        for parameter_name, new_value in dict_parameters.items():
            if self.parameters.get(parameter_name) is not None:
                self.parameters[parameter_name] = new_value

        self.update_display()

    def update_display(self):
        self.setText(0, f"{self.parameters['name']}")
        self.child(0).setText(0, f"ID: {self.parameters['ID']}")
        self.child(1).setText(0, f"Тип: {self.parameters['tip']}")
        self.child(2).setText(0, f"Область определения: ({self.parameters['min_x']}, {self.parameters['max_x']})")
        self.child(3).setText(0, f"Область значений: ({self.parameters['min_y']}, {self.parameters['max_y']})")

        stats_item = self.findChild("Статистические данные")
        if stats_item:
            stats_item.child(0).setText(0, f"Среднее: {self.parameters['mean']}")
            stats_item.child(1).setText(0, f"Стандартное отклонение: {self.parameters['std']}")

    def add_filter(self, filter_name, parameters):
        filters_item = self.findChild("Фильтры")
        if filters_item is None:
            filters_item = QTreeWidgetItem(self, ["Фильтры"])
            filters_item.setFont(0, self.font)
            filters_item.setExpanded(True)

        filter_item = QTreeWidgetItem(filters_item, [f"Фильтр: {filter_name}"])
        filter_item.addChild(QTreeWidgetItem([f"Параметры: {parameters}"]))

    def add_statistics(self, mean, std_dev):
        stats_item = self.findChild("Статистические данные")
        if stats_item is None:
            stats_item = QTreeWidgetItem(self, ["Статистические данные"])
            stats_item.setFont(0, self.font)
            stats_item.setExpanded(True)

        stats_item.addChild(QTreeWidgetItem([f"Среднее: {mean}"]))
        stats_item.addChild(QTreeWidgetItem([f"Стандартное отклонение: {std_dev}"]))

    def add_change_history(self, description):
        history_item = self.findChild("История изменений")
        if history_item is None:
            history_item = QTreeWidgetItem(self, ["История изменений"])
            history_item.setFont(0, self.font)
            history_item.setExpanded(True)

        history_item.addChild(QTreeWidgetItem([f"[{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}] {description}"]))

    def add_notes(self, notes):
        notes_item = self.findChild("Примечания")
        if notes_item is None:
            notes_item = QTreeWidgetItem(self, ["Примечания"])
            notes_item.setFont(0, self.font)

        notes_item.addChild(QTreeWidgetItem([notes]))

    def findChild(self, title):
        for i in range(self.childCount()):
            if self.child(i).text(0) == title:
                return self.child(i)
        return None
    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Приложение с графиком и древовидной структурой")
        self.setGeometry(100, 100, 800, 600)

        # Основной виджет
        main_widget = treeWin()
        self.setCentralWidget(main_widget)

class treeWin(QWidget):
    def __init__(self):
        super().__init__()

        self.curves = []
        # Вертикальный слой для кнопок и QTreeWidget
        left_layout = QVBoxLayout()

        # Горизонтальный слой для кнопок
        button_layout = QHBoxLayout()

        # Кнопки управления
        button_colors = [QColor(255, 0, 0), QColor(0, 255, 0)]
        button_names = ["Добавить пример", "Создать"]
        self.buttons = []
        i = 0
        for color in button_colors:
            button = QPushButton(button_names[i])
            #button.setFixedSize(50, 50)
            button.setStyleSheet(f"background-color: {color.name()}; border:none;")
            button_layout.addWidget(button)
            self.buttons.append(button)
            i+=1

        # Подключение кнопок к функциям
        self.buttons[0].clicked.connect(self.add_test_curve)  # Добавить
        self.buttons[1].clicked.connect(self.create_curve)  # Создать

        # Добавляем горизонтальный слой с кнопками в вертикальный слой
        left_layout.addLayout(button_layout)

        self.visibility_button = QPushButton()
        self.visibility_button.setIcon(QIcon("eye.png"))  # Замените на путь к вашему значку глаза
        self.visibility_button.setCheckable(True)
        self.visibility_button.clicked.connect(self.toggle_visibility)
        self.visibility_button.setToolTip("Показать активные кривые")
        button_layout.addWidget(self.visibility_button)

        # Создание QTreeWidget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Кривые"])  # Заголовки столбцов
        left_layout.addWidget(self.tree_widget)

        # Установка общего слоя
        main_layout = QHBoxLayout(self)
        main_layout.addLayout(left_layout)

        # Устанавливаем контекстное меню
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
    def toggle_visibility(self):
        if self.visibility_button.isChecked():
            self.visibility_button.setIcon(QIcon("eye_crossed.png"))  # Замените на путь к вашему значку с зачёркнутым глазом
            self.visibility_button.setToolTip("Показать все кривые")
            if self.curves:
                for curve in self.curves:
                    curve.setHidden(True)
            # Действие при скрытии (например, скрыть кривые)
        else:
            self.visibility_button.setIcon(QIcon("eye.png"))  # Замените на путь к вашему значку глаза
            self.visibility_button.setToolTip("Показать активные кривые")
            # Действие при отображении (например, показать кривые)
            if self.curves:
                for curve in self.curves:
                    curve.setHidden(False)

    def create_curve(self):
        # Создаем новый объект CurveItem
        print("Создание кривой")
    def add_curve(self, curve_item:CurveTreeItem ):

        self.tree_widget.addTopLevelItem(curve_item)
        curve_item.update_parameters({"ID": "CUR" + str(len(self.curves) + 1)})
        self.curves.append(curve_item)

    def add_test_curve(self):
        # Создаем новый объект CurveItem
        curve_item = CurveTreeItem()
        self.add_curve(curve_item)

    def show_context_menu(self, position):
        # Получаем элемент по позиции курсора
        item = self.tree_widget.itemAt(position)

        # Создаем контекстное меню
        context_menu = QMenu(self)

        # Добавляем действия в меню
        if item:  # Если на элемент было нажато
            view_action = QAction("Просмотр", self)
            edit_action = QAction("Редактировать", self)
            delete_action = QAction("Удалить график", self)
            context_menu.addAction(view_action)
            context_menu.addAction(edit_action)
            context_menu.addAction(delete_action)

            # Соединяем действия с соответствующими функциями
            view_action.triggered.connect(lambda: self.view_curve(item))
            edit_action.triggered.connect(lambda: self.edit_curve(item))
            delete_action.triggered.connect(lambda: self.delete_curve(item))

        # Показываем контекстное меню
        context_menu.exec_(self.tree_widget.viewport().mapToGlobal(position))

    def delete_curve(self, item=None):
        # Удаление выбранного элемента
        if item is None:  # Если item не передан, берем текущий
            selected_items = self.tree_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
            else:
                QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите элемент для удаления.")
                return
            
        if item is self.curves:
            self.curves.remove(item)

        parent = item.parent()
        if parent:  # Если у элемента есть родитель
            parent.removeChild(item)
        else:  # Если элемент корневой
            index = self.tree_widget.indexOfTopLevelItem(item)
            if index != -1:
                self.tree_widget.takeTopLevelItem(index)

    def view_curve(self, item):
        QMessageBox.information(self, "Просмотр", f"Просмотр данных для {item.text(0)}")

    def edit_curve(self, item):
        QMessageBox.information(self, "Редактировать", f"Редактирование данных для {item.text(0)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())
    
