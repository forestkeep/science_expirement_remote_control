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
import copy
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QPolygon
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QGridLayout, QLabel, QScrollArea,
                             QSizePolicy, QVBoxLayout, QWidget, QSplitter)
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class deviceAction(QLabel):
    def __init__(self, name, info=None, color=None):
        super().__init__(name)
        self.base_color = color
        self.status = None
        if color:
            self.setStyleSheet(f"background-color: {self.base_color};")
        if info:
            self.setToolTip(info)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(30)

    def set_status(self, status):
        """Устанавливает статус блока и меняет стиль рамки"""
        self.status = status
        if status is True or status == 'True':
            self.setStyleSheet(f"background-color: {self.base_color}; border: 3px solid green;")
        elif status is False or status == 'False':
            self.setStyleSheet(f"background-color: {self.base_color}; border: 3px solid red;")
        else:
            self.setStyleSheet(f"background-color: {self.base_color};")  # без рамки

class ArrowOverlay(QWidget):
    """Прозрачный слой для рисования стрелок поверх actionField"""
    def __init__(self, diagram, parent=None):
        super().__init__(parent)
        self.diagram = diagram
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # не перехватывать события мыши
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):
        """Отрисовывает все стрелки из диаграммы"""
        super().paintEvent(event)
        if not self.diagram:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(100, 100, 100), 2, Qt.SolidLine)
        painter.setPen(pen)

        for (src_actor, src_idx), (dst_actor, dst_idx) in self.diagram.arrows:
            # Получаем блоки по сохранённым индексам
            src_blocks = self.diagram.actor_actions.get(src_actor, [])
            dst_blocks = self.diagram.actor_actions.get(dst_actor, [])
            if src_idx >= len(src_blocks) or dst_idx >= len(dst_blocks):
                continue  # блок был удалён, стрелка недействительна
            src_widget = src_blocks[src_idx]
            dst_widget = dst_blocks[dst_idx]

            # Получаем геометрию в координатах overlay (совпадают с координатами actionField)
            src_rect = src_widget.geometry()
            dst_rect = dst_widget.geometry()

            # Центры по вертикали
            src_y = src_rect.center().y()
            dst_y = dst_rect.center().y()

            # Точки: правая сторона source, левая сторона target
            x1 = src_rect.right()
            x2 = dst_rect.left()

            # Рисуем линию со стрелкой
            if src_y == dst_y:
                painter.drawLine(x1, src_y, x2, dst_y)
                self._draw_arrow(painter, QPoint(x2, dst_y), QPoint(x1, src_y))
            else:
                mid_x = (x1 + x2) // 2
                painter.drawLine(x1, src_y, mid_x, src_y)
                painter.drawLine(mid_x, src_y, mid_x, dst_y)
                painter.drawLine(mid_x, dst_y, x2, dst_y)
                self._draw_arrow(painter, QPoint(x2, dst_y), QPoint(mid_x, dst_y))

    def _draw_arrow(self, painter, tip, tail):
        """Рисует стрелку в конце линии от tail к tip"""
        arrow_size = 10
        angle = 30  # градусов
        vec = tip - tail
        length = (vec.x()**2 + vec.y()**2)**0.5
        if length == 0:
            return
        unit = QPoint(int(vec.x() / length), int(vec.y() / length))
        import math
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        left = QPoint(int(-unit.y() * sin_a + unit.x() * cos_a),
                      int(unit.x() * sin_a + unit.y() * cos_a))
        right = QPoint(int(unit.y() * sin_a + unit.x() * cos_a),
                       int(-unit.x() * sin_a + unit.y() * cos_a))
        p1 = tip - left * arrow_size
        p2 = tip - right * arrow_size
        painter.setBrush(QColor(100, 100, 100))
        painter.drawPolygon(QPolygon([tip, p1, p2]))

class actionField(QWidget):
    def __init__(self, diagram, parent=None):
        super().__init__(parent)
        self.diagram = diagram  # ссылка на actDiagram
        self.layout = QGridLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)
        self.column_count = 0

        # Создаём слой для стрелок
        self.overlay = ArrowOverlay(diagram, self)
        self.overlay.setGeometry(self.rect())
        self.overlay.show()

    def resizeEvent(self, event):
        """При изменении размера поля обновляем размер overlay"""
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())

    def add_new_block(self, action: deviceAction, num_row, num_col=None):
        if num_col is None:
            num_col = self.column_count
            self.layout.addWidget(action, num_row+1, num_col, 1, 1)
            # Добавляем заголовок столбца (номер)
            self.layout.addWidget(deviceAction(f"{num_col}"), 0, num_col, 1, 1)
        else:
            self.layout.addWidget(action, num_row+1, num_col, 1, 1)

        self.column_count += 1
        # После добавления нового блока обновляем слой со стрелками
        self.overlay.update()

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

        # Правая область с действиями (будет создана позже с ссылкой на диаграмму)
        self.action_field = None

        self.scroll_area_horizontal = QScrollArea()
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

        main_layout.addWidget(splitter)

@dataclass
class actorInfo:
    actor_name: str
    number_row: int
    color: str
    label: deviceAction

class actDiagram:
    def __init__(self, color_manager):
        self.diagram = actDiagramWin()
        self.color_manager = color_manager
        # Создаём actionField с ссылкой на self
        self.diagram.action_field = actionField(self)
        self.diagram.scroll_area_horizontal.setWidget(self.diagram.action_field)

        self.actors = {}
        self.actor_actions = {}  # словарь: имя актора -> список его блоков (deviceAction)
        # Стрелки хранятся как кортежи: ((actor_имя, индекс_в_actor_actions), (actor_имя, индекс_в_actor_actions))
        self.arrows = []
        self.current_number = 1

        self.diagram.names_layout.addWidget(deviceAction("Actors"), 0, 0)

    def add_actor(self, actor_name):
        new_color = self.color_manager.get_color(actor_name)
        number_row_actor = len(self.actors) + 1
        lb = deviceAction(actor_name, actor_name, new_color)
        self.actors[actor_name] = actorInfo(actor_name, number_row_actor, new_color, lb)
        self.diagram.names_layout.addWidget(lb, number_row_actor, 0)
        empty_block = deviceAction("")
        self.diagram.action_field.add_new_block(empty_block, number_row_actor, 0)
        if actor_name not in self.actor_actions:
            self.actor_actions[actor_name] = []
        self.actor_actions[actor_name].append(empty_block)
        self.current_number += 1

    def add_action(self, actor_name, action_info, action_name="", status=None, trigger=None):
        """
        Добавляет действие для актора.
        :param actor_name: имя актора
        :param action_info: всплывающая подсказка
        :param action_name: текст на блоке
        :param status: "ok", "not ok" или None
        :param trigger: имя актора-триггера или None/"time" (тогда стрелка не рисуется)
        """
        actor = self.actors.get(actor_name)
        if not actor:
            return False

        new_block = deviceAction(action_name, action_info, actor.color)
        if status:
            new_block.set_status(status)

        # Определяем индекс для триггера (если есть)
        trigger_info = None
        if trigger and trigger in self.actors and trigger != "time":
            trigger_actions = self.actor_actions.get(trigger, [])
            if trigger_actions:
                # Индекс последнего блока триггера на текущий момент
                trigger_idx = len(trigger_actions) - 1
                trigger_info = (trigger, trigger_idx)

        # Добавляем новый блок в список действий актора
        if actor_name not in self.actor_actions:
            self.actor_actions[actor_name] = []
        self.actor_actions[actor_name].append(new_block)

        # Добавляем в layout
        self.diagram.action_field.add_new_block(new_block, actor.number_row)

        # Если есть триггер, сохраняем стрелку
        if trigger_info:
            target_idx = len(self.actor_actions[actor_name]) - 1  # индекс только что добавленного
            self.arrows.append((trigger_info, (actor_name, target_idx)))

        # Прокрутка вправо
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
            # Оставляем только первый (пустой) блок в столбце 0
            del lst[1:]

        # Удаляем все стрелки, так как блоки, на которые они ссылались, удалены
        self.arrows.clear()
        # Обновляем overlay
        self.diagram.action_field.overlay.update()

    def remove_actor(self, actor_name):
        """Удаляет прибор и связанные с ним действия, а также стрелки с его участием"""
        actor = self.actors.get(actor_name)
        if not actor:
            return False

        # Удаляем стрелки, где этот актор участвует (как источник или цель)
        self.arrows = [arrow for arrow in self.arrows
                       if arrow[0][0] != actor_name and arrow[1][0] != actor_name]

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

        # Обновляем overlay
        self.diagram.action_field.overlay.update()
        return True

    def remove_all_actors(self):
        actors_list = copy.deepcopy(list(self.actors.keys()))
        for actor in actors_list:
            self.remove_actor(actor)
        self.current_number = 1

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
                self.diag.add_actor(new_actor)

        elif self.actors_added:
                focus_actor = random.choice(self.actors_added)
                name = ""
                is_name = random.randint(0, 1)
                if is_name:
                    name = f"Action {random.randint(0, 100)}"
                # Случайно добавляем статус
                status = random.choice([None, True, False])
                # Случайно добавляем триггер (если есть другие акторы)
                trigger = None
                if self.actors_added and random.random() > 0.5:
                    other = random.choice([a for a in self.actors_added if a != focus_actor] or [None])
                    if other:
                        trigger = other
                self.diag.add_action(focus_actor, f"Description {random.randint(0, 100)}",
                                     action_name=name, status=status, trigger=trigger)

        
        if random.random() > 1 and not self.actors_def:
            self.diag.clear_action_field()
            print("Action field cleared")

        elif self.counter_step % 3 == 0 and self.actors_added:
            inactive_actor = random.choice(self.actors_added)
            self.actors_added.remove(inactive_actor)
            self.actors_removing.append(inactive_actor)
            self.diag.set_actor_inactive(inactive_actor)
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