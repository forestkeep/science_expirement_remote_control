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
                             QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                             QScrollArea, QWidget, QSizePolicy, QComboBox)

class Check_data_import_win(QDialog):
    def __init__(self, strings, callback=None, is_osc=False):
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

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.scroll_content_widget = QWidget()
        self.scroll_content_layout = QVBoxLayout(self.scroll_content_widget)

        self.scroll_area.setWidget(self.scroll_content_widget)

        layout_vert_main.addWidget(self.scroll_area)

        self.step_combo = QComboBox()
        self.step_combo.addItems( strings )
        if is_osc:
            lay_combo = QVBoxLayout() 
            step_label = QLabel( QApplication.translate("GraphWindow","Шаг времени"))
            lay_combo.addWidget(step_label)
            lay_combo.addWidget(self.step_combo)

            layout_hor.addLayout(lay_combo)

        if not is_osc:
            self.all_checkbox = QCheckBox(QApplication.translate("GraphWindow","Выбрать все"))
            lay_columns.addWidget(self.all_checkbox)
            self.all_checkbox.clicked.connect(self.on_all_checkbox_checked)

        self.checkboxes = []

        for string in strings:
            checkbox = QCheckBox(string)
            lay_columns.addWidget(checkbox)
            self.checkboxes.append(checkbox)

        layout_hor.addLayout(lay_columns)

        self.setLayout(layout_vert_main)
        self.setWindowTitle(QApplication.translate("GraphWindow",'Импорт данных'))

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.on_ok)

        self.scroll_content_layout.addLayout(layout_hor)
        layout_vert_main.addWidget(ok_button)

    def on_ok(self):
        self.accept()

    def on_all_checkbox_checked(self, checked):
        for checkbox in self.checkboxes:
            checkbox.setChecked(checked)

    def retranslateUi(self):
        self.setWindowTitle( QApplication.translate("GraphWindow","Мастер импорта") )
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    sample_strings = ["sec", "Ch 2", "CH 3"]  # Пример строк
    window = Check_data_import_win(sample_strings, None, True)
    window.show()
    sys.exit(app.exec_())