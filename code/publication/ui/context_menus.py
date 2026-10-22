"""Контекстное меню холста: добавить панель, импортировать сессию,
z-order, presentation-элементы. Никаких JSON.
"""
from __future__ import annotations
from typing import Callable, List, Tuple

from PyQt5.QtWidgets import QMenu, QInputDialog, QComboBox, QDialog, QDialogButtonBox, QVBoxLayout, QLabel

from ..model.session_ref import DataRef


class ImportSessionDialog(QDialog):
    """Выбор панели-источника: session_id + series_root_name."""

    def __init__(self, session_controller, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Импортировать сессию в панель")
        self.sessions = getattr(session_controller, "graph_sessions", {}) or {}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Сессия:"))
        self.session_combo = QComboBox()
        for sid in sorted(self.sessions.keys()):
            try:
                name = self.sessions[sid].session_name
            except Exception:
                name = sid
            self.session_combo.addItem(f"{sid}: {name}", sid)
        self.session_combo.currentIndexChanged.connect(self._reload_series)
        layout.addWidget(self.session_combo)

        layout.addWidget(QLabel("Серия:"))
        self.series_combo = QComboBox()
        layout.addWidget(self.series_combo)
        self._reload_series()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _reload_series(self):
        self.series_combo.clear()
        sid = self.session_combo.currentData()
        sess = self.sessions.get(sid)
        if sess is None:
            return
        gm = getattr(sess, "graph_main", None)
        if gm is None:
            return
        try:
            curves = gm.get_curves()
        except Exception:
            curves = {}
        for root_name, curve in curves.items():
            name = getattr(curve, "curve_name", root_name)
            self.series_combo.addItem(name, root_name)

    def get_data_ref(self) -> DataRef:
        sid = self.session_combo.currentData() or ""
        root = self.series_combo.currentData() or ""
        return DataRef(session_id=sid, series_root_name=root)


def build_canvas_menu(
    parent_widget,
    session_controller,
    on_add_panel: Callable[[], None],
    on_import_session: Callable[[str], None],
    on_add_annotation: Callable[[str], None],
    on_zorder_front: Callable[[], None],
    on_zorder_back: Callable[[], None],
    on_align: Callable[[str], None],
) -> QMenu:
    menu = QMenu(parent_widget)

    menu.addAction("Добавить панель", on_add_panel)

    import_dialog_action = QMenu("Импортировать сессию в панель", menu)
    dialog = ImportSessionDialog(session_controller, parent_widget)
    if dialog.exec_() == QDialog.Accepted:
        ref = dialog.get_data_ref()
        if ref.session_id and ref.series_root_name:
            on_import_session(ref)
    menu.addMenu(import_dialog_action)

    pres_menu = QMenu("Presentation-элементы", menu)
    for kind in ("text", "panel_label", "scale_bar", "bracket", "arrow"):
        pres_menu.addAction(kind, lambda k=kind: on_add_annotation(k))
    menu.addMenu(pres_menu)

    align_menu = QMenu("Выровнять", menu)
    for mode in ("left", "right", "top", "bottom", "center_h", "center_v"):
        align_menu.addAction(mode, lambda m=mode: on_align(m))
    menu.addMenu(align_menu)

    menu.addSeparator()
    menu.addAction("Z-order: на передний план", on_zorder_front)
    menu.addAction("Z-order: на задний план", on_zorder_back)

    return menu