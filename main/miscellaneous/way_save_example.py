from interface.installation_window import Ui_Installation
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from maisheng_power_class import maisheng_power_class
from sr830_class import sr830_class
from pymodbus.client import ModbusSerialClient
from pymodbus.utilities import computeCRC
import serial.tools.list_ports
from datetime import datetime
import time
from Classes import device_response_to_step
import threading
from PyQt5.QtCore import QTimer
from interface.save_repeat_set_window import save_repeat_set_window


def tkexample():
    import tkinter as tk
    from tkinter import filedialog as fd

    def callback():
        name = fd.asksaveasfilename()
        print(name)

    errmsg = 'Error!'
    tk.Button(text='Click to Open File',
              command=callback).pack(fill=tk.X)
    tk.mainloop()



class Notepad(QtWidgets.QMainWindow):


    def __init__(self):
        super().__init__()
        self.setWindowTitle('New document - Notepad Alpha[*]')
        fileMenu = self.menuBar().addMenu('File')
        
        saveAction = fileMenu.addAction('Save')
        saveAction.triggered.connect(self.save)
        saveAsAction = fileMenu.addAction('Save as...')
        saveAsAction.triggered.connect(self.saveAs)

        self.editor = QtWidgets.QTextEdit()
        self.setCentralWidget(self.editor)
        self.editor.document().modificationChanged.connect(self.setWindowModified)
        self.fileName = None

    def save(self):
        if not self.isWindowModified():
            return
        if not self.fileName:
            self.saveAs()
        else:
            with open(self.fileName, 'w') as f:
                f.write(self.editor.toPlainText())

    def saveAs(self):
        if not self.isWindowModified():
            return
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        print(self)
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,
                                                            "Save File", "", "All Files(*);;Text Files(*.txt);; Книга Excel (*.xlsx)", options=options)
        if fileName:
            with open(fileName, 'w') as f:
                f.write(self.editor.toPlainText())
            self.fileName = fileName
            self.setWindowTitle(
                str(sys.os.path.basename(fileName)) + " - Notepad Alpha[*]")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    a = Notepad()
    a.show()
    sys.exit(app.exec_())
