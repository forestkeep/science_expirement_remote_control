import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QPushButton, QWidget, QFileDialog
from PyQt5.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drag and Drop Example")

        self.text_edit = QTextEdit(self)
        self.setAcceptDrops(True)

        self.button = QPushButton("Выбрать файл")
        self.button.clicked.connect(self.open_file)

        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def open_file(self):
        # Логика открытия файла
        filename, _ = QFileDialog.getOpenFileName(self, "Выбрать файл")
        if filename:
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()
                self.text_edit.setPlainText(content)
    
    def dragEnterEvent(self, event):
        print("dragEnterEvent")
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        print(event)
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.text_edit.setPlainText(content)
                break
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(600, 400)
    window.show()
    sys.exit(app.exec_())