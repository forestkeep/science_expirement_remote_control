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

import os
import sys
from enum import Enum

import qdarktheme
from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (QApplication, QFrame, QLabel, QSizePolicy,
                             QVBoxLayout, QWidget)
from functions import get_active_ch_and_device

class Position(Enum):
    LEFT = 1
    RIGHT = 2
    TOP = 3
    BOTTOM = 4
    LEFT_TOP = 5
    LEFT_BOTTOM = 6
    RIGHT_TOP = 7
    RIGHT_BOTTOM = 8
    SAME = 9
    
    
unique_colors= [
    "rgba(186, 0, 0, 1)",       
    "rgba(0, 128, 0, 1)",        
    "rgba(0, 0, 255, 1)",        
    "rgba(0, 160, 240, 1)",      
    "rgba(128, 0, 128, 1)",      
    "rgba(255, 165, 0, 1)",      
    "rgba(255, 20, 147, 1)",     
    "rgba(255, 105, 180, 1)",    
    "rgba(255, 80, 0, 1)",      
    "rgba(0, 255, 127, 1)",       
    "rgba(0, 120, 120, 1)",       
    "rgba(75, 0, 130, 1)",        
    "rgba(200, 160, 150, 1)"     
]

class connectionType(Enum):
    SINGLE = 1
    DOUBLE = 2

def get_center_side(widget: QWidget, side: Position):
        posit = widget.pos()

        if side == Position.LEFT:
            return QPoint( posit.x(), int(posit.y() + widget.height() / 2) )
        elif side == Position.RIGHT:
            return QPoint( posit.x() + widget.width(), int(posit.y() + widget.height() / 2) )
        elif side == Position.TOP:
            return QPoint( int(posit.x() + widget.width() / 2), posit.y() )
        elif side == Position.BOTTOM:
            return QPoint( int(posit.x() + widget.width() / 2), posit.y() + widget.height()  )

class connection():
    '''save connection two some objects'''
    def __init__(self, base_widget = None, name = None):
        self.base_widget = base_widget
        self.first_unit = None
        self.second_unit = None
        self.name = name
        self.type_signal = None
        if os.getenv("APP_THEME") == "dark":
            self.pen = QPen(QColor(255, 255, 255), 1, Qt.SolidLine)
        else:
            self.pen = QPen(QColor(0, 0, 0), 1, Qt.SolidLine)
        self.type = connectionType.SINGLE

    def set_type(self, type: connectionType):
        self.type = type

    def set_units(self, first_unit = False, second_unit = False):
        if first_unit is not False:
            self.first_unit = first_unit
        if second_unit is not False:
            self.second_unit = second_unit
            self.type_signal = second_unit.value_trigger

    def get_coords(self):
        if self.first_unit is None or self.second_unit is None:
            return None

        first_pos = self.first_unit.pos()
        second_pos = self.second_unit.pos()
        
        width_first = self.first_unit.width()
        height_first = self.first_unit.height()
        width_second = self.second_unit.width()
        height_second = self.second_unit.height()

        # Середина первого выше верхнего края второго
        first_above_second = (first_pos.y() + height_first / 2) < second_pos.y()
        # Середина первого ниже нижнего края второго
        second_above_first = (first_pos.y() + height_first / 2) > (second_pos.y() + height_second)
        # Середина первого левее левого края второго
        first_left_of_second = (first_pos.x() + width_first / 2) < second_pos.x()
        # Середина первого правее правого края второго
        first_right_of_second = (first_pos.x() + width_first / 2) > (second_pos.x() + width_second)

        is_overlap_y = not first_above_second and not second_above_first
        is_overlap_x = not first_left_of_second and not first_right_of_second
        is_overlap = is_overlap_x and is_overlap_y  # Перекрытие по обеим осям
        
        if is_overlap:
            start_point = get_center_side(self.first_unit, Position.RIGHT)
            end_point = get_center_side(self.second_unit, Position.LEFT)
            direction_first = False
            pass
        elif is_overlap_y:
            if first_left_of_second:
                start_point = get_center_side(self.first_unit, Position.RIGHT)
                end_point = get_center_side(self.second_unit, Position.LEFT)
                direction_first = Position.LEFT

            elif first_right_of_second:
                start_point = get_center_side(self.first_unit, Position.LEFT)
                end_point = get_center_side(self.second_unit, Position.RIGHT)
                direction_first = Position.RIGHT

        elif is_overlap_x:
            if first_above_second:
                start_point = get_center_side(self.first_unit, Position.BOTTOM)
                end_point = get_center_side(self.second_unit, Position.TOP)
                direction_first = Position.BOTTOM

            elif second_above_first:
                start_point = get_center_side(self.first_unit, Position.TOP)
                end_point = get_center_side(self.second_unit, Position.BOTTOM)
                direction_first = Position.TOP

        else:
            if first_above_second and first_left_of_second:
                start_point = get_center_side(self.first_unit, Position.RIGHT)
                end_point = get_center_side(self.second_unit, Position.TOP)
                direction_first = Position.LEFT
            elif first_above_second and first_right_of_second:
                start_point = get_center_side(self.first_unit, Position.LEFT)
                end_point = get_center_side(self.second_unit, Position.TOP)
                direction_first = Position.RIGHT
            elif second_above_first and first_right_of_second:
                start_point = get_center_side(self.first_unit, Position.LEFT)
                end_point = get_center_side(self.second_unit, Position.BOTTOM)
                direction_first = Position.RIGHT
            elif second_above_first and first_left_of_second:
                start_point = get_center_side(self.first_unit, Position.RIGHT)
                end_point = get_center_side(self.second_unit, Position.BOTTOM)
                direction_first = Position.LEFT

        return (start_point, end_point, direction_first, (is_overlap_x or is_overlap_y) )
       
    def setStyle(self, new_pen : QPen):
        self.pen = new_pen

    def add_in_simbol(self, coords: QPoint):
        painter = QPainter(self.base_widget)
        painter.setPen(self.pen)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        height = int(self.second_unit.height()/5)
        width = height

        x = int(coords.x()-height/2)
        y = int(coords.y()-width/2)

        painter.drawEllipse(x, y, height, width)

    def draw_connection_to_self(self):
        painter = QPainter(self.base_widget)
        painter.setPen(self.pen)
        

        text = str(self.name)
        text_width = painter.fontMetrics().boundingRect(text).width()

        width = self.first_unit.width()
        height = self.first_unit.height()
        min_dis = min(width, height)

        x = self.first_unit.pos().x() + self.first_unit.width() - min_dis*(1/3)
        y = self.first_unit.pos().y() + self.first_unit.height() - min_dis*(1/3)

        painter.drawRect(int(x), int(y), int( min_dis*2/3), int( min_dis*2/3 ))

        text_x = int(x + (min_dis*2/3 - text_width) / 2)
        text_y = int(y + min_dis*2/3)

        painter.drawText(text_x, text_y, text)
        x = self.first_unit.pos().x() + self.first_unit.width() - min_dis*(1/3)
        y = self.first_unit.pos().y() + self.first_unit.height() 
        self.add_in_simbol(QPoint(int(x), int(y)))

    def draw_line(self):
        painter = QPainter(self.base_widget)
        painter.setPen(self.pen)
        
        start_point, end_point, direction_first, is_overlap = self.get_coords()

        if os.getenv("APP_THEME") == "dark":
            sourse_color = QColor(120, 120, 0)
        else:
            sourse_color = QColor(200, 200, 200)

        if direction_first != False:

            try:
                sig_text = str(self.type_signal.split()[2])
            except:
                sig_text = str(self.type_signal)


            font = QFont("Arial", 8)
            painter.setFont(font)


            bounding_rect = painter.boundingRect(QRect(), 0, sig_text)
            text_width = bounding_rect.width()
            text_height = bounding_rect.height()

            painter.setPen(self.pen)
            if is_overlap:
                #три линии
                midpoint = QPoint( int((start_point.x() + end_point.x()) / 2) , int((start_point.y() + end_point.y()) / 2))
                if direction_first == Position.LEFT or direction_first == Position.RIGHT:
                    painter.drawLine(start_point.x(), start_point.y(), midpoint.x(), start_point.y())
                    painter.drawLine(midpoint.x(), start_point.y(), midpoint.x(), end_point.y())
                    painter.drawLine(midpoint.x(), end_point.y(), end_point.x(), end_point.y())

                    painter.setPen(sourse_color)
                    if direction_first == Position.LEFT:
                        painter.drawText(end_point.x()-text_width-10, end_point.y()-3, str(sig_text))
                    else:
                        painter.drawText(end_point.x()+10, end_point.y() + text_height, str(sig_text))

                else:
                    painter.drawLine(start_point.x(), start_point.y(), start_point.x(), midpoint.y())
                    painter.drawLine(start_point.x(), midpoint.y(), end_point.x(), midpoint.y())
                    painter.drawLine(end_point.x(), midpoint.y(), end_point.x(), end_point.y())

                    painter.setPen(sourse_color)
                    painter.drawText(end_point.x()+10, end_point.y(), str(sig_text))
            else:
                #две линии
                if direction_first == Position.LEFT or direction_first==Position.RIGHT:
                    painter.drawLine(start_point.x(), start_point.y(), end_point.x(), start_point.y())
                    painter.drawLine(end_point.x(), start_point.y(), end_point.x(), end_point.y())
                if direction_first == Position.TOP or direction_first==Position.BOTTOM:
                    painter.drawLine(start_point.x(), start_point.y(), start_point.x(), end_point.y())
                    painter.drawLine(start_point.x(), end_point.y(), end_point.x(), end_point.y())

                painter.setPen(sourse_color)
                painter.drawText(end_point.x()+10, end_point.y(), str(sig_text))

            self.add_in_simbol(end_point)
        
    def draw( self ):
            if self.first_unit is None or self.second_unit is None:
                return
            elif self.first_unit == self.second_unit:
                self.draw_connection_to_self()
            else:
                self.draw_line()

class setBlock:
    def __init__(self):
        self.blocks = []
        self.vertical_size = 1
        self.horizontal_size = 1
        self.x_offset = 0
        self.y_offset = 0

        self.current_x = 0
        self.current_y = 0

class Packing:
    def __init__(self, rectangles):
        self.rectangles = sorted(rectangles, key=lambda r: r.current_x, reverse=True)
        self.levels = []
        self.current_level = []
        self.field_height = 0

    def is_ceiling_feasible(self, rectangle):
        return rectangle.current_y + sum(r.current_y for r in self.current_level) <= self.strip_width

    def is_floor_feasible(self, rectangle):
        return rectangle.current_y <= self.strip_width

    def pack_rectangles(self, width:float, height:float):

        self.strip_width = width
        self.box_height = height
        current_x = 0

        for rectangle in self.rectangles:

            if rectangle.current_y > self.strip_width:
                self.pack_on_ceiling(rectangle, current_x)
                self.field_height = max(self.field_height, rectangle.current_y)
            elif self.is_ceiling_feasible(rectangle):
                self.pack_on_ceiling(rectangle, current_x)
                self.field_height = max(self.field_height, rectangle.current_y + (rectangle.current_y - self.strip_width))

            else:
                self.levels.append(self.current_level)
                current_x += max(r.current_x for r in self.current_level)  # Переход на новый уровень
                self.current_level = []
                rectangle.y_offset = 0
                rectangle.x_offset = current_x
                
            self.current_level.append(rectangle)

        if self.current_level:
            current_x += max(r.current_x for r in self.current_level)
        return current_x, self.field_height

    def pack_on_ceiling(self, rectangle, current_x):   
        rectangle.x_offset = current_x
        rectangle.y_offset = sum(r.current_y for r in self.current_level if r.x_offset == current_x)

class blockDevice(QWidget):
    def __init__(self, ch_name, dev_name, parent=None):
        super().__init__(parent)
        self.parent_wid = parent
        self.base_color = "background-color: rgba(250, 250, 250, 50);"
        self.setObjectName("device")
        self.is_ctrl_pressed = False
        self.setMouseTracking(True)
        self.dragging        = False
        self.last_pos        = None
        self.type_trigger    = None
        self.value_trigger   = None
        self.number_meas     = None
        self.master          = None
        self.slave           = []

        #координаты для автоасстановки, показывают смещение виджета внутри блока
        self.x_offset = 0
        self.y_offset = 0
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 0, 0, 0)

        self.ch_name  = ch_name
        self.dev_name = dev_name

        self.label_ch = QLabel(self.ch_name)
        self.label_ch.setMaximumHeight(20)
        
        self.label_dev = QLabel(self.dev_name)
        self.label_dev.setMaximumHeight(20)


        layout.addWidget(self.label_dev)
        layout.addWidget(self.label_ch)

        self.frame = QFrame(self)
        self.frame.setFrameShape(QFrame.Panel)
        self.frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.frame.setLayout(layout)

        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(self.frame)

        self.setLayout(outer_layout)

        self.setMaximumHeight(3 * self.label_ch.height())
        self.setMaximumWidth(max(self.label_ch.width(), self.label_dev.width()))

        self.label_ch.raise_()
        self.label_dev.raise_()
        self.is_check = False

    def mousePressEvent(self, event):
        if self.parentWidget().is_ctrl_pressed and event.button() == Qt.LeftButton:  # Ctrl + Левый клик
            self.toggle_selection()
        elif event.button() == Qt.LeftButton:  # Левый клик
            self.drag_start_position = event.pos()
            self.dragging = True
        elif event.button() == Qt.RightButton:
            pass
            #self.create_copy()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            new_coord = self.pos() + event.pos() - self.drag_start_position
            y = max( [new_coord.y(), 0] )
            x = max( [new_coord.x(), 0] )
            y = min( [y, self.parent_wid.height() - self.height() ] )
            x = min( [x, self.parent_wid.width() - self.width() ] )
            new_coord = QPoint(x, y)
            
            self.move(new_coord)
            self.parentWidget().update()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def toggle_selection(self, set_check = None):
        if set_check == True:
            self.frame.setStyleSheet(self.base_color)
            self.is_check = True
            
        elif set_check   == False:
            self.is_check = False
            self.set_default_style()
        else:
            if self.is_check:
                self.is_check = False
                self.set_default_style()
            else:
                self.frame.setStyleSheet("background-color: rgba(128, 128, 128, 0.5);")
                self.is_check = True

    def create_copy(self):
        new_device = blockDevice(self.ch_name + "(copy)", self.ch_name + "(copy)",self.parentWidget())
        new_device.frame.setStyleSheet(self.frame.styleSheet())
        new_device.move(self.pos() + QPoint(20, 20))
        new_device.show()

    def set_default_style(self):
        pass
        #self.frame.setStyleSheet(self.base_color)

class expDiagram(QWidget):
    def __init__(self):
        super().__init__()
        self.is_ctrl_pressed = False
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.connections = []

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            all_child_widgets = self.findChildren(blockDevice)
            for widget in all_child_widgets:
                widget.toggle_selection(set_check=False)
                    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.is_ctrl_pressed = True

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.is_ctrl_pressed = False
        elif event.key() == Qt.Key_Delete:
            all_child_widgets = self.findChildren(blockDevice)
            for widget in all_child_widgets:
                if widget.is_check:
                    widget.hide()
                    widget.setParent(None)
                    
    def set_content(self, objects: list):
        self.objects = objects
        self.labels = []
        for obj in objects:
            lb = blockDevice(obj.ch_name, obj.dev_name, self)
            lb.type_trigger = obj.type_trigger
            lb.value_trigger = obj.value_trigger
            lb.number_meas = obj.number_meas
            lb.frame.setStyleSheet(f"background-color: {obj.color};")
            lb.base_color = f"background-color: {obj.color};"
            self.labels.append(lb)

        self.connections = []
        for index, obj in enumerate(objects):

            if obj.type_trigger == QApplication.translate("construct","Таймер"):
                con = connection(self, str(obj.value_trigger) + "сек")
                con.set_units(self.labels[index], self.labels[index])
                self.connections.append(con)
                continue

            try:
                components = obj.value_trigger.split()
            except:
                continue

            for label in self.labels:
                if components[1] ==label.ch_name and  components[0] == label.dev_name:
                    con = connection(self, "do action")
                    con.set_units(label, self.labels[index])
                    self.connections.append(con)

                    #перекрестные ссылки ведущий ведомый

                    label.slave.append( self.labels[index] )
                    self.labels[index].master = label
        self.auto_place(self.labels)

    def auto_place(self, components: list):
        '''
        группа 1: компоненты работают по таймеру и от них не зависит ни один другой компонент
        группа 2: компоненты зависят от других компонентов и в цепочке есть компонент с таймером
        группа 3: компоненты зависят от других компонентов и в цепочке нет ни одного компонента с таймером'''

        components = set(components)
        for obj in components:
            obj.group = None

        added_components = set()
        groups1 = []
        groups2 = []
        groups3 = []
        
        for obj in components:
            if obj.group == None:
                if obj.type_trigger == QApplication.translate("construct","Таймер"):
                    if obj.slave  == []:
                        obj.group = 1
                        added_components.add(obj)
                        buf = setBlock()
                        buf.blocks.append(obj)

                        min_dis = min( obj.width(), obj.height() )

                        obj.x_offset = buf.current_x
                        obj.y_offset = buf.current_y
                        buf.current_x+=obj.width() + int(min_dis*3/3)
                        buf.current_y+=obj.height() + int(min_dis*3/3)
                        groups1.append( buf )
                    else:
                        buf = setBlock()
                        obj.group = 2
                        added_components.add( obj )
                        buf.blocks.append( obj )

                        min_dis = min( obj.width(), obj.height() )
                        obj.x_offset = buf.current_x
                        obj.y_offset = buf.current_y
                        buf.current_x+=obj.width()# + int(min_dis*4/3)
                        buf.current_y+=obj.height() + int(min_dis*2/3)

                        current_level = obj.slave
                        #поиск в ширину, послойно проходим по всем линиям дерева
                        levels_length = []
                        buf_cur_x = buf.current_x
                        while current_level:
                            next_level = []

                            for node in current_level:
                                if node not in added_components:
                                    buf.blocks.append(node)
                                    node.group = 2

                                    node.x_offset = buf_cur_x
                                    node.y_offset = buf.current_y

                                    height = node.height()
                                    width = int(node.width())
                                    buf_cur_x+=width
                                    added_components.add(node)
                                    for node in node.slave:
                                        if node not in added_components:
                                            next_level.append(node)
                            levels_length.append(buf_cur_x)
                            buf_cur_x=width
                            buf.current_y+=int(height*4/3)
                            current_level = next_level
                        buf.current_x = max(levels_length)
                        groups2.append(buf)

        for obj in components:
            if obj.group == None:
                        buf = setBlock()
                        obj.group = 3
                        added_components.add(obj)
                        buf.blocks.append(obj)
                        height = int( obj.height()*1.5)
                        width = int(obj.width())
                        obj.x_offset = buf.current_x
                        obj.y_offset = buf.current_y
                        buf.current_x+=width
                        buf.current_y+=height

                        current_level = obj.slave
                        #поиск в ширину, послойно проходим по всем линиям дерева

                        while current_level:
                            next_level = []
                            for node in current_level:
                                if node not in added_components:
                                    buf.blocks.append(node)
                                    node.group = 3
                                    height = int(node.height()*1.5)
                                    width = int(node.width())
                                    node.x_offset = buf.current_x
                                    node.y_offset = buf.current_y
                                    buf.current_x+=width
                                    added_components.add(node)
                                    for node in node.slave:
                                        if node not in added_components:
                                            next_level.append(node)
                            buf.current_y+=height
                            current_level = next_level
                        groups3.append(buf)

        general_group = []
        for group in groups1:
            general_group.append(group)
        for group in groups2:
            general_group.append(group)
        for group in groups3:
            general_group.append(group)

        self.auto_place_group(groups=general_group)

        for family in groups1:
            for obj in family.blocks:
                obj.move(obj.x_offset+family.x_offset, obj.y_offset+family.y_offset)

        for family in groups2:
            for obj in family.blocks:
                obj.move(obj.x_offset+family.x_offset, obj.y_offset+family.y_offset)

        for family in groups3:
            for obj in family.blocks:
                obj.move(obj.x_offset+family.x_offset, obj.y_offset+family.y_offset)

    def auto_place_group(self, groups):
        packing = Packing(groups)
        focus_widht, focus_height = packing.pack_rectangles( width = self.height(), height= self.width())#90 degrees
        self.setMinimumSize(focus_widht, focus_height)

    def delete_old_draw(self):
        all_child_widgets = self.findChildren(blockDevice)
        for widget in all_child_widgets:
            widget.hide()
            widget.setParent(None)
            
        all_child_widgets = self.findChildren(connection)
        for widget in all_child_widgets:
            widget.hide()
            widget.setParent(None)

    def rebuild_schematic(self, install_class, components):

        self.delete_old_draw()
        self.labels = []
        color_index = 0
        color_map = {}
        
        for dev, ch in get_active_ch_and_device( install_class.dict_active_device_class ):
            y = install_class.message_broker.get_subscribers(publisher = ch, name_subscribe = ch.do_operation_trigger)
            name_dev = dev.get_name()
            if name_dev not in color_map:
                if color_index < len(unique_colors):
                    color_map[name_dev] = unique_colors[color_index]
                    color_index += 1
                else:
                    color_map[name_dev] = "#ffffff"  # цвет по умолчанию, белый
            
            color = color_map[name_dev]
            
            
            lb = blockDevice(ch.get_name(), dev.get_name(), self)
            lb.type_trigger = dev.get_trigger(ch)
            lb.value_trigger = dev.get_trigger_value(ch)
            lb.number_meas = dev.get_steps_number(ch)
            lb.show()
            lb.setStyleSheet(f"background-color: {color};")
            self.labels.append(lb)

        self.connections = []
        index = -1
        for dev, ch in get_active_ch_and_device( install_class.dict_active_device_class ):
            index += 1
            if dev.get_trigger(ch) == QApplication.translate("construct","Таймер"):
                con = connection(self, str(dev.get_trigger_value(ch)) + "s")
                con.set_units(self.labels[index], self.labels[index])
                self.connections.append(con)
                continue

            try:
                components = dev.get_trigger_value(ch).split()
            except:
                continue

            for label in self.labels:
                if len(components) >= 2:
                    if components[1] == label.ch_name and components[0] == label.dev_name:
                        con = connection(self, "do action")
                        con.set_units(label, self.labels[index])
                        label.slave.append( self.labels[index] )
                        self.labels[index].master = label
                        self.connections.append(con)


        self.auto_place(self.labels)  
        self.update()

    def paintEvent(self, event):
        for con in self.connections:
            con.draw()
                    
class connectObject:
    def __init__(self, device, ch, type, value, num, color):
        self.name = f"{device} {ch}"
        self.type_trigger  = type
        self.value_trigger = value
        self.number_meas   = num
        self.color         = color
        self.ch_name       = ch
        self.dev_name      = device

def create_objects(main_dict):
    objects = []
    
    # Список уникальных цветов
    unique_colors= [
    "rgba(186, 0, 0, 1)",       
    "rgba(0, 128, 0, 1)",        
    "rgba(0, 0, 255, 1)",        
    "rgba(0, 160, 240, 1)",      
    "rgba(128, 0, 128, 1)",      
    "rgba(255, 165, 0, 1)",      
    "rgba(255, 20, 147, 1)",     
    "rgba(255, 105, 180, 1)",    
    "rgba(255, 80, 0, 1)",      
    "rgba(0, 255, 127, 1)",       
    "rgba(0, 120, 120, 1)",       
    "rgba(75, 0, 130, 1)",        
    "rgba(200, 160, 150, 1)"     
]
    color_map = {}
    color_index = 0

    for device, channels in main_dict.items():
        # Присваиваем цвет, если еще не присвоили
        if device not in color_map:
            if color_index < len(unique_colors):
                color_map[device] = unique_colors[color_index]
                color_index += 1
            else:
                color_map[device] = "#ffffff"  # цвет по умолчанию, белый
        
        color = color_map[device]
        
        for ch, params in channels.items():
            obj = connectObject(
                device=device,
                ch=ch,
                type=params["type_trigger"],
                value=params["Value_trigger"],
                num=params["Num_meas"],
                color=color
            )
            objects.append(obj)
    
    return objects

# Пример использования
main_dict1 = {
    "device1": {
        "ch_1": {
            "type_trigger": "Внешний сигнал",
            "Value_trigger": "device2 ch_1 something",
            "Num_meas": "num",
        },
    },
    "device2": {
        "ch_1": {
            "type_trigger": "Внешний сигнал",
            "Value_trigger": "device3 ch_1 something",
            "Num_meas": "Пока активны другие приборы",
        },
    },
    "device3": {
        "ch_1": {
            "type_trigger": "Внешний сигнал",
            "Value_trigger": "device1 ch_1 something",
            "Num_meas": 5,
        },
        "ch_2": {
            "type_trigger": "Таймер",
            "Value_trigger": 10,
            "Num_meas": "num",
        },
        "ch_8": {
            "type_trigger": "Таймер",
            "Value_trigger": 10,
            "Num_meas": "num",
        }
    },
    "device4": {
        "ch_1": {
            "type_trigger": "Внешний сигнал",
            "Value_trigger": "device3 ch_8 something",
            "Num_meas": "num",
        },
        "ch_2": {
            "type_trigger": "Внешний сигнал",
            "Value_trigger": "device3 ch_8 something",
            "Num_meas": "num",
        },
    },
    "device5": {
        "ch_1": {
            "type_trigger": "Таймер",
            "Value_trigger": 20,
            "Num_meas": "num",
        },
    },
    "device7": {
        "ch_1": {
            "type_trigger": "Внешний сигнал",
            "Value_trigger": "device7 ch_2 something",
            "Num_meas": "num",
        },
        "ch_2": {
            "type_trigger": "Внешний сигнал",
            "Value_trigger": "device7 ch_1 something",
            "Num_meas": "num",
        },
    },
}

main_dict2 = {
    "device1": {
        "ch_1": {
            "type_trigger": "Таймер",
            "Value_trigger": 30,
            "Num_meas": "num",
        },
    },
    "device2": {
        "ch_1": {
            "type_trigger": "Внешний сигнал",
            "Value_trigger": "device1 ch_1 something",
            "Num_meas": "Пока активны другие приборы",
        },
    },
}

if __name__ == '__main__':
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    objects_list = create_objects(main_dict1)
    ex = expDiagram()
    ex.set_content(objects_list)
    ex.show()
    sys.exit(app.exec_())
