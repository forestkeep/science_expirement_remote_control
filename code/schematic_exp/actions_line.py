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

from PyQt5.QtWidgets import QGridLayout, QWidget
from PyQt5.QtWidgets import QLabel, QWidget

try:
	from stack_experiment import deviceAction
except:
    from schematic_exp.stack_experiment import deviceAction
    
class deviceAction(QLabel):
    def __init__(self, name, info, color):
        super().__init__(name)
        self.base_color = color

        self.setStyleSheet( f"background-color: {self.base_color};" )
        self.setToolTip( info)
        self.setContentsMargins(0, 0, 0, 0)

class actionField(QWidget):
    def __init__(self,  parent=None):
        super().__init__(parent)
        
        self.setContentsMargins(0, 0, 0, 0)
        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.last_column = 0
        self.setLayout(self.layout)
        
    def add_new_block(self, action: deviceAction, num_row ):     
        self.layout.addWidget(action, num_row, self.last_column, 1, 1)
        self.last_column += 1

            