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

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import  QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (QAction, QApplication,  QDialog,
                             QHBoxLayout, QHeaderView, QLineEdit, QMainWindow,
                             QMenu, QMessageBox, QPushButton, QTextEdit,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)
from PyQt5.QtGui import QBrush, QColor
import copy

from graphs.core.calc_values_for_graph import ArrayProcessor
from graphs.core.dataManager import relationData, measTimeData
from graphs.animation_graph.curve_animation import Animator
import numexpr as ne
import numpy as np
import logging
logger = logging.getLogger(__name__)


class HistoryItem(QTreeWidgetItem):
    def __init__(self, text: str, filter_command, parent=None):
        super().__init__(parent, [text])
        self.filter_command = filter_command

class AnalysisTreeItem(QTreeWidgetItem):
    """Узел дерева — результат анализа. Всегда вложен непосредственно в источник."""

    def __init__(self, artifact_id: str, text: str, parent=None, tool_id: str = ""):
        super().__init__(parent, [text])
        self.artifact_id = artifact_id
        self.tool_id = tool_id
        self.setFont(0, QFont("Arial", 9))
        self.setForeground(0, QBrush(QColor("#cccccc")))

class CurveTreeItem(QTreeWidgetItem):

    STAT_ORDER = (
        "count", "mean", "median", "mode",
        "std", "var", "min", "max",
        "range", "cv", "skew", "kurtosis",
        "q25", "q50", "q75", "iqr",
        "sum", "n_zeros", "n_positive", "n_negative",
        "missing_ratio"
    )

    def __init__(self, curve_data_obj=None, parent=None, name=None):
        super().__init__(parent)

        self.setText(0, f"Кривая {name}")
        self.font = QFont()
        self.font.setItalic(True)
        self.font.setPointSize(10)
        self.setFont(0, self.font)

        self.col_font = QFont()
        self.col_font.setPointSize(15)
        self.setFont(1, self.col_font)

        self.setText(1, "--●--")

        self.curve_data_obj = curve_data_obj

        self.parameters = {
            "min_x": None, "max_x": None,
            "min_y": None, "max_y": None,
            "name": name, "tip": None, "id": None,
            # Статистики
            "count": None, "mean": None, "median": None, "mode": None,
            "std": None, "var": None, "min": None, "max": None,
            "range": None, "cv": None, "skew": None, "kurtosis": None,
            "q25": None, "q50": None, "q75": None, "iqr": None,
            "sum": None, "n_zeros": None, "n_positive": None, "n_negative": None,
            "missing_ratio": None
        }

        self.add_basic_characteristics()

    def set_name(self, name):
        self.setText(0, QApplication.translate("filters", f"Кривая {name}"))
        self.parameters["name"] = name

    def add_basic_characteristics(self):
        self.addChild(QTreeWidgetItem([f"ID: {self.parameters['id']}"]))
        
        text = QApplication.translate("GraphWindow", "Тип: {tip}")
        text = text.format(tip=self.parameters["tip"])
        self.addChild(QTreeWidgetItem([text]))

        text = QApplication.translate("GraphWindow", "Область определения: ({min_x}, {max_x})")
        text = text.format(min_x=self.parameters["min_x"], max_x=self.parameters["max_x"])
        self.addChild(QTreeWidgetItem([text]))

        text = QApplication.translate("GraphWindow", "Область значений: ({min_y}, {max_y})")
        text = text.format(min_y=self.parameters["min_y"], max_y=self.parameters["max_y"])
        self.addChild(QTreeWidgetItem([text]))

        self._add_statistics_block()

    def _add_statistics_block(self):
        """Создаёт родительский элемент 'Статистические данные' и дочерние для каждой статистики."""
        stats_item = self.findChild(QApplication.translate("GraphWindow", "Статистические данные"))
        if stats_item is None:
            stats_item = QTreeWidgetItem(self, [QApplication.translate("GraphWindow", "Статистические данные")])
            stats_item.setFont(0, self.font)
            stats_item.setExpanded(True)

            for key in self.STAT_ORDER:
                value = self.parameters.get(key, None)
                text = f"{key}: {value}"
                stats_item.addChild(QTreeWidgetItem([text]))

    def add_new_block(self, block_name, data):
        block_item = self.findChild(block_name)
        if block_item is None:
            block_item = QTreeWidgetItem(self, [block_name])
            block_item.setFont(0, self.font)
            block_item.setExpanded(True)

        for key, value in data.items():
            block_item.addChild(QTreeWidgetItem([f"{key}: {value}"]))

    def update_history_block(self, data, filter_command=None):
        block_name = QApplication.translate("GraphWindow", "История изменения")
        block_item = self.findChild(block_name)

        if block_item is None:
            block_item = QTreeWidgetItem(self, [block_name])
            block_item.setFont(0, self.font)
            block_item.setExpanded(True)

        for key, value in data.items():
            block_item.addChild(HistoryItem(text=f"{key}: {value}", filter_command=filter_command))

    def clear_history_block(self):
        block_name = QApplication.translate("GraphWindow", "История изменения")
        block_item = self.findChild(block_name)
        if block_item:
            block_item.takeChildren()

    def delete_block(self, block_name) -> bool:
        block_item = self.findChild(block_name)
        if block_item:
            self.takeChild(self.indexOfChild(block_item))
            return True
        return False

    def update_block_data(self, block_name, data, is_add_force=False) -> bool:
        block_item = self.findChild(block_name)
        if block_item:
            for key, value in data.items():
                if is_add_force:
                    block_item.addChild(QTreeWidgetItem([f"{key}: {value}"]))
                else:
                    exists = False
                    for i in range(block_item.childCount()):
                        if block_item.child(i).text(0).startswith(f"{key}:"):
                            block_item.child(i).setText(0, f"{key}: {value}")
                            exists = True
                            break
                    if not exists:
                        block_item.addChild(QTreeWidgetItem([f"{key}: {value}"]))
            return True
        return False

    def update_parameters(self, dict_parameters):
        for parameter_name, new_value in dict_parameters.items():
            if parameter_name in self.parameters:
                if isinstance(new_value, (int, float)) and not isinstance(new_value, bool):
                    val = np.format_float_scientific(new_value, precision=5, unique=True)
                else:
                    val = new_value
                self.parameters[parameter_name] = val
            else:
                try:
                    logger.info(f"ключ {parameter_name} не найден в параметрах отображения кривой")
                except NameError:
                    pass
        self.update_display()

    def get_description(self):
        block_item = self.findChild(QApplication.translate("GraphWindow", "Разное"))
        if block_item:
            for i in range(block_item.childCount()):
                text = block_item.child(i).text(0)
                if QApplication.translate("GraphWindow", "Описание") in text:
                    text = text.replace(QApplication.translate("GraphWindow", "Описание") + ": ", "")
                    return text
        return ""

    def this_choise(self):
        self.curve_data_obj.higlight_curve()

    def deselection(self):
        self.curve_data_obj.unhiglight_curve()

    def is_draw(self):
        return self.curve_data_obj.is_draw

    def update_display(self):
        self.setText(0, f"{self.parameters['name']}")
        text_id = QApplication.translate("GraphWindow", "ID: {id}")
        text_id = text_id.format(id=self.parameters["id"])
        self.child(0).setText(0, text_id)

        text_tip = QApplication.translate("GraphWindow", "Тип: {tip}")
        text_tip = text_tip.format(tip=self.parameters["tip"])
        self.child(1).setText(0, text_tip)

        text_domain = QApplication.translate("GraphWindow", "Область определения: ({min_x}, {max_x})")
        text_domain = text_domain.format(min_x=self.parameters["min_x"], max_x=self.parameters["max_x"])
        self.child(2).setText(0, text_domain)

        text_range = QApplication.translate("GraphWindow", "Область значений: ({min_y}, {max_y})")
        text_range = text_range.format(min_y=self.parameters["min_y"], max_y=self.parameters["max_y"])
        self.child(3).setText(0, text_range)

        stats_item = self.findChild(QApplication.translate("GraphWindow", "Статистические данные"))
        if stats_item:
            for idx, key in enumerate(self.STAT_ORDER):
                if idx < stats_item.childCount():
                    val = self.parameters.get(key, None)
                    stats_item.child(idx).setText(0, f"{key}: {val}")

    def findChild(self, title):
        for i in range(self.childCount()):
            if self.child(i).text(0) == title:
                return self.child(i)
        return None

    # ---- Analysis results ---------------------------------------------
    def add_analysis_item(self, item: AnalysisTreeItem, order_index: int = 0) -> None:
        """Добавляет дочерний узел-результат анализа (без промежуточных групп)."""
        self.addChild(item)
        item.setData(0, Qt.UserRole, order_index)
        self.setExpanded(True)

    def remove_analysis_item(self, item: AnalysisTreeItem) -> None:
        idx = self.indexOfChild(item)
        if idx >= 0:
            self.takeChild(idx)

    def get_analysis_items(self) -> list:
        return [self.child(i) for i in range(self.childCount())
                if isinstance(self.child(i), AnalysisTreeItem)]

class CurveDialog(QDialog):
    def __init__(self, parent=None, description=None, formula=None, name=None):
        super().__init__(parent)
        self.setWindowTitle( QApplication.translate("GraphWindow","Создать новую кривую"))
        self.setFixedSize(300, 200)
        layout = QVBoxLayout(self)

        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText( QApplication.translate("GraphWindow","Имя"))
        layout.addWidget(self.name_input)

        self.formula_input = QLineEdit(self)
        self.formula_input.setPlaceholderText( QApplication.translate("GraphWindow","Формула"))
        layout.addWidget(self.formula_input)

        self.description_input = QTextEdit(self)
        self.description_input.setPlaceholderText( QApplication.translate("GraphWindow","Описание"))
        layout.addWidget(self.description_input)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("ОК", self)
        self.cancel_button = QPushButton( QApplication.translate("GraphWindow","Отмена"), self)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        if description is not None:
            self.description_input.setText(description)
        if formula is not None:
            self.formula_input.setText(formula)
        if name is not None:
            self.name_input.setText(name)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def get_curve_data(self):
        return self.name_input.text(), self.formula_input.text(), self.description_input.toPlainText()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("")
        self.setGeometry(100, 100, 800, 600)
        main_widget = treeWin()
        self.setCentralWidget(main_widget)

class customTreeWidget(QTreeWidget):
    def __init__(self, par_class):
        super().__init__()
        self.par_class = par_class
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        self.par_class.on_item_entered(item)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.par_class.on_item_entered(None)
        super().leaveEvent(event)

class treeWin(QWidget):
    curve_deleted = pyqtSignal( object )
    curve_shown = pyqtSignal( object )
    curve_hide = pyqtSignal( object )
    curve_reset = pyqtSignal( object )
    curve_created = pyqtSignal( object, str, str )
    analysis_item_removed = pyqtSignal(str)
    analysis_item_visibility_toggled = pyqtSignal(str, bool)
    analysis_item_properties_requested = pyqtSignal(str)
    def __init__(self, main_class = None, action_registry = None):
        super().__init__()
        self.setMinimumSize(0,0)
        self.action_registry = action_registry
        self.curves = []
        left_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        self.main_class = main_class
        self._curve_id_counter = 0  # счётчик уникальных ID

        self.buttons = []
        button = QPushButton("Создать кривую", self)
        button.setMaximumSize(30, 30)
        button.setMinimumSize(0, 0)
        button_layout.addWidget(button)
        self.buttons.append(button)

        self.buttons[0].clicked.connect(self.open_curve_dialog)

        left_layout.addLayout(button_layout)

        self.buf_formula = None
        self.buf_description = None
        self.buf_new_curve_name = None

        self.visibility_button = QPushButton()
        self.visibility_button.setIcon(QIcon("picture/open_eye_light.png"))
        self.visibility_button.setCheckable(True)
        self.visibility_button.setChecked(True)
        self.visibility_button.setToolTip(
            QApplication.translate("GraphWindow", "Показать все кривые")
        )
        self.visibility_button.setMinimumSize(0, 30)
        self.visibility_button.setMaximumSize(30, 30)
        self.visibility_button.clicked.connect(self.toggle_visibility)
        button_layout.addWidget(self.visibility_button)

        self.tree_widget = customTreeWidget(self)
        self.tree_widget.setColumnCount(3)
        self.tree_widget.setSortingEnabled(False)
        self.tree_widget.setHeaderLabels([QApplication.translate("GraphWindow","Кривые")])

        left_layout.addWidget(self.tree_widget)

        header = self.tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(left_layout)

        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget.itemDoubleClicked.connect(self.on_history_item_double_clicked)

    def on_history_item_double_clicked(self, item, column):
        if not isinstance(item, HistoryItem):
            return

        parent = item
        while True:
            root_item = parent
            parent = parent.parent()
            if parent is None:
                break

        if not isinstance(root_item, CurveTreeItem):
            return

        curve = root_item.curve_data_obj
        fc = item.filter_command

        session = self.main_class
        cmd = None
        if session is not None and hasattr(session, "undo_manager"):
            from graphs.core.undo_commands import RemoveFilterCommand
            cmd = RemoveFilterCommand(curve=curve, filter_command=fc)

        curve.delete_filter(fc)
        if item.parent() is not None:
            item.parent().removeChild(item)

        if cmd is not None and not session.undo_manager.is_applying:
            session.undo_manager.push(cmd)

    def on_item_entered(self, item):
        """Подсветить кривую под курсором с дебаунсом (60 мс)."""
        if item is getattr(self, "_hover_item", None):
            return
        self._hover_item = item
        if getattr(self, "_hover_timer", None) is None:
            from PyQt5.QtCore import QTimer
            self._hover_timer = QTimer(self)
            self._hover_timer.setSingleShot(True)
            self._hover_timer.timeout.connect(self._apply_hover)
        self._hover_timer.start(60)

    def _apply_hover(self):
        """Применить подсветку к актуальному hover-элементу."""
        item = getattr(self, "_hover_item", None)
        root_item = None
        if item is not None:
            parent = item
            while True:
                root_item = parent
                parent = parent.parent()
                if parent is None:
                    break
        if not isinstance(root_item, CurveTreeItem):
            for cur in self.curves:
                cur.deselection()
            return
        root_item.this_choise()
        for cur in self.curves:
            if cur is not root_item:
                cur.deselection()

    def update_visible(self):
        """Применить текущий режим видимости ко всем элементам дерева.

        Вызывается:
          * из toggle_visibility() при клике по кнопке;
          * автоматически из add_curve / delete_curve / show_curve /
            hide_curve / clear_all и из undo/redo-команд.
        """
        show_only_active = self.visibility_button.isChecked()
        for curve in self.curves:
            hidden = bool(show_only_active and not curve.is_draw())
            curve.setHidden(hidden)

    def toggle_visibility(self):
        """Переключить режим видимости и обновить иконку/tooltip по действию.

        При нажатой кнопке показываются только активные (is_draw) кривые,
        tooltip подсказывает, что клик вернёт показ всех. При отжатой —
        наоборот.
        """
        if self.visibility_button.isChecked():
            self.visibility_button.setIcon(QIcon("picture/open_eye_light.png"))
            self.visibility_button.setToolTip(
                QApplication.translate("GraphWindow", "Показать все кривые")
            )
        else:
            self.visibility_button.setIcon(QIcon("picture/close_eye_light.png"))
            self.visibility_button.setToolTip(
                QApplication.translate("GraphWindow", "Показать только активные кривые")
            )
        self.update_visible()

    def open_curve_dialog(self):
        dialog = CurveDialog(self, self.buf_description, self.buf_formula, self.buf_new_curve_name)
        if dialog.exec_() == QDialog.Accepted:
            self.buf_new_curve_name, self.buf_formula, self.buf_description = dialog.get_curve_data()

            choised_curves = {}
            is_consist_curve = False
            for curve in self.curves:
                if curve.parameters["id"] in self.buf_formula:
                    is_consist_curve = True
                    choised_curves[curve.parameters["id"]] = curve
            if not is_consist_curve:
                return
            
            names_x_parameters = set()
            for id, curve in choised_curves.items():
                if curve.curve_data_obj.rel_data.x_root_name not in names_x_parameters and names_x_parameters:
                    logger.info(f"Выбранные кривые построены в различных пространствах. {names_x_parameters}")
                    self.main_class.show_tooltip( QApplication.translate("GraphWindow","Выбранные кривые находятся в разных пространствах. Построение невозможно."), timeout=3000)
                    return
                names_x_parameters.add(curve.curve_data_obj.rel_data.x_root_name)

            all_curves, all_x, status = self.preparation_arrays(choised_curves)
            if not status:
                logger.info("ошибка в расчете, таймаут, возможно, что-то с исходными данными")
                self.main_class.show_tooltip( QApplication.translate("GraphWindow","Таймаут при расчете параметров. Возможно, исходные данные содержат некорректные значенияю."), timeout=3000)
                return
                
            result = self.evaluate_expression(self.buf_formula, all_curves)

            temp_rel_data = copy.deepcopy( curve.curve_data_obj.rel_data )

            x_meas = measTimeData(device=temp_rel_data.x_device, ch=temp_rel_data.x_ch, param=temp_rel_data.x_param, par_val=all_x[0], num_or_time=all_x[0])
            y_meas = measTimeData(device="", ch="", param=self.buf_new_curve_name, par_val=result, num_or_time=all_x[0])
            buf_rel_data = relationData(x_meas, y_meas, is_gen=True)

            self.curve_created.emit(buf_rel_data, self.buf_formula, self.buf_description)

            #если построение успешно, то очищаем буфер
            self.buf_formula = None
            self.buf_description = None
            self.buf_new_curve_name = None

    def preparation_arrays(self, tree_curves: dict):
        keys = list(tree_curves.keys())
        all_x = []
        all_y = []
        for key in keys:
            curve_data = tree_curves[key].curve_data_obj
            x = curve_data.filtered_x_data
            y = curve_data.filtered_y_data
            
            all_x.append(x)
            all_y.append(y)

        all_x, all_y, status = ArrayProcessor.combine_all_arrays(all_x, all_y)
        
        for i, key in enumerate(keys):
            tree_curves[key] = all_y[i]

        return tree_curves, all_x, status

    def evaluate_expression(self, expression, context=None) -> np.ndarray:
        result = None
        try:
            result = ne.evaluate(expression, context)
        except Exception as e:
            logger.info(f'Ошибка: {str(e)}')

        return result

    def add_curve(self, curve_item: CurveTreeItem):
        self._curve_id_counter += 1
        self.tree_widget.addTopLevelItem(curve_item)
        curve_item.update_parameters({"id": f"CUR{self._curve_id_counter}"})
        self.curves.append(curve_item)
        self.update_visible()

    def show_context_menu(self, position):
        item = self.tree_widget.itemAt(position)

        parent = item
        while True:
            root_item = parent
            parent = parent.parent()
            if parent  is None:
                break

        if root_item:
            context_menu = QMenu(self) 

            if root_item.curve_data_obj.is_draw:
                text_show = QApplication.translate("filters","Скрыть")
                show_action = QAction(text_show, self)
                context_menu.addAction(show_action)
                show_action.triggered.connect(lambda: self.hide_curve(root_item))
            else:
                text_show = QApplication.translate("filters","Отобразить")
                show_action = QAction(text_show, self)
                context_menu.addAction(show_action)
                show_action.triggered.connect(lambda: self.show_curve(root_item))

            delete_action = QAction( QApplication.translate("GraphWindow","Удалить график"), self)
            add_in_compare = QAction( QApplication.translate("GraphWindow","Добавить в сравнение"), self)
            animation_action = QAction( QApplication.translate("GraphWindow","Анимировать"), self)

            context_menu.addAction(delete_action)
            context_menu.addAction(add_in_compare)
            context_menu.addAction(animation_action)

            delete_action.triggered.connect(lambda: self.delete_curve(root_item))
            add_in_compare.triggered.connect(lambda: self.add_in_compare(root_item))
            animation_action.triggered.connect(lambda: self.show_animation(root_item))

            if self.action_registry is not None:
                registry_actions = self.action_registry.get_actions_for_context("curve")
                if registry_actions:
                    context_menu.addSeparator()
                    for action in registry_actions:
                        context_menu.addAction(action)


            if isinstance(item, AnalysisTreeItem):
                context_menu = QMenu(self)
                hide_action = QAction(_("Скрыть") if True else "Скрыть", self)
                del_action = QAction("Удалить", self)
                props_action = QAction("Свойства", self)
                hide_action.triggered.connect(
                    lambda: self.analysis_item_visibility_toggled.emit(item.artifact_id, False))
                del_action.triggered.connect(
                    lambda: self.analysis_item_removed.emit(item.artifact_id))
                props_action.triggered.connect(
                    lambda: self.analysis_item_properties_requested.emit(item.artifact_id))
                context_menu.addAction(hide_action)
                context_menu.addAction(del_action)
                context_menu.addAction(props_action)
                context_menu.exec_(self.tree_widget.viewport().mapToGlobal(position))
                return

            context_menu.exec_(self.tree_widget.viewport().mapToGlobal(position))

        self.update_visible()

    def show_animation(self, item):
        self.animator = Animator(item.curve_data_obj)
        self.main_class.animation_start(self.animator)

    def add_in_compare(self, item):
        compare_controller = self.main_class.get_compare_graph()
        graph_compare_field = compare_controller.get_graph_fields()
        item.curve_data_obj.add_to_graph(graph_compare_field, graph_compare_field.legend, 1)

    def delete_curve(self, item: CurveTreeItem = None):
        if item is None:
            selected_items = self.tree_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
            else:
                QMessageBox.warning(
                    self,
                    QApplication.translate("GraphWindow", "Ошибка"),
                    QApplication.translate("GraphWindow",
                                           "Пожалуйста, выберите элемент для удаления."),
                )
                return

        if item not in self.curves:
            return

        session = self.main_class
        cmd = None
        if session is not None and hasattr(session, "undo_manager"):
            from graphs.core.undo_commands import DeleteCurveCommand
            cmd = DeleteCurveCommand(session=session, tree_win=self, tree_item=item)

        # Существующий поток удаления (adapter снимает кривую и её артефакты)
        self.curve_deleted.emit(item.curve_data_obj)
        if item in self.curves:
            self.curves.remove(item)

        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            index = self.tree_widget.indexOfTopLevelItem(item)
            if index != -1:
                self.tree_widget.takeTopLevelItem(index)

        self.update_visible()

        if cmd is not None and not session.undo_manager.is_applying:
            session.undo_manager.push(cmd, execute=True)

    def show_curve(self, item: CurveTreeItem =None):
        if item is None:
            selected_items = self.tree_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
            else:
                QMessageBox.warning(self, QApplication.translate("GraphWindow","Ошибка"),
                                          QApplication.translate("GraphWindow", "Пожалуйста, выберите элемент для отображения."))
                return
        logger.info(f"show_curve {item=} {self.curves=}")
            
        if item in self.curves:
            self.curve_shown.emit(item.curve_data_obj)


        self.update_visible()

    def hide_curve(self, item: CurveTreeItem=None):
        if item is None:
            selected_items = self.tree_widget.selectedItems()
            if selected_items:
                item = selected_items[0]
            else:
                QMessageBox.warning(self, QApplication.translate("GraphWindow","Ошибка"),
                                          QApplication.translate("GraphWindow", "Пожалуйста, выберите элемент для отображения."))
                return
        if item in self.curves:
            self.curve_hide.emit(item.curve_data_obj)

        self.update_visible()

    def clear_all(self):
        for curve in self.curves:
            self.delete_curve(curve)

        self.update_visible()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())

    
