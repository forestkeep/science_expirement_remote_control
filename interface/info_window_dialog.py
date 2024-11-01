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


class Ui_Dialog(QtWidgets.QDialog):
    signal_to_main_window = QtCore.pyqtSignal(bool)

    def setupUi(self, Dialog, mother_window):
        self.signal_to_main_window.connect(mother_window.message_from_info_dialog)

        Dialog.setObjectName("Ахтунг!")
        Dialog.resize(210, 161)
        # Dialog.setStyleSheet("background-color: rgb(255, 200, 202);")
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(20, 120, 161, 32))
        # self.buttonBox.setStyleSheet("background-color: rgb(255, 170, 0);")
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttonBox.setObjectName("buttonBox")
        self.labelinfo = QtWidgets.QLabel(Dialog)
        self.labelinfo.setGeometry(QtCore.QRect(20, 0, 171, 101))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.labelinfo.setFont(font)
        self.labelinfo.setStyleSheet("\n" "")
        self.labelinfo.setWordWrap(True)
        self.labelinfo.setObjectName("labelinfo")
        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)  # type: ignore
        self.buttonBox.rejected.connect(Dialog.reject)  # type: ignore
        QtCore.QMetaObject.connectSlotsByName(Dialog)

        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(
            self.send_signal_ok
        )
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(
            self.send_signal_cancel
        )

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.labelinfo.setText(
            _translate(
                "D", "Установка уже создана. Закрыть текущую установку и создать новую?"
            )
        )

    def send_signal_ok(self):
        self.signal_to_main_window.emit(True)

    def send_signal_cancel(self):
        self.signal_to_main_window.emit(False)
