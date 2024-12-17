import sys
import numexpr as ne
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit

class MathEvaluator(QWidget):
    def __init__(self):
        super().__init__()
        
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Math Expression Evaluator')
        
        layout = QVBoxLayout()
        
        self.input_label = QLabel('Введите математическое выражение:')
        layout.addWidget(self.input_label)
        
        self.input_field = QLineEdit(self)
        layout.addWidget(self.input_field)
        
        self.run_button = QPushButton('Выполнить', self)
        self.run_button.clicked.connect(self.evaluate_expression)
        layout.addWidget(self.run_button)
        
        self.result_label = QLabel('Результат:')
        layout.addWidget(self.result_label)
        
        self.result_output = QTextEdit(self)
        self.result_output.setReadOnly(True)
        layout.addWidget(self.result_output)

        self.setLayout(layout)
        
    def evaluate_expression(self):
        expression = self.input_field.text()
        try:
            result = ne.evaluate(expression)
            self.result_output.setPlainText(str(result))
        except Exception as e:
            self.result_output.setPlainText(f'Ошибка: {str(e)}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    evaluator = MathEvaluator()
    evaluator.resize(400, 300)
    evaluator.show()
    sys.exit(app.exec_())