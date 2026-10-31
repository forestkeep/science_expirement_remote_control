"""Дерево фигуры по ТЗ.

Иерархия:
    Figure fig_0001
    ├ ● Панели
    │  ├ ● Панель A          [a]   "U(t)"
    │  │  ├ ● y1  sin              ●
    │  │  └   y2  cos
    │  └   Панель B          [b]
    ├ ● Аннотации
    │  ├ ● text "T = 300 K"
    │  └   arrow
    └   Data-bound overrides (0)

Возможности:
  * индикатор ● (серый = только pinned, цветной = есть неприменённые overrides);
  * инкрементальное редактирование метки [a] двойным кликом;
  * иконки типов кривых в правой колонке слота;
  * контекстные меню (панель / слот / аннотация);
  * базовый drag&drop (слоты между панелями, панели — по z).
"""
from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QMimeData, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QInputDialog, QLineEdit, QMenu,
    QMessageBox, QTreeWidget, QTreeWidgetItem, QWidget,
)

from ..model.figure_model import FigureSpec
from ..model.panel import PanelSpec


MIME_PANEL = "application/x-pub-panel"
MIME_SLOT = "application/x-pub-slot"
PIN_KEY = "__pinned__"

def _make_indicator(color: Optional[str]) -> QIcon:
    pixmap = QPixmap(10, 10)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    if color:
        painter.setBrush(QBrush(QColor(color)))
        painter.setPen(QColor(color).darker(180))
    else:
        painter.setBrush(QBrush(Qt.transparent))
        painter.setPen(Qt.NoPen)
    if color:
        painter.drawEllipse(1, 1, 8, 8)
    else:
        painter.drawEllipse(1, 1, 8, 8)  # пустой — не рисуем
    painter.end()
    return QIcon(pixmap)


def _indicator_for(panel: PanelSpec) -> QIcon:
    """Серый кружок = только pinned; цветной = есть неприменённые overrides."""
    if not panel.style_overrides:
        return QIcon()
    # Проверяем, есть ли только pinned-флаги
    only_pinned = all(
        k == PIN_KEY or k.startswith("legend.pinned")
        for k in panel.style_overrides
    )
    if only_pinned:
        return _make_indicator("#888888")
    return _make_indicator("#f0a000")


class _TreeDropIndicator(QWidget):
    """Светящаяся горизонтальная полоска-индикатор места вставки.

    Согласована по стилю с `FilterDropIndicator` из `graphs/ui/inspector.py`.
    Не принимает события мыши.
    """

    INDICATOR_HEIGHT = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt5.QtCore import Qt
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedHeight(self.INDICATOR_HEIGHT)
        self.setStyleSheet("background: transparent;")
        self.hide()

    def paintEvent(self, event):
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QColor, QPainter, QPen

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        try:
            w = self.width()
            h = self.height()
            cy = h / 2.0
            left, right = 4, w - 4

            base = QColor(90, 180, 255)
            for i in range(4, 0, -1):
                glow = QColor(base)
                glow.setAlpha(max(0, 60 - i * 12))
                p.setPen(QPen(glow, i * 2.0))
                p.drawLine(left, int(cy), right, int(cy))

            p.setPen(QPen(QColor(120, 210, 255), 2))
            p.drawLine(left, int(cy), right, int(cy))

            p.setBrush(QColor(120, 210, 255))
            p.setPen(Qt.NoPen)
            p.drawEllipse(left - 3, int(cy) - 3, 6, 6)
            p.drawEllipse(right - 3, int(cy) - 3, 6, 6)
        finally:
            p.end()


def _slot_type_icon(panel: PanelSpec, slot_index: int) -> str:
    """Символ типа кривой в правой колонке слота.

    ``●`` — обычная, ``Σ`` — результат анализа (есть артефакты).
    """
    if slot_index >= len(panel.curves):
        return ""
    slot = panel.curves[slot_index]
    if slot.data_ref is None or slot.data_ref.is_empty():
        return ""
    style = slot.data_ref.style
    if style is not None:
        arts = getattr(style, "artifacts", []) or []
        if arts:
            return "Σ"
    return "●"


class _PanelLabelEditor(QLineEdit):
    """Инлайн-редактор метки панели [a]."""

    def __init__(self, parent, panel_id: str, text: str, on_commit):
        super().__init__(parent)
        self._panel_id = panel_id
        self._on_commit = on_commit
        self.setText(text)
        self.setFrame(False)
        self.setFixedWidth(120)
        self.selectAll()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._commit()
            event.accept()
            return
        if event.key() == Qt.Key_Escape:
            self._cancel()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        self._commit()
        super().focusOutEvent(event)

    def _commit(self):
        text = self.text().strip()
        self._on_commit(self._panel_id, text)
        self.deleteLater()

    def _cancel(self):
        self.deleteLater()


class FigureTree(QTreeWidget):
    """Дерево фигуры. Сигналы повторяют действия пользователя наружу."""

    figure_selected        = pyqtSignal()
    panel_selected         = pyqtSignal(str)
    slot_selected          = pyqtSignal(str, int)
    annotation_selected    = pyqtSignal(str)

    panel_label_changed    = pyqtSignal(str, str)
    panel_removed          = pyqtSignal(str)
    panel_duplicated       = pyqtSignal(str)
    panel_export_requested = pyqtSignal(str)

    slot_removed           = pyqtSignal(str, int)
    slot_reset_style       = pyqtSignal(str, int)

    annotation_removed     = pyqtSignal(str)
    annotation_properties  = pyqtSignal(str)

    panel_reordered        = pyqtSignal(list)          # новый порядок panel_id
    slot_moved             = pyqtSignal(str, int, str, int)  # (from_panel, from_idx, to_panel, to_idx)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHeaderLabels(["Элемент", "Метка", "Тип"])
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 40)
        self.setColumnWidth(2, 40)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.itemDoubleClicked.connect(self._on_double_click)
        self.itemSelectionChanged.connect(self._on_selection)
        self.setIndentation(14)
        self.setFont(QFont("Arial", 9))
        self.spec: Optional[FigureSpec] = None
        self._drop_indicator = _TreeDropIndicator(self.viewport())
        self._drop_indicator.hide()
        self.setDropIndicatorShown(True)

    # ------------------------------------------------------------------
    def set_spec(self, spec: FigureSpec, preserve_selection: bool = True) -> None:
        """Обновить spec и перестроить дерево.

        Если ``preserve_selection`` — пытаемся восстановить ранее
        выделенный узел (панель/слот/аннотацию) по его data-роли.
        """
        prev = None
        if preserve_selection:
            items = self.selectedItems()
            if items:
                prev = items[0].data(0, Qt.UserRole)
        self.spec = spec
        self.rebuild()
        if prev:
            self._restore_selection(prev)

    def _restore_selection(self, role) -> None:
        if not role:
            return
        kind = role[0]
        for item in self._iter_all_items():
            data = item.data(0, Qt.UserRole) or ()
            if not data:
                continue
            if data[0] != kind:
                continue
            if kind == "panel" and data[1] == role[1]:
                self.setCurrentItem(item)
                return
            if kind == "slot" and len(data) >= 3 \
                    and data[1] == role[1] and int(data[2]) == int(role[2]):
                self.setCurrentItem(item)
                return
            if kind == "annotation" and data[1] == role[1]:
                self.setCurrentItem(item)
                return

    def _iter_all_items(self):
        stack = [self.topLevelItem(i) for i in range(self.topLevelItemCount())]
        while stack:
            it = stack.pop()
            yield it
            for i in range(it.childCount()):
                stack.append(it.child(i))

    def rebuild(self) -> None:
        self.blockSignals(True)
        try:
            self.clear()
            if self.spec is None:
                return
            root = QTreeWidgetItem(self, [f"Figure {self.spec.id}", "", ""])
            root.setData(0, Qt.UserRole, ("figure",))

            panels_root = QTreeWidgetItem(root, ["Панели", "", ""])
            panels_root.setData(0, Qt.UserRole, ("panels_root",))

            for panel in self.spec.sorted_panels():
                self._add_panel_item(panels_root, panel)

            ann_root = QTreeWidgetItem(root, ["Аннотации", "", ""])
            ann_root.setData(0, Qt.UserRole, ("ann_root",))
            for ann in sorted(self.spec.presentation_annotations,
                              key=lambda a: (int(a.z), a.id)):
                preview = (ann.text or "")[:40]
                label = f"{ann.kind}  {preview}".rstrip()
                item = QTreeWidgetItem(ann_root, [label, "", ""])
                item.setData(0, Qt.UserRole, ("annotation", ann.id))

            ov_root = QTreeWidgetItem(
                root, [f"Data-bound overrides ({len(self.spec.data_bound_overrides)})", "", ""]
            )
            ov_root.setData(0, Qt.UserRole, ("overrides_root",))
            for ann_id, ov in sorted(self.spec.data_bound_overrides.items()):
                status = "resolved" if getattr(ov, "resolved", True) else "unresolved"
                item = QTreeWidgetItem(ov_root, [f"{ann_id}  [{status}]", "", ""])
                item.setData(0, Qt.UserRole, ("override", ann_id))

            root.setExpanded(True)
            panels_root.setExpanded(True)
            ann_root.setExpanded(False)
            ov_root.setExpanded(False)
        finally:
            self.blockSignals(False)


    def _add_panel_item(self, parent: QTreeWidgetItem, panel: PanelSpec) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent, [f"Панель {panel.id}", "", ""])
        item.setIcon(0, _indicator_for(panel))
        item.setData(0, Qt.UserRole, ("panel", panel.id))
        item.setText(1, f"[{self._panel_label(panel)}]")
        item.setToolTip(0, f"{panel.x_mm:.1f}×{panel.y_mm:.1f} → {panel.w_mm:.1f}×{panel.h_mm:.1f} мм")
        item.setToolTip(1, "Двойной клик — изменить метку панели")
        item.setFlags(item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)

        for idx, slot in enumerate(panel.curves):
            slot_item = QTreeWidgetItem(item)
            axis = (slot.axis or "y1").lower()
            ref = slot.data_ref
            name = ref.series_root_name if ref is not None and not ref.is_empty() else "(пустая ссылка)"
            legend = slot.legend_label or name
            slot_item.setText(0, f"{axis}  {legend}")
            type_icon = _slot_type_icon(panel, idx)
            slot_item.setText(2, type_icon)

            # ● у слота: есть хотя бы один override (не pinned)
            if slot.style_overrides:
                only_pinned = all(k == PIN_KEY for k in slot.style_overrides)
                color = "#888888" if only_pinned else "#2a82da"
                slot_item.setIcon(0, _make_indicator(color))
            else:
                slot_item.setIcon(0, QIcon())

            slot_item.setData(0, Qt.UserRole, ("slot", panel.id, idx))
            slot_item.setFlags(slot_item.flags() | Qt.ItemIsDragEnabled)
            if slot.visible is False:
                f = slot_item.font(0)
                f.setItalic(True)
                slot_item.setFont(0, f)
        return item


    def _panel_label(self, panel: PanelSpec) -> str:
        """Пользовательская метка панели или авто-буква."""
        if panel is None:
            return "a"
        custom = panel.style_overrides.get("panel.label")
        if custom:
            return str(custom)
        return self._auto_label(panel.id)

    def _auto_label(self, panel_id: str) -> str:
        """a, b, c, …, z, aa, ab, … по позиции в спеке."""
        if self.spec is None:
            return "a"
        idx = 0
        for i, p in enumerate(self.spec.sorted_panels()):
            if p.id == panel_id:
                idx = i
                break
        letters = "abcdefghijklmnopqrstuvwxyz"
        if idx < len(letters):
            return letters[idx]
        return f"a{idx}"

    # ------------------------------------------------------------------
    def _iter_panel_items(self):
        for i in range(self.topLevelItemCount()):
            root = self.topLevelItem(i)
            for j in range(root.childCount()):
                panels_root = root.child(j)
                if panels_root.data(0, Qt.UserRole) and panels_root.data(0, Qt.UserRole)[0] == "panels_root":
                    for k in range(panels_root.childCount()):
                        yield panels_root.child(k)

    # ------------------------------------------------------------------
    def _on_selection(self):
        items = self.selectedItems()
        if not items:
            self.figure_selected.emit()
            return
        data = items[0].data(0, Qt.UserRole) or ()
        kind = data[0] if data else None
        if kind == "panel":
            self.panel_selected.emit(data[1])
        elif kind == "slot":
            self.slot_selected.emit(data[1], int(data[2]))
        elif kind == "annotation":
            self.annotation_selected.emit(data[1])
        elif kind == "figure" or kind in ("panels_root", "ann_root", "overrides_root"):
            self.figure_selected.emit()

    def _on_double_click(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.UserRole) or ()
        if not data or data[0] != "panel":
            return
        if column not in (0, 1):
            return

        panel = self.spec.find_panel(data[1]) if self.spec is not None else None
        if panel is None:
            return

        current = self._panel_label(panel)
        rect = self.visualItemRect(item)
        # позиционируем редактор в колонке 1 (там живёт метка [a])
        from PyQt5.QtWidgets import QHeaderView  # noqa: F401 (для ясности)
        x = self.header().sectionViewportPosition(1)
        w = self.header().sectionSize(1)
        editor = _PanelLabelEditor(
            self.viewport(), data[1], current,
            on_commit=self._on_panel_label_committed,
        )
        editor.setFixedWidth(max(40, w))
        editor.move(x, rect.top())
        editor.show()
        editor.raise_()
        editor.setFocus()


    def _on_panel_label_committed(self, panel_id: str, text: str):
        self.panel_label_changed.emit(panel_id, text)

    # ------------------------------------------------------------------
    def _on_context_menu(self, pos):
        item = self.itemAt(pos)
        menu = QMenu(self)
        if item is None:
            return
        data = item.data(0, Qt.UserRole) or ()
        kind = data[0] if data else None

        if kind == "panel":
            panel_id = data[1]
            act_del = menu.addAction("Удалить")
            act_dup = menu.addAction("Дублировать")
            act_exp = menu.addAction("Экспортировать только эту панель")
            act_del.triggered.connect(lambda _c=False, pid=panel_id: self.panel_removed.emit(pid))
            act_dup.triggered.connect(lambda _c=False, pid=panel_id: self.panel_duplicated.emit(pid))
            act_exp.triggered.connect(lambda _c=False, pid=panel_id: self.panel_export_requested.emit(pid))
        elif kind == "slot":
            panel_id, idx = data[1], int(data[2])
            act_del = menu.addAction("Удалить")
            act_reset = menu.addAction("Сбросить стиль к источнику")
            act_del.triggered.connect(
                lambda _c=False, pid=panel_id, i=idx: self.slot_removed.emit(pid, i))
            act_reset.triggered.connect(
                lambda _c=False, pid=panel_id, i=idx: self.slot_reset_style.emit(pid, i))
        elif kind == "annotation":
            ann_id = data[1]
            act_del = menu.addAction("Удалить")
            act_props = menu.addAction("Свойства")
            act_del.triggered.connect(lambda _c=False, aid=ann_id: self.annotation_removed.emit(aid))
            act_props.triggered.connect(lambda _c=False, aid=ann_id: self.annotation_properties.emit(aid))
        else:
            return
        menu.exec_(self.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_PANEL) or event.mimeData().hasFormat(MIME_SLOT):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if not (event.mimeData().hasFormat(MIME_PANEL)
                or event.mimeData().hasFormat(MIME_SLOT)):
            self._hide_drop_indicator()
            super().dragMoveEvent(event)
            return

        event.acceptProposedAction()
        super().dragMoveEvent(event)
        self._update_drop_indicator(event.pos())

    def dragLeaveEvent(self, event):
        self._hide_drop_indicator()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._hide_drop_indicator()
        source_item = self.currentItem()
        source_data = source_item.data(0, Qt.UserRole) if source_item else None
        target_item = self.itemAt(event.pos())
        target_data = target_item.data(0, Qt.UserRole) if target_item else None

        if not source_data or not target_data:
            event.ignore()
            return

        # --- слот ---
        if source_data[0] == "slot":
            from_panel_id, from_idx = source_data[1], int(source_data[2])

            if target_data[0] == "slot":
                to_panel_id, target_idx = target_data[1], int(target_data[2])
                pos = self.dropIndicatorPosition()
                if pos == QAbstractItemView.AboveItem:
                    to_idx = target_idx
                elif pos == QAbstractItemView.BelowItem:
                    to_idx = target_idx + 1
                else:
                    to_idx = target_idx

                if to_panel_id == from_panel_id and from_idx < to_idx:
                    to_idx -= 1

                self.slot_moved.emit(from_panel_id, from_idx, to_panel_id, to_idx)
                event.acceptProposedAction()
                return

            if target_data[0] == "panel":
                to_panel_id = target_data[1]
                panel = self.spec.find_panel(to_panel_id) if self.spec is not None else None
                to_idx = len(panel.curves) if panel is not None else 0
                if to_panel_id == from_panel_id and from_idx < to_idx:
                    to_idx -= 1
                self.slot_moved.emit(from_panel_id, from_idx, to_panel_id, to_idx)
                event.acceptProposedAction()
                return

        # --- панель ---
        if source_data[0] == "panel" and target_data[0] == "panel":
            src_id = source_data[1]
            dst_id = target_data[1]
            if src_id != dst_id and self.spec is not None:
                ordered = [p.id for p in self.spec.sorted_panels()]
                if src_id in ordered and dst_id in ordered:
                    ordered.remove(src_id)
                    ordered.insert(ordered.index(dst_id), src_id)
                    self.panel_reordered.emit(ordered)
                    event.acceptProposedAction()
                    return

        event.ignore()

        # ------------------------------------------------------------------
    # Drop-индикатор
    # ------------------------------------------------------------------
    def _hide_drop_indicator(self) -> None:
        if self._drop_indicator.isVisible():
            self._drop_indicator.hide()

    def _update_drop_indicator(self, pos) -> None:
        """Показать полоску в точке вставки по координате `pos` (viewport)."""
        item = self.itemAt(pos)
        if item is None:
            self._hide_drop_indicator()
            return

        rect = self.visualItemRect(item)
        if rect.isNull() or not rect.isValid():
            self._hide_drop_indicator()
            return

        from PyQt5.QtWidgets import QAbstractItemView

        drop_pos = self.dropIndicatorPosition()
        if drop_pos == QAbstractItemView.AboveItem:
            y_center = rect.top()
        elif drop_pos == QAbstractItemView.BelowItem:
            y_center = rect.bottom()
        else:
            # OnItem / OnViewport — выбираем верх/низ по позиции курсора
            if pos.y() < rect.center().y():
                y_center = rect.top()
            else:
                y_center = rect.bottom()

        vp_w = self.viewport().width()
        vp_h = self.viewport().height()
        ind_h = self._drop_indicator.height()

        x = 0
        y = int(y_center - ind_h / 2)
        if y < 0:
            y = 0
        if y + ind_h > vp_h:
            y = max(0, vp_h - ind_h)

        self._drop_indicator.setGeometry(x, y, vp_w, ind_h)
        self._drop_indicator.raise_()
        self._drop_indicator.show()

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if item is None:
            return
        data = item.data(0, Qt.UserRole) or ()
        mime = QMimeData()
        if data and data[0] == "slot":
            mime.setData(MIME_SLOT, f"{data[1]}:{data[2]}".encode())
        elif data and data[0] == "panel":
            mime.setData(MIME_PANEL, str(data[1]).encode())
        else:
            return
        from PyQt5.QtGui import QDrag
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(Qt.MoveAction)