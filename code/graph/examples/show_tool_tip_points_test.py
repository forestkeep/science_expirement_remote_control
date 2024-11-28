import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui


app = pg.mkQApp()                  
pg.setConfigOptions(antialias=True)


class Graph(pg.GraphItem):
    def __init__(self, pw):
        self.pw = pw
        self.dragPoint = None
        self.dragOffset = None
        pg.GraphItem.__init__(self)   

    def setData(self, **kwds):
        self.data = kwds
        if 'pos' in self.data:
            npts = self.data['pos'].shape[0]
            self.data['adj'] = np.column_stack(
                (np.arange(0, npts-1), np.arange(1, npts))
            )
            self.data['data'] = np.empty(npts, dtype=[('index', int)])
            self.data['data']['index'] = np.arange(npts)
        self.updateGraph()

    def updateGraph(self):
        pg.GraphItem.setData(self, **self.data)

    def mouseDragEvent(self, ev):
        if ev.button() != QtCore.Qt.LeftButton:
            ev.ignore()
            return
        if ev.isStart():
            pos = ev.buttonDownPos()
            pts = self.scatter.pointsAt(pos)
            if len(pts) == 0:
                ev.ignore()
                return
                
            self.dragPoint = pts[0]
            ind = pts[0].data()[0]
            self.dragOffset = self.data['pos'][ind][1] - pos[1]
        elif ev.isFinish():
            self.dragPoint = None
            return
        else:
            if self.dragPoint is None:
                ev.ignore()
                return

        ind = self.dragPoint.data()[0]
        self.data['pos'][ind][1] = ev.pos()[1] + self.dragOffset
        self.data['pos'][ind][0] = ev.pos()[0] + self.dragOffset
        self.updateGraph()
        print(ev.pos(), self.dragPoint.data()[0])
        ev.accept()

# !!!    
    def hoverEvent(self, ev):        
        try:
            items = self.pw.scene().items(ev.scenePos())
        except AttributeError as e:
            return

        for item in items:
           if isinstance(item, pg.GraphItem): 
               if item.scatter.pointsAt(ev.pos()):
                   pw.setToolTip(f'<b>x={ev.pos().x():.1f}, y={ev.pos().y():.1f}</b>')
               else:
                   pw.setToolTip('')        


pw = pg.PlotWidget(title="PlotItem")
g = Graph(pw)                                                   # +++ pw

pw.addItem(g)
pw.showGrid(x=True, y=True)
pw.show()                                    

#                      v <---- попробуйте изменить значение
x = np.linspace(1, 10, 5)

pos = np.column_stack((x, np.sin(x)))
g.setData(pos=pos, size=10, pxMode=True)


if __name__ == '__main__':
    import sys

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QGuiApplication.instance().exec_()