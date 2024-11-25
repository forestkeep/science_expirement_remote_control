from PyQt5.QtWidgets import QWidget, QApplication, QLabel
from PyQt5.QtGui import QPainter, QBrush, QColor
import sys
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

class callStack(QWidget):
	def __init__(self):
		super().__init__()
		self.setGeometry(100, 100, 600, 400)
		self.max_width = 100
		self.y_line_points = []
		self.actors_names = {}
		self.lb = QLabel("ererer")
		print("создали стек")
		#self.show()
        
	def set_data(self, meta_data_class):
		print("данные установлены в стек")
		self.actors_names = meta_data_class.actors_names
		self.exp_queue = meta_data_class.exp_queue
		self.update()

	def paintEvent(self, event):
			try:
				painter = QPainter(self)
				if self.actors_names:
        
					max_chars = max(len(name) for name in self.actors_names.values())
					offset_y = 0
					rect_height = 15
					rect_width = 30
					spacing = 2  # Отступ между прямоугольниками

					if self.actors_names:
						
						max_chars = max(len(name) for name in self.actors_names.values())
			
						for index, num_actor in enumerate(self.actors_names.keys()):
							name = self.actors_names[num_actor]
							offset_x = max_chars * 8
							painter.setPen( unique_colors[index] )
							painter.drawText(10, offset_y + rect_height - 5, name)

							brush = QBrush( unique_colors[index] )  # Цвет прямоугольников
							painter.setBrush(brush)
							for act in self.exp_queue:
								if num_actor == act:
									painter.drawRect(10 + offset_x, offset_y-2, rect_width, rect_height)
								else:
									pass
								
								offset_x += rect_width + spacing  # Смещение по X для следующего прямоугольника

							offset_y += rect_height + 5  # Смещение по Y для следующей строки
				
							self.y_line_points.append(offset_y - 5)
						self.max_width = max(self.max_width, offset_x + 10) 
						self.setMinimumSize(self.max_width, offset_y)
						painter.setPen( QColor(100, 100, 100, 255) )
						for y_coord in self.y_line_points:   
							painter.drawLine(0, y_coord, self.max_width, y_coord)
			except Exception as e:
				print(f"error {e}")


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
    drawing_field.show()
    drawing_field.set_data(test_data)

    return drawing_field


if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
     
    data = actions_table()
    
    sys.exit(app.exec_())
            