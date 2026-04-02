from PyQt5.QtWidgets import (QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QHBoxLayout, QVBoxLayout, QPushButton, QMenu, QAbstractItemView,
                             QAction, QFileDialog, QApplication, QDialog, QTextEdit, QDialogButtonBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPoint
import os
import logging

import pandas as pd
import numpy as np

from graph.Link_data_import_win import Check_data_import_win, SheetSelectionDialog
from graph.Message_graph import messageDialog

logger = logging.getLogger(__name__)

class ButtonsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    def init_ui(self):
        self.btn_import_data = QPushButton(QApplication.translate("filters","Импортировать данные"))
        self.btn_import_osc = QPushButton(QApplication.translate("filters","Импортировать осциллограммы"))
        self.btn_compare_sessions = QPushButton(QApplication.translate("filters","Сравнение сессий"))
        
        button_layout = QHBoxLayout(self)
        button_layout.addWidget(self.btn_import_data)
        button_layout.addWidget(self.btn_import_osc)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_compare_sessions)



class ButtonsControl(QObject):

    new_data_imported = pyqtSignal(str, str, dict)
    compare_sessions_requested = pyqtSignal()

    def __init__(self, session_selector):
        super().__init__()
        self.session_selector = session_selector
        self.widget = ButtonsWidget()
        
        self.widget.btn_import_data.clicked.connect(self.handle_import_data)
        self.widget.btn_import_osc.clicked.connect(self.handle_import_osc)
        self.widget.btn_compare_sessions.clicked.connect(self.compare_sessions_requested)

    def handle_import_data(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, ans = QFileDialog.getOpenFileName(
            caption=QApplication.translate("GraphWindow", "укажите путь импорта"),
            directory="",
            filter="Книга Excel (*.xlsx)",
            options=options,
        )

        if fileName and ans == "Книга Excel (*.xlsx)":
            try:
                xl = pd.ExcelFile(fileName, engine='openpyxl')
                sheet_names = xl.sheet_names
            except Exception as e:
                logger.error(f"Failed to read Excel file: {e}")
                return

            sheet_dialog = SheetSelectionDialog(sheet_names)
            if sheet_dialog.exec_() != QDialog.Accepted:
                return

            selected_sheets = sheet_dialog.get_selected_sheets()
            if not selected_sheets:
                logger.warning("No sheets selected. Import aborted")
                return

            short_name_flag = sheet_dialog.get_short_name()
            all_data_flag = sheet_dialog.get_import_all_data()   # <-- новый флаг
            base_name = os.path.basename(fileName)

            for sheet in selected_sheets:
                try:
                    df = pd.read_excel(fileName, sheet_name=sheet, engine='openpyxl')
                except Exception as e:
                    logger.error(f"Failed to read sheet '{sheet}': {e}")
                    continue

                df = df.dropna(axis=1, how='all')
                if df.empty or len(df.columns) == 0:
                    logger.warning(f"Sheet '{sheet}' has no data. Skipping.")
                    continue

                if all_data_flag:
                    selected_columns = list(df.columns)
                    logger.info(f"Auto-importing all {len(selected_columns)} columns from sheet '{sheet}'")
                else:
                    df_col_type = type(df.columns[0])
                    column_names = sorted([str(col) for col in df.columns])

                    window = Check_data_import_win(column_names)
                    window.setWindowTitle(
                        QApplication.translate("GraphWindow", f"Импорт данных с листа '{sheet}'")
                    )
                    ans = window.exec_()
                    if ans != QDialog.Accepted:
                        logger.info(f"User cancelled column selection for sheet '{sheet}'. Skipping.")
                        continue

                    selected_columns = [df_col_type(cb.text()) for cb in window.checkboxes if cb.isChecked()]
                    if not selected_columns:
                        logger.warning(f"No columns selected for sheet '{sheet}'. Skipping.")
                        continue

                result = {}
                errors_col = []

                for col in selected_columns:
                    try:
                        pd.to_numeric(df[col], errors='raise')
                    except (ValueError, TypeError):
                        errors_col.append(str(col))

                if errors_col:
                    res = ', '.join(errors_col)
                    text = QApplication.translate(
                        "GraphWindow",
                        "В столбцах {res} обнаружены данные, которые не получается преобразовать в числа.\nПри построении эти точки будут пропущены."
                    ).format(res=res)
                    message = messageDialog(
                        title=QApplication.translate("GraphWindow", "Сообщение"),
                        text=text
                    )
                    message.exec_()

                for col in selected_columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    col_name = str(col).replace('(', '[').replace(')', ']')
                    values = np.array(df[col].tolist())
                    result[col_name] = [values, np.array(range(len(values)))]

                id = self.session_selector.get_free_id()

                if short_name_flag:
                    display_name = sheet
                else:
                    display_name = f"{base_name} {sheet}"

                logger.info(f"Data imported emitted {id} for sheet '{sheet}'")
                self.new_data_imported.emit(display_name, id, result)

    def handle_import_osc(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, ans = QFileDialog.getOpenFileName(
            caption=QApplication.translate("GraphWindow","укажите путь импорта"),
            directory="",
            filter="Книга Excel (*.xlsx)",
            options=options,
        )
        
        #fileName = r"C:\Users\zahidovds\Desktop\testimport.xlsx"
        #ans = "Книга Excel (*.xlsx)"
        
        if fileName:
            if ans == "Книга Excel (*.xlsx)":
                df = pd.read_excel(fileName, engine='openpyxl')

                if 'time' not in df.columns:
                    self.is_time_column = False

                df = df.dropna(axis=1, how='all')

                window = Check_data_import_win(sorted([str(col) for col in df.columns]), None, True)
                ans = window.exec_()
                if ans == QDialog.Accepted: 
                    selected_step = window.step_combo.currentText()
                    selected_channels = [cb.text() for cb in window.checkboxes if cb.isChecked()]
                else:
                    return

                selected_channels.append(selected_step)
                errors_col = []

                for col in selected_channels:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='raise')
                    except ValueError:
                        errors_col.append(col)
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

                selected_channels.pop()

                import_time_scale_column = pd.to_numeric(df[selected_step], errors='coerce')

                import_time_scale = None
                for scale in import_time_scale_column:
                    if isinstance(scale, (float, int)) and scale > 0:
                        import_time_scale = scale
                        break

                if import_time_scale is None:
                    message = messageDialog(
                        title = QApplication.translate("GraphWindow","Сообщение"),
                        text= QApplication.translate("GraphWindow","Выбранный шаг не является числом или равен нулю, проверьте столбец с шагом времени")
                    )
                    return

                dev = {}
                result = {}
                df = df[[col for col in df.columns if col in selected_channels]]

                for col in selected_channels:
                    df[col] = (pd.to_numeric(df[col], errors='coerce'))
                df = df.dropna()

                '''
                for col in selected_channels:
                    col_ = col.replace('(', '[').replace(')', ']') + ' wavech'
                    volt_val = np.array( df[col].tolist() )
                    dev[col] = {col_: {0 : volt_val}, "scale": [import_time_scale for i in range(len(volt_val))]}
                '''
                    
                for index, col in enumerate(selected_channels):
                    col_ = str(col).replace('(', '[').replace(')', ']')
                    val = np.array( df[col].tolist())
                    result[col_] = {}
                    result[col_]['wavech'] = [ [val], [1]]
                    result[col_]["step"] = [[import_time_scale], [1]]

                '''формат
                data={'DS1104Z_1': {'ch-1_meas': {'wavech': [[[0.04, -0.0, 0.04, 0.04, 0.06, 0.04, 0.02, 0.04, 0.04, -0.0, 0.04, 0.02, 0.04, 0.04, 0.04, 0.02, 0.04, 0.04, 0.04, 0.04, 0.04, 0.06, 0.04, 0.04, 0.04, -0.0, 0.02, 0.02, 0.04, 0.04, 0.04, 0.04, 0.04, 0.02, 0.04, 0.04, 0.04, 0.04, 0.02, 0.04, 0.02, -0.0, 0.02, 0.04, 0.06, 0.04, 0.04, 0.04, 0.04, 0.02, 0.04, 0.04, 0.04, 0.04, 0.02, 0.04, 0.04, 0.02]], [4.367210099939257]],
                  'scale': [[5e-09], [4.367210099939257]], 'step': [[1e-09], [4.367210099939257]]}}}
                '''

                id = self.session_selector.get_free_id()

                logger.info(f"Data imported emitted {id}")
                self.new_data_imported.emit(fileName, id, result)
                
                #self.add_session({'id': id, 'name': fileName, 'status': 'imported'})



