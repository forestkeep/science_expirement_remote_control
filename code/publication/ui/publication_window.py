"""Standalone QMainWindow для публикационной фигуры."""
from __future__ import annotations
from PyQt5.QtWidgets import QMainWindow, QWidget

from .publication_widget import PublicationWidget
from ..model.figure_model import FigureSpec

class PublicationWindow(QWidget):
    def __init__(self, session_controller, spec: FigureSpec = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Publication Figure")
        self._widget = PublicationWidget(session_controller, spec, self)
        self.setCentralWidget(self._widget)
        self.resize(1280, 800)

    def widget(self) -> PublicationWidget:
        return self._widget