"""QDockWidget-обёртка: встраиваемый публикационный слой."""
from __future__ import annotations
from PyQt5.QtWidgets import QDockWidget

from .publication_widget import PublicationWidget
from ..model.figure_model import FigureSpec


class PublicationDock(QDockWidget):
    def __init__(self, session_controller, spec: FigureSpec = None, parent=None):
        super().__init__("Публикационная фигура", parent)
        self._widget = PublicationWidget(session_controller, spec, self)
        self.setWidget(self._widget)
        self.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )

    def widget(self) -> PublicationWidget:
        return self._widget