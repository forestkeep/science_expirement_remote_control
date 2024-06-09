import sys
from PyQt5 import QtGui, QtCore, QtWidgets
import pyvisa

class Window1(QtWidgets.QMainWindow):
    textSaved = QtCore.pyqtSignal(str)
    def __init__(self):
        super(Window1,self).__init__()
        self.setGeometry(50,50,500,300)
        self.setWindowTitle("PyQt Signal Signal Emitter")
        self.home()
        self.counter = 0
    def home(self):

        self.__line=QtWidgets.QLineEdit("howdy", self)
        self.__line.move(120,100)

        btn=QtWidgets.QPushButton("Send Signal", self)
        btn.clicked.connect(self.send_signal)
        btn.move(0,100)
        self.counter = 0

        self.show()

    def send_signal(self):
        if self.counter == 0:
            signal=self.__line.displayText()
            self.Window2=Window2(signal, self)
            self.Window2.show()
            self.textSaved.connect(self.Window2.showMessage)
            self.counter = 1
            self.response = Window2.text_saved
        else:
            signal = self.__line.displayText()
            self.textSaved.emit(signal)
    def showMessage2(self, message):
        self.counter=self.counter+1
        #print(self.counter,message)
        
class Window2(QtWidgets.QDialog):
    text_saved = QtCore.pyqtSignal(str)
    def __init__(self, txt, window1):
        self.text = txt
        self.signal1 = window1.textSaved
        super(Window2,self).__init__()
        self.setGeometry(50,50,500,300)
        self.setWindowTitle("PyQt Signal Slot Receiver")
        self.home()
        self.signal1.connect(self.showMessage)


        btn=QtWidgets.QPushButton("Send Signal", self)
        btn.clicked.connect(self.send_signal)
        self.text_saved.connect(window1.showMessage2)

    def home(self):
        self.line_response=QtWidgets.QLineEdit(self.text, self)
        self.line_response.move(120,100)
    def showMessage(self, message):
        self.line_response.setText(message)
    def send_signal(self):
            signal = 'self.__line.displayText()'
            self.text_saved.emit("hello")


def run():
    app=QtWidgets.QApplication(sys.argv)
    GUI=Window1()
    sys.exit(app.exec_())


from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.Qt import *


class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        
        self.checkOne = QtWidgets.QCheckBox('Событие one')
        self.checkTwo = QtWidgets.QCheckBox('Событие two')

        self.labelOne = QLabel()
        self.labelOne.setPixmap(QPixmap('off.png').scaled(50, 50))
        self.labelTwo = QLabel()
        self.labelTwo.setPixmap(QPixmap('off.png').scaled(50, 50))
        
        self.textEdit = QTextEdit()
        
        self.layout = QtWidgets.QGridLayout(self)
        self.layout.addWidget(self.textEdit, 0, 0, 1, 2)
        self.layout.addWidget(self.labelOne, 1 , 0)
        self.layout.addWidget(self.checkOne, 1 , 1)
        self.layout.addWidget(self.labelTwo, 2 , 0)
        self.layout.addWidget(self.checkTwo, 2 , 1)
       
        self.checkOne.stateChanged.connect(
            lambda state=self.checkOne.isChecked(), cb=self.checkOne: \
                   self.selectCheckBox(state, cb))
        self.checkTwo.stateChanged.connect(
            lambda state=self.checkTwo.isChecked(), cb=self.checkTwo: \
                   self.selectCheckBox(state, cb))

    def selectCheckBox(self, toggle, cb):
        text = ''
        
        if toggle and cb.text() == 'Событие one':
            self.labelOne.setPixmap(QPixmap('on.png').scaled(50, 50))
            if self.checkTwo.isChecked():
                text = text + 'Событие two\n'
            text = text + 'Событие one'
        elif not toggle and cb.text() == 'Событие one':
            self.labelOne.setPixmap(QPixmap('off.png').scaled(50, 50))
            if self.checkTwo.isChecked():
                text = text + 'Событие two\n'
            
        elif toggle and cb.text() == 'Событие two':
            self.labelTwo.setPixmap(QPixmap('on.png').scaled(50, 50))
            if self.checkOne.isChecked():
                text = text + 'Событие one\n'
            text = text + 'Событие two'
            
        elif not toggle and cb.text() == 'Событие two':
            self.labelTwo.setPixmap(QPixmap('off.png').scaled(50, 50))
            if self.checkOne.isChecked():
                text = text + 'Событие one'

        self.textEdit.setText(text)





import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QIcon, QPixmap

app = QApplication(sys.argv)
window = QWidget()
window.setWindowTitle("Конфигурация окна")

# Нижний слой - вертикальный слой 1
layout1 = QVBoxLayout()

# Горизонтальные слои 2 и 3 внутри слоя 1
layout2 = QHBoxLayout()
layout3 = QHBoxLayout()


device_lay = QHBoxLayout()
lcd1 = QtWidgets.QLCDNumber()
lcd2 = QtWidgets.QLCDNumber()
device_lay.addWidget(lcd1)
device_lay.addWidget(lcd2)

save_result_lay = QVBoxLayout()
but1 = QtWidgets.QPushButton()
but1.setStyleSheet("background-color: rgb(150, 0, 0);")
but2 = QtWidgets.QPushButton()
but2.setStyleSheet("background-color: rgb(150, 0, 0);")
save_result_lay.addWidget(but1)
save_result_lay.addWidget(but2)

# Горизонтальный слой 3
log_lay = QVBoxLayout()
but3 = QtWidgets.QPushButton()
but3.setStyleSheet("background-color: rgb(0, 150, 0);")
but4 = QtWidgets.QPushButton()
but4.setStyleSheet("background-color: rgb(0, 150, 0);")
log_lay.addWidget(but3)
log_lay.addWidget(but4)

button_lay = QVBoxLayout()
start_button = QtWidgets.QPushButton()
pause_button = QtWidgets.QPushButton()
button_lay.addWidget(start_button)
button_lay.addWidget(pause_button)




# Добавление слоев в иерархию
layout2.addLayout(device_lay)
layout2.addLayout(save_result_lay)

layout3.addLayout(log_lay)
layout3.addLayout(button_lay)

layout1.addLayout(layout2)
layout1.addLayout(layout3)

window.setLayout(layout1)
window.show()
sys.exit(app.exec_())




if __name__ == '__main__':

    rm = pyvisa.ResourceManager()
    #print(rm.list_resources())

    #app = QtWidgets.QApplication(sys.argv)
    #w = MainWindow()
   # w.show()
    #sys.exit(app.exec_())
