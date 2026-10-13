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
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QCheckBox, QHBoxLayout,QLabel,
                             QListWidget, QSizePolicy, QVBoxLayout, QWidget)

from graph.ui.numShowPoints_win import numShowPointsClass

logger = logging.getLogger(__name__)

class customQListWidget(QListWidget):
    def __init__(self):
        super().__init__()

    # ---------- работа с элементами ----------
    def add_parameters(self, parameters):
        if isinstance(parameters, str):
            parameters = [parameters]
        existing = {self.item(i).text() for i in range(self.count()) if self.item(i)}
        for p in parameters:
            if p not in existing:
                self.addItem(p)
                existing.add(p)

    def rename_parameter(self, old, new):
        for i in range(self.count()):
            item = self.item(i)
            if item and item.text() == old:
                item.setText(new)

    def remove_parameters(self, parameters):
        if isinstance(parameters, str):
            parameters = [parameters]
        kill = set(parameters)
        for i in range(self.count() - 1, -1, -1):
            item = self.item(i)
            if item and item.text() in kill:
                self.takeItem(i)

    def get_selected_texts(self) -> list:
        return [item.text() for item in self.selectedItems()]

    def _manage_selection(self, text, checked, is_signal=True):
        for i in range(self.count()):
            item = self.item(i)
            if item and item.text() == text:
                if checked:
                    self.setCurrentItem(item)
                item.setSelected(checked)
                if is_signal:
                    self.itemClicked.emit(item)
                return True
        logger.warning(f"parameter {text!r} not found in selector {self}")
        return False

    def clear_selection(self, text, is_signal=True):
        return self._manage_selection(text, False, is_signal)

    def set_selection(self, text, is_signal=True):
        return self._manage_selection(text, True, is_signal)

class paramSelector(QWidget):

    def __init__(self, alias_manager):
        super().__init__()
        self.alias_manager = alias_manager
        self.setLayout(self.setupDataSourceSelectors())

    def createHoverSelector(self, label_text) -> list:
        layout = QVBoxLayout()
        label = QLabel(label_text)
        listWidget = customQListWidget()
        listWidget.setSelectionMode(QListWidget.SingleSelection)

        hover_widget = QWidget()
        hover_widget.setLayout(layout)

        hover_widget.setAttribute(Qt.WA_Hover, True)

        layout.addWidget(label)
        layout.addWidget(listWidget)

        layout.setContentsMargins(0, 0, 0, 0)
        hover_widget.setContentsMargins(0, 0, 0, 0)

        return [layout, hover_widget, listWidget]
    
    def setupDataSourceSelectors(self):
        main_lay = QVBoxLayout()
        dataSourceLayout = QHBoxLayout()

        main_lay.setContentsMargins(0, 0, 0, 0)
        dataSourceLayout.setContentsMargins(0, 0, 0, 0)

        x_buf = self.createHoverSelector("X-Axis:")
        y_first_buf = self.createHoverSelector("Y main Axis:")
        y_second_buf = self.createHoverSelector("Y second Axis:")
        
        self.x_param_selector = x_buf[2]
        self.y_first_param_selector = y_first_buf[2]
        self.y_second_param_selector = y_second_buf[2]
        
        self.x_param_selector.setMaximumSize(800, 75)
        self.y_first_param_selector.setMaximumSize(800, 75)
        self.y_second_param_selector.setMaximumSize(800, 75)
        
        self.x_param_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.y_first_param_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.y_second_param_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.x_param_hover = x_buf[1]
        self.y_first_param_hover = y_first_buf[1]
        self.y_second_param_hover = y_second_buf[1]

        dataSourceLayout.addWidget(self.y_first_param_hover)
        dataSourceLayout.addWidget(self.x_param_hover)
        dataSourceLayout.addWidget(self.y_second_param_hover)

        self.second_check_box = QCheckBox("Add second axis")
        self.check_miltiple = QCheckBox("Multiple selection")

        self.hor_check_lay = QHBoxLayout()
        self.hor_check_lay.addWidget(self.check_miltiple)
        self.hor_check_lay.addWidget(self.second_check_box)

        self.hor_check_lay.setContentsMargins(0, 0, 0, 0)

        self.numPointsselector = numShowPointsClass()

        self.hor_check_lay.addWidget(self.numPointsselector)

        main_lay.addLayout(dataSourceLayout)
        main_lay.addLayout(self.hor_check_lay)

        self.y_second_param_hover.setVisible(False)

        self.second_check_box.stateChanged.connect(self.second_check_box_changed)
        self.check_miltiple.stateChanged.connect(self.check_miltiple_changed)

        return main_lay
    
    def check_miltiple_changed(self):
        if self.check_miltiple.isChecked() == True:
            self.y_first_param_selector.setSelectionMode(QListWidget.MultiSelection)
            self.y_second_param_selector.setSelectionMode(QListWidget.MultiSelection)
        else:
            self.y_first_param_selector.setSelectionMode(QListWidget.SingleSelection)
            self.y_second_param_selector.setSelectionMode(QListWidget.SingleSelection)
            self.y_second_param_selector.clearSelection()
            self.y_first_param_selector.clearSelection()
    
    def second_check_box_changed(self):
        logger.debug(f"second_check_box_changed {self.second_check_box.isChecked()}")
        if self.second_check_box.isChecked():
            self.y_second_param_hover.setVisible(True)
        else:
            self.y_second_param_hover.setVisible(False)

    def set_second_check_box(self, state: bool):
        self.second_check_box.setChecked(state)

    def set_multiple_mode(self, state: bool):
        self.check_miltiple.setChecked(state)

class paramController(QObject):
    parameters_updated        = pyqtSignal(str, list, list)
    multiple_checked          = pyqtSignal(bool)
    state_second_axis_changed = pyqtSignal(bool)
    numPointsChanged          = pyqtSignal(int)
    showingAllPoints          = pyqtSignal(bool)

    def __init__(self, paramSelector: "paramSelector", alias_manager) -> None:
        super().__init__()
        self.alias_manager = alias_manager
        self.paramSelector = paramSelector

        # пользовательские клики
        self.paramSelector.x_param_selector.itemClicked.connect(
            lambda item: self._on_x_clicked(item))
        self.paramSelector.y_first_param_selector.itemClicked.connect(
            lambda item: self._on_y_clicked(item, "first"))
        self.paramSelector.y_second_param_selector.itemClicked.connect(
            lambda item: self._on_y_clicked(item, "second"))

        # переключатели режимов
        self.paramSelector.check_miltiple.stateChanged.connect(self._on_multiple_changed)
        self.paramSelector.second_check_box.stateChanged.connect(self._on_second_axis_changed)

        # --- видимое окно: ЯВНАЯ трансляция вместо signal→signal ---
        num_widget = self.paramSelector.numPointsselector
        num_widget.numPointsChanged.connect(self._forward_num_points)
        num_widget.showingAllPoints.connect(self._forward_showing_all)

        self.alias_manager.aliases_updated.connect(self._on_alias_changed)

        # Состояние
        self.curent_x_parameter: str | None = None
        self.curent_y_first_parameters: list[str]  = []
        self.curent_y_second_parameters: list[str] = []

        # «Доступные» параметры (алиасы)
        self.__x_parameters: set[str]       = set()
        self.__y_first_parameters: set[str] = set()
        self.__y_second_parameters: set[str] = set()

        # защита от рекурсии
        self._suppress_user_action = False
        self._last_emitted_state   = None

    # ------------------------------------------------------------------
    # Слоты-трансляторы видимого окна
    # ------------------------------------------------------------------
    def _forward_num_points(self, value: int) -> None:
        self.numPointsChanged.emit(int(value))

    def _forward_showing_all(self, state: bool) -> None:
        self.showingAllPoints.emit(bool(state))


    def get_parameters(self):
        x  = self.alias_manager.get_original_name(self.curent_x_parameter) if self.curent_x_parameter else ""
        y1 = [self.alias_manager.get_original_name(p) for p in self.curent_y_first_parameters]
        y2 = [self.alias_manager.get_original_name(p) for p in self.curent_y_second_parameters]
        return x, y1, y2

    def add_parameters(self, new_parameters: list):
        aliases = [self.alias_manager.get_alias(p) for p in new_parameters]
        self.__x_parameters.update(aliases)
        self.__y_first_parameters.update(aliases)
        self.__y_second_parameters.update(aliases)

        self.paramSelector.x_param_selector.add_parameters(aliases)
        # y-списки пересобираем, чтобы сохранить инвариант «не показываем
        # в одном списке то, что выбрано в другом»
        self._rebuild_y_lists()

    def set_selections(self, x_param: str, y_first_params: list, y_second_params: list, is_signal=True):
        """Программно ДОБАВИТЬ параметры в выделение."""
        x_alias = self.alias_manager.get_alias(x_param) if x_param else None
        y1 = [self.alias_manager.get_alias(p) for p in y_first_params]
        y2 = [self.alias_manager.get_alias(p) for p in y_second_params]

        if x_alias:
            self.curent_x_parameter = x_alias
        for p in y1:
            if p not in self.curent_y_first_parameters:
                self.curent_y_first_parameters.append(p)
        for p in y2:
            if p not in self.curent_y_second_parameters:
                self.curent_y_second_parameters.append(p)

        self._enforce_invariants()
        self._rebuild_y_lists()
        if is_signal:
            self._emit_parameters_updated()

    def clear_selections(self, x_param: str, y_first_params: list, y_second_params: list, is_signal=True):
        """Программно СНЯТЬ выделение с указанных параметров."""
        x_alias = self.alias_manager.get_alias(x_param) if x_param else None
        y1 = [self.alias_manager.get_alias(p) for p in y_first_params]
        y2 = [self.alias_manager.get_alias(p) for p in y_second_params]

        if x_alias and self.curent_x_parameter == x_alias:
            self.curent_x_parameter = None
        self.curent_y_first_parameters  = [p for p in self.curent_y_first_parameters  if p not in y1]
        self.curent_y_second_parameters = [p for p in self.curent_y_second_parameters if p not in y2]

        self._enforce_invariants()
        self._rebuild_y_lists()
        if is_signal:
            self._emit_parameters_updated()

    def set_default(self):
        self.curent_x_parameter = None
        self.curent_y_first_parameters = []
        self.curent_y_second_parameters = []
        self.__x_parameters.clear()
        self.__y_first_parameters.clear()
        self.__y_second_parameters.clear()

        for w in (self.paramSelector.x_param_selector,
                  self.paramSelector.y_first_param_selector,
                  self.paramSelector.y_second_param_selector):
            w.clear()
        self._last_emitted_state = None
        self._emit_parameters_updated()

    def stop_session(self) -> None:
        """Остановка эксперимента.

        Скрываем селектор точек и принудительно переключаем в режим
        «все точки» — после эксперимента данные не растут.
        """
        widget = self.paramSelector.numPointsselector
        widget.hide()
        if not widget.checkbox.isChecked():
            widget.checkbox.setChecked(True)   # → showingAllPoints(True)

    # ================================================================
    # Обработчики пользователя
    # ================================================================
    def _on_x_clicked(self, item):
        if self._suppress_user_action:
            return
        # toggle-off при клике на уже выбранный
        if item.text() == self.curent_x_parameter:
            self.curent_x_parameter = None
            self._suppress_user_action = True
            try:
                self.paramSelector.x_param_selector.clearSelection()
            finally:
                self._suppress_user_action = False
        else:
            self.curent_x_parameter = item.text()
        self._emit_parameters_updated()

    # ================================================================
    # Пользовательский клик по Y-селектору
    # ================================================================
    def _on_y_clicked(self, item, which: str):
        if self._suppress_user_action:
            return
        text = item.text()
        is_multiple = self.paramSelector.check_miltiple.isChecked()

        if which == "first":
            lst = self.curent_y_first_parameters
        else:
            lst = self.curent_y_second_parameters

        if is_multiple:
            # multi: обычный toggle
            if text in lst:
                lst.remove(text)
            else:
                lst.append(text)
        else:
            # single: замена или снятие
            if text in lst:
                # повторный клик по выбранному → скрыть
                lst.clear()
            else:
                # новый клик → заменить единственный
                lst.clear()
                lst.append(text)

        self._enforce_invariants()
        self._rebuild_y_lists()
        self._emit_parameters_updated()

    # ================================================================
    # Переключение multiple
    # ================================================================
    def _on_multiple_changed(self):
        is_multiple = self.paramSelector.check_miltiple.isChecked()
        self._suppress_user_action = True
        try:
            if not is_multiple:
                # при выключении multiple оставляем по одному последнему
                self.curent_y_first_parameters  = self.curent_y_first_parameters[-1:]
                self.curent_y_second_parameters = self.curent_y_second_parameters[-1:]
        finally:
            self._suppress_user_action = False

        self._enforce_invariants()
        self._rebuild_y_lists()
        self.multiple_checked.emit(is_multiple)
        self._emit_parameters_updated()

    def _on_second_axis_changed(self):
        state = self.paramSelector.second_check_box.isChecked()
        if not state:
            self.curent_y_second_parameters = []
        self._enforce_invariants()
        self._rebuild_y_lists()
        self.state_second_axis_changed.emit(state)
        self._emit_parameters_updated()          # ← БАГ 5 исправлен

    def _on_alias_changed(self, original_name, old_alias, alias):
        # переименовать в виджетах
        for w in (self.paramSelector.x_param_selector,
                  self.paramSelector.y_first_param_selector,
                  self.paramSelector.y_second_param_selector):
            w.rename_parameter(old_alias, alias)

        # и в нашем наборе «доступных»
        for s in (self.__x_parameters, self.__y_first_parameters, self.__y_second_parameters):
            if old_alias in s:
                s.discard(old_alias)
                s.add(alias)

        # и в состоянии
        if self.curent_x_parameter == old_alias:
            self.curent_x_parameter = alias
        self.curent_y_first_parameters  = [alias if p == old_alias else p for p in self.curent_y_first_parameters]
        self.curent_y_second_parameters = [alias if p == old_alias else p for p in self.curent_y_second_parameters]
        # списки пересобирать не нужно — элементы уже переименованы на месте

    # ================================================================
    # Инварианты
    # ================================================================
    def _enforce_invariants(self):
        changed = False

        # 1. Вторая ось выключена → нет выделений на ней
        if not self.paramSelector.second_check_box.isChecked():
            if self.curent_y_second_parameters:
                self.curent_y_second_parameters = []
                changed = True

        # 2. Single-mode: не более 1 элемента на каждой оси
        if not self.paramSelector.check_miltiple.isChecked():
            if len(self.curent_y_first_parameters) > 1:
                # оставляем последний добавленный
                self.curent_y_first_parameters = self.curent_y_first_parameters[-1:]
                changed = True
            if len(self.curent_y_second_parameters) > 1:
                self.curent_y_second_parameters = self.curent_y_second_parameters[-1:]
                changed = True

        return changed

    def _rebuild_y_lists(self):
        """Пересобрать оба y-списка: показать все доступные, кроме выбранных в соседнем."""
        first_selected  = set(self.curent_y_first_parameters)
        second_selected = set(self.curent_y_second_parameters)
        all_y = sorted(self.__y_first_parameters | self.__y_second_parameters)

        first_items  = [p for p in all_y if p not in second_selected]
        second_items = [p for p in all_y if p not in first_selected]

        self._populate_list(self.paramSelector.y_first_param_selector,  first_items,  first_selected)
        self._populate_list(self.paramSelector.y_second_param_selector, second_items, second_selected)

    @staticmethod
    def _populate_list(widget, items, selected):
        widget.blockSignals(True)
        try:
            widget.clear()
            widget.addItems(items)
            for i in range(widget.count()):
                item = widget.item(i)
                if item.text() in selected:
                    item.setSelected(True)
                    widget.setCurrentItem(item)
        finally:
            widget.blockSignals(False)

    # ================================================================
    # Emit
    # ================================================================
    def _emit_parameters_updated(self):
        state = (
            self.curent_x_parameter,
            tuple(self.curent_y_first_parameters),
            tuple(self.curent_y_second_parameters),
        )
        if state == self._last_emitted_state:
            return
        self._last_emitted_state = state
        self.parameters_updated.emit(
            self.curent_x_parameter or "",
            list(self.curent_y_first_parameters),
            list(self.curent_y_second_parameters),
        )

if __name__ == '__main__':
    import sys

    def print_param(x_list, y_first_list, y_second_list):
        print("parameters updated")
        print(x_list, y_first_list, y_second_list)

    app = QApplication(sys.argv)
    main_win = paramSelector()
    my_class = paramController(main_win)
    my_class.add_parameters(["a", "b", "c", "d", "e", "f", "g", "b", "a"])
    my_class.parameters_updated.connect(print_param)
    main_win.show()
    sys.exit(app.exec_())