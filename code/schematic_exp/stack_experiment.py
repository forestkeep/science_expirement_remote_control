from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QFrame, QSizePolicy
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen
from PyQt5.QtCore import Qt, QPoint
import sys
import time
import qdarktheme

unique_colors= [
    QColor(186, 0, 0, 255),       
    QColor(0, 128, 0, 255),        
    QColor(120, 0, 255, 255),        
    QColor(0, 160, 240, 255),      
    QColor(128, 0, 128, 255),      
    QColor(255, 165, 0, 255),      
    QColor(255, 20, 147, 255),     
    QColor(255, 105, 180, 255),    
    QColor(255, 80, 0, 255),      
    QColor(0, 255, 127, 255),       
    QColor(0, 120, 120, 255),       
    QColor(75, 0, 130, 255),        
    QColor(200, 160, 150, 255)    
]

unique_colors1= [
    "rgba(186, 0, 0, 255)",       
    "rgba(0, 128, 0, 255)",        
    "rgba(120, 0, 255, 255)",        
    "rgba(0, 160, 240, 255)",      
    "rgba(128, 0, 128, 255)",      
    "rgba(255, 165, 0, 255)",      
    "rgba(255, 20, 147, 255)",     
    "rgba(255, 105, 180, 255)",    
    "rgba(255, 80, 0, 255)",      
    "rgba(0, 255, 127, 255)",       
    "rgba(0, 120, 120, 255)",       
    "rgba(75, 0, 130, 255)",        
    "rgba(200, 160, 150, 255)"     
]

class deviceAction(QWidget):
    def __init__(self, ch_name, color, max_height = 12, max_width = 30, parent=None):
        super().__init__(parent)
        self.parent_wid = parent
        self.base_color = color
        self.setObjectName("device")
        self.setMouseTracking(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.ch_name = ch_name

        self.label_ch = QLabel( ch_name )
        self.label_ch.setMinimumSize( max_width, max_height)
        
        self.label_ch.setStyleSheet(self.base_color)
        
        layout.addWidget(self.label_ch)

        self.frame = QFrame(self)
        self.frame.setFrameShape(QFrame.Panel)
        self.frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        

        self.frame.setLayout(layout)

        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(self.frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.setLayout(outer_layout)

        self.label_ch.raise_()
        self.is_check = False

    def mousePressEvent(self, event):
        print(3434343)
        
    def mouseMoveEvent(self, event):
        pass
        
    def mouseReleaseEvent(self, event):
        self.dragging = False

    def toggle_selection(self, set_check = None):
        pass

    def set_default_style(self):
        pass
        #self.frame.setStyleSheet(self.base_color)
        
class callStack(QWidget):
    def __init__(self):
        super().__init__()
        self.actors_names = {}
        self.exp_queue = []
        self.objects = []
        self.spacing = 2 # Отступ между прямоугольниками
        
        self.rect_height = 12
        self.rect_width = 30
        
    def set_data(self, meta_data_class):
        print("данные установлены в стек")
        self.actors_names = meta_data_class.actors_names
        self.exp_queue = meta_data_class.exp_queue
               
        self.add_blocks()
        self.update()
        
    def add_blocks(self):
        painter = QPainter(self)
        self.offset_y = 0
        self.actions = []
        self.max_width = 100

        if self.actors_names:
            max_chars = max(len(name) for name in self.actors_names.values())
            
            for index, num_actor in enumerate(self.actors_names.keys()):
                offset_x = max_chars * 6

                for act in self.exp_queue:
                    if num_actor == act:
                        new_block = deviceAction(ch_name='123444',
                                       color=f"background-color: {unique_colors1[index]};",
                                       max_height = self.rect_height,
                                       max_width = self.rect_width,
                                       parent=self)
                        new_block.move(offset_x, self.offset_y-6)
                        self.actions.append(new_block)
                    
                    offset_x += self.rect_width + self.spacing

                self.offset_y += self.rect_height+6

                painter.setPen( QColor(100, 100, 100, 255) )
                painter.drawLine(0, self.offset_y - 5, self.width(), self.offset_y - 5) 

                self.max_width = max(self.max_width, offset_x + 10)

    def paintEvent(self, event):
        painter = QPainter(self)
        offset_y_lines = 5
        
        self.y_line_points = []

        if self.actors_names:
            max_chars = max(len(name) for name in self.actors_names.values())
          
            for index, num_actor in enumerate(self.actors_names.keys()):
                name = self.actors_names[num_actor]
                offset_x = max_chars * 8
                painter.setPen( unique_colors[index] )
                painter.drawText(10, offset_y_lines + self.rect_height - 5, name)
                
                for act in self.exp_queue:     
                    offset_x += self.rect_width + self.spacing
                offset_y_lines += self.rect_height+6

                self.y_line_points.append(offset_y_lines - 5)

            self.max_width = max(self.max_width, offset_x + 10) 
         
            self.setMinimumSize(self.max_width, offset_y_lines)
            painter.setPen( QColor(100, 100, 100, 255) )
            
            for y_coord in self.y_line_points:
                
                painter.drawLine(0, y_coord, self.max_width, y_coord)
            
class metaDataExp():
    def __init__(self):
        self.actors_names = {}
        self.actors_classes = {}
        self.numbers = {}
        self.exp_queue = []
        self.exp_start_time = 0
        self.exp_stop_time = 0

def actions_table():
    test_data = metaDataExp()
    test_data.actors_names = {1: "Приборeerere 1", 2: "Прибор 2", 3: "Прибор 3", 4: "Прибор 4"}
    test_data.exp_queue = [1, 3, 2, 1, 3, 1, 2, 2, 2, 3, 1, 2, 1, 4, 4, 1]  # Примеры приборов для отображения

    drawing_field = callStack()
    drawing_field.set_data(test_data)
    drawing_field.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
     
    actions_table()
    
    sys.exit(app.exec_())
            
