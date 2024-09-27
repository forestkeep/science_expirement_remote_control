import sys
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
import qdarktheme
import math
from enum import Enum


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

class DraggableLabel(QLabel):
    def __init__(self, text, parent):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.drag_start_position = None

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.create_copy(event.pos())
        if event.buttons() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if self.drag_start_position is None:
            return
        if event.buttons() == Qt.LeftButton:
            diff = QPoint(event.pos() - self.drag_start_position)
            self.move(self.pos() + diff)
            self.parentWidget().update()

    def mouseReleaseEvent(self, event):
        self.drag_start_position = None

    def create_copy(self, pos):
        new_label = DraggableLabel(self.text(), self.parentWidget())
        new_label.setStyleSheet(self.styleSheet())
        new_label.move(self.pos() + QPoint(20, 20))
        new_label.show()

class connection():
    '''save connection two some objects'''
    def __init__(self, base_widget = None, name = None):
        self.base_widget = base_widget
        self.first_unit = None
        self.second_unit = None
        self.name = name
        self.pen = QPen(QColor(255, 255, 255), 1, Qt.SolidLine)
        self.type = connectionType.SINGLE

    def set_type(self, type: connectionType):
        self.type = type

    def set_units(self, first_unit = False, second_unit = False):
        if first_unit is not False:
            self.first_unit = first_unit
        if second_unit is not False:
            self.second_unit = second_unit

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
        
        x = self.first_unit.pos().x() + self.first_unit.width() * (2 / 3)
        y = self.first_unit.pos().y() + self.first_unit.height() * (2 / 3)
        width = self.first_unit.width()
        height = self.first_unit.height()
        
        painter.drawRect(int(x), int(y), width, height)
        
        text = str(self.name)  # Замените на нужный текст
        text_width = painter.fontMetrics().boundingRect(text).width()
        text_x = int(x + (width - text_width) / 2)
        text_y = int(y + height)

        painter.drawText(text_x, text_y, text)
        x = self.first_unit.pos().x() + self.first_unit.width() * (2 / 3)
        y = self.first_unit.pos().y() + self.first_unit.height()
        self.add_in_simbol(QPoint(int(x), int(y)))

    def draw_line(self):
        painter = QPainter(self.base_widget)
        painter.setPen(self.pen)
        
        start_point, end_point, direction_first, is_overlap = self.get_coords()

        if direction_first != False:
            if is_overlap:
                #три линии
                midpoint = QPoint( int((start_point.x() + end_point.x()) / 2) , int((start_point.y() + end_point.y()) / 2))
                if direction_first == Position.LEFT or direction_first == Position.RIGHT:
                    painter.drawLine(start_point.x(), start_point.y(), midpoint.x(), start_point.y())
                    painter.drawLine(midpoint.x(), start_point.y(), midpoint.x(), end_point.y())
                    painter.drawLine(midpoint.x(), end_point.y(), end_point.x(), end_point.y())
                else:
                    painter.drawLine(start_point.x(), start_point.y(), start_point.x(), midpoint.y())
                    painter.drawLine(start_point.x(), midpoint.y(), end_point.x(), midpoint.y())
                    painter.drawLine(end_point.x(), midpoint.y(), end_point.x(), end_point.y())
            else:
                #две линии
                if direction_first == Position.LEFT or direction_first==Position.RIGHT:
                    painter.drawLine(start_point.x(), start_point.y(), end_point.x(), start_point.y())
                    painter.drawLine(end_point.x(), start_point.y(), end_point.x(), end_point.y())
                if direction_first == Position.TOP or direction_first==Position.BOTTOM:
                    painter.drawLine(start_point.x(), start_point.y(), start_point.x(), end_point.y())
                    painter.drawLine(start_point.x(), end_point.y(), end_point.x(), end_point.y())

        
            self.add_in_simbol(end_point)
        
    def draw( self ):
            if self.first_unit is None or self.second_unit is None:
                return
            elif self.first_unit == self.second_unit:
                self.draw_connection_to_self()
            else:
                self.draw_line()

class expDiagram(QWidget):
    def __init__(self):
        super().__init__()


        '''
        self.labels = [
            DraggableLabel('Блок питания', self),
            DraggableLabel('Первый', self),
            DraggableLabel('Второйsdfdfdgdgdfdfgfdg', self)
        ]

        #self.labels[0].setStyleSheet("background-color: lightblue;")
        self.labels[1].move(150, 0)
        self.labels[1].setStyleSheet("border: 1px solid rgb(0, 150, 0); border-radius: 5px; QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white;}")
        #self.labels[1].setFixedSize(50,50)
        self.labels[2].move(300, 0)
        #self.labels[2].setFixedSize(50,50)
        self.labels[2].setStyleSheet("border: 1px solid rgb(0, 150, 0); border-radius: 5px; QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white;}")

        self.connect12 = connection(self, "do action")
        self.connect12.set_units(self.labels[1], self.labels[2])
        self.connect12.setStyle(QPen(QColor(0, 100, 0), 3, Qt.DashLine))

        self.connect21 = connection(self, "do action")
        self.connect21.set_units(self.labels[2], self.labels[1])
        self.connect21.setStyle(QPen(QColor(100, 0, 0), 3, Qt.DashLine))
        self.connections = [self.connect12, self.connect21]
        '''
        self.setGeometry(300, 300, 400, 200)
        self.setWindowTitle('Перемещение и копирование лейблов')

    def set_content(self, objects: list):
        self.objects = objects
        self.labels = []
        for obj in objects:
            lb = DraggableLabel(obj.name, self)
            lb.setStyleSheet(f"background-color: {obj.color};")
            self.labels.append(lb)

        self.connections = []
        for index, obj in enumerate(objects):

            if obj.type_trigger == "Таймер":
                con = connection(self, str(obj.value_trigger) + "сек")
                con.set_units(self.labels[index], self.labels[index])
                self.connections.append(con)
                continue

            try:
                print(obj.value_trigger)
                components = obj.value_trigger.split()
                name = components[0] + " " + components[1]
            except:
                continue

            for label in self.labels:
                if name == label.text():
                    con = connection(self, "do action")
                    con.set_units(label, self.labels[index])
                    self.connections.append(con)

    def paintEvent(self, event):
            for con in self.connections:
                con.draw()

class connectObject:
    def __init__(self, device, ch, type, value, num, color):
        self.name = f"{device} {ch}"
        self.type_trigger = type
        self.value_trigger = value
        self.number_meas = num
        self.color = color

def create_objects(main_dict):
    objects = []
    
    # Список уникальных цветов
    unique_colors = ["красный", "зеленый", "синий", "желтый", "фиолетовый", "оранжевый"]
    unique_colors = ["#FF0000", "#008000", "#0000FF", "#FFFF00", "#800080", "#FFA500"]
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
    },
    "device5": {
        "ch_1": {
            "type_trigger": "Таймер",
            "Value_trigger": 20,
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


