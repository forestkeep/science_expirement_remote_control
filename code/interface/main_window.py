# Copyright © 2023 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.


import logging

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)

def tr(context, text):
        return QApplication.translate(context, text)

name_window = tr("UI_MainWindow","Контроллер установки")
class Ui_MainWindow(object):

    def __init__(self, version):
        self.is_design_mode = False
        self.version_app = version

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowIcon(QIcon('picture/key.png'))  # Укажите путь к вашей иконке
        self.mother_class = MainWindow

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")

        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton.setMinimumSize(QtCore.QSize(100, 100))
        font = QtGui.QFont()
        font.setFamily("Noto Sans SC")
        font.setPointSize(13)
        self.pushButton.setFont(font)
        self.pushButton.setObjectName("pushButton")
        self.verticalLayout.addWidget(self.pushButton)

        self.pushButton_2 = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_2.setMinimumSize(QtCore.QSize(100, 100))
        self.pushButton_2.setFont(font)
        self.pushButton_2.setObjectName("pushButton_2")
        self.verticalLayout.addWidget(self.pushButton_2)

        MainWindow.setCentralWidget(self.centralwidget)

        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 397, 20))
        self.menubar.setObjectName("menubar")

        self.menu = QtWidgets.QMenu(self.menubar)
        self.menu.setObjectName("menu")

        MainWindow.setMenuBar(self.menubar)

        self.actionCreateNew = QtWidgets.QAction(MainWindow)
        self.actionCreateNew.setObjectName("CreateNew")

        self.design_mode = QtWidgets.QAction(MainWindow)
        self.design_mode.setObjectName("CreateNew")
        self.design_mode.triggered.connect(self.set_design_mode)

        self.menu.addSeparator()
        self.menu.addAction(self.design_mode)

        self.menubar.addAction(self.menu.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def set_design_mode(self):
        self.is_design_mode = not self.is_design_mode

        if self.is_design_mode:
            self.design_mode.setText(tr("UI_MainWindow","Выключить режим разработчика"))
            self.mother_class.setWindowTitle(name_window + tr("UI_MainWindow","(режим разработчика)") + self.version_app)
            self.menu.addAction(self.actionCreateNew)
        else:
            self.menu.removeAction(self.actionCreateNew)
            self.design_mode.setText(tr("UI_MainWindow","Включить режим разработчика"))
            self.mother_class.setWindowTitle(name_window + self.version_app)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(name_window + " " + self.version_app)
        self.pushButton.setText(tr("UI_MainWindow","Локальное управление приборами"))
        self.pushButton_2.setText(tr("UI_MainWindow","Создание экспериментальной установки"))
        self.menu.setTitle(tr("UI_MainWindow","Меню"))
        self.actionCreateNew.setText(tr("UI_MainWindow","Создать прибор"))
        self.design_mode.setText(tr("UI_MainWindow","Включить режим разработчика"))
