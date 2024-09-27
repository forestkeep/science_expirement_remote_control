import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton
from dev_creator import deviceCreator

class MainWindow(QMainWindow):
    def __init__(self, device_creator):
        super().__init__()
        self.device_creator = device_creator
        
        self.setWindowTitle("Главное окно")
        self.setGeometry(100, 100, 300, 200)

        # Создание кнопки
        self.run_device_creator_button = QPushButton("Запустить Конструктор", self)
        self.run_device_creator_button.setGeometry(50, 50, 200, 50)
        self.run_device_creator_button.clicked.connect(self.run_device_creator)

    def run_device_creator(self):
        self.device_creator.show()  # Показать окно deviceCreator

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Создаем экземпляр deviceCreator
    device_creator = deviceCreator()

    # Создаем главное окно и передаем экземпляр deviceCreator
    main_window = MainWindow(device_creator)
    main_window.show()

    sys.exit(app.exec_())
