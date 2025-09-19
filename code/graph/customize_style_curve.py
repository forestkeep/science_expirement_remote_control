from PyQt5 import QtWidgets, QtCore, QtGui
#from graph.curve_data import LineStyle
from graph.line_styles import PRESETS_LINE
import pyqtgraph as pg
import numpy as np
import copy

class GraphCustomizer(QtWidgets.QDialog):
    def __init__(self, graph_item, parent=None):
        super().__init__(parent)
        self.graph_item = graph_item
        self.original_style = copy.deepcopy(self.graph_item.saved_style)
        self.current_style = None

        self.line_styles = {
            "Solid": QtCore.Qt.SolidLine,
            "Dash": QtCore.Qt.DashLine,
            "Dot": QtCore.Qt.DotLine,
            "DashDot": QtCore.Qt.DashDotLine
        }

        self.setup_ui()
        self.setWindowTitle("Graph Customizer")
        
    def apply_preset(self, preset_name):
        if preset_name in PRESETS_LINE:
            preset = PRESETS_LINE[preset_name]
            # Применяем параметры стиля из пресета
            self.current_style.color = preset['color']
            self.current_style.line_style = preset['line_style']
            self.current_style.line_width = preset['line_width']
            self.current_style.symbol = preset['symbol']
            self.current_style.symbol_size = preset['symbol_size']
            self.current_style.symbol_color = preset['symbol_color']
            self.current_style.fill_color = preset['fill_color']
            self.current_style.px_mode = preset.get('px_mode', True)  # Добавлено применение pxMode
            
            # Обновляем UI в соответствии с новым стилем
            self.update_ui_from_style()
            self.update_style()

    def update_ui_from_style(self):
        # Обновляем комбобокс стиля линии
        line_style_name = next(
            (name for name, style in self.line_styles.items() 
             if style == self.current_style.line_style),
            "Solid"
        )
        self.line_style.setCurrentText(line_style_name)
        
        # Обновляем другие элементы UI
        self.line_width.setValue(int(self.current_style.line_width))
        
        symbol_text = self.current_style.symbol if self.current_style.symbol else "None"
        index = self.symbol.findText(symbol_text)
        if index >= 0:
            self.symbol.setCurrentIndex(index)
            
        self.symbol_size.setValue(int(self.current_style.symbol_size))
        self.px_mode_checkbox.setChecked(self.current_style.px_mode)  # Добавлено обновление чекбокса
        
    def get_current_properties(self):
        """Получить текущие свойства графика"""
        opts = self.graph_item.plot_obj.opts
        
        # Обработка цвета линии
        if isinstance(opts['pen'], str):
            color = pg.mkColor(opts['pen'])
            line_style = QtCore.Qt.SolidLine
            line_width = 1
        elif hasattr(opts['pen'], 'color'):
            color = opts['pen'].color()
            line_style = opts['pen'].style()
            line_width = opts['pen'].width()
        else:
            color = pg.mkColor('w')
            line_style = QtCore.Qt.SolidLine
            line_width = 1
        
        # Обработка цвета символа
        if opts['symbolPen'] is None:
            symbol_color = pg.mkColor('w')
        elif isinstance(opts['symbolPen'], dict):
            symbol_color = pg.mkColor(opts['symbolPen'].get('color', 'w'))
        elif hasattr(opts['symbolPen'], 'color'):
            symbol_color = opts['symbolPen'].color()
        elif isinstance(opts['symbolPen'], (tuple, list, str)):
            symbol_color = pg.mkColor(opts['symbolPen'])
        else:
            symbol_color = pg.mkColor('w')
        
        # Обработка цвета заливки
        if opts['symbolBrush'] is None:
            fill_color = pg.mkColor('w')
        elif isinstance(opts['symbolBrush'], dict):
            fill_color = pg.mkColor(opts['symbolBrush'].get('color', 'w'))
        elif hasattr(opts['symbolBrush'], 'color'):
            fill_color = opts['symbolBrush'].color()
        elif isinstance(opts['symbolBrush'], (tuple, list, str)):
            fill_color = pg.mkColor(opts['symbolBrush'])
        else:
            fill_color = pg.mkColor('w')
        
        # Получаем значение pxMode
        px_mode = opts.get('pxMode', True)
        print(f"{px_mode=}")
        
        return {
            'color': color.name(),
            'line_style': line_style,
            'line_width': line_width,
            'symbol': opts['symbol'],
            'symbol_size': opts['symbolSize'],
            'symbol_color': symbol_color.name(),
            'fill_color': fill_color.name(),
            'px_mode': px_mode  # Добавлено получение pxMode
        }

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()

        # Добавляем выбор предустановленных стилей
        layout.addWidget(QtWidgets.QLabel("Предустановленные стили:"))
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItem("Выберите стиль")
        self.preset_combo.addItems(PRESETS_LINE.keys())
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        layout.addWidget(self.preset_combo)

        # Выбор цвета линии
        self.color_btn = QtWidgets.QPushButton("Цвет линии")
        self.color_btn.clicked.connect(self.choose_color)
        layout.addWidget(self.color_btn)

        # Стиль линии
        layout.addWidget(QtWidgets.QLabel("Стиль линии:"))
        self.line_style = QtWidgets.QComboBox()
        self.line_style.addItems(self.line_styles.keys())
        # Устанавливаем текущий стиль
        current_style = self.original_style.line_style
        if current_style == QtCore.Qt.SolidLine:
            self.line_style.setCurrentText("Solid")
        elif current_style == QtCore.Qt.DashLine:
            self.line_style.setCurrentText("Dash")
        elif current_style == QtCore.Qt.DotLine:
            self.line_style.setCurrentText("Dot")
        elif current_style == QtCore.Qt.DashDotLine:
            self.line_style.setCurrentText("DashDot")
        self.line_style.currentIndexChanged.connect(self.line_style_changed)
        layout.addWidget(self.line_style)

        # Толщина линии
        layout.addWidget(QtWidgets.QLabel("Толщина линии:"))
        self.line_width = QtWidgets.QSpinBox()
        self.line_width.setRange(1, 10)
        self.line_width.setValue(int(self.original_style.line_width))
        self.line_width.valueChanged.connect(self.line_width_changed)
        layout.addWidget(self.line_width)

        # Символ
        layout.addWidget(QtWidgets.QLabel("Маркер:"))
        self.symbol = QtWidgets.QComboBox()
        self.symbol.addItems([
                                        "None",     # Без символа
                                        "o",        # Круг
                                        "s",        # Квадрат
                                        "t",        # Треугольник (обычный)
                                        "t1",       # Треугольник направленный вверх
                                        "t2",       # Треугольник направленный вправо
                                        "t3",       # Треугольник направленный влево
                                        "d",        # Ромб
                                        "+",        # Плюс
                                        "x",        # Крест (x)
                                        "p",        # Пятиугольник
                                        "h",        # Шестиугольник
                                        "star",     # Звезда
                                        "|",        # Вертикальная линия
                                        "_",        # Горизонтальная линия
                                        "arrow_up",     # Стрелка вверх
                                        "arrow_right",  # Стрелка вправо
                                        "arrow_down",   # Стрелка вниз
                                        "arrow_left",   # Стрелка влево
                                        "crosshair"     # Перекрестие
                                    ])

        # Устанавливаем текущее значение
        current_symbol = self.original_style.symbol
        index = self.symbol.findText(current_symbol if current_symbol else "None")
        if index >= 0:
            self.symbol.setCurrentIndex(index)
        self.symbol.currentIndexChanged.connect(self.symbol_changed)
        layout.addWidget(self.symbol)

        # Размер символа
        layout.addWidget(QtWidgets.QLabel("Размер маркера:"))
        self.symbol_size = QtWidgets.QSpinBox()
        self.symbol_size.setRange(1, 20)
        self.symbol_size.setValue(int(self.original_style.symbol_size))
        self.symbol_size.valueChanged.connect(self.symbol_size_changed)
        layout.addWidget(self.symbol_size)

        # Чекбокс pxMode
        self.px_mode_checkbox = QtWidgets.QCheckBox("Режим пикселей (pxMode)")
        self.px_mode_checkbox.setChecked(self.original_style.px_mode)
        self.px_mode_checkbox.stateChanged.connect(self.px_mode_changed)
        layout.addWidget(self.px_mode_checkbox)

        # Цвет символа
        self.symbol_color_btn = QtWidgets.QPushButton("Цвет маркера")
        self.symbol_color_btn.clicked.connect(self.choose_symbol_color)
        layout.addWidget(self.symbol_color_btn)

        # Цвет заливки
        self.fill_color_btn = QtWidgets.QPushButton("Цвет заливки маркера")
        self.fill_color_btn.clicked.connect(self.choose_fill_color)
        layout.addWidget(self.fill_color_btn)

        # Кнопки принятия/отмены
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.setLayout(layout)
        
        # Инициализируем текущие цвета
        self.current_style = copy.deepcopy(self.original_style)

    def line_style_changed(self, index):
        self.current_style.line_style = self.line_styles[self.line_style.itemText(index)]
        self.update_style()

    def line_width_changed(self, value):
        self.current_style.line_width = value
        self.update_style()

    def symbol_changed(self, index):
        self.current_style.symbol = self.symbol.itemText(index)
        self.update_style()

    def symbol_size_changed(self):
        self.current_style.symbol_size = self.symbol_size.value()
        self.update_style()

    def px_mode_changed(self, state):
        self.current_style.px_mode = state == QtCore.Qt.Checked
        self.update_style()

    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.current_style.color))
        if color.isValid():
            self.current_style.color = color.name()
            self.update_style()

    def choose_symbol_color(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.current_style.symbol_color))
        if color.isValid():
            self.current_style.symbol_color = color.name()
            self.update_style()

    def choose_fill_color(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.current_style.fill_color))
        if color.isValid():
            self.current_style.fill_color = color.name()
            self.update_style()

    def update_style(self):
        # Обновляем стиль графика
        self.graph_item.change_style(self.current_style)

    def get_pen_style(self):
        styles = {
            "Solid": QtCore.Qt.SolidLine,
            "Dash": QtCore.Qt.DashLine,
            "Dot": QtCore.Qt.DotLine,
            "DashDot": QtCore.Qt.DashDotLine
        }
        return styles[self.line_style.currentText()]

    def accept(self):
        # Сохраняем изменения
        super().accept()

    def reject(self):
        # Восстанавливаем оригинальные свойства
        self.restore_original_properties()
        super().reject()

    def restore_original_properties(self):
        """Восстановить оригинальные свойства графика"""
        self.graph_item.change_style(self.original_style)