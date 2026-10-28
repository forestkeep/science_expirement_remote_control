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
    legend_recreated = pyqtSignal(object, object)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.preset_styles = [
                                {
                                    "name": "Nature",
                                    "bg": (255, 255, 255),
                                    "text": (0, 0, 0),
                                    "grid": (200, 200, 200),
                                    "legend": (0, 0, 0),
                                    "helper_line_color": "#000000",
                                    "helper_line_width": 1,
                                    "helper_text_color": "#000000",
                                    "helper_font_size": 8,
                                    "helper_marker_color": "#000000",
                                },
                                {
                                    "name": "Science",
                                    "bg": (255, 255, 255),
                                    "text": (0, 0, 0),
                                    "grid": (200, 200, 200),
                                    "legend": (0, 0, 0),
                                    "helper_line_color": "#000000",
                                    "helper_line_width": 1,
                                    "helper_text_color": "#000000",
                                    "helper_font_size": 8,
                                    "helper_marker_color": "#000000",
                                },
                                {
                                    "name": "APA",
                                    "bg": (255, 255, 255),
                                    "text": (0, 0, 0),
                                    "grid": (200, 200, 200),
                                    "legend": (0, 0, 0),
                                    "helper_line_color": "#000000",
                                    "helper_line_width": 1,
                                    "helper_text_color": "#000000",
                                    "helper_font_size": 10,
                                    "helper_marker_color": "#000000",
                                },
                                {
                                    "name": "IEEE",
                                    "bg": (255, 255, 255),
                                    "text": (0, 0, 0),
                                    "grid": (200, 200, 200),
                                    "legend": (0, 0, 0),
                                    "helper_line_color": "#000000",
                                    "helper_line_width": 1,
                                    "helper_text_color": "#000000",
                                    "helper_font_size": 8,
                                    "helper_marker_color": "#000000",
                                },
                                {
                                    "name": "ACS",
                                    "bg": (255, 255, 255),
                                    "text": (0, 0, 0),
                                    "grid": (200, 200, 200),
                                    "legend": (0, 0, 0),
                                    "helper_line_color": "#000000",
                                    "helper_line_width": 1,
                                    "helper_text_color": "#000000",
                                    "helper_font_size": 8,
                                    "helper_marker_color": "#000000",
                                },
                            ]

        self.is_second_axis = False
        self.inf_lines = []

        self.legend_font = QtGui.QFont("Arial", 10)
        self.legend_color = QtGui.QColor(255, 255, 255)

        self.legend = self._create_legend(offset=(10, 10))
        self.legend2 = self._create_legend(offset=(50, 10))

        self.setAntialiasing(False)
        self.scene().sigMouseMoved.connect(self.showToolTip)

        self.is_grid_shown = False

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

        self.set_second_axis(False)

        view_rect = self.plots_lay.vb.viewRect()

    def _collect_legend_entries(self, legend):
        if legend is None:
            return []
        result = []
        for sample, label in list(getattr(legend, "items", []) or []):
            plot_item = getattr(sample, "item", None)
            if plot_item is None:
                continue
            name = getattr(label, "text", "")
            result.append((plot_item, name))
        return result


    def _destroy_legend(self, legend):
        if legend is None:
            return
        scene = legend.scene()
        if scene is not None:
            scene.removeItem(legend)


    def _create_legend(self, offset):
        return self._build_legend(None, [], offset)


    def _build_legend(self, parent, entries, offset):
        legend = pg.LegendItem(
            size=None,
            offset=offset,
            labelTextColor=self.legend_color,
            labelTextSize=f"{self.legend_font.pointSize()}pt",
        )
        if parent is not None:
            legend.setParentItem(parent)
        for plot_item, name in entries:
            legend.addItem(plot_item, name)
        legend.updateSize()
        return legend


    def set_legend_font(self, font):
        """Сменить шрифт легенды, сохранив текущее положение.

        Легенда пересоздаётся (нужно для корректного изменения
        ``labelTextSize`` у существующих подписей). При пересоздании позиция
        сбрасывается на исходный ``offset``, поэтому фактическое положение
        ``old.pos()`` (учитывающее перетаскивание мышью) сохраняется и
        восстанавливается.

        Порядок важен:
        1) снять снимок ``pos()`` ДО пересоздания;
        2) собрать новые легенды;
        3) синхронизировать ``offset`` и ``pos`` целевым значением
            (``apply_pos``), отключить авто-подстройку ``_updateOffset``
            от сигналов родителя;
        4) заменить ссылки, уведомить наблюдателей;
        5) удалить старые легенды;
        6) отложенный повтор ``apply_pos`` на случай queued layout-pass'ов.
        """
        from PyQt5.QtCore import QTimer

        self.legend_font = QtGui.QFont(font)

        entries_main = self._collect_legend_entries(self.legend)
        entries_second = self._collect_legend_entries(self.legend2)

        old_main = self.legend
        old_second = self.legend2

        parent_main = old_main.parentItem() if old_main is not None else self.plotItem
        parent_second = old_second.parentItem() if old_second is not None else self.second_graphView

        # Снимок ТЕКУЩЕЙ позиции — ДО пересоздания. Кортеж (x, y), а не QPointF:
        # кортеж переживает удаление старой легенды без риска инвалидации.
        if old_main is not None:
            pos_main = (old_main.pos().x(), old_main.pos().y())
        else:
            pos_main = None
        if old_second is not None:
            pos_second = (old_second.pos().x(), old_second.pos().y())
        else:
            pos_second = None

        offset_main = getattr(old_main, "offset", None) if old_main is not None else None
        if offset_main is None:
            offset_main = (10, 10)
        offset_second = getattr(old_second, "offset", None) if old_second is not None else None
        if offset_second is None:
            offset_second = (50, 10)

        # --- Пересоздание (логика не меняется) ---
        new_main = self._build_legend(parent_main, entries_main, offset=offset_main)
        new_second = self._build_legend(parent_second, entries_second, offset=offset_second)

        # --- Вложенные помощники (ВАЖНО: с отступом внутри set_legend_font) ---
        def apply_pos(legend, target_xy):
            if legend is None or target_xy is None:
                return
            try:
                # 1. Сначала синхронизируем offset: если pyqtgraph сам вызовет
                #    _updateOffset() (из resize/range-change), он поставит pos
                #    ровно в ту же точку, что и мы.
                setter = getattr(legend, "setOffset", None)
                if callable(setter):
                    try:
                        setter(target_xy)
                    except Exception:
                        legend.offset = target_xy
                else:
                    legend.offset = target_xy
                # 2. Затем — фактическое положение.
                legend.setPos(target_xy[0], target_xy[1])
            except Exception:
                logger.exception("set_legend_font: apply_pos failed")

        def detach_autoupdate(legend, parent):
            """Отключить автоподстройку позиции от сигналов родителя.

            pyqtgraph подключает ``parent.sigResized`` / ``parent.sigRangeChanged``
            к ``legend._updateOffset``. Каждый такой вызов делает
            ``setPos(*legend.offset)`` и в неблагоприятный момент может
            перебить наш ``setPos``. Отключаем эти подписки — единственный
            источник позиции теперь ``apply_pos``.
            """
            if legend is None or parent is None:
                return
            updater = getattr(legend, "_updateOffset", None)
            if updater is None:
                return
            for sig_name in ("sigResized", "sigRangeChanged"):
                sig = getattr(parent, sig_name, None)
                if sig is None:
                    continue
                try:
                    sig.disconnect(updater)
                except (TypeError, RuntimeError):
                    # Не было подключено / нельзя отключить — не страшно.
                    pass

        # 1. Восстановить позицию (синхронно) — до любых style_changed.
        apply_pos(new_main, pos_main)
        apply_pos(new_second, pos_second)

        # 2. Отключить автоподстройку — чтобы никто не перебил наш setPos.
        detach_autoupdate(new_main, parent_main)
        detach_autoupdate(new_second, parent_second)

        # 3. Заменить ссылки и уведомить наблюдателей
        #    (manageGraph._on_legend_recreated делает replace_legend в presenter'ах).
        self.legend = new_main
        self.legend2 = new_second
        self.legend_recreated.emit(old_main, new_main)
        self.legend_recreated.emit(old_second, new_second)

        # 4. Удалить старые легенды из сцены.
        #    Именно этого шага не хватало из-за сбитого отступа — новые легенды
        #    копились поверх старых, а self.legend продолжал указывать на старую.
        self._destroy_legend(old_main)
        self._destroy_legend(old_second)

        self._emit_style_changed()

        # 5. Страховка от отложенных layout-pass'ов: несколько повторов
        #    apply_pos на разных временных метках переживают все queued
        #    updateSize()/layout-события. default-args в lambda гарантируют,
        #    что значения не изменятся между планированием и выполнением.
        for delay in (0, 16, 50, 150):
            QTimer.singleShot(delay, lambda l=new_main, p=pos_main: apply_pos(l, p))
            QTimer.singleShot(delay, lambda l=new_second, p=pos_second: apply_pos(l, p))


    def get_legend_font(self):
        return QtGui.QFont(self.legend_font)


    
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
        return
            
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
                except (AttributeError, TypeError) as exc:
                    logger.debug("set_legend_color: opts update failed: %s", exc)
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

        