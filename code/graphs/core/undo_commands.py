# graph/core/undo_commands.py
"""
Конкретные undo/redo-команды для графика.

Каждая команда — самодостаточная: хранит ссылки и снимок состояния,
необходимые, чтобы откатить и повторить операцию.
"""
from __future__ import annotations

import copy
import logging

from PyQt5.QtWidgets import QApplication

from common.undo.manager import UndoCommand

logger = logging.getLogger(__name__)

_TR = lambda s: QApplication.translate("GraphWindow", s)


# =====================================================================
# Кривая — имя / стиль / заметка
# =====================================================================
class RenameCurveCommand(UndoCommand):
    def __init__(self, curve, new_name: str):
        self.curve = curve
        self.new_name = new_name
        self.old_name = curve.curve_name
        self.old_customized = curve.is_name_curve_customized

    def text(self):
        return _TR("Переименование кривой")

    def redo(self):
        self.curve.change_name(self.new_name)

    def undo(self):
        if self.old_customized:
            self.curve.change_name(self.old_name)
        else:
            self.curve.reset_name()


class ResetCurveNameCommand(UndoCommand):
    def __init__(self, curve):
        self.curve = curve
        self.old_name = curve.curve_name
        self.old_customized = curve.is_name_curve_customized

    def text(self):
        return _TR("Сброс имени кривой")

    def redo(self):
        self.curve.reset_name()

    def undo(self):
        if self.old_customized:
            self.curve.change_name(self.old_name)


class ChangeCurveStyleCommand(UndoCommand):
    def __init__(self, curve, new_style):
        self.curve = curve
        self.new_style = copy.deepcopy(new_style)
        self.old_style = copy.deepcopy(curve.saved_style) if curve.saved_style is not None else None

    def text(self):
        return _TR("Изменение стиля кривой")

    def redo(self):
        self.curve.change_style(self.new_style)

    def undo(self):
        if self.old_style is not None:
            self.curve.change_style(self.old_style)


class AddNoteCommand(UndoCommand):
    """
    Добавление/изменение заметки (блок «Разное» → «Описание»).
    """
    def __init__(self, tree_item, block_name: str, old_text: str, new_text: str):
        self.tree_item = tree_item
        self.block_name = block_name
        self.old_text = old_text or ""
        self.new_text = new_text or ""
        self.key = _TR("Описание")

    def text(self):
        return _TR("Изменение заметки")

    def _apply(self, text: str):
        if text:
            if not self.tree_item.update_block_data(self.block_name, {self.key: text}):
                self.tree_item.add_new_block(self.block_name, {self.key: text})
        else:
            block = self.tree_item.findChild(self.block_name)
            if block is not None:
                for i in range(block.childCount()):
                    child = block.child(i)
                    if child.text(0).startswith(f"{self.key}:"):
                        block.removeChild(child)
                        break
                if block.childCount() == 0:
                    self.tree_item.delete_block(self.block_name)

    def redo(self):
        self._apply(self.new_text)

    def undo(self):
        self._apply(self.old_text)


# =====================================================================
# Кривая — удаление / создание
# =====================================================================
class DeleteCurveCommand(UndoCommand):
    """
    Удаление кривой. Хранит объект кривой и её tree_item, чтобы
    восстановить их при undo.
    """
    def __init__(self, session, tree_win, tree_item):
        self.session = session
        self.tree_win = tree_win
        self.tree_item = tree_item
        self.curve = tree_item.curve_data_obj
        self.root_name = self.curve.rel_data.root_name
        self.was_draw = bool(self.curve.is_draw)
        self.number_axis = self.curve.number_axis or 1
        self.top_index = tree_win.tree_widget.indexOfTopLevelItem(tree_item)
        self._artifact_cmds = []
        self._macro = None

    def text(self):
        return _TR("Удаление кривой")

    def _detach_from_graph(self):
        gm = self.session.graph_main
        self.curve.delete_curve_from_graph()
        self.curve.is_draw = False
        gm.get_curves().pop(self.root_name, None)
        if getattr(self.session, "selection_model", None) is not None:
            self.session.selection_model.remove(self.curve)

    def _detach_from_selector(self):
        if getattr(self.curve.rel_data, "is_gen", False):
            return
        sel = getattr(self.session, "select_controller", None)
        if sel is None:
            return
        y_name = self.curve.rel_data.y_root_name
        if self.number_axis == 2:
            sel.clear_selections("", [], [y_name], is_signal=True)
        elif self.number_axis == 1:
            sel.clear_selections("", [y_name], [], is_signal=True)

    def _detach_from_tree(self):
        if self.tree_item in self.tree_win.curves:
            self.tree_win.curves.remove(self.tree_item)
        parent = self.tree_item.parent()
        if parent is not None:
            parent.removeChild(self.tree_item)
        else:
            idx = self.tree_win.tree_widget.indexOfTopLevelItem(self.tree_item)
            if idx != -1:
                self.tree_win.tree_widget.takeTopLevelItem(idx)

    def _attach_to_tree(self):
        if self.tree_item not in self.tree_win.curves:
            self.tree_win.curves.append(self.tree_item)
        parent = self.tree_item.parent()
        if parent is not None:
            parent.addChild(self.tree_item)
        elif 0 <= self.top_index <= self.tree_win.tree_widget.topLevelItemCount():
            self.tree_win.tree_widget.insertTopLevelItem(self.top_index, self.tree_item)
        else:
            self.tree_win.tree_widget.addTopLevelItem(self.tree_item)

    def _attach_to_graph(self):
        gm = self.session.graph_main
        gm.get_curves()[self.root_name] = self.curve
        if self.was_draw:
            if self.number_axis == 2:
                self.curve.add_to_graph(
                    gm.graphView.second_graphView,
                    gm.graphView.legend2,
                    2,
                )
            else:
                self.curve.add_to_graph(
                    gm.graphView,
                    gm.graphView.legend,
                    1,
                )

    def _attach_to_selector(self):
        if not self.was_draw:
            return
        if getattr(self.curve.rel_data, "is_gen", False):
            return
        sel = getattr(self.session, "select_controller", None)
        if sel is None:
            return
        y_name = self.curve.rel_data.y_root_name
        if self.number_axis == 2:
            sel.set_selections("", [], [y_name], is_signal=True)
        elif self.number_axis == 1:
            sel.set_selections("", [y_name], [], is_signal=True)

    def redo(self):
        # собираем артефакты, привязанные к кривой
        session = self.session
        controller = getattr(session, "analysis_controller", None)
        self._artifact_cmds = []
        if controller is not None:
            from graphs.analysis.commands import RemoveAnalysisCommand, MacroAnalysisCommand
            artifacts = controller.get_artifacts_for_curve(self.root_name)
            macro = MacroAnalysisCommand(controller)
            for art in artifacts:
                c = RemoveAnalysisCommand(controller, art)
                self._artifact_cmds.append(c)
                macro.add(c)
            if self._artifact_cmds:
                macro.redo()
        self._macro = macro if self._artifact_cmds else None

        if self.was_draw:
            self._detach_from_selector()
        self._detach_from_graph()
        self._detach_from_tree()
        self.tree_win.update_visible()

    def undo(self):
        # сначала кривая, потом артефакты
        self._attach_to_tree()
        self._attach_to_graph()
        self._attach_to_selector()
        if getattr(self, "_macro", None) is not None:
            self._macro.undo()
        self.tree_win.update_visible()


class AddCurveCommand(UndoCommand):
    """
    Создание новой кривой (формула / автокорреляция).
    После успешного создания команда привязывается к объекту кривой
    через bind_after_creation().
    """
    def __init__(self, session, root_name: str):
        self.session = session
        self.root_name = root_name
        self.curve = None
        self.tree_item = None
        self.top_index = -1
        self.number_axis = 1

    def bind_after_creation(self) -> bool:
        curve = self.session.graph_main.get_curve(self.root_name)
        if curve is None:
            return False
        self.curve = curve
        self.tree_item = curve.tree_item
        self.number_axis = curve.number_axis or 1
        self.top_index = self.session.tree_class.tree_widget.indexOfTopLevelItem(self.tree_item)
        return True

    def text(self):
        return _TR("Создание кривой")

    def redo(self):
        if self.curve is None:
            return
        gm = self.session.graph_main
        tree = self.session.tree_class
        gm.get_curves()[self.root_name] = self.curve
        if self.tree_item not in tree.curves:
            tree.curves.append(self.tree_item)
        parent = self.tree_item.parent()
        if parent is not None:
            parent.addChild(self.tree_item)
        elif 0 <= self.top_index <= tree.tree_widget.topLevelItemCount():
            tree.tree_widget.insertTopLevelItem(self.top_index, self.tree_item)
        else:
            tree.tree_widget.addTopLevelItem(self.tree_item)
        if self.number_axis == 2:
            self.curve.add_to_graph(
                gm.graphView.second_graphView, gm.graphView.legend2, 2,
            )
        else:
            self.curve.add_to_graph(gm.graphView, gm.graphView.legend, 1)
        tree.update_visible() 

    def undo(self):
        if self.curve is None:
            return
        gm = self.session.graph_main
        tree = self.session.tree_class
        self.curve.delete_curve_from_graph()
        self.curve.is_draw = False
        gm.get_curves().pop(self.root_name, None)
        if getattr(self.session, "selection_model", None) is not None:
            self.session.selection_model.remove(self.curve)
        if self.tree_item in tree.curves:
            tree.curves.remove(self.tree_item)
        parent = self.tree_item.parent()
        if parent is not None:
            parent.removeChild(self.tree_item)
        else:
            idx = tree.tree_widget.indexOfTopLevelItem(self.tree_item)
            if idx != -1:
                tree.tree_widget.takeTopLevelItem(idx)
        tree.update_visible() 


# =====================================================================
# Фильтры
# =====================================================================
class ApplyFilterCommand(UndoCommand):
    def __init__(self, curves: list, filter_command):
        self.curves = list(curves)
        self.filter_command = filter_command

    def text(self):
        return _TR("Применение фильтра")

    def redo(self):
        for curve in self.curves:
            curve.set_filter(self.filter_command)

    def undo(self):
        for curve in self.curves:
            curve.delete_filter(self.filter_command)


class RemoveFilterCommand(UndoCommand):
    def __init__(self, curve, filter_command):
        self.curve = curve
        self.filter_command = filter_command

    def text(self):
        return _TR("Удаление фильтра")

    def redo(self):
        self.curve.delete_filter(self.filter_command)

    def undo(self):
        # set_filter пересоберёт историю и создаст новую запись в дереве
        self.curve.set_filter(self.filter_command)

class ReorderFiltersCommand(UndoCommand):
    """Изменение порядка применения фильтров у одной кривой."""

    def __init__(self, curve, filter_command, old_index: int, new_index: int):
        self.curve = curve
        self.filter_command = filter_command
        self.old_index = int(old_index)
        self.new_index = int(new_index)

    def text(self):
        return _TR("Изменение порядка фильтров")

    def redo(self):
        self.curve.move_filter(self.filter_command, self.new_index)

    def undo(self):
        self.curve.move_filter(self.filter_command, self.old_index)


class ResetFiltersCommand(UndoCommand):
    def __init__(self, curves: list):
        self.snapshots = [(c, list(c.filters_history)) for c in curves]

    def text(self):
        return _TR("Сброс фильтров")

    def redo(self):
        for curve, _ in self.snapshots:
            curve.clear_filters()

    def undo(self):
        for curve, saved in self.snapshots:
            curve.clear_filters()
            for f in saved:
                curve.set_filter(f)


# =====================================================================
# Метаданные сессии
# =====================================================================
class RenameSessionCommand(UndoCommand):
    def __init__(self, controller, session_id: str, old_name: str, new_name: str):
        self.controller = controller
        self.session_id = session_id
        self.old_name = old_name
        self.new_name = new_name

    def text(self):
        return _TR("Переименование сессии")

    def redo(self):
        self.controller.change_session_name(self.session_id, self.new_name)

    def undo(self):
        self.controller.change_session_name(self.session_id, self.old_name)


class ChangeDescriptionCommand(UndoCommand):
    def __init__(self, controller, session_id: str, old_desc, new_desc):
        self.controller = controller
        self.session_id = session_id
        self.old_desc = old_desc or ""
        self.new_desc = new_desc or ""

    def text(self):
        return _TR("Изменение описания сессии")

    def redo(self):
        self.controller.update_session_description(self.session_id, self.new_desc)

    def undo(self):
        self.controller.update_session_description(self.session_id, self.old_desc)


# =====================================================================
# Инфинитные линии
# =====================================================================
class AddInfiniteLineCommand(UndoCommand):
    def __init__(self, graph_widget, line):
        self.graph_widget = graph_widget
        self.line = line

    def text(self):
        return _TR("Добавление курсора")

    def redo(self):
        if self.line not in self.graph_widget.inf_lines:
            self.graph_widget.add_inf_line(self.line)

    def undo(self):
        if self.line in self.graph_widget.inf_lines:
            self.graph_widget.remove_inf_line(self.line)


class RemoveInfiniteLineCommand(UndoCommand):
    def __init__(self, graph_widget, line):
        self.graph_widget = graph_widget
        self.line = line

    def text(self):
        return _TR("Удаление курсора")

    def redo(self):
        if self.line in self.graph_widget.inf_lines:
            self.graph_widget.remove_inf_line(self.line)

    def undo(self):
        if self.line not in self.graph_widget.inf_lines:
            self.graph_widget.add_inf_line(self.line)


# =====================================================================
# Внешний вид графика — снимок через extract_plot_widget_settings
# =====================================================================
class GraphAppearanceCommand(UndoCommand):
    """
    Отмена изменений внешнего вида через снимок настроек.

    before/after — объекты GraphFieldSettings (из graph.hdf5_io.models).
    Восстановление делается через HDF5ToProjectAdapter.apply_graph_settings.
    """
    def __init__(self, graph_widget, before_settings, after_settings):
        self.graph_widget = graph_widget
        self.before = before_settings
        self.after = after_settings

    def text(self):
        return _TR("Изменение внешнего вида графика")

    def _apply(self, settings):
        from graphs.hdf5_io.adapters import HDF5ToProjectAdapter
        from graphs.hdf5_io.models import FieldSettings
        wrapper = FieldSettings()
        wrapper.graph_field = settings
        HDF5ToProjectAdapter().apply_graph_settings(self.graph_widget, wrapper)

    def redo(self):
        if self.after is not None:
            self._apply(self.after)

    def undo(self):
        if self.before is not None:
            self._apply(self.before)

# =====================================================================
# Редактирование одной точки кривой (локально, без data_manager)
# =====================================================================
class EditPointCommand(UndoCommand):
    def __init__(self, curve, index: int, old_x: float, old_y: float,
                 new_x: float, new_y: float):
        self.curve = curve
        self.index = int(index)
        self.old_x = float(old_x)
        self.old_y = float(old_y)
        self.new_x = float(new_x)
        self.new_y = float(new_y)

    def text(self):
        return "Изменение точки"

    def redo(self):
        self.curve.set_raw_point(self.index, x=self.new_x, y=self.new_y)

    def undo(self):
        self.curve.set_raw_point(self.index, x=self.old_x, y=self.old_y)
