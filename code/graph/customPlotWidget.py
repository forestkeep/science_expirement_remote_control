import pyqtgraph as pg

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal
from dataclasses import dataclass
from pyqtgraph import AxisItem
from graph.custom_inf_line import RemovableInfiniteLine

@dataclass
class axisStyle:
    text_font: QtGui.QFont
    tick_font: QtGui.QFont
    color: str

@dataclass
class axisSettings:
    name_axis: str
    label: str
    is_style_customized: bool
    is_inverted: bool
    is_visible: bool


class axisController():
    def __init__(self, axis_object: AxisItem, axis_settings: axisSettings, axis_style: axisStyle):
        self.axis = axis_object
        self.settings = axis_settings
        self.common_style = axis_style
        self.custom_style = axisStyle(text_font=QtGui.QFont("Arial", 13),tick_font=QtGui.QFont("Arial", 10), color=(255, 255, 255))
        self.__apply_style()

    def __getattr__(self, name):
        return getattr(self.axis, name)

    def set_custom_style(self, style: axisStyle ):
        self.custom_style = style
        self.settings.is_style_customized = True
        self.__apply_style()

    def set_common_style(self, style: axisStyle ):
        self.common_style = style
        self.settings.is_style_customized = False
        self.__apply_style()

    def update_common_style(self, style: axisStyle ):
        self.common_style = style

    def __apply_style(self):
        if self.settings.is_style_customized:
            style = self.custom_style
        else:
            style = self.common_style
        self.setLabel(self.settings.label)
        self.setTextPen(style.color)
        self.label.setFont(style.text_font)
        self.setTickFont(style.tick_font)

    def reset_style(self):
        self.settings.is_style_customized = False
        self.__apply_style()
    
class PatchedPlotWidget(pg.PlotWidget):
    new_curve_selected = pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupCustomMenu()
        
        self.is_second_axis = False

        self.inf_lines = []

        self.legend = pg.LegendItem(size=(80, 60), offset=(10, 10))
        self.legend2 = pg.LegendItem(size=(80, 60), offset=(50, 10))
        self.tooltip = pg.TextItem("X:0,Y:0", color=(255, 255, 255), anchor=(0,0))
        
        self.setAntialiasing(False)
        self.scene().sigMouseMoved.connect(self.showToolTip)

        self.is_grid_shown = False
        self.legend_color = QtGui.QColor(255, 255, 255)

        self.background_color = QtGui.QColor(255, 255, 255)
        
        self.plots_lay = self.plotItem
        self.second_graphView = pg.ViewBox(
            border=None,
            lockAspect=False,
            enableMouse=False,
            invertY=False,
            enableMenu=False,
            invertX=False,
            defaultPadding=0.05
        )

        self.common_style = axisStyle(text_font=QtGui.QFont("Arial", 13),tick_font=QtGui.QFont("Arial", 10), color=(255, 255, 255))
        self.axises = {}
        self.axises["left"] = axisController(self.plots_lay.getAxis("left"),
                                              axisSettings(name_axis="left",label = "Y", is_style_customized=False, is_inverted=False, is_visible=True),
                                              self.common_style)
        
        self.axises["bottom"] = axisController(axis_object=self.plots_lay.getAxis("bottom"),
                                               axis_settings=axisSettings(name_axis="bottom",label = "X", is_style_customized=False, is_inverted=False, is_visible=True),
                                               axis_style=self.common_style)

        self.axises["right"] = axisController(self.plots_lay.getAxis("right"),
                                              axisSettings(name_axis="right",label = "Y2", is_style_customized=False, is_inverted=False, is_visible=True),
                                              self.common_style)
        
        self.plots_lay.showAxis("right")
        self.plots_lay.scene().addItem(self.second_graphView)
        self.plots_lay.getAxis("right").linkToView(self.second_graphView)
        self.second_graphView.setXLink(self.plots_lay)
        self.plots_lay.vb.sigResized.connect(self.updateViews)
        
        self.legend.setParentItem(self.plots_lay)
        self.legend2.setParentItem(self.second_graphView)
        self.tooltip.setParentItem(self.plots_lay)
        
        self.set_second_axis(False)


        view_rect = self.plots_lay.vb.viewRect()
            
        # Устанавливаем позицию тултипа в правый верхний угол
        # с небольшим отступом от краев
        tooltip_x = view_rect.right()# - (view_rect.width() * 0.02)  # 2% отступа от правого края
        tooltip_y = view_rect.top()# + (view_rect.height() * 0.02)   # 2% отступа от верхнего края

        print(f"{tooltip_x}, {tooltip_x}")
        
        #self.tooltip.setPos(50, 50)

    def add_inf_line(self, line):
        self.inf_lines.append(line)
        self.addItem(line)

    def remove_inf_line(self, line):
        self.removeItem(line)
        self.inf_lines.remove(line)

    def updateViews(self):
        """Обновление вьюшек при изменении размера"""
        self.second_graphView.setGeometry(self.plots_lay.vb.sceneBoundingRect())
        self.second_graphView.linkedViewChanged(self.plots_lay.vb, self.second_graphView.XAxis)

    def showToolTip(self, pos):
        """Обновленный метод для отображения тултипа в правом верхнем углу"""
        if self.plots_lay.vb.sceneBoundingRect().contains(pos):
            mouse_point = self.plots_lay.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()
            
            # Обновляем текст тултипа
            self.tooltip.setText(f"X: {x:.2f}, Y: {y:.2f}")
            
            '''
            # Получаем границы ViewBox
            view_rect = self.plots_lay.vb.viewRect()
            
            # Устанавливаем позицию тултипа в правый верхний угол
            # с небольшим отступом от краев
            tooltip_x = view_rect.right() - (view_rect.width() * 0.02)  # 2% отступа от правого края
            tooltip_y = view_rect.top() + (view_rect.height() * 0.02)   # 2% отступа от верхнего края
            
            self.tooltip.setPos(tooltip_x, tooltip_y)
            '''

    def set_second_axis(self, state: bool):
        """Включение/выключение второй оси"""
        self.is_second_axis = state
        if not state:
            self.axises["right"].hide()
        else:
            self.axises["right"].show()

    def create_axis_menu(self, axis_name, axis_key, invert_method, reset_method):
        menu = QtWidgets.QMenu(axis_name, self.plotItem.vb.menu)
        
        # Сброс стиля
        reset_action = QtWidgets.QAction("Сброс стиля", menu)
        reset_action.triggered.connect(reset_method)
        menu.addAction(reset_action)
        
        # Меню кастомизации
        style_menu = QtWidgets.QMenu("Кастомизация стиля", menu)
        menu.addMenu(style_menu)
        
        # Меню выбора цвета
        color_menu = QtWidgets.QMenu("Цвет подписей", style_menu)
        style_menu.addMenu(color_menu)
        
        # Стандартные цвета
        colors = {
            "Черный": (0, 0, 0),
            "Белый": (255, 255, 255),
            "Красный": (255, 0, 0),
            "Зеленый": (0, 255, 0),
            "Синий": (0, 0, 255),
            "Выбрать свой...": None
        }
        
        for name, color in colors.items():
            action = QtWidgets.QAction(name, color_menu)
            if name == "Выбрать свой...":
                action.triggered.connect(
                    lambda: self.choose_custom_axis_color(axis_key))
            else:
                action.triggered.connect(
                    lambda checked, c=color, k=axis_key: self.set_axis_color(c, k))
            color_menu.addAction(action)
        

        #шрифт
        font_menu = QtWidgets.QMenu("Шрифт", style_menu)
        style_menu.addMenu(font_menu)

        choise_tick_font = QtWidgets.QAction(text="Делений", parent=font_menu)
        choise_tick_font.triggered.connect(lambda: self.customize_axis_tick_font(axis_key))
        choise_text_font = QtWidgets.QAction(text="Названий осей", parent=font_menu)
        choise_text_font.triggered.connect(lambda: self.customize_axis_font(axis_key))
        font_menu.addAction(choise_tick_font)
        font_menu.addAction(choise_text_font)
        
        # Инвертирование
        invert_action = QtWidgets.QAction("Invert", menu)
        invert_action.setCheckable(True)
        invert_action.setChecked(False)
        invert_action.triggered.connect(invert_method)
        menu.addAction(invert_action)
        
        return menu

    def setupCustomMenu(self):
        viewbox_menu = self.plotItem.vb.menu
        for action in viewbox_menu.actions():
            if action.menu():
                action.setParent(None)

        self.x_axis_menu = self.create_axis_menu(
            "X-axis", "x", self.invert_x_axis, self.reset_x_axis_style)
        self.y1_axis_menu = self.create_axis_menu(
            "Y1-axis", "y1", self.invert_y_axis, self.reset_y1_axis_style)
        self.y2_axis_menu = self.create_axis_menu(
            "Y2-axis", "y2", self.invert_y2_axis, self.reset_y2_axis_style)

        viewbox_menu.addMenu(self.x_axis_menu)
        viewbox_menu.addMenu(self.y1_axis_menu)
        viewbox_menu.addMenu(self.y2_axis_menu)

        self.grid_action = None
        for action in self.plotItem.ctrlMenu.actions():
            if action.text() == "Grid":
                self.grid_action = action
                self.plotItem.ctrlMenu.removeAction(action)
                break

        viewbox_menu.addSeparator()
        
        # Меню внешнего вида
        appearance_menu = QtWidgets.QMenu("Внешний вид графика", viewbox_menu)
        viewbox_menu.addMenu(appearance_menu)
        
        if self.grid_action is None:
            self.grid_action = QtWidgets.QAction("Показать сетку", appearance_menu)
            self.grid_action.setCheckable(True)
            self.grid_action.setChecked(False)
            self.grid_action.triggered.connect(self.toggleGrid)

        appearance_menu.addAction(self.grid_action)
        appearance_menu.addSeparator()
        #шрифт
        font_menu = QtWidgets.QMenu("Шрифт", appearance_menu)
        appearance_menu.addMenu(font_menu)

        choise_tick_font = QtWidgets.QAction(text="Делений", parent=font_menu)
        choise_tick_font.triggered.connect(self.customize_axes_tick_font)
        choise_text_font = QtWidgets.QAction(text="Названий осей", parent=font_menu)
        choise_text_font.triggered.connect(self.customize_axes_font)
        font_menu.addAction(choise_tick_font)
        font_menu.addAction(choise_text_font)
        
        # Цвет фона
        bg_color_menu = QtWidgets.QMenu("Цвет фона", appearance_menu)
        appearance_menu.addMenu(bg_color_menu)
        
        colors = {
            "Черный": (0, 0, 0),
            "Белый": (255, 255, 255),
            "Красный": (255, 0, 0),
            "Синий": (0, 0, 255),
            "Зеленый": (0, 255, 0),
            "Выбрать свой...": None
        }
        
        for name, color in colors.items():
            action = QtWidgets.QAction(name, bg_color_menu)
            if name == "Выбрать свой...":
                action.triggered.connect(self.chooseCustomBackgroundColor)
            else:
                action.triggered.connect(
                    lambda checked, c=color: self.setCustomBackgroundColor(c))
            bg_color_menu.addAction(action)
        
        # Цвет сетки
        grid_color_menu = QtWidgets.QMenu("Цвет сетки", appearance_menu)
        appearance_menu.addMenu(grid_color_menu)
        
        for name, color in colors.items():
            action = QtWidgets.QAction(name, grid_color_menu)
            if name == "Выбрать свой...":
                action.triggered.connect(self.chooseCustomGridColor)
            else:
                action.triggered.connect(
                    lambda checked, c=color: self.setGridColor(c))
            grid_color_menu.addAction(action)
        
        # Цвет текста
        text_color_menu = QtWidgets.QMenu("Цвет текста", appearance_menu)
        appearance_menu.addMenu(text_color_menu)
        
        # Заголовок
        '''
        title_color_menu = QtWidgets.QMenu("Заголовок", text_color_menu)
        text_color_menu.addMenu(title_color_menu)
        
        for name, color in colors.items():
            action = QtWidgets.QAction(name, title_color_menu)
            if name == "Выбрать свой...":
                action.triggered.connect(
                    lambda: self.chooseCustomTextColor())
            else:
                action.triggered.connect(
                    lambda checked, c=color: self.set_axes_color(c))
            title_color_menu.addAction(action)
        '''
        
        # Подписи осей
        axis_label_color_menu = QtWidgets.QMenu("Подписи осей", text_color_menu)
        text_color_menu.addMenu(axis_label_color_menu)
        
        for name, color in colors.items():
            action = QtWidgets.QAction(name, axis_label_color_menu)
            if name == "Выбрать свой...":
                action.triggered.connect(
                    lambda: self.chooseCustomTextColor())
            else:
                action.triggered.connect(
                    lambda checked, c=color: self.set_axes_color(c))
            axis_label_color_menu.addAction(action)
        
        # Названия кривых
        '''
        curve_name_color_menu = QtWidgets.QMenu("Названия кривых", text_color_menu)
        text_color_menu.addMenu(curve_name_color_menu)
        
        for name, color in colors.items():
            action = QtWidgets.QAction(name, curve_name_color_menu)
            if name == "Выбрать свой...":
                action.triggered.connect(
                    lambda: self.chooseCustomTextColor())
            else:
                action.triggered.connect(
                    lambda checked, c=color: self.set_axes_color(c))
            curve_name_color_menu.addAction(action)
        '''

        # Легенда
        legend_color_menu = QtWidgets.QMenu("Легенда", text_color_menu)
        text_color_menu.addMenu(legend_color_menu)
        
        for name, color in colors.items():
            action = QtWidgets.QAction(name, legend_color_menu)
            if name == "Выбрать свой...":
                action.triggered.connect(
                    lambda: self.chooseCustomLegendColor())
            else:
                action.triggered.connect(
                    lambda checked, c=color: self.set_legend_color(c))
            legend_color_menu.addAction(action)
        
        antialias_action = QtWidgets.QAction("Включить антиалиасинг", appearance_menu)
        antialias_action.setCheckable(True)
        antialias_action.setChecked(False)
        antialias_action.triggered.connect(self.toggleAntialias)
        appearance_menu.addAction(antialias_action)

    def chooseCustomLegendColor(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.set_legend_color(color)

    def set_legend_color(self, color):
        if isinstance(color, tuple):
            color = QtGui.QColor(*color)
            
        self.legend_color = color

        for legend in (self.legend, self.legend2):
            for item in legend.items:
                text = item[1].text
                item[1].setText(text = text, color = color)
        
        self.legend.setLabelTextColor(color)
        self.legend2.setLabelTextColor(color)

    def set_axis_color(self, color, axis_key):
        if isinstance(color, tuple):
            color = QtGui.QColor(*color)
        axis_map = {'x': 'bottom', 'y1': 'left', 'y2': 'right'}
        axis = self.axises[axis_map[axis_key]]
        axis.custom_style.color = color
        axis.setTextPen(color)
        if hasattr(axis, 'style') and 'tickText' in axis.style:
            axis.style['tickText'] = (color, axis.style['tickText'][1])

    def choose_custom_axis_color(self, axis_key):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.set_axis_color(color, axis_key)

    def customize_axis_font(self, axis_key):
        """Установка шрифта для оси"""
        
        # Получаем текущий шрифт оси
        axis_map = {'x': 'bottom', 'y1': 'left', 'y2': 'right'}
        axis = self.axises[axis_map[axis_key]]
        
        current_font = QtGui.QFont()
        if hasattr(axis, 'tickFont') and axis.tickFont():
            current_font = axis.tickFont()
        elif hasattr(axis, 'style') and 'tickText' in axis.style:
            current_font = axis.style['tickText'][1]
        
        # Открываем диалог выбора шрифта
        font, ok = QtWidgets.QFontDialog.getFont(current_font, self, "Выберите шрифт")
        if ok:
            axis.custom_style.text_font = font
            axis.set_custom_style( axis.custom_style )

    def customize_axis_tick_font(self, axis_key):
        """Установка шрифта для оси"""
        
        # Получаем текущий шрифт оси
        axis_map = {'x': 'bottom', 'y1': 'left', 'y2': 'right'}
        axis = self.axises[axis_map[axis_key]]
        
        current_font = QtGui.QFont()
        if hasattr(axis, 'tickFont') and axis.tickFont():
            current_font = axis.tickFont()
        elif hasattr(axis, 'style') and 'tickText' in axis.style:
            current_font = axis.style['tickText'][1]
        
        # Открываем диалог выбора шрифта
        font, ok = QtWidgets.QFontDialog.getFont(current_font, self, "Выберите шрифт")
        if ok:
            axis.custom_style.tick_font = font
            axis.set_custom_style( axis.custom_style )

    def customize_axes_font(self):

        font, ok = QtWidgets.QFontDialog.getFont(self.common_style.text_font, self, "Выберите шрифт")
        if ok:
            self.common_style.text_font = font
            for axis in self.axises.values():
                if not axis.settings.is_style_customized:#если ось не была кастомизирована инживидуально. то применяем общие настройки
                    axis.set_common_style( self.common_style )
                else:
                    axis.update_common_style(self.common_style)

    def customize_axes_tick_font(self):

        font, ok = QtWidgets.QFontDialog.getFont(self.common_style.text_font, self, "Выберите шрифт")
        if ok:
            self.common_style.tick_font = font
            for axis in self.axises.values():
                if not axis.settings.is_style_customized:#если ось не была кастомизирована инживидуально. то применяем общие настройки
                    axis.set_common_style( self.common_style )
                else:
                    axis.update_common_style(self.common_style)

    def reset_x_axis_style(self):
        self.axises["bottom"].reset_style()

    def reset_y1_axis_style(self):
        self.axises["left"].reset_style()

    def reset_y2_axis_style(self):
        self.axises["right"].reset_style()

    def customize_x_axis_font(self):
        self.customize_axis_font('x')

    def customize_y1_axis_font(self):
        self.customize_axis_font('y1')

    def customize_y2_axis_font(self):
        self.customize_axis_font('y2')
        
    def invert_x_axis(self, checked):
        self.plotItem.vb.invertX(checked)
        if hasattr(self, 'second_graphView'):
            self.second_graphView.invertX(checked)
        self.axises["bottom"].settings.is_inverted = checked

    def invert_y_axis(self, checked):
        self.plotItem.vb.invertY(checked)
        self.axises["left"].settings.is_inverted = checked

    def invert_y2_axis(self, checked):
        if hasattr(self, 'second_graphView'):
            self.second_graphView.invertY(checked)
        self.axises["right"].settings.is_inverted = checked

    def hide_second_line_grid(self):
        self.axises["right"].setGrid(0)
    
    def toggleGrid(self, checked):
        self.is_grid_shown = checked
        self.plotItem.showGrid(x=checked, y=checked)
        self.hide_second_line_grid()
    
    def setCustomBackgroundColor(self, color):
        if isinstance(color, tuple):
            color = QtGui.QColor(*color)
        self.setBackground(color)
        tooltip_color = self.get_max_contrast_color(color)
        self.tooltip.setColor(tooltip_color)

        self.background_color = color

        for line in self.inf_lines:
            line.setPen(tooltip_color)
            line.label.setColor(tooltip_color)
    
    def chooseCustomBackgroundColor(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.setCustomBackgroundColor(color)
    
    def setGridColor(self, color):
        if isinstance(color, tuple):
            color = QtGui.QColor(*color)
        plot_item = self.plotItem
        if hasattr(plot_item, 'showGrid'):
            plot_item.getAxis('bottom').setPen(color)
            plot_item.getAxis('left').setPen(color)
            
    def chooseCustomGridColor(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.setGridColor(color)
    
    def set_axes_color(self, color):
        if isinstance(color, tuple):
            color = QtGui.QColor(*color)
        
        plot_item = self.plotItem
        self.common_style.color = color
        
        for axis_name in ['bottom', 'left', 'right', 'top']:
            axis = plot_item.getAxis(axis_name)
            axis.update_common_style(self.common_style)
            if axis:
                axis.setTextPen(color)
                if hasattr(axis, 'style') and 'tickText' in axis.style:
                    axis.style['tickText'] = (color, axis.style['tickText'][1])
        
    def chooseCustomTextColor(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.common_style.color = color
            self.set_axes_color(color)
    
    def toggleAntialias(self, checked):
        for item in self.plotItem.items:
            if isinstance(item, pg.PlotCurveItem):
                item.setAntialiased(checked)
    
    def autoRangeEnabled(self):
        return self.plotItem.getViewBox().autoRangeEnabled()
    
    def get_max_contrast_color(self, color: QtGui.QColor) -> QtGui.QColor:
        r = color.red() / 255.0
        g = color.green() / 255.0
        b = color.blue() / 255.0
        
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

        return QtGui.QColor(0, 0, 0) if luminance > 0.179 else QtGui.QColor(255, 255, 255)
    
    def add_vertical_line(self):
        """Добавляет вертикальную линию в центр видимой области"""
        view_range = self.plotItem.viewRange()
        x_center = (view_range[0][0] + view_range[0][1]) / 2
        self._add_line(angle=90, pos=x_center)

    def add_horizontal_line(self):
        """Добавляет горизонтальную линию в центр видимой области"""
        view_range = self.plotItem.viewRange()
        y_center = (view_range[1][0] + view_range[1][1]) / 2
        self._add_line(angle=0, pos=y_center)

    def _add_line(self, angle, pos):
        """Создает линию с указанным углом и позицией"""
        contrast_color = self.get_max_contrast_color(self.background_color)

        if not hasattr(self, '_line_counter'):
            self._line_counter = 0
        self._line_counter += 1
        
        inf_line = RemovableInfiniteLine(
            movable=True,
            angle=angle,
            pen=(contrast_color.red(), contrast_color.green(), contrast_color.blue()),
            hoverPen=(0, 200, 0),
            label=f'#{self._line_counter}: {{value:0.6f}}',
            labelOpts={
                'color': (contrast_color.red(), contrast_color.green(), contrast_color.blue()),
                'movable': True, 
                'fill': (0, 0, 200, 100)
            },
            pos=pos
        )
        
        inf_line.removeRequested.connect(self.remove_inf_line)
        self.add_inf_line(inf_line)

        