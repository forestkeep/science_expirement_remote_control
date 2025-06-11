# Copyright © 2025 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
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
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QHBoxLayout,QLabel,QSizePolicy, QWidget, QPushButton, QSpacerItem, QComboBox)
from PyQt5.QtWidgets import (QApplication, QFileDialog, QHBoxLayout,
                             QLabel, QPushButton,
                             QSizePolicy, QSpacerItem, QWidget, QDialog, QComboBox)
from PyQt5.QtGui import QFontMetrics
import pandas as pd
import numpy as np

try:
    from Link_data_import_win import Check_data_import_win
    from Message_graph import messageDialog
    from dataManager import graphDataManager
except:
    from graph.Link_data_import_win import Check_data_import_win
    from graph.Message_graph import messageDialog
    from graph.dataManager import graphDataManager

logger = logging.getLogger(__name__)

class importDataWin(QWidget):

    def __init__(self):
        super().__init__()
        self.setupUI()

    def setupUI(self):
        self.main_lay = QHBoxLayout()
        self.setLayout(self.main_lay)

        self.main_lay.setContentsMargins(0, 0, 0, 0)

        self.import_button = QPushButton()
        self.import_button_osc = QPushButton()
        self.experiment_selector = CustomComboBox()
        self.selector = QSpacerItem(15, 15, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.main_lay.addWidget(self.import_button)
        self.main_lay.addWidget(self.import_button_osc)
        
        exp_label = QLabel(QApplication.translate("filters","Выберите сессию: "))
        self.main_lay.addItem(self.selector)
        self.main_lay.addWidget(exp_label)
        self.main_lay.addWidget(self.experiment_selector)

        self.retranslateUi()

    def retranslateUi(self):
        self.import_button.setText(QApplication.translate("filters","Импортировать.."))
        self.import_button_osc.setText(QApplication.translate("filters","Импортировать осциллограммы.."))

class CustomComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.minimum_w = None

    def addItem(self, text):
        super().addItem(text)
        fm = QFontMetrics(self.font())
        self.minimum_w = max(fm.width(self.itemText(i)) for i in range(self.count()))
        
    def showPopup(self):
        super().showPopup()  
        if self.minimum_w:
            self.view().setMinimumWidth(self.minimum_w)

    def delete_text(self, text):
        for i in range(self.count()):
            if self.itemText(i) == text:
                self.removeItem(i)
                break

class controlImportData(QObject):
    exp_name_changed = pyqtSignal(str)
    new_data_imported = pyqtSignal(str, dict)
    def __init__(self, window):
        super().__init__()
        self.win = window
        self.win.import_button.clicked.connect(self.import_data)
        self.win.import_button_osc.clicked.connect(self.import_data)

        self.win.experiment_selector.currentIndexChanged.connect(self.experimental_data_changed)

        self.__is_exp_running = False
    def experimental_data_changed(self):
        exp_name = self.win.experiment_selector.currentText()
        self.exp_name_changed.emit(exp_name)

    def add_new_data_name(self, data_name) -> str:
        all_names = [self.win.experiment_selector.itemText(i) for i in range(self.win.experiment_selector.count())]
        if data_name in all_names:
            data_name+="(1)"
            i = 2
            while data_name in all_names:
                data_name = data_name[:-3] + f"({i})"
                i+=1

        self.win.experiment_selector.addItem(data_name)

        return data_name

    def import_data(self):
        '''
        if self.__is_exp_running:
            if self.main_class.experiment_controller.is_experiment_running():
                self.main_class.show_tooltip( QApplication.translate("GraphWindow","Дождитесь окончания эксперимента"), timeout = 3000)
                return
        '''
        
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, ans = QFileDialog.getOpenFileName(
            caption=QApplication.translate("GraphWindow", "укажите путь импорта"),
            directory="",
            filter="Книга Excel (*.xlsx)",
            options=options,
        )
        
        if fileName:
            if ans == "Книга Excel (*.xlsx)":

                df = pd.read_excel(fileName, engine='openpyxl')

                df = df.dropna(axis=1, how='all')

                df_col_type = type(df.columns[0])

                window = Check_data_import_win(sorted([str(col) for col in df.columns]))
                ans = window.exec_()
                if ans == QDialog.Accepted: 
                    selected_columns = [df_col_type(cb.text()) for cb in window.checkboxes if cb.isChecked()]
                else:
                    return
                
                if not selected_columns:
                    logger.warning("No selected columns. Import aborted")
                    return

                result = {}
                errors_col = []

                for col in selected_columns:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='raise')
                    except ValueError:
                        errors_col.append(str(col))
                        continue

                    
                if errors_col != []:
                    res = ', '.join(errors_col)
                    text = QApplication.translate("GraphWindow", "В столбцах {res} обнаружены данные, которые не получается преобразовать в числа.\nПри построение эти точки будут пропущены.")
                    text = text.format(res = res)
                    message = messageDialog(
                        title = QApplication.translate("GraphWindow","Сообщение"),
                        text= text
                    )
                    message.exec_()
                    
                for col in selected_columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    col_ = str(col).replace('(', '[').replace(')', ']')
                    buf = np.array( df[col].tolist())
                    result[col_] = [ buf, np.array([i for i in range(len(buf))]) ]

                fileName = self.add_new_data_name(data_name=fileName)

                self.new_data_imported.emit(fileName, result)

                '''
                try:
                    self.data_manager.start_new_session(session_id = fileName, new_data = result)
                except Exception as e:
                    logger.warning(f"ошибка при импорте данных от дата менеджера: {str(e)}")
                    self.win.experiment_selector.delete_text(fileName)
                '''

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    widget = importDataWin()
    data_manager = graphDataManager()
    my_class = controlImportData(widget)
    widget.show()
    sys.exit(app.exec_())
