
from __future__ import annotations
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from .publication_widget import PublicationWidget
from ..model.figure_model import FigureSpec


class PublicationWindow(QWidget):
    def __init__(self, session_controller, spec: FigureSpec = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Publication Figure")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._widget = PublicationWidget(session_controller, spec, self)
        layout.addWidget(self._widget)
        self.resize(1280, 800)

    def widget(self) -> PublicationWidget:
        return self._widget