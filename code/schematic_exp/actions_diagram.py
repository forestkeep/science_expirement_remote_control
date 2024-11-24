from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QFrame, QSizePolicy
from PyQt5.QtWidgets import QApplication, QScrollArea, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt
import sys
import qdarktheme

from actions_line import actionLine, blockInfo
from stack_experiment import unique_colors1
class actDiagramWin(QWidget):
    def __init__(self):
        super().__init__()
        
        main_layout = QVBoxLayout()
        scroll_area_vertical = QScrollArea()
        main_layout.addWidget(scroll_area_vertical)

        main_widget = QWidget()
        main_layout_horizontal = QHBoxLayout()
        main_widget.setLayout(main_layout_horizontal)

        self.names_widget = QWidget()
        self.names_layout = QVBoxLayout()
        self.names_layout.setContentsMargins(0, 0, 0, 0)
        self.names_layout.setSpacing(0)

        self.names_widget.setLayout(self.names_layout)

        self.actions_widget = QWidget()
        self.actions_layout = QVBoxLayout()
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(0)
        
        self.actions_widget.setLayout(self.actions_layout)
        
        self.scroll_area_hind = QScrollArea()
        self.scroll_area_hind.setWidget(self.names_widget)
        self.scroll_area_hind.setWidgetResizable(True)
        self.scroll_area_hind.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area_hind.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area_hind.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.scroll_area_hind.setContentsMargins(0, 0, 0, 0)

        self.scroll_area_horizontal = QScrollArea()
        self.scroll_area_horizontal.setWidget(self.actions_widget)
        self.scroll_area_horizontal.setWidgetResizable(True)
        self.scroll_area_horizontal.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area_horizontal.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        

        main_layout_horizontal.addWidget(self.scroll_area_hind)
        main_layout_horizontal.addWidget(self.scroll_area_horizontal)

        scroll_area_vertical.setWidget(main_widget)
        scroll_area_vertical.setWidgetResizable(True)
        scroll_area_vertical.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area_vertical.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.setLayout(main_layout)
        
    def resizeEvent(self, event):
        pass
        # Получаем новые размеры окна
        #max_h = int(self.actions_widget.height() - self.scroll_area_horizontal.horizontalScrollBar().sizeHint().height())
        
        #self.names_widget.setMaximumHeight(max_h)
        
        
class actDiagram():
	def __init__(self):
		self.diagram = actDiagramWin()
		self.actors = {}
		self.current_number = 1
		self.max_width_name_actors = 0
  
		self.diagram.show()

	def add_actor(self, actor_name):
		new_color = unique_colors1[self.current_number - 1]
		new_act_line = actionLine(name=actor_name,
                            number = self.current_number,
                            color = f"background-color: {new_color};"
                            )
		self.actors[actor_name] = new_act_line
  
		self.diagram.actions_layout.addWidget( new_act_line )
		lb = QLabel(actor_name)
		self.diagram.names_layout.addWidget( lb )
     
		self.current_number+=1
  
		font_metrics = lb.fontMetrics()
		text_size = font_metrics.size(0, lb.text())  # Получаем размеры текста

  
		if self.max_width_name_actors < text_size.width():
			self.max_width_name_actors = int(text_size.width()*1.2)
   
		self.diagram.scroll_area_hind.setMaximumWidth(self.max_width_name_actors)
		self.diagram.scroll_area_hind.setMinimumWidth(self.max_width_name_actors)
  
	def add_action(self, actor_name, action_name, action_info) -> bool:

		if actor_name in self.actors.keys():
      
			new_block = blockInfo(name = action_name,
                              info = action_info
                              )
   
			for name, line in self.actors.items():
					if name == actor_name:
						line.add_new_block(new_block)
					else:
						line.add_new_block(None)
      
			return True

		return False
        
def test_act_diag():
    diag = actDiagram()
    diag.diagram.setWindowTitle("Demo Act Diagram")
    actors = ["Ch1", "Ch2333rrrrrrrrrrrrr3", "Ch3333", "Ch4", "Ch5"]
    for actor in actors:
        diag.add_actor(actor_name = actor)
        
    for i in range(1):
        for actor in actors:
            if not diag.add_action(actor_name  = actor,
                            action_name = f"Действие {i}",
                            action_info = f"Описание действия {i}"):
                print("Ошибка добавления действия")
        

    return diag
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    win = test_act_diag()
    sys.exit(app.exec_())