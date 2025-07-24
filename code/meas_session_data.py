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
from PyQt5.QtWidgets import QDialog, QApplication

logger = logging.getLogger(__name__)

class measSessionData:
    '''
        Объект для хранения данных сессии измерений.
    '''
    def __init__(self):
        self.session_name = ''
        self.session_description = ''
        self.session_start_time = ''
        self.session_end_time = ''
        self.session_duration = ''
        self.measurement_parameters = {}

    def get_meta_data(self) -> str:
        return f"start_time={self.session_start_time}\nend_time={self.session_end_time}\nduration={self.session_duration}"

class measSession():
    '''
        объект управления сессией измерений
    '''
    def __init__(self):
        self.meas_session_data = measSessionData()
        self._buf_file = ''

    def ask_session_name_description(self, text = None, def_name = None) -> bool:
        text_def = QApplication.translate('askInfoWindow','''
Хотите добавить название и описание к результатам? Это поможет вам легко ориентироваться в данных.

Если не хотите, названием будет текущая дата и время, а описание останется пустым.
                ''')
        if text is not None:
            text+=(" " + text_def)
        else:
            text = text_def
        askwin = askInfoWindow()
        askwin.signal_to_main_window.connect(self.receive_info_from_win)
        askwin.setupUi(text," ", def_name )
        askwin.setModal(True)
        askwin.exec_()
        return True
    def set_default_session_name_description(self):
        self.meas_session_data.session_name = ""
        self.meas_session_data.session_description = ""
    @property
    def session_name(self) -> str:
        return self.meas_session_data.session_name
    
    @session_name.setter
    def session_name(self, value):
        self.meas_session_data.session_name = value
    @property
    def session_description(self) -> str:
        return self.meas_session_data.session_description
    
    def save_results(self):
        pass

    def receive_info_from_win(self, name, description):    
        self.meas_session_data.session_name = name
        self.meas_session_data.session_description = description

class askInfoWindow(QDialog):
    signal_to_main_window = QtCore.pyqtSignal(str, str)

    def setupUi(self, message, window_name, def_value = None):

        self.main_lay = QtWidgets.QVBoxLayout(self)

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)

        font = QtGui.QFont()
        font.setPointSize(10)

        self.labelinfo = QtWidgets.QLabel(self)
        self.labelinfo.setFont(font)
        self.labelinfo.setWordWrap(True)
        self.labelinfo.setText(message)

        self.name_field = QtWidgets.QLineEdit(self)
        self.description_field = QtWidgets.QTextEdit(self)

        if def_value is not None:
            self.name_field.setText(def_value)

        self.name_field.setPlaceholderText( QApplication.translate('askInfoWindow',"Название") )
        self.description_field.setPlaceholderText( QApplication.translate('askInfoWindow',"Описание") )

        self.setWindowTitle(window_name)

        self.main_lay.addWidget(self.labelinfo)
        self.main_lay.addWidget(self.name_field)
        self.main_lay.addWidget(self.description_field)
        self.main_lay.addWidget(self.buttonBox)

        self.buttonBox.accepted.connect(self.accept)
        QtCore.QMetaObject.connectSlotsByName(self)

        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(
            self.send_signal_ok
        )

        self.retranslateUi()

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate

    def send_signal_ok(self):
        self.signal_to_main_window.emit(self.name_field.text(), self.description_field.toPlainText())



if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)

    cls = measSession()
    cls.ask_session_name_description()
    print(cls.session_name)

    sys.exit(app.exec_())