import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel

class AboutAutorsDialog(QDialog):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Информация об авторах")
        
        layout = QVBoxLayout()
        
        text = """
        Авторы:

        - Захидов Дмитрий

        Если у вас есть вопросы, замечания, или предложения по улучшению приложения, 
        пожалуйста, свяжитесь с нами по электронной почте zakhidov.dim@yandex.ru

        Благодарим вас за использование нашего приложения!
        """
        
        info_label = QLabel(text)
        layout.addWidget(info_label)
        
        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = AboutAutorsDialog()
    dialog.exec_()
    sys.exit(app.exec_())
