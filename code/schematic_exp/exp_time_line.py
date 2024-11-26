from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QToolTip
from PyQt5.QtGui import QPainter, QBrush, QColor, QPalette
from PyQt5.QtCore import Qt, QRect
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
		self.rect_height = 10
		self.rect_width = 17
		self.setStyleSheet("QToolTip { background-color: rgb(50, 50, 60); color: white; }")
		#self.show()

	def mousePressEvent(self, event):
		for r in self.rects:
			if r["rect"].contains(event.pos()):
				QToolTip.showText(event.globalPos(), r["text"], self)
				return
        
	def set_data(self, meta_data_class):
		print("данные установлены в стек")
		self.actors_names = meta_data_class.actors_names
		self.exp_queue = meta_data_class.exp_queue
		self.queue_info = meta_data_class.queue_info
		self.rects = []
		for inf in self.queue_info:
			self.rects.append({"rect": None, "text": inf})
		self.update()

	def paintEvent(self, event):
		painter = QPainter(self)
		self.paintsome(painter = painter)
	def paintsome(self, painter):
			try:
				painter = QPainter(self)
				if self.actors_names:
        
					max_chars = max(len(name) for name in self.actors_names.values())
					offset_y = 15
					spacing = 2  # Отступ между прямоугольниками

					if self.actors_names:
						
						max_chars = max(len(name) for name in self.actors_names.values())
			
						for index, num_actor in enumerate(self.actors_names.keys()):
							name = self.actors_names[num_actor]
							offset_x = max_chars * 8
							painter.setPen( unique_colors[index] )
							painter.drawText(10, offset_y + self.rect_height - 5, name)

							brush = QBrush( unique_colors[index] )  # Цвет прямоугольников
							painter.setBrush(brush)

							painter.setPen( QColor(255, 255, 255, 255) )
							ind = 1
							for act in self.exp_queue:
								painter.drawText(13 + offset_x, 10, str(ind))
								if num_actor == act:
									self.rects[ind-1]["rect"] = QRect(10 + offset_x, offset_y-2, self.rect_width, self.rect_height)
									painter.drawRect(self.rects[ind-1]["rect"])
								else:
									pass
								ind+=1
								
								offset_x += self.rect_width + spacing  # Смещение по X для следующего прямоугольника

							offset_y += self.rect_height + 5  # Смещение по Y для следующей строки
				
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
		self.queue_info = []
		self.exp_queue = []
		self.exp_start_time = 0
		self.exp_stop_time = 0

def actions_table():
	test_data = metaDataExp()
	test_data.actors_names = {1: "Приборeerere 1", 2: "Прибор 2", 3: "Прибор 3", 4: "Прибор 4"}
	test_data.exp_queue = [1, 3, 2, 1, 3, 1, 2, 2, 2, 3, 1, 2, 1, 4, 4, 1]  # Примеры приборов для отображения
	test_data.queue_info = ["1", "3","2", "один измерение вот эо вот \n 444444444444444444444444444", "3", "1", "2", "2", "2", "3", "1", "2", "1", "4", "4", "1"]

	drawing_field = callStack()

	drawing_field.set_data(test_data)
	drawing_field.show()

	return drawing_field

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
     
    data = actions_table()
    
    sys.exit(app.exec_())
            