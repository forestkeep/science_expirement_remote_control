"""Дерево фигуры: Figure → Panels → Presentation → Data-bound overrides."""
from __future__ import annotations
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QApplication

from ..model.figure_model import FigureSpec


class FigureTree(QTreeWidget):
    selection_changed = pyqtSignal(str)       # panel_id или ""
    annotation_selected = pyqtSignal(str)     # ann_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)
        self.setHeaderLabels(["Фигура"])
        self.spec: Optional[FigureSpec] = None
        self.itemSelectionChanged.connect(self._on_sel)

    def set_spec(self, spec: FigureSpec) -> None:
        self.spec = spec
        self.rebuild()

    def rebuild(self) -> None:
        self.clear()
        if self.spec is None:
            return
        root = QTreeWidgetItem(self, [f"Figure {self.spec.id}"])
        root.setExpanded(True)

        panels_root = QTreeWidgetItem(root, ["Панели"])
        panels_root.setExpanded(True)
        for panel in self.spec.sorted_panels():
            label = f"{panel.id}  —  {panel.title or '(без имени)'}"
            item = QTreeWidgetItem(panels_root, [label])
            item.setData(0, Qt.UserRole, ("panel", panel.id))

        pres_root = QTreeWidgetItem(root, ["Presentation-аннотации"])
        pres_root.setExpanded(True)
        for ann in sorted(self.spec.presentation_annotations,
                          key=lambda a: (int(a.z), a.id)):
            label = f"{ann.id}  [{ann.kind}] {ann.text[:24]}"
            item = QTreeWidgetItem(pres_root, [label])
            item.setData(0, Qt.UserRole, ("annotation", ann.id))

        ov_root = QTreeWidgetItem(root, ["Data-bound overrides"])
        ov_root.setExpanded(False)
        for ann_id, ov in sorted(self.spec.data_bound_overrides.items()):
            status = "resolved" if ov.resolved else "unresolved"
            item = QTreeWidgetItem(ov_root, [f"{ann_id}  [{status}]"])
            item.setData(0, Qt.UserRole, ("override", ann_id))

    def _on_sel(self) -> None:
        items = self.selectedItems()
        if not items:
            self.selection_changed.emit("")
            return
        data = items[0].data(0, Qt.UserRole)
        if not data:
            self.selection_changed.emit("")
            return
        kind, ident = data
        if kind == "panel":
            self.selection_changed.emit(ident)
        elif kind == "annotation":
            self.annotation_selected.emit(ident)
        elif kind == "override":
            self.annotation_selected.emit(ident)