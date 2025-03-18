# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.

import sys

from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                             QHBoxLayout, QLabel, QPushButton, QVBoxLayout)



class Check_data_import_win(QDialog):
    def __init__(self, strings, callback, is_osc=False):
        super().__init__()
        self.callback = callback
        self.initUI(strings, is_osc)

    def initUI(self, strings, is_osc):
        layout_vert_main = QVBoxLayout()
        layout_hor = QHBoxLayout()
        lay_columns = QVBoxLayout() 
        if is_osc:
            title_text = QApplication.translate("GraphWindow","Выберите столбец с шагом времени и отметьте столбцы для импорта")
        else:
            title_text = QApplication.translate("GraphWindow","Выберите столбцы для импорта")

        title_label = QLabel( title_text)
        layout_vert_main.addWidget(title_label)

        
        self.step_combo = QComboBox()
        self.step_combo.addItems(strings)
        if is_osc:
            lay_combo = QVBoxLayout() 
            step_label = QLabel( QApplication.translate("GraphWindow","Шаг времени"))
            lay_combo.addWidget(step_label)
            lay_combo.addWidget(self.step_combo)

            layout_hor.addLayout(lay_combo)

        self.checkboxes = []

        for string in strings:
            checkbox = QCheckBox(string)
            lay_columns.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        layout_hor.addLayout(lay_columns)
        layout_vert_main.addLayout(layout_hor)

        self.setLayout(layout_vert_main)
        self.setWindowTitle(QApplication.translate("GraphWindow",'Импорт данных'))

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.on_ok)
        layout_vert_main.addWidget(ok_button)
    def on_ok(self):
        self.accept()

    def retranslateUi(self):
        self.setWindowTitle( QApplication.translate("GraphWindow","Мастер импорта") )
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    sample_strings = ["sec", "Ch 2", "CH 3"]  # Пример строк
    window = Check_data_import_win(sample_strings, None, True)
    window.show()
    sys.exit(app.exec_())