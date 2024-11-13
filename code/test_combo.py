import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QComboBox, QLabel, QVBoxLayout, QWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ComboBox ToolTips Example")
        self.setGeometry(100, 100, 300, 150)

        # Создаем виджет центрального окна
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Создаем компоновщик
        layout = QVBoxLayout(central_widget)

        # Создаем комбобокс
        self.combo = QComboBox(self)
        self.combo.addItems(["1", "2", "3"])
        
        # Устанавливаем подсказки
        self.tooltips = {
            "1": "Это первая опция",
            "2": "Это вторая опция",
            "3": "Это третья опция"
        }

        # Подключаем сигнал для отображения подсказок
        self.combo.highlighted.connect(self.display_tooltip)

        # Создаем метку для отображения инструментальных подсказок
        self.tooltip_label = QLabel("", self)
        
        # Добавляем элементы в компоновщик
        layout.addWidget(self.combo)
        layout.addWidget(self.tooltip_label)

    def display_tooltip(self, index):
        # Обновляем текст подсказки в метке в зависимости от выделенного элемента
        value = self.combo.itemText(index)
        self.tooltip_label.setText(self.tooltips.get(value, ""))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())