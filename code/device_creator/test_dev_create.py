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

from dev_creator import deviceCreator
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton


class MainWindow(QMainWindow):
    def __init__(self, device_creator):
        super().__init__()
        self.device_creator = device_creator
        
        self.setWindowTitle("Главное окно")
        self.setGeometry(100, 100, 300, 200)

        self.run_device_creator_button = QPushButton("Запустить Конструктор", self)
        self.run_device_creator_button.setGeometry(50, 50, 200, 50)
        self.run_device_creator_button.clicked.connect(self.run_device_creator)

    def run_device_creator(self):
        self.device_creator.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    device_creator = deviceCreator()

    main_window = MainWindow(device_creator)
    main_window.show()

    sys.exit(app.exec_())
