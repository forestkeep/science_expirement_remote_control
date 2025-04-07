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

import sys

import qdarktheme
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget

try:
	from stack_experiment import deviceAction
except:
    from schematic_exp.stack_experiment import deviceAction
    
class blockInfo():
    def __init__(self, name, info):
        self.name = name
        self.info = info

class actionLine(QWidget):
    def __init__(self, name, number, color, parent=None):
        super().__init__(parent)
        self.parent_wid = parent
        self.name = name
        self.number = number
        self.spacing = 2 # Отступ между прямоугольниками
        self.blocks = []
        
        self.block_h = 12
        self.block_w = 30
        self.empty_color = "background-color: rgba(0, 0, 0, 0);"
        self.default_color = color
        self.setContentsMargins(0, 0, 0, 0)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)
        
          
    def add_new_block(self, block: blockInfo = None):
        if block is None:
            new_block = deviceAction(ch_name="",
                            color=self.empty_color,
                            max_height = self.block_h,
                            max_width = self.block_w,
                            parent=self)
        else:
            new_block = deviceAction(ch_name=block.name,
                            color=self.default_color,
                            max_height = self.block_h,
                            max_width = self.block_w,
                            parent=self)
        self.layout.addWidget(new_block)


    def paintEvent(self, event):
        pass

def test_action_line():
    from stack_experiment import deviceAction
    test_line = actionLine("test", 1, "background-color: rgba(255, 80, 0, 255);")
    new_block = blockInfo(name = "test",
                           info="some info")
    test_line.add_new_block(new_block)
    test_line.show()
    
    new_block2 = blockInfo(name = "test",
                           info="some info")
    test_line.add_new_block()
    
    test_line.add_new_block(new_block2)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    test_action_line()
    sys.exit(app.exec_())
            