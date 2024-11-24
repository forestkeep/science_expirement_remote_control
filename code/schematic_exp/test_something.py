import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QScrollArea, QSpacerItem, QSizePolicy

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Главное окно
        self.setWindowTitle("Пример с QScrollArea")
        self.setGeometry(100, 100, 800, 400)

        # Создаем главный горизонтальный слой
        main_layout = QHBoxLayout()

        # Слой 1
        layer1 = QVBoxLayout()
        for i in range(5):
            button = QPushButton(f"Кнопка {i+1} из слоя 1")
            layer1.addWidget(button)

        # Слой 2 с QScrollArea
        layer2_widget = QWidget()
        layer2_layout = QVBoxLayout(layer2_widget)
        for i in range(5):
            button = QPushButton(f"Кнопка {i+1} из слоя 2")
            layer2_layout.addWidget(button)

        scroll_area = QScrollArea()
        scroll_area.setWidget(layer2_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedWidth(200)  # Фиксированная ширина скролл-арии

        # Добавляем слои в главный слой
        main_layout.addLayout(layer1)
        main_layout.addWidget(scroll_area)

        # Создаем центральный виджет и устанавливаем в нем главный слой
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())