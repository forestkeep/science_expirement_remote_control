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



class Ui_MainWindow(object):
    def __init__(self, version, main_class):
        self.main_class = main_class
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

        self.services = QtWidgets.QMenu(self.menubar)
        self.services.setObjectName("services")

        self.open_graph = QtWidgets.QAction(MainWindow)
        self.open_graph.setObjectName("open_graph")
        self.open_graph.triggered.connect(self.main_class.open_graph_in_exp)

        self.open_test_commands = QtWidgets.QAction(MainWindow)
        self.open_test_commands.setObjectName("open_test_commands")
        self.open_test_commands.triggered.connect(self.main_class.open_test_cmd)


        self.services.addAction(self.open_graph)
        self.services.addAction(self.open_test_commands)

        MainWindow.setMenuBar(self.menubar)

        self.actionCreateNew = QtWidgets.QAction(MainWindow)
        self.actionCreateNew.setObjectName("CreateNew")

        self.debug_mode = QtWidgets.QAction(MainWindow)
        self.debug_mode.setObjectName("debug_mode")
        self.debug_mode.triggered.connect(self.set_design_mode)

        # Создание подменю для выбора языка
        self.language_menu = QtWidgets.QMenu(self.menu)
        
        # Добавление пунктов в подменю
        self.actionEnglish = QtWidgets.QAction(MainWindow)
        self.actionEnglish.triggered.connect(lambda: self.change_language('ENG'))
        
        self.actionRussian = QtWidgets.QAction(MainWindow)
        self.actionRussian.triggered.connect(lambda: self.change_language('RUS'))
        
        self.language_menu.addAction(self.actionEnglish)
        self.language_menu.addAction(self.actionRussian)
        
        # Добавление подменю в основное меню
        self.menu.addAction(self.language_menu.menuAction())  # Добавляем действие подменю

        self.menu.addSeparator()
        self.menu.addAction(self.debug_mode)

        self.menubar.addAction(self.menu.menuAction())
        self.menubar.addAction(self.services.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def change_language(self, language):
        self.main_class.change_language(language)

    def set_design_mode(self):
        print("Design mode activated")

    def set_design_mode(self):
        self.is_design_mode = not self.is_design_mode

        if self.is_design_mode:

            self.debug_mode.setText(QApplication.translate("main","Выключить режим разработчика"))
            self.mother_class.setWindowTitle( QApplication.translate("main","Контроллер установки (режим разработчика)") + self.version_app)
            self.menu.addAction(self.actionCreateNew)
        else:
            self.menu.removeAction(self.actionCreateNew)
            self.debug_mode.setText(QApplication.translate("main","Включить режим разработчика"))
            self.mother_class.setWindowTitle(QApplication.translate("main","Контроллер установки") + self.version_app)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("main", "Контроллер установки") + " " + self.version_app)
        
        if self.is_design_mode:
            self.debug_mode.setText(_translate("main","Выключить режим разработчика"))
            self.mother_class.setWindowTitle(_translate("main","Контроллер установки" + "(режим разработчика)") + self.version_app)
        else:
            self.debug_mode.setText(_translate("main","Включить режим разработчика"))
            self.mother_class.setWindowTitle(_translate("main","Контроллер установки") + self.version_app)
        
        self.pushButton.setText(_translate("main","Локальное управление приборами"))
        self.pushButton_2.setText(_translate("main","Создание экспериментальной установки"))
        self.menu.setTitle(_translate("main","Меню"))
        self.services.setTitle( _translate("main","Сервисы") )
        self.actionCreateNew.setText(_translate("main","Создать прибор"))

        self.language_menu.setTitle(_translate("main","Выбрать язык"))
        self.open_graph.setText(_translate("main","Анализ графиков"))
        self.open_test_commands.setText(_translate("main","Тест команд"))
        self.actionEnglish.setText("English")
        self.actionRussian.setText("Русский")
