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

import enum
import sys

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                             QDialogButtonBox, QFileDialog, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QVBoxLayout)


class type_save_file(enum.Enum):
    txt = 1
    excel = 2
    origin = 3


class settigsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 400, 300)

        main_layout = QVBoxLayout()
        set_layout = QHBoxLayout()

        self.checkboxes_layout_1 = QVBoxLayout()

        self.is_delete_buf_file = QCheckBox()
        self.is_exp_run_anywhere = QCheckBox()
        self.should_prompt_for_session_name = QCheckBox()

        self.manage_new_checkbox(self.is_delete_buf_file)
        self.manage_new_checkbox(self.is_exp_run_anywhere)
        self.manage_new_checkbox(self.should_prompt_for_session_name)

        set_layout.addLayout(self.checkboxes_layout_1)

        self.comboboxes = []
        self.labels = []

        def_list = [str(i) for i in range(1, 11)]
        bufvlay1 = QVBoxLayout()
        self.labelbuf1 = QLabel()
        self.repeat_exp_enter = QComboBox()
        self.repeat_exp_enter.addItems(def_list)
        self.repeat_exp_enter.setEditable(False)
        self.repeat_exp_enter.setMaximumWidth( int(self.height()/2))

        bufvlay1.addWidget(self.labelbuf1)
        bufvlay1.addWidget(self.repeat_exp_enter)
        self.checkboxes_layout_1.addLayout(bufvlay1)

        bufvlay2 = QVBoxLayout()
        self.labelbuf2 = QLabel()
        self.repeat_measurement_enter = QComboBox()
        self.repeat_measurement_enter.addItems(def_list)
        self.repeat_measurement_enter.setEditable(False)
        self.repeat_measurement_enter.setMaximumWidth( int(self.height()/2))
        bufvlay2.addWidget(self.labelbuf2)
        bufvlay2.addWidget(self.repeat_measurement_enter)
        self.checkboxes_layout_1.addLayout(bufvlay2)

        bufvlay3 = QVBoxLayout()
        bufhlay3 = QHBoxLayout()
        self.labelbuf3 = QLabel()
        self.place_save_res = QLineEdit()
        self.save_results_but = QPushButton()

        bufhlay3.addWidget(self.place_save_res)
        bufhlay3.addWidget(self.save_results_but)
        bufhlay3.setStretch(0, 5)
        bufhlay3.setStretch(1, 1)
        bufvlay3.addWidget(self.labelbuf3)
        bufvlay3.addLayout(bufhlay3)
        self.checkboxes_layout_1.addLayout(bufvlay3)

        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setGeometry(QtCore.QRect(80, 340, 191, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        main_layout.addLayout(set_layout)
        main_layout.addWidget(self.buttonBox)

        self.setLayout(main_layout)
        
        self.retranslateUi(self)

    def closeEvent(self, event):
        pass

    def manage_new_checkbox(self, checkbox):
        checkbox.setChecked(True)
        checkbox.setStyleSheet(
            "QToolTip { background-color: lightblue; color: black; border: 1px solid black; }"
        )
        self.checkboxes_layout_1.addWidget(checkbox)
    
    def retranslateUi(self, Installation):
        _translate = QtCore.QCoreApplication.translate
        
        self.setWindowTitle(_translate('set exp window',"Настройки эксперимента"))
        self.is_exp_run_anywhere.setText(_translate('set exp window',"Продолжать эксперимент при ошибке прибора"))
        self.is_exp_run_anywhere.setToolTip(
            _translate('set exp window',"При активации эксперимент будет продолжаться независимо от ответа прибора, \n\r если ответа от прибора не будет, в файл результатов будет записано слово fail")
        )

        self.is_delete_buf_file.setText(_translate('set exp window',"Удалить буферный файл после эксперимента"))
        self.is_delete_buf_file.setToolTip(
            _translate('set exp window',"При каждом измерении значения записываются в буферный файл, \n\r после эксперимента файл вычитывается и переводится в удобочитаемый формат, \n\r в случае активации этого пункта буферный файл будет удаляться после удачного сохранения результатов.")
        )

        self.should_prompt_for_session_name.setText(_translate('set exp window',"Запрашивать имя и описание измерений"))
        self.should_prompt_for_session_name.setToolTip(
            _translate('set exp window',"При активации этого пункта установка будет запрашивать имя и описание измерений в конце эксперимента")
        )
        
        self.labelbuf1.setText(_translate('set exp window',"Количество повторов эксперимента"))

        self.labelbuf2.setText(_translate('set exp window',"Количество измерений в точке"))

        self.labelbuf3.setText(_translate('set exp window',"Место сохранения результатов"))

        self.save_results_but.setText(_translate('set exp window',"путь"))


class experimentSettings():
    def __init__(self):
        self.window_dialog = settigsDialog()
        self.is_exp_run_anywhere = False
        self.is_delete_buf_file = True
        self.way_to_save = None
        self.repeat_exp = 1
        self.repeat_meas = 1

        self.window_dialog.repeat_measurement_enter.currentIndexChanged.connect(lambda: self._read_par())
        self.window_dialog.repeat_exp_enter.currentIndexChanged.connect(lambda: self._read_par())
        self.window_dialog.is_exp_run_anywhere.stateChanged.connect(lambda: self._read_par())
        self.window_dialog.is_delete_buf_file.stateChanged.connect(lambda: self._read_par())
        self.window_dialog.should_prompt_for_session_name.stateChanged.connect(lambda: self._read_par())
        self.window_dialog.save_results_but.clicked.connect(lambda: self.set_way_save())
        self.window_dialog.place_save_res.textChanged.connect(lambda: self._read_par())

    def read_settings(self,
                    is_exp_run_anywhere,
                    is_delete_buf_file,
                    should_prompt_for_session_name,
                    way_to_save,
                    type_file_for_result,
                    repeat_exp,
                    repeat_meas
                    ):
        self.type_file_for_result = type_file_for_result
        self.window_dialog.repeat_measurement_enter.setCurrentText(str(repeat_meas))
        self.window_dialog.repeat_exp_enter.setCurrentText( str(repeat_exp) )
        self.window_dialog.is_exp_run_anywhere.setChecked( is_exp_run_anywhere == True )
        self.window_dialog.is_delete_buf_file.setChecked( is_delete_buf_file == True )
        self.window_dialog.should_prompt_for_session_name.setChecked( should_prompt_for_session_name == True )
        self.window_dialog.place_save_res.setText( "" if not way_to_save else way_to_save )
        answer = self.window_dialog.exec_()
        if answer:
            return (True,
                    self.is_exp_run_anywhere,
                    self.is_delete_buf_file,
                    self.should_prompt_for_session_name,
                    self.way_to_save,
                    self.type_file_for_result,
                    self.repeat_exp,
                    self.repeat_meas
                   )
        return (False,
                is_exp_run_anywhere,
                is_delete_buf_file,
                should_prompt_for_session_name,
                way_to_save,
                self.type_file_for_result,
                repeat_exp,
                repeat_meas
               )

    def _read_par(self):
        self.is_exp_run_anywhere = self.window_dialog.is_exp_run_anywhere.checkState() == Qt.Checked
        self.is_delete_buf_file = self.window_dialog.is_delete_buf_file.checkState() == Qt.Checked
        self.should_prompt_for_session_name = self.window_dialog.should_prompt_for_session_name.checkState() == Qt.Checked

        self.way_to_save = self.window_dialog.place_save_res.text()
        self.repeat_exp = int(self.window_dialog.repeat_exp_enter.currentText())
        self.repeat_meas = int(self.window_dialog.repeat_measurement_enter.currentText())

    def set_way_save(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, ans = QFileDialog.getSaveFileName(
            self.window_dialog,
            QApplication.translate('set exp window',"укажите путь сохранения результатов"),
            "",
            "Книга Excel (*.xlsx);; Text Files(*.txt)",
            #"Text Files(*.txt);; Книга Excel (*.xlsx);;Origin (*.opju)",
            options=options,
        )
        if fileName:
            if ans == "Origin (*.opju)":
                if fileName.find(".opju") == -1:
                    fileName = fileName + ".opju"
                self.type_file_for_result = type_save_file.origin

            elif ans == "Книга Excel (*.xlsx)":
                if fileName.find(".xlsx") == -1:
                    fileName = fileName + ".xlsx"
                self.type_file_for_result = type_save_file.excel

            else:
                if fileName.find(".txt") == -1:
                    fileName = fileName + ".txt"
                self.type_file_for_result = type_save_file.txt

            self.way_to_save = fileName
            self.window_dialog.place_save_res.setText(self.way_to_save)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    cls = experimentSettings()
    is_exp_run_anywhere = True
    is_delete_buf_file = False
    way_to_save_file = "wweeeeewweewwwe"
    repeat_experiment = 5
    repeat_meas = 5
    for i in range(5):
        (is_exp_run_anywhere,
        is_delete_buf_file,
        way_to_save_file,
        repeat_experiment,
        repeat_meas) = cls.read_settings(
                                                            is_exp_run_anywhere,
                                                            is_delete_buf_file,
                                                            way_to_save_file,
                                                            repeat_experiment,
                                                            repeat_meas
                                                           )
        
        print(is_exp_run_anywhere,
        is_delete_buf_file,
        way_to_save_file,
        repeat_experiment,
        repeat_meas)

    sys.exit(app.exec_())
