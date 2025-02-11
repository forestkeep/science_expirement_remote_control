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

import logging

from PyQt5 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)

try:
    from Devices.interfase.base_set_window import base_settings_window
except:
    from interfase.base_set_window import base_settings_window

class pigInAPokeWindow(base_settings_window):
    def __init__(self) -> None:
        super().__init__()

    def setupUi(self):

        self.remove_act()
        # self.remove_meas()

        self.resize(800, 600)

        self.description_label = QtWidgets.QLabel()

        self.downloaded_file_lable = QtWidgets.QLabel()
        self.command_text = QtWidgets.QTextEdit(self)
        self.download_button = QtWidgets.QPushButton(self)
        
        self.Layout_set_dev_meas.addWidget(self.description_label)
        self.Layout_set_dev_meas.addWidget(self.downloaded_file_lable, 2, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.command_text, 3, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.download_button, 4, 0, 1, 1)

        self.retranslateUi(self)

    def retranslateUi(self, Set_power_supply):
        _translate = QtCore.QCoreApplication.translate
        Set_power_supply.setWindowTitle(
            _translate("pigInAPoke", "Настройка прибора Кот в мешке")
        )
        self.description_label.setText(_translate("pigInAPoke", "Впишите или загрузите команды построчно"))
        self.download_button.setText(_translate("pigInAPoke", "Загрузить файл"))
        self.downloaded_file_lable.setToolTip(_translate("pigInAPoke", "Введите команды построчно, на каждом шаге прибора команды будут построчно выполнены, а полученные от них данные записаны в качесве результатов."))

if __name__ == "__main__":
    import sys

    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = pigInAPokeWindow()
    a.setupUi()
    a.show()
    sys.exit(app.exec_())