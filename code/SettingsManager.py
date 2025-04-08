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
from PyQt5 import QtCore
from PyQt5.QtWidgets import (QApplication, QCheckBox,
                            QSpinBox, QComboBox,
                            QFileDialog, 
                            QDoubleSpinBox, QLineEdit,
                            QHBoxLayout, QVBoxLayout,
                            QDialog, QDialogButtonBox,
                            QSizePolicy, QPushButton, QLabel)

import enum


class type_save_file(enum.Enum):
    txt = 1
    excel = 2
    origin = 3

class SettingsManager():
    def __init__(self,settings: QtCore.QSettings, VERSION_APP: str, def_persistent_sett: dict=None, def_cache_sett: dict=None):
        self.persistent_settings = settings

        self.cache_settings = {}
        self.load_all_settings()

        if def_persistent_sett is not None:
            for key, value in def_persistent_sett.items():
                if not self.persistent_settings.contains(key):
                    self.save_settings({key: value})

        if def_cache_sett is not None:
            for key, value in def_cache_sett.items():
                self.cache_settings[key] = value

        self.experiment_settings = ExperimentSettings( self.cache_settings )

        all_set, persistent_set = self.experiment_settings.get_settings()
        self.save_settings(persistent_set)
        self.set_settings(all_set)

    def save_settings(self, data: dict):
        """
        Saves settings to cache and persistent storage.

        Args:
            data (dict): Dictionary with keys and values to be saved.
        """
        for key, value in data.items():
            self.cache_settings[key] = value
            self.persistent_settings.setValue(key, value)
            self.experiment_settings.set_settings(data)

    def set_settings(self, data: dict):
        """
        Sets settings to cache.

        Args:
            data (dict): Dictionary with keys and values to be set.
        """
        for key, value in data.items():
            self.cache_settings[key] = value
            self.experiment_settings.set_settings(data)

    def load_settings(self, keys: list | str) -> dict:
        """
        Loads settings from persistent storage and cache.

        Args:
            keys (list | str): Keys or a single key to load from settings.

        Returns:
            dict: Dictionary with loaded values.
        """
        data = {}

        if isinstance(keys, str):
            keys = [keys]

        for key in keys:
            val = self.format_settings( self.persistent_settings.value(key) )
            data[key] = val
            self.cache_settings[key] = val
        return data
    
    def get_settings(self, keys: list | str) -> dict:
        data = {}

        if isinstance(keys, str):
            keys = [keys]

        for key in keys:
            val = self.cache_settings.get(key, None)
            data[key] = val

        return data
    
    def get_setting(self, key: str) -> tuple:
        """
        Checks if a setting exists and returns its value if it does.

        Args:
            key (str): Key to check and retrieve.

        Returns:
            tuple: A tuple containing a boolean indicating if the setting exists and its value if it does.
        """
        if self.cache_settings.get(key, None):

            return True, self.cache_settings.get(key, None)
        return False, None
    
    def ask_exp_settings(self):
        all_set, persistent_set = self.experiment_settings.show()
        self.save_settings(persistent_set)
        self.set_settings(all_set)
        return all_set
    
    def load_all_settings(self) -> dict:
        keys = self.persistent_settings.allKeys()
        self.load_settings(keys)
    
    def format_settings(self, value):

        if isinstance(value, str ):
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            else:
                try:
                    value = float(value)
                except:
                    pass
        return value

class ConfigDialog(QDialog):
    def __init__(self, configs, parent=None):
        super().__init__(parent)
        self.configs = configs
        self.widget_layouts = {
            QCheckBox: [],
            QSpinBox: [],
            QComboBox: [],
            QLineEdit: []
        }
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.create_widgets()
        self.setWindowTitle(QApplication.translate( "message_win", "Настройки эксперимента" ))
        
        for widget_type in [QCheckBox, QSpinBox, QComboBox, QLineEdit]:
            for layout in self.widget_layouts[widget_type]:
                main_layout.addLayout(layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        main_layout.addStretch()

    def create_widgets(self):
        for config in self.configs:
            widget_class = config['widget']
            attr = config['attr']
            name = config['name']
            tooltip = config['tooltip']
            default = config['default']
            callback = config['callback']

            widget = widget_class()
            widget.setToolTip(tooltip)
            setattr(self, attr, widget)

            config['setter'](widget,default)

            if widget_class == QCheckBox:
                self.create_checkbox_layout(widget, name, callback)
            elif widget_class == QSpinBox:
                self.create_spinbox_layout(widget, name, callback)
            elif widget_class == QComboBox:
                self.create_combobox_layout(widget, name, callback)
            elif widget_class == QLineEdit:
                self.create_lineedit_layout(widget, name, callback)

    def create_checkbox_layout(self, widget, name, callback):
        widget.setText(name)
        layout = QHBoxLayout()
        layout.addWidget(widget)
        self.widget_layouts[QCheckBox].append(layout)

    def create_spinbox_layout(self, widget, name, callback):
        layout = QHBoxLayout()
        layout.addWidget(widget)
        layout.addWidget(QLabel(name))
        layout.addStretch()
        self.widget_layouts[QSpinBox].append(layout)

    def create_combobox_layout(self, widget, name, callback):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(name))
        layout.addWidget(widget)
        self.widget_layouts[QComboBox].append(layout)

    def create_lineedit_layout(self, widget, name, callback):
        v_layout = QVBoxLayout()
        v_layout.addWidget(QLabel(name))
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(widget, 5)
        
        button = QPushButton("...")
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if callback is not None:
            button.clicked.connect(callback)

        h_layout.addWidget(button, 1)
        
        v_layout.addLayout(h_layout)
        self.widget_layouts[QLineEdit].append(v_layout)

    def get_values(self) -> tuple:
        values_persistent = {}
        values = {}
        for config in self.configs:
            attr = config['attr']
            getter = config['getter']
            is_persistent = config['is_persistent']
            widget = getattr(self, attr)
            values[attr] = getter(widget)
            if is_persistent:
                values_persistent[attr] = values[attr]

        return (values, values_persistent)

class ExperimentSettings:
    def __init__(self, downloaded_settings: dict):
        self.persistent_settings = [
            {
                'attr': 'is_exp_run_anywhere',
                'name': QApplication.translate('exp_settings',"Продолжать эксперимент при ошибке опроса прибора"),
                'tooltip': QApplication.translate('exp_settings',"При активации этого пункта в случае ошибки опроса прибора эксперимент продолжается"),
                'widget': QCheckBox,
                'default': downloaded_settings.get('is_exp_run_anywhere', False)
            },
            {
                'attr': 'is_delete_buf_file',
                'name': QApplication.translate('exp_settings',"Удалить буфферный файл после завершения эксперимента"),
                'tooltip': QApplication.translate('exp_settings',"При активации этого пункта в случае успешного сохранения данных буферный файл будет перемещен в корзину"),
                'widget': QCheckBox,
                'default': downloaded_settings.get('is_delete_buf_file', False)
            },
            {
                'attr': 'should_prompt_for_session_name',
                'name': QApplication.translate('exp_settings',"Запрашивать имя и описание сессии измерений после окончания эксперимента"),
                'tooltip': QApplication.translate('exp_settings',"При активации этого пункта после завершения эксперимента программа всегда будет запрашивать имя измерений и описание"),
                'widget': QCheckBox,
                'default': downloaded_settings.get('should_prompt_for_session_name', True)
            }
        ]
        
        self.default_settings = [
            {
                'attr': 'way_to_save',
                'name': QApplication.translate('exp_settings',"Путь сохранения результатов"),
                'tooltip': QApplication.translate('exp_settings',""),
                'widget': QLineEdit,
                'default': None,
                'callback': self.set_way_save
            },
            {
                'attr': 'repeat_exp',
                'name': QApplication.translate('exp_settings',"Количество повторов эксперимента"),
                'tooltip': QApplication.translate('exp_settings',"Процедура эксперимента будет повторяться указанное количество раз"),
                'widget': QSpinBox,
                'default': 1
            },
            {
                'attr': 'repeat_meas',
                'name': QApplication.translate('exp_settings',"Количество измерений в точке"),
                'tooltip': QApplication.translate('exp_settings',"Выберите количество измерений в точке, измерения будут происходить без остановки заданное количество раз"),
                'widget': QSpinBox,
                'default': 1
            }
        ]
        
        self.add_type_key(self.persistent_settings, is_persistent=True)
        self.add_type_key(self.default_settings, is_persistent=False)
        self.__settings_config = self.setup_widget_config(self.persistent_settings + self.default_settings)

        self.window = ConfigDialog(self.__settings_config)

        self.values, self.values_persistent = self.window.get_values()

        self.type_file = None
    def set_settings(self, settings):
        for key, value in settings.items():
            if self.values.get(key) is not None:
                self.values[key] = value
                widget = getattr(self.window, key)
                setter = self.search_config(key)['setter']
                setter(widget, value)

            if self.values_persistent.get(key) is not None:
                self.values_persistent[key] = value
                widget = getattr(self.window, key)
                setter = self.search_config(key)['setter']
                setter(widget, value)

    def add_type_key(self, configs, is_persistent):
        for config in configs:
            config['is_persistent'] = is_persistent

    def search_config(self, filt_value):
        """
        Search for config in self.__settings_config where value equal filt_value.

        Parameters
        ----------
        filt_value : Any
            Value to search.

        Returns
        -------
        dict or None
            Config if found, None otherwise.
        """
        for config in self.__settings_config:
            for value in config.values():
                if value == filt_value:
                    return config
        return None

    def show(self) -> dict:
        if self.window.exec_():
            self.values, self.values_persistent = self.window.get_values()

        return self.values, self.values_persistent
    
    def get_settings(self):
        self.values, self.values_persistent = self.window.get_values()
        return self.values, self.values_persistent
    
    def set_way_save(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filters = "Книга Excel (*.xlsx);;Text Files(*.txt);;Origin (*.opju)"
        
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self.window,
            QApplication.translate('set exp window', "Укажите путь сохранения"),
            "",
            filters,
            options=options
        )

        if file_name:
            ext_map = {
                "Excel": (".xlsx", type_save_file.excel),
                "Text": (".txt", type_save_file.txt),
                "Origin": (".opju", type_save_file.origin)
            }
            
            for key, (ext, file_type) in ext_map.items():
                if key in selected_filter:
                    if not file_name.endswith(ext):
                        file_name += ext
                    self.type_file = file_type
                    break

            config = self.search_config(self.set_way_save)

            focus_widget =getattr(self.window, config['attr'])

            config['setter'](focus_widget, file_name)

    def setup_widget_config(self, configs):
        """Добавляет геттеры, сеттеры и сигналы в конфиг на основе типа виджета.
        
        Args:
            configs (list[dict]): Список словарей с настройками виджетов.
        """
        for config in configs:
            widget_type = config.get('widget')
            
            if not widget_type:
                continue

            config.setdefault('callback')
            
            if issubclass(widget_type, QCheckBox):
                config.setdefault('setter', lambda w, v: w.setChecked(bool(v)))
                config.setdefault('getter', lambda w: w.isChecked())
                config.setdefault('signal', 'stateChanged')
            
            elif issubclass(widget_type, QLineEdit):
                config.setdefault('setter', lambda w, v: w.setText(str(v) if v is not None else ""))
                config.setdefault('getter', lambda w: w.text())
                config.setdefault('signal', 'textChanged')
            
            elif issubclass(widget_type, QComboBox):
                config.setdefault('setter', lambda w, v: w.setCurrentText(str(v)))
                config.setdefault('getter', lambda w: w.currentText())
                config.setdefault('signal', 'currentIndexChanged')
            
            elif issubclass(widget_type, (QSpinBox, QDoubleSpinBox)):
                config.setdefault('setter', lambda w, v: w.setValue(v))
                config.setdefault('getter', lambda w: w.value())
                config.setdefault('signal', 'valueChanged')
            

        return configs

if __name__ == "__main__":
    Application = QApplication(sys.argv)
    VERSION_APP = "1.0.5"
    my_class = SettingsManager(VERSION_APP, def_persistent_sett=None, def_cache_sett={'test': 1, 'test2': 2, 'test3': 3})
    print(my_class.get_settings(['teste', 'test2', 'test3']))
    print(my_class.ask_exp_settings())



            