import pyqtgraph as pg
from PyQt5 import QtCore
import time

class RemovableInfiniteLine(pg.InfiniteLine):
    removeRequested = QtCore.pyqtSignal(object)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptHoverEvents(True)
        self.last_time_click = 0
        
    def mouseClickEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            event.accept()
        else:
            if time.perf_counter() - self.last_time_click < 0.5:
                self.removeRequested.emit(self)#double click
            else:
                self.last_time_click = time.perf_counter()
            super().mouseClickEvent(event)