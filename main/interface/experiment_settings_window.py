import sys
from PyQt5.QtWidgets import QApplication, QWidget, QCheckBox, QComboBox, QVBoxLayout, QHBoxLayout, QDialog, QPushButton, QDialogButtonBox
from PyQt5 import QtCore

class settigsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Диалоговое окно с чекбоксами и комбобоксами')
        self.setGeometry(100, 100, 400, 300)

        main_layout = QVBoxLayout()
        set_layout = QHBoxLayout()

        # Создание чекбоксов
        checkboxes_layout_1 = QVBoxLayout()
        checkboxes_layout_2 = QVBoxLayout()
        self.check_boxes_1 = []
        for i in range(2):
            checkbox = QCheckBox(f'Чекбокс {i+1}')
            self.check_boxes_1.append(checkbox)
            checkboxes_layout_1.addWidget(checkbox)
        set_layout.addLayout(checkboxes_layout_1)
        self.check_boxes_1[0].setText("Продолжать эксперимент при ошибке прибора")
        self.check_boxes_1[0].setToolTip("При активации эксперимент будет продолжаться независимо от ответа прибора, \n\r если ответа от прибора не будет, в файл результатов будет записано слово fail")
        self.check_boxes_1[0].setChecked(True)
        self.check_boxes_1[0].setStyleSheet("QToolTip { background-color: lightblue; color: black; border: 1px solid black; }")

        self.check_boxes_1[1].setText("Удалить буферный файл после эксперимента")
        self.check_boxes_1[1].setToolTip("При каждом измерении значения записываются в буферный файл, \n\r после эксперимента файл вычитывается и переводится в удобочитаемый формат, \n\r в случае активации этого пункта буферный файл будет удаляться после удачного сохранения результатов.")
        self.check_boxes_1[1].setChecked(True)
        self.check_boxes_1[1].setStyleSheet("QToolTip { background-color: lightblue; color: black; border: 1px solid black; }")

        for i in range(2):
            checkbox = QCheckBox(f'Вакантно')
            checkboxes_layout_2.addWidget(checkbox)
        set_layout.addLayout(checkboxes_layout_2)

        # Создание комбобоксов
        for i in range(1):
            combobox = QComboBox()
            combobox.addItems(['здесь пока ничего нет'])
            checkboxes_layout_1.addWidget(combobox)

        for i in range(1):
            combobox = QComboBox()
            combobox.addItems(['И здесь тоже ничего нет', 'совсем ничего', 'ни капли'])
            checkboxes_layout_2.addWidget(combobox)

        # Создание кнопок
        buttons_layout = QHBoxLayout()
        save_button = QPushButton('Сохранить')
        cancel_button = QPushButton('Отмена')

        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setGeometry(QtCore.QRect(80, 340, 191, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(
            self.accept)  # type: ignore
        self.buttonBox.rejected.connect(
            self.reject)  # type: ignore
        
        main_layout.addLayout(set_layout)
        main_layout.addWidget(self.buttonBox)


        self.setLayout(main_layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = settigsDialog()
    dialog.show()
    sys.exit(app.exec_())