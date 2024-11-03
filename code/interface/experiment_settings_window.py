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
import enum

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
    QLineEdit, 
    QFileDialog
)

class type_save_file(enum.Enum):
    txt = 1
    excel = 2
    origin = 3


class settigsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Настройки эксперимента")
        self.setGeometry(100, 100, 400, 300)

        main_layout = QVBoxLayout()
        set_layout = QHBoxLayout()

        # Создание чекбоксов
        checkboxes_layout_1 = QVBoxLayout()
        checkboxes_layout_2 = QVBoxLayout()
        self.check_boxes_1 = []
        for i in range(2):
            checkbox = QCheckBox(f"Чекбокс {i+1}")
            checkbox.checkState()
            self.check_boxes_1.append(checkbox)
            checkboxes_layout_1.addWidget(checkbox)
        set_layout.addLayout(checkboxes_layout_1)
        self.check_boxes_1[0].setText("Продолжать эксперимент при ошибке прибора")
        self.check_boxes_1[0].setToolTip(
            "При активации эксперимент будет продолжаться независимо от ответа прибора, \n\r если ответа от прибора не будет, в файл результатов будет записано слово fail"
        )
        self.check_boxes_1[0].setChecked(True)
        self.check_boxes_1[0].setStyleSheet(
            "QToolTip { background-color: lightblue; color: black; border: 1px solid black; }"
        )

        self.check_boxes_1[1].setText("Удалить буферный файл после эксперимента")
        self.check_boxes_1[1].setToolTip(
            "При каждом измерении значения записываются в буферный файл, \n\r после эксперимента файл вычитывается и переводится в удобочитаемый формат, \n\r в случае активации этого пункта буферный файл будет удаляться после удачного сохранения результатов."
        )
        self.check_boxes_1[1].setChecked(True)
        self.check_boxes_1[1].setStyleSheet(
            "QToolTip { background-color: lightblue; color: black; border: 1px solid black; }"
        )

        self.comboboxes = []
        self.labels = []

        def_list = [str(i) for i in range(1, 11)]
        bufvlay1 = QVBoxLayout()
        labelbuf1 = QLabel("Количество повторов эксперимента")
        self.repeat_exp_enter = QComboBox()
        self.repeat_exp_enter.addItems(def_list)
        self.repeat_exp_enter.setEditable(False)
        self.repeat_exp_enter.setMaximumWidth( int(self.height()/2))

        bufvlay1.addWidget(labelbuf1)
        bufvlay1.addWidget(self.repeat_exp_enter)
        checkboxes_layout_1.addLayout(bufvlay1)

        bufvlay2 = QVBoxLayout()
        labelbuf2 = QLabel("Количество измерений в точке")
        self.repeat_measurement_enter = QComboBox()
        self.repeat_measurement_enter.addItems(def_list)
        self.repeat_measurement_enter.setEditable(False)
        self.repeat_measurement_enter.setMaximumWidth( int(self.height()/2))
        bufvlay2.addWidget(labelbuf2)
        bufvlay2.addWidget(self.repeat_measurement_enter)
        checkboxes_layout_1.addLayout(bufvlay2)

        bufvlay3 = QVBoxLayout()
        bufhlay3 = QHBoxLayout()
        labelbuf3 = QLabel("Место сохранения результатов")
        self.place_save_res = QLineEdit()
        self.save_results_but = QPushButton("путь")

        bufhlay3.addWidget(self.place_save_res)
        bufhlay3.addWidget(self.save_results_but)
        bufhlay3.setStretch(0, 5)
        bufhlay3.setStretch(1, 1)
        bufvlay3.addWidget(labelbuf3)
        bufvlay3.addLayout(bufhlay3)
        checkboxes_layout_1.addLayout(bufvlay3)

        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setGeometry(QtCore.QRect(80, 340, 191, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)  # type: ignore
        self.buttonBox.rejected.connect(self.reject)  # type: ignore

        main_layout.addLayout(set_layout)
        main_layout.addWidget(self.buttonBox)

        self.setLayout(main_layout)

    def closeEvent(self, event):
        pass

class experimentSettings():
    def __init__(self):
        self.window_dialog = settigsDialog()
        self.is_exp_run_anywhere = False
        self.is_delete_buf_file = True
        self.way_to_save = None
        self.repeat_exp = None
        self.repeat_meas = None

        self.window_dialog.repeat_measurement_enter.currentIndexChanged.connect(lambda: self._read_par())
        self.window_dialog.repeat_exp_enter.currentIndexChanged.connect(lambda: self._read_par())
        self.window_dialog.check_boxes_1[0].stateChanged.connect(lambda: self._read_par())
        self.window_dialog.check_boxes_1[1].stateChanged.connect(lambda: self._read_par())
        self.window_dialog.save_results_but.clicked.connect(lambda: self.set_way_save())
        self.window_dialog.place_save_res.textChanged.connect(lambda: self._read_par())

    def read_settings(self,
                    is_exp_run_anywhere,
                    is_delete_buf_file,
                    way_to_save,
                    repeat_exp,
                    repeat_meas
                    ):

        self.window_dialog.repeat_measurement_enter.setCurrentText(str(repeat_meas))
        self.window_dialog.repeat_exp_enter.setCurrentText( str(repeat_exp) )
        self.window_dialog.check_boxes_1[0].setChecked( is_exp_run_anywhere == True )
        self.window_dialog.check_boxes_1[1].setChecked( is_delete_buf_file == True )
        self.window_dialog.place_save_res.setText( "" if not way_to_save else way_to_save )
        answer = self.window_dialog.exec_()
        if answer:
            return (True,
                    self.is_exp_run_anywhere,
                    self.is_delete_buf_file,
                    self.way_to_save,
                    self.repeat_exp,
                    self.repeat_meas
                   )
        return (False,
                is_exp_run_anywhere,
                is_delete_buf_file,
                way_to_save,
                repeat_exp,
                repeat_meas
               )

    def _read_par(self):
        self.is_exp_run_anywhere = self.window_dialog.check_boxes_1[0].checkState() == Qt.Checked
        self.is_delete_buf_file = self.window_dialog.check_boxes_1[1].checkState() == Qt.Checked
        self.way_to_save = self.window_dialog.place_save_res.text()
        self.repeat_exp = int(self.window_dialog.repeat_exp_enter.currentText())
        self.repeat_meas = int(self.window_dialog.repeat_measurement_enter.currentText())

    def set_way_save(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, ans = QFileDialog.getSaveFileName(
            self.window_dialog,
            "укажите путь сохранения результатов",
            "",
            "Книга Excel (*.xlsx)",
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
