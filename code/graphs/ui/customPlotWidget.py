import pyqtgraph as pg

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal
from dataclasses import dataclass
from pyqtgraph import AxisItem
import logging
from graphs.ui.custom_inf_line import RemovableInfiniteLine

logger = logging.getLogger(__name__)

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
    inf_line_added   = pyqtSignal(object)
    inf_line_removed = pyqtSignal(object)
    style_changed    = pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.preset_styles = [
            {"name": "Светлый", "bg": (255,255,255), "text": (0,0,0), "grid": (200,200,200), "legend": (0,0,0)},
            {"name": "Тёмный", "bg": (0,0,0), "text": (255,255,255), "grid": (80,80,80), "legend": (255,255,255)},
            {"name": "Серый", "bg": (240,240,240), "text": (0,0,0), "grid": (180,180,180), "legend": (0,0,0)},
            {"name": "Высококонтрастный", "bg": (255,255,255), "text": (0,0,0), "grid": (0,0,0), "legend": (0,0,0)},
            {"name": "Минималистичный", "bg": (255,255,255), "text": (50,50,50), "grid": (230,230,230), "legend": (50,50,50)},
        ]

        self.is_second_axis = False

        self.inf_lines = []

        self.legend = pg.LegendItem(size=(80, 60), offset=(10, 10))
        self.legend2 = pg.LegendItem(size=(80, 60), offset=(50, 10))
        self.tooltip = pg.TextItem("X:0,Y:0", color=(255, 255, 255), anchor=(0,0))
        
        self.setAntialiasing(False)
        self.scene().sigMouseMoved.connect(self.showToolTip)

        self.is_grid_shown = False
        self.legend_color = QtGui.QColor(255, 255, 255)

        self.background_color = QtGui.QColor(0, 0, 0)
        
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

    def _emit_style_changed(self):
        """Оповестить подписчиков (сессия → дочерние графики) о смене стиля."""
        try:
            self.style_changed.emit()
        except Exception:
            logger.exception("style_changed emit failed")

    def add_inf_line(self, line):
        self.inf_lines.append(line)
        self.addItem(line)
        try:
            self.inf_line_added.emit(line)
        except Exception:
            logger.exception("add_inf_line emit failed")

    def remove_inf_line(self, line):
        if line in self.inf_lines:
            self.inf_lines.remove(line)
        self.removeItem(line)
        try:
            self.inf_line_removed.emit(line)
        except Exception:
            logger.exception("remove_inf_line emit failed")

    def apply_preset_style(self, style):
        self.common_style.color = style["text"]
        for axis in self.axises.values():
            axis.settings.is_style_customized = False
            axis.set_common_style(self.common_style)
        self.setCustomBackgroundColor(style["bg"])
        self.setGridColor(style["grid"])
        self.set_legend_color(style["legend"])
        self.toggleGrid(True)
        self._emit_style_changed()
        

    def updateViews(self):
        """Обновление вьюшек при изменении размера"""
        self.second_graphView.setGeometry(self.plots_lay.vb.sceneBoundingRect())
        self.second_graphView.linkedViewChanged(self.plots_lay.vb, self.second_graphView.XAxis)

    def showToolTip(self, pos):
        if self.plots_lay.vb.sceneBoundingRect().contains(pos):
            mouse_point = self.plots_lay.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()
            self.tooltip.setText(f"X: {x:.2f}, Y: {y:.2f}")
            
    def set_second_axis(self, state: bool):
        """Включение/выключение второй оси"""
        self.is_second_axis = state
        if not state:
            self.axises["right"].hide()
        else:
            self.axises["right"].show()
        self._emit_style_changed()

    def chooseCustomLegendColor(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.set_legend_color(color)

    def set_legend_color(self, color):
        """Обновить цвет текста легенды.

        - Нормализует вход в QColor.
        - Обновляет подписи у всех текущих элементов.
        - Запоминает цвет для будущих подписей.
        - Гарантированно эмитит style_changed (через finally), чтобы даже
          при частичной ошибке propagation к дочерним графикам всё равно
          произошёл.
        """
        try:
            # 1. Нормализация цвета
            if isinstance(color, tuple):
                color = QtGui.QColor(*color)
            elif isinstance(color, str):
                color = QtGui.QColor(color)
            self.legend_color = color

            # 2. Обход обеих легенд (main + вторая ось)
            for legend in (getattr(self, "legend", None),
                           getattr(self, "legend2", None)):
                if legend is None:
                    continue

                # 2a. Существующие подписи
                for entry in list(getattr(legend, "items", []) or []):
                    label = None
                    if isinstance(entry, (tuple, list)) and len(entry) >= 2:
                        label = entry[1]
                    elif hasattr(entry, "setText"):
                        label = entry
                    if label is None or not hasattr(label, "setText"):
                        continue
                    text = getattr(label, "text", "")
                    try:
                        label.setText(text, color=color)
                    except TypeError:
                        # Старые сборки pyqtgraph: setText(text) + отдельная установка цвета
                        try:
                            label.setText(text)
                        except Exception:
                            pass
                        if hasattr(label, "setAttr"):
                            try:
                                label.setAttr("color", color)
                            except Exception:
                                pass
                        if hasattr(label, "updateText"):
                            try:
                                label.updateText(text, color=color)
                            except Exception:
                                pass

                # 2b. Цвет для будущих подписей
                for setter_name in ("setLabelTextColor", "setLabelTextColour"):
                    setter = getattr(legend, setter_name, None)
                    if callable(setter):
                        try:
                            setter(color)
                        except Exception:
                            logger.exception("set_legend_color: %s failed", setter_name)
                try:
                    opts = getattr(legend, "opts", None)
                    if isinstance(opts, dict):
                        opts["labelTextColor"] = color
                except Exception:
                    pass
        finally:
            self._emit_style_changed()

    def set_axis_color(self, color, axis_key):
        if isinstance(color, tuple):
            color = QtGui.QColor(*color)
        axis_map = {'x': 'bottom', 'y1': 'left', 'y2': 'right'}
        axis = self.axises[axis_map[axis_key]]
        axis.custom_style.color = color
        axis.setTextPen(color)
        if hasattr(axis, 'style') and 'tickText' in axis.style:
            axis.style['tickText'] = (color, axis.style['tickText'][1])
        self._emit_style_changed()

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
            self._emit_style_changed()

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
            self._emit_style_changed()

    def customize_axes_font(self):

        font, ok = QtWidgets.QFontDialog.getFont(self.common_style.text_font, self, "Выберите шрифт")
        if ok:
            self.common_style.text_font = font
            for axis in self.axises.values():
                if not axis.settings.is_style_customized:#если ось не была кастомизирована инживидуально. то применяем общие настройки
                    axis.set_common_style( self.common_style )
                else:
                    axis.update_common_style(self.common_style)
            self._emit_style_changed()

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
        self._emit_style_changed()

    def reset_y1_axis_style(self):
        self.axises["left"].reset_style()
        self._emit_style_changed()

    def reset_y2_axis_style(self):
        self.axises["right"].reset_style()
        self._emit_style_changed()

    def customize_x_axis_font(self):
        self.customize_axis_font('x')
        self._emit_style_changed()

    def customize_y1_axis_font(self):
        self.customize_axis_font('y1')
        self._emit_style_changed()

    def customize_y2_axis_font(self):
        self.customize_axis_font('y2')
        self._emit_style_changed()
        
    def invert_x_axis(self, checked):
        self.plotItem.vb.invertX(checked)
        if hasattr(self, 'second_graphView'):
            self.second_graphView.invertX(checked)
        self.axises["bottom"].settings.is_inverted = checked
        self._emit_style_changed()

    def invert_y_axis(self, checked):
        self.plotItem.vb.invertY(checked)
        self.axises["left"].settings.is_inverted = checked
        self._emit_style_changed()

    def invert_y2_axis(self, checked):
        if hasattr(self, 'second_graphView'):
            self.second_graphView.invertY(checked)
        self.axises["right"].settings.is_inverted = checked
        self._emit_style_changed()

    def hide_second_line_grid(self):
        self.axises["right"].setGrid(0)
    
    def toggleGrid(self, checked):
        self.is_grid_shown = checked
        self.plotItem.showGrid(x=checked, y=checked)
        self.hide_second_line_grid()
        self._emit_style_changed()
    
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
        self._emit_style_changed()
    
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
        self._emit_style_changed()
            
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
            if self.axises.get(axis_name) is None:
                continue
            axis = self.axises[axis_name]
            axis.update_common_style(self.common_style)
            if axis:
                axis.setTextPen(color)
                if hasattr(axis, 'style') and 'tickText' in axis.style:
                    axis.style['tickText'] = (color, axis.style['tickText'][1])
        self._emit_style_changed()
        
    def chooseCustomTextColor(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.common_style.color = color
            self.set_axes_color(color)
    
    def toggleAntialias(self, checked):
        for item in self.plotItem.items:
            if isinstance(item, pg.PlotCurveItem):
                item.setAntialiased(checked)
            self._emit_style_changed()
    
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

    def apply_appearance_change(self, mutate_callable):
        """
        Выполнить мутацию внешнего вида и — если что-то изменилось —
        эмитировать запрос на регистрацию undo-команды.

        Колбэк `appearance_undo_callback` вызывается с самим виджетом:
        `cb(widget, before_settings, after_settings)` — так обработчик
        знает, для какого графа регистрировать команду.
        """
        from graphs.hdf5_io.utils import extract_plot_widget_settings
        before = extract_plot_widget_settings(self)
        mutate_callable()
        after = extract_plot_widget_settings(self)
        cb = getattr(self, "appearance_undo_callback", None)
        if cb is not None and before != after:
            try:
                cb(self, before, after)
            except TypeError:
                # обратная совместимость со старым 2-аргументным колбэком
                cb(before, after)
        self._emit_style_changed()
    
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

        