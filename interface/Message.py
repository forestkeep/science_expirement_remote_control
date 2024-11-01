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

from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class messageDialog(QDialog):
    def __init__(
        self, title="Сообщение", text="Отлично выглядите!", are_show_again=False
    ):
        super().__init__()
        self.setMinimumSize(400, 200)  # устанавливаем минимальный размер окна

        self.setWindowTitle(title)

        layout = QVBoxLayout()

        info_label = QLabel(text)
        info_label.setStyleSheet("font-size: 14px; font-family: Arial;")
        layout.addWidget(info_label)

        ok_button = QPushButton("Ok", self)
        ok_button.clicked.connect(
            self.accept
        )  # закрываем окно при нажатии на кнопку Ok
        if are_show_again:
            self.check_not_show = QCheckBox("Не показывать снова")
            layout.addWidget(self.check_not_show)
        layout.addWidget(ok_button)
        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = messageDialog(are_show_again=True)
    dialog.exec_()
    sys.exit(app.exec_())
