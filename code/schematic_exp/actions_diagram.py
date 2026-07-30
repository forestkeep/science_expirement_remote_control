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
import math
import logging
import copy
import colorsys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import qdarktheme
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QPolygon
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QGridLayout, QLabel,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget, QSplitter
)

logger = logging.getLogger(__name__)

class deviceAction(QLabel):
    """Блок действия актора (наследует QLabel)."""

    def __init__(self, name: str, info: Optional[str] = None, color: Optional[str] = None):
        super().__init__(name)
        self.base_color = color
        self.status: Optional[Union[bool, str]] = None
        self.column = 0
        if color:
            self.setStyleSheet(f"background-color: {self.base_color};")
        if info:
            self.setToolTip(info)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(30)

    def set_status(self, status: Optional[Union[bool, str]]) -> None:
        """Устанавливает статус и соответствующий стиль рамки."""
        self.status = status
        if status in (True, 'True'):
            self.setStyleSheet(f"background-color: {self.base_color}; border: 3px solid green;")
        elif status in (False, 'False'):
            self.setStyleSheet(f"background-color: {self.base_color}; border: 3px solid red;")
        else:
            self.setStyleSheet(f"background-color: {self.base_color};")


class ArrowOverlay(QWidget):
    """Прозрачный слой для рисования стрелок между блоками."""

    def __init__(self, diagram: "actDiagram", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.diagram = diagram
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.diagram:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for src_actor, src_idx, dst_actor, dst_idx, color in self.diagram.arrows:
            src_blocks = self.diagram.actor_actions.get(src_actor, [])
            dst_blocks = self.diagram.actor_actions.get(dst_actor, [])
            if src_idx >= len(src_blocks) or dst_idx >= len(dst_blocks):
                continue
            src_widget = src_blocks[src_idx]
            dst_widget = dst_blocks[dst_idx]
            src_rect = src_widget.geometry()
            dst_rect = dst_widget.geometry()
            src_y = src_rect.center().y()
            dst_y = dst_rect.center().y()
            x1 = src_rect.right()
            x2 = dst_rect.left()

            pen = QPen(color, 2, Qt.SolidLine)
            painter.setPen(pen)

            if src_y == dst_y:
                painter.drawLine(x1, src_y, x2, dst_y)
                self._draw_arrow(painter, QPoint(x2, dst_y), QPoint(x1, src_y), color)
            else:
                mid_x = (x1 + x2) // 2
                painter.drawLine(x1, src_y, mid_x, src_y)
                painter.drawLine(mid_x, src_y, mid_x, dst_y)
                painter.drawLine(mid_x, dst_y, x2, dst_y)
                self._draw_arrow(painter, QPoint(x2, dst_y), QPoint(mid_x, dst_y), color)

    def _draw_arrow(self, painter: QPainter, tip: QPoint, tail: QPoint, color: QColor) -> None:
        """Рисует треугольную стрелку у tip, направленную от tail к tip."""
        arrow_size = 10
        angle = 30
        vec = tip - tail
        length = (vec.x()**2 + vec.y()**2)**0.5
        if length == 0:
            return
        unit = QPoint(int(vec.x() / length), int(vec.y() / length))
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        left = QPoint(int(-unit.y() * sin_a + unit.x() * cos_a),
                      int(unit.x() * sin_a + unit.y() * cos_a))
        right = QPoint(int(unit.y() * sin_a + unit.x() * cos_a),
                       int(-unit.x() * sin_a + unit.y() * cos_a))
        p1 = tip - left * arrow_size
        p2 = tip - right * arrow_size
        painter.setBrush(color)
        painter.drawPolygon(QPolygon([tip, p1, p2]))


class actionField(QWidget):
    """Поле, на котором размещаются блоки действий (deviceAction)."""

    def __init__(self, diagram: "actDiagram", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.diagram = diagram
        self.layout = QGridLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)
        self.max_column = 0
        self.overlay = ArrowOverlay(diagram, self)
        self.overlay.setGeometry(self.rect())
        self.overlay.show()

    def add_new_block(self, action: deviceAction, num_row: int, column: int) -> None:
        """Добавляет блок в указанную позицию и создаёт заголовок столбца при необходимости."""
        action.column = column
        self.layout.addWidget(action, num_row, column)
        if column > self.max_column:
            self.max_column = column
        if self.layout.itemAtPosition(0, column) is None:
            header = deviceAction(f"{column}")
            self.layout.addWidget(header, 0, column)
        self.overlay.update()

    def rebuild_layout(self, actors_sorted: List["actorInfo"],
                       actor_actions: Dict[str, List[deviceAction]]) -> None:
        """Полностью перестраивает размещение блоков действий."""
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget and widget is not self.overlay:
                self.layout.removeWidget(widget)

        for col in range(self.max_column + 1):
            header = deviceAction(f"{col}")
            self.layout.addWidget(header, 0, col)

        for actor in actors_sorted:
            for action in actor_actions.get(actor.actor_name, []):
                self.layout.addWidget(action, actor.number_row, action.column)

        self.overlay.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())


class actDiagramWin(QWidget):
    """Главное окно диаграммы действий."""

    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_widget = QWidget()
        main_layout_horizontal = QHBoxLayout(main_widget)
        main_layout_horizontal.setContentsMargins(5, 5, 5, 5)
        main_layout_horizontal.setSpacing(0)

        self.names_widget = QWidget()
        self.names_layout = QGridLayout(self.names_widget)
        self.names_layout.setContentsMargins(5, 5, 5, 5)
        self.names_layout.setSpacing(5)

        self.scroll_area_hind = QScrollArea()
        self.scroll_area_hind.setWidget(self.names_widget)
        self.scroll_area_hind.setWidgetResizable(True)
        self.scroll_area_hind.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.action_field: Optional[actionField] = None

        self.scroll_area_horizontal = QScrollArea()
        self.scroll_area_horizontal.setWidgetResizable(True)
        self.scroll_area_horizontal.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

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
    trigger: Optional[str] = None


class actDiagram:
    """Управляет диаграммой действий: акторы, блоки, стрелки."""

    def __init__(self, color_manager=None):
        self.diagram = actDiagramWin()
        self.color_manager = color_manager
        self.diagram.action_field = actionField(self)
        self.diagram.scroll_area_horizontal.setWidget(self.diagram.action_field)

        self.actors: Dict[str, actorInfo] = {}
        self.actor_actions: Dict[str, List[deviceAction]] = {}
        # Стрелка хранит: (src_actor, src_idx, dst_actor, dst_idx, color)
        self.arrows: List[Tuple[str, int, str, int, QColor]] = []
        self.current_number = 0

        self._stop_rebuild = False

        # Палитра и счётчик для уникальных цветов стрелок
        self._arrow_color_index = 0
        self._arrow_colors = self._generate_arrow_palette(20)

        # Словарь для постоянных цветов пар акторов: ключ – кортеж (actor1, actor2) в алфавитном порядке
        self._pair_colors: Dict[Tuple[str, str], QColor] = {}

        self.diagram.names_layout.addWidget(deviceAction("Actors"), 0, 0)

    def _get_next_color(self, actor_name: str) -> str:
        """Возвращает цвет для нового актора, используя color_manager или серый по умолчанию."""
        if self.color_manager:
            return self.color_manager.get_color(actor_name)
        return "#CCCCCC"

    def _generate_arrow_palette(self, n: int) -> List[QColor]:
        """Генерирует n различимых цветов, хорошо видимых на белом и чёрном фоне."""
        colors = []
        for i in range(n):
            hue = i / n
            # saturation=0.9, value=0.55 даёт насыщенные цвета средней яркости,
            # контрастные и на светлом, и на тёмном фоне
            r, g, b = colorsys.hsv_to_rgb(hue, 0.9, 0.55)
            colors.append(QColor(int(r * 255), int(g * 255), int(b * 255)))
        return colors

    def _get_next_arrow_color(self) -> QColor:
        """Возвращает следующий цвет из палитры (используется только для новой пары акторов)."""
        color = self._arrow_colors[self._arrow_color_index % len(self._arrow_colors)]
        self._arrow_color_index += 1
        return color

    def reset_color_index(self) -> None:
        self._arrow_color_index = 0

    def _rebuild_layouts(self) -> None:
        """Перестраивает панель имён и поле действий."""
        names_layout = self.diagram.names_layout
        for i in reversed(range(names_layout.count())):
            widget = names_layout.itemAt(i).widget()
            if widget:
                names_layout.removeWidget(widget)
        names_layout.addWidget(deviceAction("Actors"), 0, 0)

        sorted_actors = sorted(self.actors.values(), key=lambda a: a.number_row)
        for actor in sorted_actors:
            names_layout.addWidget(actor.label, actor.number_row, 0)

        self.diagram.action_field.rebuild_layout(sorted_actors, self.actor_actions)

    def optimize_actor_order(self, max_iterations: int = 10) -> None:
        """
        Оптимизирует порядок акторов, минимизируя суммарную длину стрелок.
        Правила:
        - Акторы без исходящих триггеров (out=0) размещаются на крайних строках
        (чередование верх/низ).
        - Акторы-триггеры (out>0) — в центре. Чем выше out_degree, тем ближе к середине.
        Для уменьшения длины стрелок внутри каждой группы используется
        итеративная барицентрическая эвристика.
        """
        actors_list = list(self.actors.values())
        n = len(actors_list)
        if n < 2:
            if n == 1:
                actors_list[0].number_row = 1
                self._rebuild_layouts()
            return

        out_deg = {a.actor_name: 0 for a in actors_list}
        in_deg  = {a.actor_name: 0 for a in actors_list}
        for src, _, dst, _, _ in self.arrows:
            out_deg[src] += 1
            in_deg[dst] += 1

        group_A = [a for a in actors_list if out_deg[a.actor_name] == 0 and in_deg[a.actor_name] != 1]
        group_B = [a for a in actors_list if out_deg[a.actor_name] == 0 and in_deg[a.actor_name] == 1]
        group_C = [a for a in actors_list if out_deg[a.actor_name] > 0]
        group_C.sort(key=lambda a: out_deg[a.actor_name], reverse=True)

        for i, a in enumerate(actors_list, start=1):
            a.number_row = i

        for _ in range(max_iterations):
            bary = {a.actor_name: None for a in actors_list}
            for src, _, dst, _, _ in self.arrows:
                if dst in bary:
                    if bary[dst] is None:
                        bary[dst] = []
                    bary[dst].append(self.actors[src].number_row)
            for name in bary:
                if isinstance(bary[name], list):
                    bary[name] = sum(bary[name]) / len(bary[name])
                elif bary[name] is None:
                    bary[name] = (n + 1) / 2

            bary_c = {}
            for src, _, dst, _, _ in self.arrows:
                if src in [a.actor_name for a in group_C]:
                    bary_c.setdefault(src, []).append(self.actors[dst].number_row)
            for a in group_C:
                name = a.actor_name
                if name in bary_c:
                    bary[name] = sum(bary_c[name]) / len(bary_c[name])
                else:
                    bary[name] = (n + 1) / 2

            ab = group_A + group_B
            ab.sort(key=lambda a: bary[a.actor_name])

            num_ab = len(ab)
            edge_pos = []
            top, bottom = 1, n
            for i in range(num_ab):
                if i % 2 == 0:
                    edge_pos.append(top)
                    top += 1
                else:
                    edge_pos.append(bottom)
                    bottom -= 1

            for actor, pos in zip(ab, edge_pos):
                actor.number_row = pos

            used = set(edge_pos)
            central_positions = [i for i in range(1, n + 1) if i not in used]
            center_coord = (n + 1) / 2
            central_positions.sort(key=lambda pos: abs(pos - center_coord))

            group_C.sort(key=lambda a: (-out_deg[a.actor_name], bary[a.actor_name]))
            for actor, pos in zip(group_C, central_positions):
                actor.number_row = pos

        self._rebuild_layouts()

        '''
        print("\n" + "=" * 70)
        print(" ОПТИМИЗИРОВАННЫЙ ПОРЯДОК АКТОРОВ ".center(70, "="))
        print(f"{'Актор':<15} {'Строка':<8} {'Триггер':<15} {'Исх.связи':<12} {'Вх.связи':<12} {'Триггерит':<20}")
        print("-" * 70)
        for actor in sorted(self.actors.values(), key=lambda a: a.number_row):
            out = out_deg[actor.actor_name]
            inc = in_deg[actor.actor_name]
            targets = [dst for src, _, dst, _, _ in self.arrows if src == actor.actor_name]
            triggers_str = ", ".join(sorted(set(targets))) if targets else "-"
            trig_field = actor.trigger if actor.trigger is not None else "-"
            print(f"{actor.actor_name:<15} {actor.number_row:<8} {trig_field:<15} {out:<12} {inc:<12} {triggers_str:<20}")
        print("-" * 70)
        print("Стрелки:")
        if self.arrows:
            for src, src_idx, dst, dst_idx, color in self.arrows:
                print(f"  {src}[{src_idx}] -> {dst}[{dst_idx}] (цвет: {color.name() if hasattr(color, 'name') else '?'})")
        else:
            print("  (нет стрелок)")
        print("=" * 70 + "\n")
        '''

    def add_actor(self, actor_name: str) -> None:
        """Добавляет нового актора с пустым блоком."""
        new_color = self._get_next_color(actor_name)
        max_row = max((a.number_row for a in self.actors.values()), default=0)
        number_row = max_row + 1
        lb = deviceAction(actor_name, actor_name, new_color)
        self.actors[actor_name] = actorInfo(actor_name, number_row, new_color, lb)
        self.diagram.names_layout.addWidget(lb, number_row, 0)

        empty_block = deviceAction("")
        empty_block.column = 0
        if actor_name not in self.actor_actions:
            self.actor_actions[actor_name] = []
        self.actor_actions[actor_name].append(empty_block)
        self.diagram.action_field.add_new_block(empty_block, number_row, 0)
        self.current_number += 1

    def add_action(self, actor_name: str, action_info: str,
                   action_name: str = "",
                   status: Optional[Union[bool, str]] = None,
                   trigger: Optional[str] = None) -> bool:
        """Добавляет действие актору, при необходимости связывая стрелкой с триггером."""
        actor = self.actors.get(actor_name)
        if not actor:
            return False

        new_block = deviceAction(action_name, action_info, actor.color)
        if status is not None:
            new_block.set_status(status)

        trigger_info = None
        if trigger and trigger in self.actors and trigger != "time":
            trigger_actions = self.actor_actions.get(trigger, [])
            if trigger_actions:
                trigger_idx = len(trigger_actions) - 1
                trigger_info = (trigger, trigger_idx)

            if actor.trigger is None or actor.trigger != trigger:
                actor.trigger = trigger

        if actor_name not in self.actor_actions:
            self.actor_actions[actor_name] = []
        self.actor_actions[actor_name].append(new_block)

        column = self.diagram.action_field.max_column + 1
        self.diagram.action_field.add_new_block(new_block, actor.number_row, column)

        if trigger_info:
            target_idx = len(self.actor_actions[actor_name]) - 1
            pair = tuple(sorted((trigger_info[0], actor_name)))
            if pair not in self._pair_colors:
                self._pair_colors[pair] = self._get_next_arrow_color()
            arrow_color = self._pair_colors[pair]
            self.arrows.append((trigger_info[0], trigger_info[1],
                                actor_name, target_idx, arrow_color))

        scroll_bar = self.diagram.scroll_area_horizontal.horizontalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())
        return True

    def set_actor_inactive(self, actor_name: str) -> bool:
        """Отображает актора как неактивного (серый, зачёркнутый)."""
        actor = self.actors.get(actor_name)
        if not actor:
            return False
        actor.label.setStyleSheet(
            "background-color: #808080;"
            "color: #FFFFFF;"
            "text-decoration: line-through;"
        )
        return True

    def activate_all_actors(self) -> None:
        """Возвращает всем акторам активный вид."""
        for actor in self.actors.values():
            actor.label.setStyleSheet(f"background-color: {actor.color};")

    def finalize_layout(self) -> None:
        if not self._stop_rebuild:
            print("Finalize layout")
            self.optimize_actor_order()
            self._stop_rebuild = True

    def clear_action_field(self) -> None:
        """Очищает все действия, кроме первых пустых блоков, и все стрелки."""
        layout = self.diagram.action_field.layout
        widgets_to_remove = []
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget:
                _, col, _, _ = layout.getItemPosition(i)
                if col != 0:
                    widgets_to_remove.append(widget)
        for widget in widgets_to_remove:
            layout.removeWidget(widget)
            widget.deleteLater()

        for actor_name in self.actor_actions:
            self.actor_actions[actor_name] = self.actor_actions[actor_name][:1]

        self.arrows.clear()
        # Назначенные цвета пар акторов сохраняются, счётчик палитры не сбрасывается
        self.diagram.action_field.max_column = 0
        self.current_number = 0
        self._arrow_color_index = 0
        self._stop_rebuild = False
        self._rebuild_layouts()

    def remove_actor(self, actor_name: str) -> bool:
        """Удаляет актора, его действия и связанные стрелки."""
        actor = self.actors.get(actor_name)
        if not actor:
            return False

        # Удаляем стрелки, где участвует актор
        self.arrows = [arrow for arrow in self.arrows
                       if arrow[0] != actor_name and arrow[2] != actor_name]

        # Удаляем записи о цветах пар, в которых участвует удаляемый актор
        keys_to_remove = [pair for pair in self._pair_colors if actor_name in pair]
        for key in keys_to_remove:
            del self._pair_colors[key]

        self.diagram.names_layout.removeWidget(actor.label)
        actor.label.deleteLater()

        for action in self.actor_actions.get(actor_name, []):
            self.diagram.action_field.layout.removeWidget(action)
            action.deleteLater()
        if actor_name in self.actor_actions:
            del self.actor_actions[actor_name]

        removed_row = actor.number_row
        del self.actors[actor_name]
        for a in self.actors.values():
            if a.number_row > removed_row:
                a.number_row -= 1

        self._rebuild_layouts()
        return True

    def remove_all_actors(self) -> None:
        """Удаляет всех акторов."""
        for actor in list(self.actors.keys()):
            self.remove_actor(actor)
        self.current_number = 0


class tester_diag(QWidget):
    """Тестовый класс для демонстрации работы диаграммы."""

    def __init__(self, diag: actDiagram):
        super().__init__()
        self.diag = diag
        self.add_timer = QTimer(self)
        self.add_timer.timeout.connect(self.test_act_diag)
        self.actors_def = ["Ch1", "Ch2", "Ch3", "Ch4", "Ch5"]
        self.actors_added: List[str] = []
        self.actors_removing: List[str] = []
        self.counter_step = 0

    def test_act_diag(self) -> None:
        import random
        import gc
        self.counter_step += 1
        if self.actors_def and random.randint(0, 1):
            new_actor = self.actors_def.pop(0)
            self.actors_added.append(new_actor)
            self.diag.add_actor(new_actor)
        elif self.actors_added:
            focus_actor = random.choice(self.actors_added)
            name = f"Action {random.randint(0, 100)}" if random.randint(0, 1) else ""
            status = random.choice([None, True, False])
            trigger = None
            if self.actors_added and random.random() > 0.5:
                other = random.choice([a for a in self.actors_added if a != focus_actor] or [None])
                if other:
                    trigger = other
            self.diag.add_action(focus_actor, f"Description {random.randint(0, 100)}",
                                 action_name=name, status=status, trigger=trigger)

        if random.random() > 1 and not self.actors_def:
            self.diag.clear_action_field()
        elif self.counter_step % 3 == 0 and self.actors_added:
            inactive_actor = random.choice(self.actors_added)
            self.actors_added.remove(inactive_actor)
            self.actors_removing.append(inactive_actor)
            self.diag.set_actor_inactive(inactive_actor)
        elif not self.actors_def and not self.actors_added and self.actors_removing:
            rem_actor = random.choice(self.actors_removing)
            self.actors_removing.remove(rem_actor)
            self.diag.remove_actor(rem_actor)

        gc.collect()

    def run(self) -> None:
        self.counter_step = 0
        self.add_timer.start(1000)


if __name__ == "__main__":
    import random
    import gc

    app = QApplication(sys.argv)
    qdarktheme.setup_theme()

    diag = actDiagram()
    diag.diagram.setWindowTitle("Demo Act Diagram")

    # Для тестовой демонстрации используем автоматическое добавление
    test_diag = tester_diag(diag)
    test_diag.run()

    # После того как все акторы и связи добавлены (в реальном коде – перед финализацией),
    # вызываем оптимизацию порядка строк и фиксируем макет.
    # В тестовом примере это можно сделать по таймеру или кнопке.
    # Здесь для наглядности оставлено, но не вызывается автоматически.
    # diag.optimize_actor_order()
    # diag.finalize_layout()

    diag.diagram.show()
    sys.exit(app.exec_())