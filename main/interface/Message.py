import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton

class messageDialog(QDialog):
    def __init__(self, title = "Сообщение", text = "Отлично выглядите!"):
        super().__init__()
        self.setMinimumSize(400, 200)  # устанавливаем минимальный размер окна
        
        self.setWindowTitle(title)
        
        layout = QVBoxLayout()
        
        info_label = QLabel(text)
        info_label.setStyleSheet("font-size: 14px; font-family: Arial;") 
        layout.addWidget(info_label)
        
        ok_button = QPushButton("Ok", self)
        ok_button.clicked.connect(self.accept)  # закрываем окно при нажатии на кнопку Ok
        layout.addWidget(ok_button)
        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = messageDialog()
    dialog.exec_()
    sys.exit(app.exec_())