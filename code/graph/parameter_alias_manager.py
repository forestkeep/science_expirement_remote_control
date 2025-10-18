import re
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple
from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                            QTableWidgetItem, QPushButton, QHeaderView, QMessageBox,
                            QLineEdit, QLabel, QStyledItemDelegate)
import logging

logger = logging.getLogger(__name__)

class ParameterAliasManager(QObject):
    """Менеджер псевдонимов параметров"""
    
    aliases_updated = pyqtSignal( str, str, str )
    
    def __init__(self):
        super().__init__()
        self._original_to_alias: Dict[str, str] = {}  # оригинальное_имя -> псевдоним
        self._alias_to_original: Dict[str, str] = {}  # псевдоним -> оригинальное_имя
        self._validation_pattern = re.compile(r'^[A-Za-z0-9А-Яа-я ]+$')
    
    def set_alias(self, original_name: str, alias: str) -> Tuple[bool, str]:
        """Устанавливает псевдоним для параметра"""
        if not self._is_valid_alias(alias):
            return False, "Имя может содержать только буквы, цифры и пробелы"
        
        if alias in self._alias_to_original and self._alias_to_original[alias] != original_name:
            return False, "Это имя уже используется для другого параметра"
        
        # Удаляем старый псевдоним если был
        if original_name in self._original_to_alias:
            old_alias = self._original_to_alias[original_name]
            del self._alias_to_original[old_alias]
        else:
            old_alias = original_name
        
        self._original_to_alias[original_name] = alias
        self._alias_to_original[alias] = original_name
        
        self.aliases_updated.emit( original_name, old_alias, alias )
        return True, "Успешно"
    
    def add_param(self, original_name: str):
        if original_name in self._original_to_alias:
            return
        self._original_to_alias[original_name] = original_name
        self._alias_to_original[original_name] = original_name
    
    def remove_alias(self, original_name: str):
        """Удаляет псевдоним параметра"""
        if original_name in self._original_to_alias:
            alias = self._original_to_alias[original_name]
            del self._original_to_alias[original_name]
            del self._alias_to_original[alias]
            self.aliases_updated.emit( original_name, alias, original_name  )
    
    def get_alias(self, original_name: str) -> str:
        """Возвращает псевдоним или оригинальное имя если псевдоним не задан"""
        return self._original_to_alias.get(original_name, original_name)
    
    def get_original_name(self, alias_or_original: str) -> str:
        """Возвращает оригинальное имя по псевдониму или оригинальному имени"""
        return self._alias_to_original.get(alias_or_original, alias_or_original)
    
    def get_all_aliases(self) -> Dict[str, str]:
        """Возвращает все псевдонимы"""
        return self._original_to_alias.copy()
    
    def get_original_names(self) -> List[str]:
        """Возвращает список оригинальных имен"""
        return list(self._original_to_alias.keys())
    
    def has_alias(self, original_name: str) -> bool:
        """Проверяет есть ли псевдоним у параметра"""
        return original_name in self._original_to_alias
    
    def _is_valid_alias(self, alias: str) -> bool:
        """Проверяет валидность псевдонима"""
        return bool(self._validation_pattern.match(alias)) and alias.strip() != ""

class AliasDelegate(QStyledItemDelegate):
    """Делегат для валидации ввода псевдонимов"""
    
    def __init__(self, alias_manager: ParameterAliasManager, parent=None):
        super().__init__(parent)
        self.dialog = parent
        self.alias_manager = alias_manager
    
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.textChanged.connect(lambda text: self.validate_text(editor, text))
        return editor
    
    def validate_text(self, editor, text):
        """Валидация текста на лету"""
        is_valid = self.alias_manager._is_valid_alias(text)
        
        # Дополнительные проверки, специфичные для UI
        if is_valid:
            # Проверка уникальности (если нужно)
            if not self.is_alias_unique(text):
                editor.setStyleSheet("border: 2px solid orange; ")
                self.show_tooltip(editor, "Предупреждение: такое имя уже существует")
            else:
                editor.setStyleSheet("border: 2px solid green;")
                self.hide_tooltip(editor)
        else:
            editor.setStyleSheet("border: 2px solid red;")
            self.show_tooltip(editor, "Ошибка: недопустимое имя")
    
    def is_alias_unique(self, alias: str) -> bool:
        """Проверяет уникальность псевдонима"""
        return self.dialog.check_available_name(alias)
    
    def show_tooltip(self, editor, message):
        """Показывает подсказку с ошибкой"""
        editor.setToolTip(message)
    
    def hide_tooltip(self, editor):
        """Скрывает подсказку"""
        editor.setToolTip("")

class ParameterAliasDialog(QDialog):
    """Диалоговое окно для управления псевдонимами параметров"""
    
    def __init__(self, alias_manager: ParameterAliasManager, parent=None):
        super().__init__(parent)
        self.alias_manager = alias_manager
        self.available_parameters = {}
        for key, data in alias_manager.get_all_aliases().items():
            if key == data:
                self.available_parameters[key] = ""
            else:
                self.available_parameters[key] = data
        self.setup_ui()
        self.load_parameters()
        
    def setup_ui(self):
        self.setWindowTitle("Управление псевдонимами параметров")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # Таблица параметров
        self.table = QTableWidget()
        self.table.setColumnCount(2)  # Убрали столбец "Действия"
        self.table.setHorizontalHeaderLabels(["Оригинальное имя", "Псевдоним"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        # Устанавливаем делегат для столбца псевдонимов
        self.table.setItemDelegateForColumn(1, AliasDelegate(self.alias_manager, self))
        
        layout.addWidget(self.table)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.save_all)
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_parameters(self):
        """Загружает параметры в таблицу"""
        self.table.setRowCount(0)
        for param, alias in self.available_parameters.items():
            self.add_table_row(param, alias)
    
    def add_table_row(self, original_name: str, alias: str):
        """Добавляет строку в таблицу"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        original_item = QTableWidgetItem(original_name)
        original_item.setFlags(original_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 0, original_item)
        alias_item = QTableWidgetItem(alias)
        self.table.setItem(row, 1, alias_item)
        
        # Функция добавления строки остается, но вызывается автоматически
        # при необходимости (например, при вводе в последнюю строку)
        self.setup_alias_validation(row)
    
    def setup_alias_validation(self, row: int):
        """Настраивает валидацию для ячейки псевдонима"""
        alias_item = self.table.item(row, 1)
        if alias_item:
            editor = QLineEdit()
            editor.setText(alias_item.text())
            self.validate_alias_cell(editor, alias_item.text())
    
    def validate_alias_cell(self, editor, text):
        """Валидация ячейки псевдонима"""
        if self.alias_manager._is_valid_alias(text):
            editor.setStyleSheet("border: 2px solid green;")
        else:
            editor.setStyleSheet("border: 2px solid red;")

    def check_available_name(self, name: str):
        '''Имя доступно в том случае, если оно больше не использовано нигде'''
        for row in range(self.table.rowCount()):
            alias_item = self.table.item(row, 1)
            text = alias_item.text().strip()
            if text == name:
                return False
        return True
    
    def add_parameter_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        alias_item = QTableWidgetItem("")
        self.table.setItem(row, 1, alias_item)
        
        self.setup_alias_validation(row)
    
    def save_all(self):
        """Сохраняет все изменения"""
        for row in range(self.table.rowCount()):
            original_item = self.table.item(row, 0)
            alias_item = self.table.item(row, 1)
            
            original_name = original_item.text().strip() if original_item else ""
            alias = alias_item.text().strip() if alias_item else ""
            
            if not original_name:
                continue
                
            if alias:
                success, message = self.alias_manager.set_alias(original_name, alias)
                if not success:
                    QMessageBox.warning(self, "Ошибка", 
                                      f"Ошибка для параметра '{original_name}': {message}")
            else:
                pass
                #self.alias_manager.remove_alias(original_name)
        
        self.accept()
