import sys
from PyQt5 import QtCore, QtGui, QtWidgets


class MyTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(MyTab, self).__init__()
        self.parent = parent
        self.rows = [
            ('10.16.26.25', 2),
            ('10.16.26.26', 3),
            ('10.16.26.27', 1),
            ('10.16.26.28', 4)
        ]
        self.lineEdit = QtWidgets.QLineEdit(
            placeholderText='Введите номер из 4х цифр')

        self.pushButton = QtWidgets.QPushButton('Создать TableWidget')
        self.pushButton.clicked.connect(self.func_connect)

        self.tableWidget = QtWidgets.QTableWidget(0, 4)
        self.tableWidget.setHorizontalHeaderLabels(
            ['IP', 'Number', 'SSH', 'VNC'])
        self.tableWidget.horizontalHeader().setDefaultSectionSize(150)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.tableWidget)
        vbox.addWidget(self.lineEdit)
        vbox.addWidget(self.pushButton)

    def func_connect(self):
        num = self.lineEdit.text()
        if not num.isdigit():
            self.parent.statusBar().showMessage(
                'Достустимо вводить только цифры, номер состоит из 4х цифр')
            return
        if len(num) != 4:
            self.parent.statusBar().showMessage('Номер состоит из 4х цифр, повторите ввод.')
            return
        self.parent.statusBar().showMessage('')

        self.tableWidget.setRowCount(len(self.rows))
        for row, items in enumerate(self.rows):
            self.tableWidget.setItem(
                row, 0, QtWidgets.QTableWidgetItem(items[0]))
            self.tableWidget.setItem(
                row, 1, QtWidgets.QTableWidgetItem(str(items[1])))

            button = QtWidgets.QPushButton(f'SSH {row}')
            button.clicked.connect(lambda ch, ip=items[0], n=items[1], btn=button:
                                   self.button_pushed_SSH(ip, n, btn))
            self.tableWidget.setCellWidget(row, 2, button)

            button = QtWidgets.QPushButton(f'VNC {row}')
            button.clicked.connect(lambda ch, ip=items[0], n=items[1], btn=button:
                                   self.button_pushed_VNC(ip, n, btn))
            self.tableWidget.setCellWidget(row, 3, button)
        self.tableWidget.setSortingEnabled(True)

    def button_pushed_SSH(self, ip, n, btn):
        print(f'{btn.text()}: ip={ip}, n={n}, lineEdit={self.lineEdit.text()}')

    def button_pushed_VNC(self, ip, n, btn):
        print(f'{btn.text()}: ip={ip}, n={n}, lineEdit={self.lineEdit.text()}')


class MyWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.centralwidget = QtWidgets.QWidget()
        self.setCentralWidget(self.centralwidget)

# + vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
        self.tabWidget = QtWidgets.QTabWidget()
        count = self.tabWidget.count()
        self.nb = QtWidgets.QToolButton(text="Добавить", autoRaise=True)
        self.nb.clicked.connect(self.new_tab)
        self.tabWidget.insertTab(count, QtWidgets.QWidget(), "")
        self.tabWidget.tabBar().setTabButton(
            count, QtWidgets.QTabBar.RightSide, self.nb)

        self.new_tab()

        self.layout = QtWidgets.QGridLayout(self.centralwidget)
        self.layout.addWidget(self.tabWidget)

        self.statusBar().showMessage('Message in statusbar. '
                                     'Будет Скрыто через 5000 миллисекунд - 5 секунды! ', 5000)

    def new_tab(self):
        index = self.tabWidget.count() - 1
        tabPage = MyTab(self)
        self.tabWidget.insertTab(index, tabPage, f"Tab {index}")
        self.tabWidget.setCurrentIndex(index)
        tabPage.lineEdit.setFocus()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(QtGui.QFont("Times", 12, QtGui.QFont.Bold))
    win = MyWindow()
    win.resize(640, 480)
    win.show()
    sys.exit(app.exec_())
