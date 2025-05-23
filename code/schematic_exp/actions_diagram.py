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
import logging
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QGridLayout, QLabel, QScrollArea,
                             QSizePolicy, QVBoxLayout, QWidget, QSplitter)
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class deviceAction(QLabel):
    def __init__(self, name, info=None, color=None):
        super().__init__(name)
        self.base_color = color
        if color:
            self.setStyleSheet(f"background-color: {self.base_color};")
        if info:
            self.setToolTip(info)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(30)

class actionField(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)
        self.column_count = 0
        
    def add_new_block(self, action: deviceAction, num_row, num_col=None ):
        if num_col is None:
            num_col = self.column_count
            self.layout.addWidget(action, num_row+1, num_col, 1, 1)
            self.layout.addWidget(deviceAction(f"{num_col}"), 0, num_col, 1, 1)
        else:
            self.layout.addWidget(action, num_row+1, num_col, 1, 1)

        self.column_count += 1

class actDiagramWin(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        main_widget = QWidget()
        main_layout_horizontal = QHBoxLayout(main_widget)
        main_layout_horizontal.setContentsMargins(5, 5, 5, 5)
        main_layout_horizontal.setSpacing(0)
        
        # Левая область с именами
        self.names_widget = QWidget()
        self.names_layout = QGridLayout(self.names_widget)
        self.names_layout.setContentsMargins(5, 5, 5, 5)
        self.names_layout.setSpacing(5)
        
        self.scroll_area_hind = QScrollArea()
        self.scroll_area_hind.setWidget(self.names_widget)
        self.scroll_area_hind.setWidgetResizable(True)
        self.scroll_area_hind.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        # Правая область с действиями
        self.action_field = actionField()
        self.scroll_area_horizontal = QScrollArea()
        self.scroll_area_horizontal.setWidget(self.action_field)
        self.scroll_area_horizontal.setWidgetResizable(True)
        self.scroll_area_horizontal.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        # Синхронизация скролла
        self.scroll_area_hind.verticalScrollBar().valueChanged.connect(
            self.scroll_area_horizontal.verticalScrollBar().setValue
        )
        self.scroll_area_horizontal.verticalScrollBar().valueChanged.connect(
            self.scroll_area_hind.verticalScrollBar().setValue
        )

        splitter = QSplitter()
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        splitter.setOrientation(1)

        splitter.addWidget(self.scroll_area_hind)
        splitter.addWidget(self.scroll_area_horizontal)

        splitter.setHandleWidth(1)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        
        #main_layout_horizontal.addWidget(self.scroll_area_hind, 1)
        #main_layout_horizontal.addWidget(self.scroll_area_horizontal, 5)
        #main_layout.addWidget(main_widget)
        main_layout.addWidget(splitter)

@dataclass
class actorInfo:
    actor_name: str
    number_row: int
    color: str
    label: deviceAction  # Добавляем ссылку на виджет

class actDiagram:
    def __init__(self):
        self.diagram = actDiagramWin()
        self.actors = {}
        self.actor_actions = {}  # Словарь для отслеживания действий по актору
        self.current_number = 1

        self.diagram.names_layout.addWidget(deviceAction("Actors"), 0, 0)

    def add_actor(self, actor_name):
        new_color = "#%06x" % (0x809080 + self.current_number * 1000)
        number_row_actor = len(self.actors) + 1
        lb = deviceAction(actor_name, actor_name, new_color)
        self.actors[actor_name] = actorInfo(actor_name, number_row_actor, new_color, lb)
        self.diagram.names_layout.addWidget(lb, number_row_actor, 0)
        empty_block = deviceAction(f"")
        self.diagram.action_field.add_new_block(empty_block, number_row_actor, 0)
        if actor_name not in self.actor_actions:
            self.actor_actions[actor_name] = []
        self.actor_actions[actor_name].append(empty_block)
        self.current_number += 1

    def add_action(self, actor_name, action_info, action_name = ""):
        actor = self.actors.get(actor_name)
        if not actor:
            return False
        
        new_block = deviceAction(action_name, action_info, actor.color)
        self.diagram.action_field.add_new_block(new_block, actor.number_row)
        if actor_name not in self.actor_actions:
            self.actor_actions[actor_name] = []
        self.actor_actions[actor_name].append(new_block)

        scroll_bar = self.diagram.scroll_area_horizontal.horizontalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
        return True

    def set_actor_inactive(self, actor_name):
        """Визуально отображает неактивный прибор"""
        actor = self.actors.get(actor_name)
        if not actor:
            return False

        actor.label.setStyleSheet(
            f"background-color: #808080;"
            "color: #FFFFFF;"
            "text-decoration: line-through;"
        )
        return True

    def activate_all_actors(self):
        """Возвращает всем приборам активный вид"""
        for actor in self.actors.values():
            actor.label.setStyleSheet(f"background-color: {actor.color};")

    def clear_action_field(self):
        """Очищает поле действий, кроме виджетов в первом столбце"""
        layout = self.diagram.action_field.layout

        self.diagram.action_field.column_count = 0
        widgets_to_remove = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget:
                row, column, row_span, column_span = layout.getItemPosition(i)
                if column != 0:
                    widgets_to_remove.append(widget)
        
        for widget in widgets_to_remove:
            layout.removeWidget(widget)
            widget.deleteLater()
        for lst in self.actor_actions.values():
            del lst[1:]

        
        
    def remove_actor(self, actor_name):
        """Удаляет прибор и связанные с ним действия"""
        actor = self.actors.get(actor_name)
        if not actor:
            return False

        # Удаление метки прибора
        self.diagram.names_layout.removeWidget(actor.label)
        actor.label.deleteLater()

        # Удаление связанных действий
        for action in self.actor_actions.get(actor_name, []):
            self.diagram.action_field.layout.removeWidget(action)
            action.deleteLater()
        if actor_name in self.actor_actions:
            del self.actor_actions[actor_name]

        # Обновление номеров строк для оставшихся приборов
        del self.actors[actor_name]
        removed_row = actor.number_row
        for a in self.actors.values():
            if a.number_row > removed_row:
                a.number_row -= 1

        # Перемещение оставшихся виджетов в names_layout
        for a in self.actors.values():
            if a.number_row >= removed_row:
                self.diagram.names_layout.addWidget(a.label, a.number_row, 0)

        return True

class tester_diag(QWidget):
    def __init__(self, diag):
        super().__init__()
        self.diag = diag
        self.add_timer = QTimer(self)
        self.add_timer.timeout.connect(self.test_act_diag)
        self.actors_def = ["Ch1", "Ch2", "Ch3", "Ch4", "Ch5"]
        self.actors_added = []
        self.actors_removing = []
        self.counter_step = 0

    def test_act_diag(self):
        self.counter_step += 1
        if self.actors_def and random.randint(0, 1):
                new_actor = self.actors_def.pop(0)
                self.actors_added.append(new_actor)
                diag.add_actor(new_actor)

        elif self.actors_added:
                focus_actor = random.choice(self.actors_added)
                name = ""
                is_name = random.randint(0, 1)
                if is_name:
                    name = f"Action {random.randint(0, 100)}"
                diag.add_action(focus_actor, name, f"Description {random.randint(0, 100)}")

        if random.random() > 1 and not self.actors_def:
            diag.clear_action_field()
            print("Action field cleared")

        elif self.counter_step % 3 == 0 and self.actors_added:
            inactive_actor = random.choice(self.actors_added)
            self.actors_added.remove(inactive_actor)
            self.actors_removing.append(inactive_actor)
            diag.set_actor_inactive(inactive_actor)
            print(f"Actor {inactive_actor} set inactive")

        elif not self.actors_def and not self.actors_added and self.actors_removing:
            rem_actor = random.choice(self.actors_removing)
            self.actors_removing.remove(rem_actor)
            self.diag.remove_actor(rem_actor)
            print(f"Actor {rem_actor} removed")

        gc.collect()
        all_objects = gc.get_objects()
        print("Количество отслеживаемых объектов:", len(all_objects))

    def run(self):
        self.counter_step = 0
        self.add_timer.start(1000)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    qdarktheme.setup_theme()
    import random
    import gc

    diag = actDiagram()
    diag.diagram.setWindowTitle("Demo Act Diagram")

    test_diag = tester_diag(diag)
    test_diag.run()

    diag.diagram.show()
    sys.exit(app.exec_())