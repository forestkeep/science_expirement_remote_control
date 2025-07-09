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

import enum
import logging
import os

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QSizePolicy, QSplitter

from Devices.Classes import (not_ready_style_background,
                             not_ready_style_border, ready_style_background,
                             ready_style_border, warning_style_background,
                             warning_style_border)

logger = logging.getLogger(__name__)


#not_ready_style_border = "border: 1px solid rgb(180, 0, 0); border-radius: 5px; QToolTip { color: #ffffff; background-color: rgb(100, 50, 50); border: 1px solid white;}"
class state_ch(enum.Enum):
    closed = 0
    open = 1

class device_page(QtWidgets.QWidget):
    def __init__(self, device_class, installation_class, parent=None):
        super(device_page, self).__init__()
        self.is_standart_device = True#стандартные приборы это те, у которых каждый канал может работать как отдельный прибор, связи между каналами нет
        ind_channels_buf = [0,0,0,0,0,0,0,0,0,0]
        for i in device_class.channels:
            ind_channels_buf[i.get_number()-1]+=1
        self.ind_channels =  0
        for i in ind_channels_buf:
            if i > 0:
                self.ind_channels+=1
            
        self.setMinimumSize( self.ind_channels*140, 300 )
        self.device_class = device_class
        self.installation_class = installation_class
        self.verticalLayout = QtWidgets.QGridLayout(self)
        self.verticalLayout.setHorizontalSpacing(2)
        self.verticalLayout.setVerticalSpacing(2)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)

        self.name_device = QtWidgets.QLabel()
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.channels = {}
        self.ch_state = []

        for i in device_class.channels:
            if i.is_active == True:
                self.ch_state.append(state_ch.open)
            else:
                self.ch_state.append(state_ch.closed)

        self.name_device.setFont(font)
        self.name_device.setAlignment(QtCore.Qt.AlignCenter)
        self.name_device.setObjectName(
            "name_device_" + device_class.get_name())
        self.name_device.setText(device_class.get_name())
        self.name_device.setStyleSheet(not_ready_style_border)
        #self.name_device.setStyleSheet("background-color: rgb(20, 20, 20);")

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("picture/close.png"),
                       QtGui.QIcon.Normal, QtGui.QIcon.On)
        
        self.del_button = QtWidgets.QToolButton()
        self.del_button.setStyleSheet("background-color: rgb(150, 30, 0);border: 1px solid rgb(70, 70, 10); border-radius: 1px;")
        self.del_button.setFixedSize(20, 20)
        self.del_button.clicked.connect(lambda: self.click_del_button())
        self.del_button.setToolTip("удалить прибор")
        self.del_button.setIcon(icon)
        
        self.verticalLayout.addWidget(self.name_device, 0, 0)
        self.verticalLayout.addWidget(self.del_button, 0, 1)

        self.add_ch_button = {}
        font = QFont()
        font.setFamily("Arial") 
        font.setPointSize(18)   
        font.setBold(True)       
        for i in range(self.ind_channels):
            self.add_ch_button[i+1] = QtWidgets.QToolButton()
            self.add_ch_button[i+1].setFixedSize(15, 180)
            self.add_ch_button[i+1].setToolTip(f"добавить канал {1+i}")
            self.add_ch_button[i+1].setStyleSheet("text-align: center; padding: 0px; QToolTip { background-color: lightblue; color: black; border: 1px solid black; }")
                                                  #"border-color: rgb(90, 90, 50);border: 1px solid rgb(70, 70, 10); border-radius: 1px;") # Установить выравнивание текста и отступы

            self.add_ch_button[i+1].setText(f"+")
            self.add_ch_button[i+1].setFont(font)
            self.add_ch_button[i+1].setToolButtonStyle(1)  # 1 - показать текст

        self.channelsLayout = QtWidgets.QHBoxLayout()


        self.channelsLayout.setObjectName("channelsLayout")
        self.verticalLayout.addLayout(self.channelsLayout, 1, 0, 12, 2)

        for j in range(self.ind_channels):
            page = channel_page(j+1, installation_class,
                                device_class.get_name(), device_class=device_class)
            self.channels[j+1] = page

            if self.ch_state[j] == state_ch.open:
                self.channelsLayout.addWidget(page)
            else:
                self.channelsLayout.addWidget(self.add_ch_button[j+1])

        for i in range(len(self.add_ch_button)):
            self.add_ch_button[i+1].clicked.connect(lambda ch, index = i+1: self.click_change_ch(index))
            self.channels[i+1].state_Button.clicked.connect(lambda ch, index = i+1: self.click_change_ch(index))

    def click_change_ch(self, num, is_open = None):
        '''открыть или закрыть канал'''
        if self.installation_class.is_experiment_running() == False:
            num = int(num)
            if is_open == None:
            # меняем состояние
                if self.ch_state[num-1] == state_ch.open:
                    self.ch_state[num-1] = state_ch.closed
                else:
                    self.ch_state[num-1] = state_ch.open
                    self.installation_class.add_new_channel(self.device_class.get_name(),num)
            elif is_open == True:
                self.ch_state[num-1] = state_ch.open
            else:
                self.ch_state[num-1] = state_ch.closed

            self.installation_class.set_state_ch(self.device_class.get_name(), num, self.ch_state[num-1] == state_ch.open)

            self.update_widgets()
        else:
            self.installation_class.add_new_channel(self.device_class.get_name(),num)

    def update_widgets(self):
        # удаляем виджеты
        for i in reversed(range(self.channelsLayout.count())):
            self.channelsLayout.itemAt(i).widget().setParent(None)

        # добавляем виджеты
        for j in range(self.ind_channels):
            if self.ch_state[j] == state_ch.open:
                self.channelsLayout.addWidget(self.channels[j+1])
            else:
                
                self.channelsLayout.addWidget(self.add_ch_button[j+1])

    def click_del_button(self):
        if self.installation_class.is_experiment_running() == False:
            self.setParent(None)#удаляем виджет устройства
        self.installation_class.delete_device(self.device_class.get_name())

    def set_ch_color(self, ch_num, color):
        self.channels[ch_num].set_color(color)

    def set_state_ch_widget(self, num, state):
        num = int(num)
        if state == True:
            self.ch_state[num-1] = state_ch.open
        else:
            self.ch_state[num-1] = state_ch.closed

        self.installation_class.set_state_ch(self.device_class.get_name(), num, self.ch_state[num-1] == state_ch.open)

class CustomButton(QtWidgets.QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.style_sheet = self.styleSheet()
        self.clicked.connect( self.lock_button )

    def lock_button(self):
        self.setEnabled(False)
        QtCore.QTimer.singleShot(1000, self.unlock_button)
        
    def unlock_button(self):
        self.setEnabled(True)

    def update_buf_style(self):
        self.style_sheet = self.styleSheet()

    def enterEvent(self, event):
        self.style_sheet = self.styleSheet()
        self.setStyleSheet("QToolTip { color: rgb(0,0,0); border: 1px solid white; background-color: rgba(250, 250, 250, 100);}")
    def leaveEvent(self, event):
        self.setStyleSheet(self.style_sheet)

class channel_page(QtWidgets.QWidget):
    def __init__(self, num, installation_class, name_device, parent=None, device_class = None):
        super(channel_page, self).__init__()
        self.installation_class = installation_class
        self.name_device = name_device
        self.number = num
        self.layout = QtWidgets.QGridLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setObjectName("ch" + str(num))

        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(80)
        self.label_settings_channel = QtWidgets.QLabel("Не настроено")
        self.label_settings_channel.setObjectName("labelchset" + str(num))
        self.label_settings_channel.setStyleSheet(not_ready_style_border)
        self.label_settings_channel.setAlignment(QtCore.Qt.AlignCenter)
        self.label_settings_channel.setWordWrap(True)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidget(self.label_settings_channel)
        scroll_area.setWidgetResizable(True)
        self.is_standart_device = True
        if device_class is not None:

                if device_class.device_type == "oscilloscope":
                    '''
                    определение типа прибора необходимо для корректного отображения на главном 
                    окне установки, некоторые приборы(осциллограф) имеют физические каналы, но 
                    отдельно настраивать каждый канал нет смысла, для этого отображается один канал,
                    а все настройки происходят внутри
                    '''
                    self.is_standart_device = False


        if self.is_standart_device == True:
            self.state_Button = QtWidgets.QPushButton('Ch ' + str(self.number))
            self.state_Button.setToolTip(f"Закрыть ch {self.number}")
        else:
            self.state_Button = QtWidgets.QPushButton(str(self.name_device[:-2]))
            self.state_Button.setToolTip(f"Зыкрыть {self.name_device[:-2:]}")


        self.pushButton = QtWidgets.QPushButton('Настройка')
        self.pushButton.clicked.connect(lambda: self.click_set())
        self.layout.addWidget(self.state_Button, 0, 0)
        self.layout.addWidget(scroll_area, 2, 0, 9, 1)
        self.layout.addWidget(self.pushButton, 11, 0)
        
        self.retranslateUi()

    def click_set(self):
        self.installation_class.click_set(self.name_device, self.number)

    def hide_elements(self):
        self.state_Button.setMinimumSize(5, 5)
        self.state_Button.setFixedSize(5, 5)
        self.pushButton.hide()
        self.pushButton.setFixedSize(5, 5)
        self.label_settings_channel.hide()
        self.label_settings_channel.setFixedSize(5, 5)

    def enterEvent(self, event):
        pass

    def leaveEvent(self, event):
        pass
    
    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.pushButton.setText( _translate("channel page",'Настройка') )
        self.label_settings_channel.setText( _translate("channel page","Не настроено") )
        if self.is_standart_device == True:
            self.state_Button.setToolTip(_translate("channel page","Закрыть") + f"ch {self.number}")
        else:
            self.state_Button.setToolTip(_translate("channel page","Закрыть") + f"{self.name_device[:-2:]}")


class Ui_Installation(QtWidgets.QMainWindow):
    installation_close_signal = QtCore.pyqtSignal(int)

    def setupUi(self, base_window, installation_class, class_of_devices, exp_diagram, exp_call_stack):
        base_window.setObjectName("Installation")
        self.setWindowIcon(QIcon('picture/key.png'))
        self.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")
        self.central_widget = QtWidgets.QWidget(base_window)
        self.setCentralWidget(self.central_widget)

        self.N = 0
        for device in class_of_devices.values():
            ind_channels_buf = [0,0,0,0,0,0,0,0,0,0]
            for i in device.channels:
                ind_channels_buf[i.get_number()-1]+=1
            self.ind_channels =  0
            for i in ind_channels_buf:
                if i > 0:
                    self.ind_channels+=1  
            self.N+=1

        if self.N < 3:
            self.N = 3
        if self.N > 10:
            self.N = 10

        #--------------------------------
        self.base_lay = QtWidgets.QVBoxLayout(self.central_widget)
        # Горизонтальные слои 2 и 3 внутри слоя 1
        self.upper_lay = QtWidgets.QHBoxLayout()#слой с приборами и слой с окном сохранения результатов
        self.lower_lay = QtWidgets.QHBoxLayout()
        self.base_lay.addLayout( self.upper_lay, stretch = 2 )
        self.base_lay.addLayout( self.lower_lay, stretch = 1 )
        
        self.exp_diagram = exp_diagram
        self.exp_call_stack = exp_call_stack

        base_window.resize(self.N*120+10+600, 700)

        self.horLayout = QtWidgets.QHBoxLayout()
        self.horLayout.setObjectName("horLayout")

        self.devices_lay = {}
        self.installation_class = installation_class

        for device in class_of_devices:
            dev = device_page(class_of_devices[device], installation_class)
            self.horLayout.addWidget(dev)
            self.devices_lay[device] = dev

            sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Ignored)
            ind_channels_buf = [0,0,0,0,0,0,0,0,0,0]
            for i in class_of_devices[device].channels:
                ind_channels_buf[i.get_number()-1]+=1
            self.ind_channels =  0
            for i in ind_channels_buf:
                if i > 0:
                    self.ind_channels+=1  
            sizePolicy.setHorizontalStretch(self.ind_channels)
            dev.setSizePolicy(sizePolicy)

        self.verticalSpacerButton = QtWidgets.QSpacerItem(15, 15, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        #####################################################################
        
        self.start_button = CustomButton(self.central_widget)
        self.start_button.setMinimumSize(200, 100)
        font = QtGui.QFont()
        font.setPointSize(24)
        self.start_button.setFont(font)
        self.start_button.setObjectName("start_button")
        
        self.pause_button = CustomButton(self.central_widget)
        self.pause_button.setMinimumSize(100, 50)
        self.pause_button.setObjectName("pause_button")

        self.verticalSpacerButton = QtWidgets.QSpacerItem(15, 15, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        self.button_lay = QtWidgets.QVBoxLayout()

        self.button_lay.addItem(self.verticalSpacerButton)
        
        self.button_lay.addWidget(self.start_button)
        self.button_lay.addWidget(self.pause_button)
        #####################################################################

        self.clear_log_button = QtWidgets.QPushButton(self.central_widget)

        icon = QtGui.QIcon()

        if os.environ["APP_THEME"] == "dark":
            pic = "picture/clean_light.png"
        else:
            pic = "picture/clean_dark.png"

        icon.addPixmap(QtGui.QPixmap( pic ), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.clear_log_button.setIcon(icon)
        #self.clear_log_button.setIconSize(QtCore.QSize(15, 15))
        self.horizontalSpacer = QtWidgets.QSpacerItem(15, 15, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_31 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_31.addWidget(self.clear_log_button)
        self.horizontalLayout_31.addItem(self.horizontalSpacer)
    
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        self.pbar = QtWidgets.QProgressBar()
        self.pbar.setMinimum(0)
        self.pbar.setMaximum(100)
        self.pbar.setValue(0)
 
        font = QtGui.QFont()
        font.setPointSize(9)
        self.label_state = QtWidgets.QLabel(self.central_widget)
        self.label_state.setFont(font)
        

        self.label_time = QtWidgets.QLabel(self.central_widget)
        self.label_time.setFont(font)

        self.label_cont_time = QtWidgets.QLabel(self.central_widget)
        self.label_cont_time.setFont(font)

        self.horizontalLayout_for_label = QtWidgets.QHBoxLayout()
        self.horizontalLayout_for_label.addWidget(self.label_state)
        self.horizontalLayout_for_label.addWidget(self.label_cont_time)
        self.horizontalLayout_for_label.addWidget(self.label_time)

        self.horizontalLayout_for_label.setStretch(0, 3)

        self.log_lay = QtWidgets.QVBoxLayout()
        self.log_lay.addLayout(self.horizontalLayout_31)
        self.log_lay.addWidget(self.log)
        self.log_lay.addWidget(self.pbar)
        self.log_lay.addLayout(self.horizontalLayout_for_label)
        ####################################################################

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.verticalLayout_2 = QtWidgets.QVBoxLayout()

        self.horizontalLayout = QtWidgets.QHBoxLayout()

        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()

        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()

        #=======================


        self.scroll_area_diagram = QtWidgets.QScrollArea()
        self.scroll_area_diagram.setWidgetResizable(True)
        self.scroll_area_diagram.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.scroll_area_diagram.setWidget(self.exp_diagram)
        
        
        self.scroll_area_stack = QtWidgets.QScrollArea()
        self.scroll_area_stack.setWidgetResizable(True)
        self.scroll_area_stack.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
        self.scroll_area_stack.setWidget(self.exp_call_stack)
        
        #======================

        self.verticalSpacer = QtWidgets.QSpacerItem(15, 15, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        self.open_graph_button = QtWidgets.QPushButton()


        self.schematic_exp_name = QtWidgets.QLabel()
        self.schematic_exp_name.setAlignment(QtCore.Qt.AlignCenter)
        self.schematic_exp_name.setFont(font)
        #===============================
        splitter = QSplitter()
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        splitter.setOrientation(0)

        splitter.addWidget(self.scroll_area_diagram)
        splitter.addWidget(self.scroll_area_stack)

        splitter.setHandleWidth(1)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)


        #one_deca_part = int(self.width()/10)
        #splitter.setSizes([one_deca_part, one_deca_part*9, 0])
        #==============================

        self.verticalLayout_2.addWidget(self.schematic_exp_name)

        self.verticalLayout_2.addWidget(splitter, stretch=12)
        #self.verticalLayout_2.addWidget(self.scroll_area_diagram, stretch=10)
        #self.verticalLayout_2.addWidget(self.scroll_area_stack, stretch=6)
        
        self.verticalLayout_2.addWidget(self.open_graph_button)
        # ================================================================

        self.upper_lay.addLayout(self.horLayout, stretch=3)
        self.upper_lay.addLayout(self.verticalLayout_2, stretch=9)
        self.lower_lay.addLayout(self.log_lay)
        self.lower_lay.addLayout(self.button_lay)

        self.menubar = QtWidgets.QMenuBar(base_window)
        self.menubar.setGeometry(QtCore.QRect(10, 0, 590, 20))
        self.menubar.setObjectName("menubar")
        self.menu = QtWidgets.QMenu(self.menubar)
        self.menu.setObjectName("menu")

        base_window.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(base_window)
        self.statusbar.setObjectName("statusbar")
        base_window.setStatusBar(self.statusbar)
        self.save_installation_button_as = QtWidgets.QAction(base_window)
        self.save_installation_button_as.setObjectName("save_installation_button_as")
        self.save_installation_button = QtWidgets.QAction(base_window)
        self.save_installation_button.setObjectName("save_installation_button")
        self.open_installation_button = QtWidgets.QAction(base_window)
        self.open_installation_button.setObjectName("open_installation_button")
        self.add_device_button = QtWidgets.QAction(base_window)
        self.add_device_button.setObjectName("add_device_button")

        self.log_path_open = QtWidgets.QAction(base_window)

        self.convert_buf_button = QtWidgets.QAction(base_window)

        self.menu.addAction(self.save_installation_button)
        self.menu.addAction(self.save_installation_button_as)
        self.menu.addAction(self.open_installation_button)
        self.menu.addSeparator()
        self.menu.addAction(self.add_device_button)
        self.menu.addSeparator()
        self.menu.addAction(self.convert_buf_button)
        self.menu.addAction(self.log_path_open)
        self.menubar.addAction(self.menu.menuAction())

        self.set = QtWidgets.QMenu(self.menubar)
        self.menubar.addAction(self.set.menuAction())
        self.develop_mode = QtWidgets.QAction(base_window)
        self.general_settings = QtWidgets.QAction(base_window)
        self.set.addAction(self.develop_mode)
        self.set.addAction(self.general_settings)

        self.info = QtWidgets.QMenu(self.menubar)
        self.menubar.addAction(self.info.menuAction())
        self.instruction = QtWidgets.QAction(base_window)
        self.about_autors = QtWidgets.QAction(base_window)
        self.version = QtWidgets.QAction(base_window)
        self.info.addAction(self.instruction)
        self.info.addAction(self.about_autors)
        self.info.addAction(self.version)
        self.setAcceptDrops(True)
        

        self.retranslateUi(base_window)
        QtCore.QMetaObject.connectSlotsByName(base_window)


    def closeEvent(self, event):
        for dev_win in self.devices_lay.values():
            dev_win.setParent(None)
        self.installation_close_signal.emit(1)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path:
                    if ".ns" in file_path:
                        event.acceptProposedAction()
                        break

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path:
                if ".ns" in file_path:
                    self.installation_class.extract_saved_installlation(fileName=file_path)
                    break

    def add_new_devices(self, class_of_devices):
        for device in class_of_devices:
            dev = device_page(class_of_devices[device], self.installation_class)
            self.horLayout.addWidget(dev)
            self.devices_lay[device] = dev

            sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            ind_channels_buf = [0,0,0,0,0,0,0,0,0,0]
            for i in class_of_devices[device].channels:
                ind_channels_buf[i.get_number()-1]+=1
            self.ind_channels =  0
            for i in ind_channels_buf:
                if i > 0:
                    self.ind_channels+=1  
            sizePolicy.setHorizontalStretch(self.ind_channels)
            dev.setSizePolicy(sizePolicy)


    def retranslateUi(self, Installation):
        _translate = QtCore.QCoreApplication.translate
        self.open_graph_button.setText(_translate("Installation","показать график"))
        self.start_button.setText(_translate("Installation", "Запуск"))
        self.pause_button.setText(_translate("Installation", "Пауза"))

        self.menu.setTitle(_translate("Installation", "Меню"))
        self.set.setTitle(_translate("Installation", "Расширенные настройки"))
        self.info.setTitle(_translate("Installation", "Инфо"))
        self.save_installation_button.setText(
            _translate("Installation", "Сохранить установку"))
        self.save_installation_button_as.setText(
            _translate("Installation", "Сохранить установку как..."))
        self.open_installation_button.setText(
            _translate("Installation", "Открыть установку"))
        self.add_device_button.setText(
            _translate("Installation", "Добавить прибор"))
        
        self.develop_mode.setText(
            _translate("Installation", "Вкл режим разработчика"))
        self.general_settings.setText(_translate("Installation", "Настройки эксперимента"))
        
        self.instruction.setText(
            _translate("Installation", "Инструкция"))
        self.about_autors.setText(
            _translate("Installation", "Об авторах"))
        self.version.setText(
            _translate("Installation", "Версия приложения"))
        
        self.schematic_exp_name.setText(_translate("settings_save", "Схема взаимодействия приборов"))
        self.label_state.setText(_translate(
            "settings_save", "Состояние"))
        
        self.label_time.setText(_translate(
            "settings_save", ""))
        
        self.label_cont_time.setText(_translate(
            "settings_save", ""))
        
        self.convert_buf_button.setText(_translate(
            "settings_save", "Сохранить результаты из buf файла"))
        
        self.log_path_open.setText(_translate("main","Открыть лог файл"))
