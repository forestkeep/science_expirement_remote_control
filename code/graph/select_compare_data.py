import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QCheckBox, QListWidget, QAbstractItemView, QScrollArea,
    QWidget, QDialogButtonBox
)
from PyQt5.QtCore import Qt
from typing import Dict, Any, List, Optional, Hashable

class MultiSelectionDialog(QDialog):
    """
    Диалог для выбора ключей (по ID) и связанных с ними строк.
    Пользователь видит отображаемые имена, но результат привязывается к ID.

    Аргументы:
        data (Dict[Hashable, Dict[str, Any]]): Словарь вида
            {id: {"name": "отображаемое имя", "values": ["строка1", "строка2", ...]}, ...}
        exclude_list (Optional[List[str]]): Список строк, которые следует исключить из результата.
        min_items (int): Минимальное количество элементов в списке ключа для включения в результат (по умолчанию 2).
        parent (Optional[QWidget]): Родительский виджет.

    Атрибуты:
        result_dict (Optional[Dict[Hashable, List[str]]]): Результирующий словарь {id: список_строк}.
    """

    def __init__(
        self,
        data: Dict[Hashable, Dict[str, Any]],
        exclude_list: Optional[List[str]] = None,
        min_items: int = 2,
        parent=None
    ):
        super().__init__(parent)
        self.data = data
        self.exclude_list = exclude_list if exclude_list is not None else []
        self.min_items = min_items
        self.result_dict = None
        self.groups = []  # список кортежей (id, checkbox, list_widget)
        self.setWindowTitle("Множественный выбор")
        self.setup_ui()

    def setup_ui(self):
        """Создание пользовательского интерфейса."""
        main_layout = QVBoxLayout(self)

        # Глобальный чекбокс "Выбрать все"
        self.global_checkbox = QCheckBox("Выбрать все")
        self.global_checkbox.stateChanged.connect(self.on_global_toggled)
        main_layout.addWidget(self.global_checkbox)

        # Прокручиваемая область для групп
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Создание групп для каждого ID
        for id_key, info in self.data.items():
            name = info.get("name", str(id_key))  # если name нет, используем id как строку
            values = info.get("values", [])

            group_layout = QHBoxLayout()

            # Чекбокс для ключа (отображается имя)
            cb = QCheckBox(name)
            cb.stateChanged.connect(self.on_key_checkbox_toggled)

            # Список для строк (множественный выбор)
            lw = QListWidget()
            lw.addItems(values)
            lw.setSelectionMode(QAbstractItemView.MultiSelection)
            lw.setMaximumHeight(100)

            group_layout.addWidget(cb)
            group_layout.addWidget(lw)
            scroll_layout.addLayout(group_layout)

            self.groups.append((id_key, cb, lw))

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # Кнопки OK и Cancel
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def on_global_toggled(self, state):
        """Обработчик изменения состояния глобального чекбокса."""
        self.global_checkbox.blockSignals(True)

        checked = (state == Qt.Checked)
        for _, cb, lw in self.groups:
            cb.setChecked(checked)
            if checked:
                lw.selectAll()
            else:
                lw.clearSelection()

        self.global_checkbox.blockSignals(False)

    def on_key_checkbox_toggled(self):
        """Обработчик изменения состояния чекбокса ключа."""
        all_checked = all(cb.isChecked() for _, cb, _ in self.groups)
        self.global_checkbox.blockSignals(True)
        self.global_checkbox.setChecked(all_checked)
        self.global_checkbox.blockSignals(False)

    def accept(self):
        """Сбор результата с применением фильтров."""
        raw_result = {}
        for id_key, cb, lw in self.groups:
            if cb.isChecked():
                selected = [item.text() for item in lw.selectedItems()]
                raw_result[id_key] = selected

        # Применяем фильтр исключений и проверку минимального количества
        filtered_result = {}
        for id_key, values in raw_result.items():
            # Исключаем строки, присутствующие в exclude_list
            filtered_values = [v for v in values if v not in self.exclude_list]
            # Оставляем только ключи, у которых после фильтрации не меньше min_items элементов
            if len(filtered_values) >= self.min_items:
                filtered_result[id_key] = filtered_values

        self.result_dict = filtered_result
        super().accept()

    def get_result(self) -> Optional[Dict[Hashable, List[str]]]:
        """Возвращает результат после закрытия диалога."""
        return self.result_dict


# Пример использования
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Исходные данные с уникальными ID
    data = {
        101: {"name": "Фрукты", "values": ["яблоко", "банан", "апельсин", "киви"]},
        102: {"name": "Овощи", "values": ["морковь", "картофель", "помидор", "огурец"]},
        103: {"name": "Ягоды", "values": ["клубника", "малина", "черника", "ежевика"]},
        # Пример повторяющегося имени (для демонстрации)
        104: {"name": "Фрукты", "values": ["груша", "персик", "слива"]}
    }

    # Список исключений (задаётся программистом)
    exclude = []

    dialog = MultiSelectionDialog(data, exclude_list=exclude, min_items=2)
    if dialog.exec_() == QDialog.Accepted:
        result = dialog.get_result()
        print("Выбранные данные после фильтрации (ключи - ID):")
        for id_key, values in result.items():
            # Для наглядности выведем также имя
            name = data[id_key]["name"]
            print(f"{id_key} ({name}): {values}")
    else:
        print("Отмена")
