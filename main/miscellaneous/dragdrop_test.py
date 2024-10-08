import sys
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QFrame, QSizePolicy
import qdarktheme
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

class blockDevice(QWidget):
    def __init__(self, ch_name, dev_name, parent=None):
        super().__init__(parent)
        self.base_color = "background-color: rgba(250, 250, 250, 50);"
        self.setObjectName("device")
        self.is_ctrl_pressed = False
        self.setMouseTracking(True)
        self.dragging = False
        self.last_pos = None
        self.type_trigger = None
        self.value_trigger = None
        self.number_meas = None
        
        layout = QVBoxLayout(self)

        self.ch_name = ch_name
        self.dev_name = dev_name

        self.label_ch = QLabel(self.ch_name)
        layout.addWidget(self.label_ch)
        
        self.label_dev = QLabel(self.dev_name)
        layout.addWidget(self.label_dev)

        self.frame = QFrame(self)
        self.frame.setFrameShape(QFrame.Panel)
        #self.frame.setStyleSheet("background-color: lightgreen;")
        self.frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.frame.setLayout(layout)

        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(self.frame)

        self.setLayout(outer_layout)

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
            self.create_copy()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(self.pos() + event.pos() - self.drag_start_position)
            self.parentWidget().update()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def toggle_selection(self, set_check = None):
        # Изменяем стиль выделенного виджета
        if set_check == True:
            self.frame.setStyleSheet(self.base_color)
            self.is_check = True
            
        elif set_check == False:
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
        new_device = blockDevice(self.ch_name + "(copy)",self.parentWidget())
        new_device.frame.setStyleSheet(self.frame.styleSheet())
        new_device.move(self.pos() + QPoint(20, 20))
        new_device.show()

    def set_default_style(self):
        self.frame.setStyleSheet(self.base_color)

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
            print(all_child_widgets)
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

            if obj.type_trigger == "Таймер":
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
        self.auto_place(self.labels)


    def auto_place(self, components: list):
        '''
        группа 1: компоненты работают по таймеру и от них не зависит ни один другой компонент
        группа 2: компоненты зависят от других компонентов и в цепочке есть компонент с таймером
        группа 3: компоненты зависят от других компонентов и в цепочке нет ни одного компонента с таймером'''
        group3 = []
        for com in components:
            group3.append(com)

        for obj in group3:
            obj.group = None

        group1 = []
        group2 = []
        groups = [group1, group2, group3]
        is_exit = False
        while group3 and not is_exit:
            for obj in group3:
                if obj.group != None:
                    continue
                if obj.type_trigger == "Таймер":
                    is_checked = False
                    for obj2 in group3:
                        if isinstance(obj2.value_trigger, str):
                            if obj.ch_name in obj2.value_trigger and obj.dev_name in obj2.value_trigger:
                                p_group =  []
                                p_group.append(obj)
                                p_group.append(obj2)
                                group2.append(p_group)
                                group3.remove(obj)
                                group3.remove(obj2)
                                obj.group = 2
                                obj2.group = 2
                                is_checked = True
                                is_exit = False
                    if not is_checked:
                        group1.append(obj)
                        group3.remove(obj)
                        obj.group = 1
                        is_exit = False
                else:
                    #здесь компонент может относится как к группе 2 так и к группе 3, но у них у всех в триггере стоят компоненты
                    for group in group2:
                        for obj2 in group:
                            if isinstance(obj2.value_trigger, str):
                                if obj.ch_name in obj2.value_trigger and obj.dev_name in obj2.value_trigger:
                                    group.append(obj)
                                    components.remove(obj)
                                    obj.group = 2
                                    is_exit = False
                                    break
                        if obj.group != None:
                            break #условие необходимо для ускорения процесса, если элемент уже помещен в группу, то дальше итерироваться по группам не нужно
            is_exit = True

        y = 0
        for obj in group1:
            obj.move(0, y)
            y +=int( obj.height()*3.2 )

        print(group2)
        print(group3)


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
        for dev, ch in install_class.get_active_ch_and_device():
            y = install_class.message_broker.get_subscribers(publisher = ch, name_subscribe = ch.do_operation_trigger)
            
            
            lb = blockDevice(ch.get_name(), dev.get_name(), self)
            lb.show()
            if color_index < len(unique_colors):
                col = unique_colors[color_index]
                color_index += 1
            lb.setStyleSheet(f"background-color: {col};")
            self.labels.append(lb)

        self.connections = []
        if False:
            for index, obj in enumerate(objects):

                if obj.type_trigger == "Таймер":
                    con = connection(self, str(obj.value_trigger) + "сек")
                    con.set_units(self.labels[index], self.labels[index])
                    self.connections.append(con)
                    continue

                try:
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
        self.ch_name = ch
        self.dev_name = device

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
            "Value_trigger": "device4 ch_1 something",
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
