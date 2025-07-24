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

from Devices.interfase.base_set_window import base_settings_window


class pigInAPokeWindow(base_settings_window):
    def __init__(self) -> None:
        super().__init__()

    def setupUi(self):

        self.remove_act()
        # self.remove_meas()

        self.resize(800, 600)

        self.description_label = QtWidgets.QLabel()

        self.timeotlabel = QtWidgets.QLabel()
        self.timeout_line = QtWidgets.QLineEdit()

        self.downloaded_file_lable = QtWidgets.QLabel()
        self.command_text = QtWidgets.QTextEdit(self)
        self.download_button = QtWidgets.QPushButton(self)
        self.check_not_command = QtWidgets.QCheckBox(self)
        
        self.Layout_set_dev_meas.addWidget(self.description_label)
        self.Layout_set_dev_meas.addWidget(self.check_not_command, 2, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.downloaded_file_lable, 3, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.command_text, 4, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.download_button, 5, 0, 1, 1)

        self.Layout_set_dev_meas.addWidget(self.timeotlabel)
        self.Layout_set_dev_meas.addWidget(self.timeout_line)

        self.retranslateUi(self)

    def retranslateUi(self, Set_power_supply):
        _translate = QtCore.QCoreApplication.translate
        Set_power_supply.setWindowTitle(
            _translate("pigInAPoke", "Настройка прибора Кот в мешке")
        )
        text_timeout = _translate("pigInAPoke", "Введите значение таймаута опроса прибора в мсек")
        self.timeotlabel.setText( text_timeout )
        self.timeout_line.setPlaceholderText( text_timeout )
        self.timeout_line.setToolTip(_translate("pigInAPoke", "Большое значение таймаута замедлит опрос прибора.\n" \
        " Если у вас один прибор, выдающий данные не по запросу, а через определенные интервалы времени,\n" \
        " то имеет смысл установить значение таймаута чуть большим, чем период выдачи результатов прибором."))
        self.description_label.setText(_translate("pigInAPoke", "Впишите или загрузите команды построчно"))
        self.download_button.setText(_translate("pigInAPoke", "Загрузить файл"))
        self.downloaded_file_lable.setToolTip(_translate("pigInAPoke", "Введите команды построчно, на каждом шаге прибора команды будут построчно выполнены, а полученные от них данные записаны в качесве результатов."))
        self.check_not_command.setText(_translate("pigInAPoke", "Не отправлять команду перед чтением"))
        self.check_not_command.setToolTip(_translate("pigInAPoke", "Отметьте этот пункт, если ваш прибор непрерывно посылает данные независимо от команды"))

if __name__ == "__main__":
    import sys

    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = pigInAPokeWindow()
    a.setupUi()
    a.show()
    sys.exit(app.exec_())