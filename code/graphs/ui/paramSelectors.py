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
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QScrollArea, QSizePolicy, QSplitter,
    QVBoxLayout, QWidget,
)

from graphs.ui.numShowPoints_win import numShowPointsClass

logger = logging.getLogger(__name__)

_TR = lambda s: QApplication.translate("GraphWindow", s)


# =====================================================================
# YAxisGroup — панель одной Y-оси
# =====================================================================
class YAxisGroup(QGroupBox):
    """Группа выбора Y-параметров одной оси.

    Параметры выводятся в N столбцов (по умолчанию 2) — это экономит
    вертикальную высоту. Список прокручивается, если не помещается.

    Все Y-параметры всегда присутствуют в списке. Параметры, уже
    отмеченные на другой оси, блокируются через ``set_blocked()``:
    чекбокс отключается, текст сереет, всплывает тултип-подсказка.
    """

    selection_changed = pyqtSignal()
    activation_changed = pyqtSignal(bool)
    multiple_changed = pyqtSignal(bool)

    def __init__(self, title: str, axis_id: int, parent=None, columns: int = 2):
        super().__init__(title, parent)
        self.axis_id = axis_id
        self._columns = max(1, int(columns))
        self._suppress = False
        self._checkboxes: dict[str, QCheckBox] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 4)
        outer.setSpacing(3)

        # --- Заголовок: активна + множ. + счётчик в одной строке ---
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        self.activate_check = QCheckBox(_TR("Активна"))
        self.activate_check.setToolTip(_TR(
            "Если выключено, параметры этой оси не отображаются на графике"
        ))
        self.activate_check.stateChanged.connect(self._on_activation_changed)
        header.addWidget(self.activate_check)

        self.multiple_check = QCheckBox(_TR("Множ."))
        self.multiple_check.setToolTip(_TR(
            "Разрешить выбирать несколько параметров одновременно"
        ))
        self.multiple_check.stateChanged.connect(self._on_multiple_changed)
        header.addWidget(self.multiple_check)

        header.addStretch()

        self.counter_label = QLabel("0")
        self.counter_label.setStyleSheet("color: #888; font-size: 11px;")
        self.counter_label.setToolTip(_TR("Выбрано параметров"))
        header.addWidget(self.counter_label)

        outer.addLayout(header)

        # --- Поиск (компактный) ---
        '''
        self.search = QLineEdit()
        self.search.setPlaceholderText(_TR("Поиск..."))
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumHeight(22)
        self.search.textChanged.connect(self._apply_filter)
        outer.addWidget(self.search)
        '''

         # --- Прокручиваемая сетка чекбоксов ---
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(0, 0, 0, 0)
        # Вертикальный зазор — в ноль; горизонтальный оставляем для читаемости
        self._grid.setVerticalSpacing(0)
        self._grid.setHorizontalSpacing(6)
        for c in range(self._columns):
            self._grid.setColumnStretch(c, 1)

        # Плотный вид чекбоксов: убираем внутренние отступы и margin,
        # уменьшаем расстояние «квадратик ↔ текст», фиксируем размер индикатора.
        # Без этого системный стиль даёт ~22–24 px на элемент — вдвое больше нужного.
        self._container.setStyleSheet(
            "QCheckBox { padding: 0px; margin: 0px; spacing: 4px; }"
            "QCheckBox::indicator { width: 14px; height: 14px; }"
        )
        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll, 1)

    # ------------------------------------------------------------------
    # Внутренние обработчики
    # ------------------------------------------------------------------
    def _on_activation_changed(self, state):
        if self._suppress:
            return
        enabled = state != 0
        self._scroll.setEnabled(enabled)
        #self.search.setEnabled(enabled)
        self.multiple_check.setEnabled(enabled)
        self.activation_changed.emit(enabled)

    def _on_multiple_changed(self, state):
        if self._suppress:
            return
        self.multiple_changed.emit(state != 0)

    def _on_cb_changed(self, name: str, state: int):
        if self._suppress:
            return
        # Единичный режим: пользователь поставил галочку — снимаем остальные.
        if not self.multiple_check.isChecked() and state != 0:
            to_uncheck = [
                cb for n, cb in self._checkboxes.items()
                if n != name and cb.isChecked()
            ]
            if to_uncheck:
                self._suppress = True
                try:
                    for cb in to_uncheck:
                        cb.blockSignals(True)
                        cb.setChecked(False)
                        cb.blockSignals(False)
                finally:
                    self._suppress = False
        self._update_counter()
        self.selection_changed.emit()

    def _apply_filter(self, text):
        text = (text or "").strip().lower()
        for name, cb in self._checkboxes.items():
            checked = cb.isChecked()
            visible = (not text) or (text in name.lower()) or checked
            cb.setVisible(visible)

    def _update_counter(self):
        n = sum(1 for cb in self._checkboxes.values() if cb.isChecked())
        self.counter_label.setText(str(n))

    def _clear_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._checkboxes.clear()

    def _rebuild_from_names(self, names, checked):
        self._clear_grid()
        for idx, name in enumerate(names):
            cb = QCheckBox(name)
            cb.setToolTip(name)
            cb.setChecked(name in checked)
            cb.setMinimumWidth(0)
            # Preferred (а не Fixed) — чтобы sizeHint после stylesheet
            # действительно сжимался; при необходимости виджет всё равно
            # не растянется по высоте, т.к. внутри QScrollArea.
            cb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            cb.stateChanged.connect(
                lambda st, n=name: self._on_cb_changed(n, st)
            )
            row = idx // self._columns
            col = idx % self._columns
            self._grid.addWidget(cb, row, col)
            self._checkboxes[name] = cb
        self._update_counter()

    # ------------------------------------------------------------------
    # Публичный API (не изменился)
    # ------------------------------------------------------------------
    def set_parameters(self, names):
        checked = set(self.get_selected())
        self._rebuild_from_names(names, checked)
        #self._apply_filter(self.search.text())

    def get_selected(self):
        return [n for n, cb in self._checkboxes.items() if cb.isChecked()]

    def set_selected(self, names, is_signal=False):
        checked = set(names or [])
        self._suppress = True
        try:
            for name, cb in self._checkboxes.items():
                cb.setChecked(name in checked)
        finally:
            self._suppress = False
        self._update_counter()
        if is_signal:
            self.selection_changed.emit()

    def set_blocked(self, blocked_names, reason: str = ""):
        """Заблокировать чекбоксы для имён из ``blocked_names``.

        Блокированный элемент остаётся видимым: серый текст, чекбокс
        отключён, тултип с причиной. Если параметр был отмечен — снимаем.
        """
        blocked = set(blocked_names or [])
        self._suppress = True
        try:
            for name, cb in self._checkboxes.items():
                if name in blocked:
                    if cb.isChecked():
                        cb.setChecked(False)
                    cb.setEnabled(False)
                    cb.setStyleSheet("color: #888;")
                    cb.setToolTip(reason)
                else:
                    cb.setEnabled(True)
                    cb.setStyleSheet("")
                    cb.setToolTip(name)
        finally:
            self._suppress = False
        #self._apply_filter(self.search.text())
        self._update_counter()

    def rename_parameter(self, old: str, new: str):
        cb = self._checkboxes.pop(old, None)
        if cb is None:
            return
        cb.blockSignals(True)
        try:
            cb.setText(new)
            cb.setToolTip(new)
        finally:
            cb.blockSignals(False)
        # переподключаем сигнал с новым именем
        try:
            cb.stateChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        cb.stateChanged.connect(
            lambda st, n=new: self._on_cb_changed(n, st)
        )
        self._checkboxes[new] = cb
        #self._apply_filter(self.search.text())

    def is_active(self) -> bool:
        return self.activate_check.isChecked()

    def set_active(self, state: bool, is_signal: bool = False):
        self._suppress = True
        try:
            self.activate_check.setChecked(bool(state))
        finally:
            self._suppress = False
        enabled = bool(state)
        self._scroll.setEnabled(enabled)
        #self.search.setEnabled(enabled)
        self.multiple_check.setEnabled(enabled)
        if is_signal:
            self.activation_changed.emit(enabled)

    def is_multiple(self) -> bool:
        return self.multiple_check.isChecked()

    def set_multiple(self, state: bool, is_signal: bool = False):
        self._suppress = True
        try:
            self.multiple_check.setChecked(bool(state))
        finally:
            self._suppress = False
        if is_signal:
            self.multiple_changed.emit(bool(state))

# =====================================================================
# paramSelector — вся секция выбора X/Y + видимое окно
# =====================================================================
class paramSelector(QWidget):
    """Секция выбора X/Y-параметров и видимого окна точек.

    X — одна независимая переменная (combo). Y1/Y2 — две оси в сплиттере,
    у каждой свой список с чекбоксами и свойством «активна/нет».
    """

    def __init__(self, alias_manager):
        super().__init__()
        self.alias_manager = alias_manager
        self._all_y_params = []          # кэш алиасов
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        # --- X combo ---
        x_row = QHBoxLayout()
        x_row.setContentsMargins(0, 0, 0, 0)
        x_label = QLabel("X:")
        x_label.setFixedWidth(24)
        self.x_combo = QComboBox()
        self.x_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.x_combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self.x_combo.setMinimumContentsLength(20)
        self.x_combo.addItem(_TR("— не выбрано —"), None)
        x_row.addWidget(x_label)
        x_row.addWidget(self.x_combo, 1)
        outer.addLayout(x_row)

        # --- Y1 / Y2 в горизонтальном сплиттере ---
        self.y_splitter = QSplitter(Qt.Horizontal)
        self.y1_group = YAxisGroup(
            _TR("Y1 — левая ось"), axis_id=1, columns=2
        )
        self.y2_group = YAxisGroup(
            _TR("Y2 — правая ось"), axis_id=2, columns=2
        )
        self.y_splitter.addWidget(self.y1_group)
        self.y_splitter.addWidget(self.y2_group)
        self.y_splitter.setStretchFactor(0, 1)
        self.y_splitter.setStretchFactor(1, 1)
        self.y_splitter.setSizes([400, 400])
        self.y_splitter.setChildrenCollapsible(False)
        outer.addWidget(self.y_splitter, 1)

        # --- Видимое окно точек ---
        # Скрыто по умолчанию: имеет смысл только в LIVE-режиме.
        # Показывается через paramController.set_live_mode(True)
        # при старте эксперимента и скрывается при остановке.
        self.numPointsselector = numShowPointsClass()
        self.numPointsselector.setVisible(False)
        outer.addWidget(self.numPointsselector)

        # --- Дефолт активации осей ---
        self.y1_group.set_active(True, is_signal=False)
        self.y2_group.set_active(False, is_signal=False)


    def _sync_multiple(self, source: YAxisGroup, target: YAxisGroup, state: bool):
        if target.is_multiple() != state:
            target.set_multiple(state, is_signal=False)

    # ------------------------------------------------------------------
    # Совместимость с graph_main.py (save/load)
    # ------------------------------------------------------------------
    @property
    def second_check_box(self):
        """Чекбокс «вторая ось» (для save/load в graph_main.py)."""
        return self.y2_group.activate_check

    @property
    def check_miltiple(self):
        """Чекбокс «множественный выбор» (для save/load в graph_main.py)."""
        return self.y1_group.multiple_check

    def set_second_check_box(self, state: bool):
        self.y2_group.set_active(bool(state), is_signal=True)

    def set_multiple_mode(self, state: bool):
        """Совместимость: старые вызовы трактуются как настройка Y1.

        Это поведение согласовано с property ``check_miltiple``,
        который тоже отдаёт чекбокс Y1.
        """
        self.y1_group.set_multiple(bool(state), is_signal=False)

    def set_multiple_mode_y1(self, state: bool):
        self.y1_group.set_multiple(bool(state), is_signal=False)

    def set_multiple_mode_y2(self, state: bool):
        self.y2_group.set_multiple(bool(state), is_signal=False)

    # ------------------------------------------------------------------
    # X combo
    # ------------------------------------------------------------------
    def set_x_selection(self, alias, is_signal: bool = True):
        idx = 0
        if alias:
            idx = self.x_combo.findData(alias)
            if idx < 0:
                idx = 0
        self.x_combo.blockSignals(True)
        try:
            self.x_combo.setCurrentIndex(idx)
        finally:
            self.x_combo.blockSignals(False)
        if is_signal:
            self.x_combo.currentIndexChanged.emit(idx)

    def get_x_selection(self):
        return self.x_combo.currentData()

    # ------------------------------------------------------------------
    # Наполнение параметрами
    # ------------------------------------------------------------------
    def set_available_params(self, names_sorted):
        """Полностью пересобрать списки X и Y.

        :param names_sorted: отсортированный список алиасов.
        """
        self._all_y_params = list(names_sorted)

        # X combo
        current_x = self.x_combo.currentData()
        self.x_combo.blockSignals(True)
        try:
            self.x_combo.clear()
            self.x_combo.addItem(_TR("— не выбрано —"), None)
            for name in self._all_y_params:
                self.x_combo.addItem(name, name)
            if current_x is not None:
                idx = self.x_combo.findData(current_x)
                if idx >= 0:
                    self.x_combo.setCurrentIndex(idx)
        finally:
            self.x_combo.blockSignals(False)

        # Y-списки (сохраняют галочки для оставшихся имён)
        self.y1_group.set_parameters(self._all_y_params)
        self.y2_group.set_parameters(self._all_y_params)

    def add_parameters(self, new_params):
        """Добавить новые имена, не сбрасывая существующие."""
        aliases = [self.alias_manager.get_alias(p) for p in new_params]
        existing = set(self._all_y_params)
        added = [a for a in aliases if a not in existing]
        if not added:
            return
        merged = sorted(set(self._all_y_params) | set(added))
        self.set_available_params(merged)

    def rename_parameter(self, old: str, new: str):
        # X combo
        self.x_combo.blockSignals(True)
        try:
            for i in range(self.x_combo.count()):
                if self.x_combo.itemData(i) == old:
                    self.x_combo.setItemText(i, new)
                    self.x_combo.setItemData(i, new)
                    break
        finally:
            self.x_combo.blockSignals(False)
        # Y groups
        self.y1_group.rename_parameter(old, new)
        self.y2_group.rename_parameter(old, new)
        self._all_y_params = [new if p == old else p for p in self._all_y_params]


# =====================================================================
# paramController — публичный API не изменился
# =====================================================================
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

        # X combo
        paramSelector.x_combo.currentIndexChanged.connect(self._on_x_changed)

        # Y groups
        paramSelector.y1_group.selection_changed.connect(self._on_y1_changed)
        paramSelector.y2_group.selection_changed.connect(self._on_y2_changed)
        paramSelector.y1_group.multiple_changed.connect(self._on_multiple_changed)
        paramSelector.y2_group.multiple_changed.connect(self._on_multiple_changed)
        paramSelector.y1_group.activation_changed.connect(self._on_y1_activation_changed)
        paramSelector.y2_group.activation_changed.connect(self._on_y2_activation_changed)

        # Видимое окно
        num_widget = paramSelector.numPointsselector
        num_widget.numPointsChanged.connect(self._forward_num_points)
        num_widget.showingAllPoints.connect(self._forward_showing_all)

        self.alias_manager.aliases_updated.connect(self._on_alias_changed)

        # Состояние (те же поля, что и раньше)
        self.curent_x_parameter: str | None = None
        self.curent_y_first_parameters: list[str] = []
        self.curent_y_second_parameters: list[str] = []

        self.__x_parameters: set[str] = set()
        self.__y_first_parameters: set[str] = set()
        self.__y_second_parameters: set[str] = set()

        self._suppress_user_action = False
        self._last_emitted_state = None

        # Стэш выделений неактивных осей: чтобы при повторной активации
        # вернуть выбор пользователя. Живёт только в памяти — в HDF5
        # не сохраняется, в parameters_updated не попадает.
        self._stash_y1: list[str] = []
        self._stash_y2: list[str] = []

    # ------------------------------------------------------------------
    # Трансляторы видимого окна
    # ------------------------------------------------------------------
    def _forward_num_points(self, value: int) -> None:
        self.numPointsChanged.emit(int(value))

    def _forward_showing_all(self, state: bool) -> None:
        self.showingAllPoints.emit(bool(state))

    # ------------------------------------------------------------------
    # Публичный API (не изменился)
    # ------------------------------------------------------------------
    def get_parameters(self):
        x = (
            self.alias_manager.get_original_name(self.curent_x_parameter)
            if self.curent_x_parameter
            else ""
        )
        y1 = [self.alias_manager.get_original_name(p) for p in self.curent_y_first_parameters]
        y2 = [self.alias_manager.get_original_name(p) for p in self.curent_y_second_parameters]
        return x, y1, y2

    def add_parameters(self, new_parameters: list):
        aliases = [self.alias_manager.get_alias(p) for p in new_parameters]
        self.__x_parameters.update(aliases)
        self.__y_first_parameters.update(aliases)
        self.__y_second_parameters.update(aliases)
        self.paramSelector.add_parameters(new_parameters)
        self._sync_view_from_model()

    def set_selections(self, x_param, y_first_params, y_second_params, is_signal=True):
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
        self._sync_view_from_model()
        if is_signal:
            self._emit_parameters_updated()

    def clear_selections(self, x_param, y_first_params, y_second_params, is_signal=True):
        x_alias = self.alias_manager.get_alias(x_param) if x_param else None
        y1 = [self.alias_manager.get_alias(p) for p in y_first_params]
        y2 = [self.alias_manager.get_alias(p) for p in y_second_params]

        if x_alias and self.curent_x_parameter == x_alias:
            self.curent_x_parameter = None
        self.curent_y_first_parameters = [
            p for p in self.curent_y_first_parameters if p not in y1
        ]
        self.curent_y_second_parameters = [
            p for p in self.curent_y_second_parameters if p not in y2
        ]

        self._enforce_invariants()
        self._sync_view_from_model()
        if is_signal:
            self._emit_parameters_updated()

    def set_default(self):
        self.curent_x_parameter = None
        self.curent_y_first_parameters = []
        self.curent_y_second_parameters = []
        self._stash_y1 = []
        self._stash_y2 = []
        self.__x_parameters.clear()
        self.__y_first_parameters.clear()
        self.__y_second_parameters.clear()
        self.paramSelector.set_available_params([])
        self._last_emitted_state = None
        self._emit_parameters_updated()

    def set_live_mode(self, is_live: bool) -> None:
        """Показать/скрыть секцию видимого окна точек.

        Видимое окно имеет смысл только в LIVE-режиме, когда данные
        растут и есть выбор «сколько последних точек показать». При
        переходе в REVIEW секцию скрываем и принудительно включаем
        режим «все точки» — иначе ранее урезанное окно «съест» часть
        точек в статичном графике.
        """
        widget = self.paramSelector.numPointsselector
        if is_live:
            widget.setVisible(True)
            return

        widget.setVisible(False)
        if not widget.checkbox.isChecked():
            widget.checkbox.setChecked(True)

    def stop_session(self) -> None:
        # Сохранено как алиас: вызывается адаптером graphSelectAdapter
        # по сигналу data_manager.stop_current_session.
        self.set_live_mode(False)

    # ------------------------------------------------------------------
    # Обработчики пользовательских действий
    # ------------------------------------------------------------------
    def _on_x_changed(self, index: int):
        if self._suppress_user_action:
            return
        self.curent_x_parameter = self.paramSelector.x_combo.itemData(index)
        self._emit_parameters_updated()

    def _on_y1_changed(self):
        if self._suppress_user_action:
            return
        new = self.paramSelector.y1_group.get_selected()
        self.curent_y_first_parameters = list(new)
        # Параметр, отмеченный на одной оси, убираем с другой — даже
        # если по какой-то причине он там был.
        self.curent_y_second_parameters = [
            p for p in self.curent_y_second_parameters
            if p not in self.curent_y_first_parameters
        ]
        self._enforce_invariants()
        self._sync_view_from_model()
        self._emit_parameters_updated()

    def _on_y2_changed(self):
        if self._suppress_user_action:
            return
        new = self.paramSelector.y2_group.get_selected()
        self.curent_y_second_parameters = list(new)
        self.curent_y_first_parameters = [
            p for p in self.curent_y_first_parameters
            if p not in self.curent_y_second_parameters
        ]
        self._enforce_invariants()
        self._sync_view_from_model()
        self._emit_parameters_updated()

    def _on_multiple_changed(self, state: bool):
        self._enforce_invariants()
        self._sync_view_from_model()
        self.multiple_checked.emit(bool(state))
        self._emit_parameters_updated()

    def _on_y1_activation_changed(self, enabled: bool):
        if not enabled:
            # Деактивация: запоминаем текущий выбор перед очисткой.
            # _enforce_invariants() ниже сам обнулит curent_y_first.
            self._stash_y1 = list(self.curent_y_first_parameters)
        else:
            # Реактивация: возвращаем то, что не занято другой осью.
            # Объединяем со всем, что могло быть установлено программно
            # (set_selections) до активации — не затираем.
            blocked = set(self.curent_y_second_parameters)
            for p in self._stash_y1:
                if p not in blocked and p not in self.curent_y_first_parameters:
                    self.curent_y_first_parameters.append(p)
            self._stash_y1 = []
        self._enforce_invariants()
        self._sync_view_from_model()
        self._emit_parameters_updated()

    def _on_y2_activation_changed(self, enabled: bool):
        if not enabled:
            self._stash_y2 = list(self.curent_y_second_parameters)
        else:
            blocked = set(self.curent_y_first_parameters)
            for p in self._stash_y2:
                if p not in blocked and p not in self.curent_y_second_parameters:
                    self.curent_y_second_parameters.append(p)
            self._stash_y2 = []
        self._enforce_invariants()
        self._sync_view_from_model()
        self.state_second_axis_changed.emit(bool(enabled))
        self._emit_parameters_updated()

    def _on_alias_changed(self, original_name, old_alias, alias):
        self.paramSelector.rename_parameter(old_alias, alias)
        for s in (self.__x_parameters, self.__y_first_parameters, self.__y_second_parameters):
            if old_alias in s:
                s.discard(old_alias)
                s.add(alias)
        if self.curent_x_parameter == old_alias:
            self.curent_x_parameter = alias
        self.curent_y_first_parameters = [
            alias if p == old_alias else p for p in self.curent_y_first_parameters
        ]
        self.curent_y_second_parameters = [
            alias if p == old_alias else p for p in self.curent_y_second_parameters
        ]

    # ------------------------------------------------------------------
    # Инварианты и синхронизация с моделью
    # ------------------------------------------------------------------
    def _enforce_invariants(self):
        changed = False

        # 1. Неактивная ось не держит выделений
        if not self.paramSelector.y1_group.is_active():
            if self.curent_y_first_parameters:
                self.curent_y_first_parameters = []
                changed = True
        if not self.paramSelector.y2_group.is_active():
            if self.curent_y_second_parameters:
                self.curent_y_second_parameters = []
                changed = True

        # 2. Кросс-осевое пересечение (страховка)
        y1_set = set(self.curent_y_first_parameters)
        y2_set = set(self.curent_y_second_parameters)
        overlap = y1_set & y2_set
        if overlap:
            self.curent_y_second_parameters = [
                p for p in self.curent_y_second_parameters if p not in overlap
            ]
            changed = True

        # 3. Единичный режим
        if not self.paramSelector.y1_group.is_multiple():
            if len(self.curent_y_first_parameters) > 1:
                self.curent_y_first_parameters = self.curent_y_first_parameters[-1:]
                changed = True
        if not self.paramSelector.y2_group.is_multiple():
            if len(self.curent_y_second_parameters) > 1:
                self.curent_y_second_parameters = self.curent_y_second_parameters[-1:]
                changed = True

        return changed

    def _sync_view_from_model(self):
        ps = self.paramSelector

        # X combo
        ps.x_combo.blockSignals(True)
        try:
            idx = 0
            if self.curent_x_parameter:
                found = ps.x_combo.findData(self.curent_x_parameter)
                if found >= 0:
                    idx = found
            ps.x_combo.setCurrentIndex(idx)
        finally:
            ps.x_combo.blockSignals(False)

        # Кросс-блокировка
        y1_set = set(self.curent_y_first_parameters)
        y2_set = set(self.curent_y_second_parameters)
        ps.y1_group.set_blocked(
            y2_set, _TR("Уже выбрано на правой оси")
        )
        ps.y2_group.set_blocked(
            y1_set, _TR("Уже выбрано на левой оси")
        )

        # Отметки
        ps.y1_group.set_selected(self.curent_y_first_parameters, is_signal=False)
        ps.y2_group.set_selected(self.curent_y_second_parameters, is_signal=False)

        # Активация
        if ps.y1_group.is_active() != bool(self.curent_y_first_parameters or True):
            # Y1 по умолчанию активен — не трогаем UI без нужды
            pass
        if ps.y2_group.is_active() != bool(self.curent_y_second_parameters):
            # Y2 активируется пользователем явно; состояние сохраняем
            pass

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