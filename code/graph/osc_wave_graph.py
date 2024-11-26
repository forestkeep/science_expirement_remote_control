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

import copy
import random
import time
import logging

import numpy as np
import pyqtgraph as pg
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QApplication,
    QFileDialog,
    QDialog
)
from pyqtgraph.opengl import GLAxisItem, GLLinePlotItem, GLScatterPlotItem, GLViewWidget

try:
    from calc_values_for_graph import ArrayProcessor
    from Message_graph import messageDialog
    from Link_data_import_win import Check_data_import_win
except:
    from graph.calc_values_for_graph import ArrayProcessor
    from graph.Message_graph import messageDialog
    from graph.Link_data_import_win import Check_data_import_win

logger = logging.getLogger(__name__)

def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result

    return wrapper


class X:
    def __init__(self, tablet_page):
        self.page = tablet_page
        self.legend = pg.LegendItem(size=(80, 60), offset=(10, 10))
        self.is_show_warning = True
        self.key_to_update_plot = True
        self.x = []
        self.y = []
        self.dict_param = {}

        self.used_colors = set()
        self.color_gen = self.get_random_color()

        self.y_main_axis_label = ""
        self.x_axis_label = ""

        self.contrast_colors = [
            "#FFFFFF",  # Белый
            "#FF0000",  # Красный
            "#00FF00",  # Зеленый
            "#0000FF",  # Синий
            "#FFFF00",  # Желтый
            "#FF00FF",  # Пурпурный
            "#00FFFF",  # Голубой
            "#FFA500",  # Оранжевый
            "#FFA07A",  # Светло-коралловый
            "#FF1493",  # Ярко-розовый
            "#00FA9A",  # Яркий зеленый
            "#1E90FF",  # Ярко-синий
            "#FFD700",  # Золотой
            "#ADFF2F",  # Зелёный лайм
            "#FF4500",  # Оранжево-красный
            "#FF69B4",  # Ярко-розовый
            "#FFB6C1",  # Светло-розовый
            "#FFDAB9",  # Персиковый
            "#98FB98",  # Светло-зеленый
            "#7B68EE",  # Ярко-лавандовый
            "#FFD700",  # Золотой
            "#FF6347",  # Помидор
            "#FF00FF",  # Фуксия
            "#00BFFF",  # Ярко-голубой
            "#FF8C00",  # Яркий оранжевый
            "#00FF7F",  # Ярко-зеленый
            "#FF1493",  # Ярко-розовый
            "#FF7F50",  # Кoral
            "#FFD700",  # Золотой
            "#FFA500",  # Оранжевый
            "#FFB559",  # Светло-оранжевый
            "#3CB371",  # Ярко-зеленый
            "#00CED1",  # Ярко-голубой
            "#ADFF2F",  # Лаймовый
        ]

        self.key = True  # ключ предназначен для манипулирования данными в виджетах без вызова функций обработчиков, если ключ установлен в False, то обработчик не будет испольняться

        self.vertical_lines = verticals_lines()
        self.ver_curve_left = None
        self.ver_curve_right = None
        self.tooltip = QLabel("X:0,Y:0")
        self.build_hyst_loop_check = QCheckBox()
        self.build_hyst_loop_check.stateChanged.connect(
            lambda: self.hyst_loop_activate()
        )

        self.loops_stack = [] #здесь хранятся петли, которые были рассчитаны и установлены на график

        self.label = QLabel()  # Лейбл с именем канала
        self.label2 = QLabel()  # Лейбл с именем канала

        self.list_vert_curve = []
        self.initUI()

    def update_dict_param(self, new: dict):
        if new:
            self.dict_param = new
            channel_keys = self.extract_wavech_devices(self.dict_param)
            #print(f"{channel_keys=}")

            devices, channels, wavechs = self.extract_data(channel_keys)
            #print(f"{devices=} {channels=} {wavechs=}")
            current_dev = self.choice_device.currentText()
            self.key = False
            devices = set(devices)
            devices = list(devices)
            if not devices:
                devices.append(self.choice_device_default_text)
            self.choice_device.clear()
            self.choice_device.addItems(devices)
            if current_dev in devices:
                self.choice_device.setCurrentText(current_dev)
            self.key = True
            self.extract_ch_with_wave(self.dict_param)
            try:
                self.update_num_waveforms()
            except Exception as e:
                print(e)
                self.new_dev_checked()
                self.update_num_waveforms()

    def extract_data(self, input_dict):
        devices = []
        channels = []
        wavechs = []

        for (device, channel), wavech_list in input_dict.items():
            devices.append(device)
            channels.append(channel)
            wavechs.extend(wavech_list)

        return devices, channels, wavechs

    def extract_wavech_devices(self, main_dict):
        wavech_devices = []
        wavech_channels = {}
        channel_wavech_keys = {}

        for device, channels in main_dict.items():
            for channel, data in channels.items():
                #print(f"{channel=} {data=}")
                wavech_keys = [key for key in data.keys() if "wavech" in key]
                if wavech_keys:
                    wavech_devices.append(device)
                    if device not in wavech_channels:
                        wavech_channels[device] = []
                    wavech_channels[device].append(channel)
                    channel_wavech_keys[(device, channel)] = wavech_keys

        return channel_wavech_keys

    def extract_ch_with_wave(self, main_dict):

        channel_with_wave = {}
        for device in main_dict.keys():
            if device not in channel_with_wave.keys():
                channel_with_wave[device] = []

            for channel in main_dict[device].keys():
                if "wavech" in main_dict[device][channel].keys():
                    channel_with_wave[device].append(channel)
        return channel_with_wave

    def import_data(self, *args, **kwargs):
        
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, ans = QFileDialog.getOpenFileName(
            caption=QApplication.translate("GraphWindow","укажите путь импорта"),
            directory="",
            filter="Книга Excel (*.xlsx)",
            options=options,
        )
        
        if fileName:
            if ans == "Книга Excel (*.xlsx)":
                df = pd.read_excel(fileName, engine='openpyxl')

                if 'time' not in df.columns:
                    self.is_time_column = False

                df = df.dropna(axis=1, how='all')#удаление пустых столбцов

                window = Check_data_import_win([col for col in df.columns], self.update_dict_param)
                ans = window.exec_()
                if ans == QDialog.Accepted:  # проверяем, была ли нажата кнопка OK
                    selected_step = window.step_combo.currentText()
                    selected_channels = [cb.text() for cb in window.checkboxes if cb.isChecked()]
                else:
                    return

                selected_channels.append(selected_step)
                errors_col = []

                for col in selected_channels:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='raise')
                    except ValueError:
                        errors_col.append(col)
                        continue
                    
                if errors_col != []:
                    res = ', '.join(errors_col)
                    text = QApplication.translate("GraphWindow", "В столбцах {res} обнаружены данные, которые не получается преобразовать в числа.\nПри построение эти точки будут пропущены.")
                    text = text.format(res = res)
                    message = messageDialog(
                        title = QApplication.translate("GraphWindow","Сообщение"),
                        text= text
                    )
                    message.exec_()

                selected_channels.pop(len(selected_channels) - 1)

                import_time_scale_column = pd.to_numeric(df[selected_step], errors='coerce')

                import_time_scale = None
                for scale in import_time_scale_column:
                    if isinstance(scale, (float, int)) and scale > 0:
                        import_time_scale = scale
                        break

                if import_time_scale is None:
                    message = messageDialog(
                        title = QApplication.translate("GraphWindow","Сообщение"),
                        text= QApplication.translate("GraphWindow","Выбранный шаг не является числом или равен нулю, проверьте столбец с шагом времени")
                    )
                    return
                             
                dev = {'import_data': {}}
                df = df.dropna(axis=1)
                for col in selected_channels:
                    df[col] = (pd.to_numeric(df[col], errors='coerce'))
                    col_ = col.replace('(', '[').replace(')', ']') + ' wavech'
                    volt_val = np.array( df[col].tolist() )
                    dev["import_data"][col] = {col_: {0 : volt_val}, "scale": [import_time_scale for i in range(len(volt_val))]}

                self.update_dict_param(dev)
                self.new_dev_checked()
            
    def initUI(self):

        self.tab1Layout = QVBoxLayout()
        # Add all data source selectors and graph area to tab1Layout
        self.hor_lay = QHBoxLayout()
        self.choice_device = QComboBox()
        self.choice_device_default_text = QApplication.translate('graph_win',"Выберите устройство" )
        self.choice_device.addItems(
            [""]
        )

        self.choice_device.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )  # Расширяющийся по ширине и фиксированный по высоте
        self.choice_device.setMaximumSize(150, 20)  # Ограничиваем максимальный размер

        self.choice_device.currentTextChanged.connect(lambda: self.new_dev_checked())
        self.choice_device.currentIndexChanged.connect(lambda: self.new_dev_checked())

        self.hor_lay.addWidget(self.choice_device)

        self.graphView = self.setupGraphView()

        self.graphView.scene().sigMouseMoved.connect(self.showToolTip_main)

        self.import_data_button = QPushButton(
            QApplication.translate('graph_win',"Импорт данных")
        )

        self.import_data_button.setMaximumSize(150, 30)  # Ограничиваем максимальный размер
        self.import_data_button.clicked.connect(self.import_data)

        self.tab1Layout.addLayout(self.hor_lay)
        self.tab1Layout.addWidget(self.build_hyst_loop_check)
        self.tab1Layout.addWidget(self.import_data_button)
        # self.graphView.hide()
        # self.graphView.show()

        splitter = QSplitter()
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Добавяем графики в сплиттер

        # Устанавливаем ориентировку на вертикальную
        splitter.setOrientation(1)  # 1 - вертикальный

        self.graphView_loop = self.setupGraphView()

        self.graphView_loop.scene().sigMouseMoved.connect(self.showToolTip_loop)

        splitter.addWidget(self.graphView)
        splitter.addWidget(self.graphView_loop)

        # Устанавливаем ориентировку на вертикальную
        splitter.setOrientation(1)  # 1 - вертикальный

        splitter.setStretchFactor(0, 5)  # Первому виджету (Plot 1) коэффициент 1
        splitter.setStretchFactor(1, 5)  # Второму виджету (Plot 2) коэффициент 2

        self.tab1Layout.addWidget(splitter)
        self.graphView_loop.hide()

        self.hyst_loop_layer = self.create_hyst_calc_layer()
        self.hyst_loop_layer.hide()
        self.tab1Layout.addWidget(self.hyst_loop_layer)
        self.page.setLayout(self.tab1Layout)

        self.retranslateUI(self.page)

    def setupGraphView(self):
        graphView = pg.PlotWidget(title="")

        graphView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.color_line_main = "#55aa00"
        self.color_line_second = "#ff0000"

        # Placeholder items for dropdown - this will be dynamically populated later

        graphView.plotItem.getAxis("left").linkToView(graphView.plotItem.getViewBox())
        graphView.plotItem.getAxis("bottom").linkToView(graphView.plotItem.getViewBox())

        self.p1 = graphView.plotItem

        self.p2 = pg.ViewBox()
        # self.p1.showAxis('right')
        self.p1.scene().addItem(self.p2)
        self.p1.getAxis("right").linkToView(self.p2)
        self.p2.setXLink(self.p1)
        self.p1.getAxis("right").setLabel("axis2", color="#000fff")

        self.curve2 = pg.PlotCurveItem(
            pen=pg.mkPen(color=self.color_line_second, width=1)
        )
        self.p2.addItem(self.curve2)

        my_font = QFont("Times", 13)
        self.p1.getAxis("right").label.setFont(my_font)
        graphView.getAxis("bottom").label.setFont(my_font)
        graphView.getAxis("left").label.setFont(my_font)

        graphView.setMinimumSize(300, 200)

        return graphView

    def create_checkbox_layer(self, channels, waves_num):
        # waves_num = список, в элементах которого указано количество осциллограмм для соответствующего канала
        layout = QGridLayout()
        checkboxes = []
        channels_wave_forms = {}

        # Размещение лейблов и чекбоксов с комбобоксами
        for index, name_ch in enumerate(channels):
            col = index // 4  # Номер столбца
            row = (
                index % 4 + 1
            )  # Строка для размещения чекбокса и комбобокса, смещение на 1 для лейблов

            # Создание лейбла для столбца, если он еще не добавлен
            if row == 1:  # Лейбл добавляется в первую строку
                lay = QHBoxLayout()
                self.label = QLabel()  # Лейбл с именем канала
                self.label2 = QLabel()  # Лейбл с именем канала
                lay.addWidget(self.label)
                lay.addWidget(self.label2)
                layout.addLayout(lay, 0, col)

            # Создание горизонтального лэйаута для чекбокса и комбобокса
            lay = QHBoxLayout()
            checkbox = QCheckBox(name_ch)
            list_osc = QComboBox()
            list_osc.addItems([str(i) for i in range(1, waves_num[index] + 1)])
            lay.addWidget(checkbox)
            lay.addWidget(list_osc)

            list_osc.currentIndexChanged.connect(lambda: self.checked_channel())
            layout.addLayout(
                lay, row, col
            )  # Размещение в соответствующей строке и столбце
            checkboxes.append(checkbox)
            checkbox.stateChanged.connect(lambda: self.checked_channel())
            channels_wave_forms[name_ch] = list_osc

        self.tooltip = QLabel("X:0,Y:0")
        layout.addWidget(self.tooltip)

        for ch, obj in channels_wave_forms.items():
            ch_name = copy.deepcopy(ch)
            obj.currentIndexChanged.connect(lambda: self.update_status_vert_line())

        return layout, checkboxes, channels_wave_forms

    def create_hyst_calc_layer(self):

        self.button_hyst_loop = QPushButton()
        self.button_hyst_loop.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.button_hyst_loop.setMaximumSize(
            130, 100
        ) 

        self.button_hyst_loop_clear = QPushButton()
        self.button_hyst_loop_clear.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.button_hyst_loop_clear.setMaximumSize(
            130, 100
        )  

        self.button_hyst_loop_clear_last = QPushButton()
        self.button_hyst_loop_clear_last.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.button_hyst_loop_clear_last.setMaximumSize(
            130, 100
        )

        self.name_field = QLabel(QApplication.translate("GraphWindow","Поле"))
        self.field_ch_choice = QComboBox()


        self.name_sig = QLabel(QApplication.translate("GraphWindow","Сигнал"))
        
        self.sig_ch_choice = QComboBox()


        self.sig_ch_choice.setMaximumSize(250, 40)
        self.field_ch_choice.setMaximumSize(250, 40)

        self.sig_ch_choice.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.field_ch_choice.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.auto_button = QPushButton(QApplication.translate("GraphWindow","Авто"))
        self.auto_button.setMaximumSize(100, 100)

        self.avg_loop_button = QPushButton(QApplication.translate("GraphWindow","Усреднить петли"))
        self.avg_loop_button.setMaximumSize(100, 100)

        self.left_coord = wheelLineEdit()
        self.left_coord.line_edit.setPlaceholderText(QApplication.translate("GraphWindow","Координата слева"))
        self.left_coord.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.left_coord.setMaximumSize(250, 40)

        self.right_coord = wheelLineEdit()
        self.right_coord.line_edit.setPlaceholderText(QApplication.translate("GraphWindow","Координата справа"))
        self.right_coord.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.right_coord.setMaximumSize(250, 40)

        self.right_coord.set_second_line_widget(line=self.left_coord.line_edit)
        self.left_coord.set_second_line_widget(line=self.right_coord.line_edit)

        self.square = QLineEdit()
        self.square.setPlaceholderText(QApplication.translate("GraphWindow","Площадь провода(мкм)"))

        self.square.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.square.setMaximumSize(250, 40)

        self.resistance = QLineEdit()
        self.resistance.setPlaceholderText(QApplication.translate("GraphWindow","Сопротивление провода(Ом)"))
        self.resistance.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.resistance.setMaximumSize(250, 40)


        self.square.textChanged.connect(lambda: self.is_all_hyst_correct())
        self.resistance.textChanged.connect(lambda: self.is_all_hyst_correct())
        self.right_coord.line_edit.textChanged.connect(
            lambda: self.is_all_hyst_correct()
        )
        self.right_coord.line_edit.textChanged.connect(lambda: self.draw_vert_line())
        self.left_coord.line_edit.textChanged.connect(
            lambda: self.is_all_hyst_correct()
        )
        self.left_coord.line_edit.textChanged.connect(lambda: self.draw_vert_line())
        self.field_ch_choice.currentTextChanged.connect(
            lambda: self.is_all_hyst_correct()
        )
        self.sig_ch_choice.currentTextChanged.connect(
            lambda: self.is_all_hyst_correct()
        )
        self.field_ch_choice.currentTextChanged.connect(
            lambda: self.update_status_vert_line()
        )
        self.button_hyst_loop.clicked.connect(lambda: self.draw_loop())
        self.button_hyst_loop_clear.clicked.connect( lambda: self.clear_all_loops() )
        self.auto_button.clicked.connect(lambda: self.push_auto_button())

        self.button_hyst_loop_clear_last.clicked.connect(lambda: self.clear_last_loop())
        self.avg_loop_button.clicked.connect(lambda: self.avg_loop())

    #-----------------------------------------
        self.hyst_loop_layer = QFrame()
        main_lay = QHBoxLayout(self.hyst_loop_layer)

        buttons_lay = QVBoxLayout()

        buttons1_lay = QHBoxLayout()
        buttons1_lay.addWidget(self.button_hyst_loop, alignment=Qt.AlignLeft)
        buttons1_lay.addWidget(self.avg_loop_button, alignment=Qt.AlignLeft)
        buttons_lay.addLayout(buttons1_lay)

        buttons2_lay = QHBoxLayout()
        buttons2_lay.addWidget(self.auto_button, alignment=Qt.AlignLeft)
        
        buttons_lay.addLayout(buttons2_lay)

        buttons3_lay = QHBoxLayout()
        buttons3_lay.addWidget(self.button_hyst_loop_clear, alignment=Qt.AlignLeft)
        buttons3_lay.addWidget(self.button_hyst_loop_clear_last, alignment=Qt.AlignLeft)
        buttons_lay.addLayout(buttons3_lay)

        main_lay.addLayout(buttons_lay)

        enter_lay = QVBoxLayout()

        field_signal_lay = QHBoxLayout()
        
        lay_field = QVBoxLayout()

        lay_field.addWidget(self.name_field)
        lay_field.addWidget(self.field_ch_choice)
        field_signal_lay.addLayout(lay_field)

        lay_sig = QVBoxLayout()
        lay_sig.addWidget(self.name_sig)
        lay_sig.addWidget(self.sig_ch_choice)
        field_signal_lay.addLayout(lay_sig)

        enter_lay.addLayout(field_signal_lay)

        coords_line_lay = QHBoxLayout()
        coords_line_lay.addWidget(self.left_coord)
        coords_line_lay.addWidget(self.right_coord)
        enter_lay.addLayout(coords_line_lay)

        field_signal_lay2 = QHBoxLayout()
        field_signal_lay2.addWidget(self.square)

        field_signal_lay2.addWidget(self.resistance)
        enter_lay.addLayout(field_signal_lay2)

        main_lay.addLayout(enter_lay)

        return self.hyst_loop_layer
    def avg_loop(self):
        new_loop = self.calc_avg_loop(loops_stack=self.loops_stack)

    def calc_avg_loop(self, loops_stack):
        '''вернет объект петли, полученный усреднением стека петель'''
        print("вычисляем среднюю петлю")
        if len(loops_stack) == 1:
            return loops_stack[0]
        
        last_loop = None
        if len(loops_stack)%2 == 1:
            last_loop = loops_stack[-1]
            loops_stack.pop()
            
        while len(loops_stack) > 1:
            new_loop_stack = []
            for i in range(len(loops_stack)-1, 0, -2):
                loop1 = loops_stack[i]
                loop2 = loops_stack[i-1]
                loops_stack.pop()
                loops_stack.pop()
 
                new_loop = self.calc_avg_two_loops(loop1, loop2)
                
                new_loop_stack.append(new_loop)
                
            loops_stack = new_loop_stack
            
        if last_loop is not None:
            new_loop = self.calc_avg_two_loops(last_loop, loops_stack[0])
        else:
            new_loop = loops_stack[0]
            
        return new_loop
            
    def calc_avg_two_loops(loop1, loop2):
        calculator = ArrayProcessor()
        mean_x, y1, y2 = calculator.combine_interpolate_arrays(arr_time_x1=loop1.filtered_raw_data_x,
                                                      arr_time_x2=loop2.filtered_raw_data_x,
                                                      values_y1=loop1.filtered_raw_data_y,
                                                      values_y2=loop2.filtered_raw_data_y)
        mean_resistance = (loop1.resistance + loop2.resistance)/2
        mean_wire_square = (loop1.wire_square + loop2.wire_square)/2
        
        mean_y = (y1+y2)/2
        
        new_loop = hystLoop(raw_x=mean_x,
                            raw_y=mean_y,
                            resistance=mean_resistance,
                            wire_square=mean_wire_square
                            )
        
        return new_loop
            
            
    def clear_last_loop(self):
        if len( self.loops_stack ) > 0:
            deleting_loop = self.loops_stack[-1]
            self.graphView_loop.removeItem( deleting_loop.plot_obj )  # Удаляем график
            self.loops_stack.pop()
            del deleting_loop

        else:
            print("no loops")

    def clear_all_loops(self):
        count = len(self.loops_stack)
        for i in range(count):
            self.clear_last_loop()
        self.loops_stack = []

    def update_num_waveforms(self):

        # формируем список каналов
        devices = self.extract_ch_with_wave(self.dict_param)

        current_dev = self.choice_device.currentText()
        if current_dev == self.choice_device_default_text:
            pass
        else:
            for ch in devices[current_dev]:
                waves_num = len(self.dict_param[current_dev][ch]["wavech"])
                current = self.channels_wave_choice[ch].currentText()
                self.key = False
                self.channels_wave_choice[ch].clear()
                self.channels_wave_choice[ch].addItems(
                    [str(i) for i in range(1, waves_num + 1)]
                )
                self.channels_wave_choice[ch].setCurrentText(current)
                self.key = True

    def new_dev_checked(self):
        """функция считывает имя устройства, на основании имени перестраивает поле выбора каналов и осциллограмм"""
        if self.key:
            dev_name = self.choice_device.currentText()

            if dev_name == self.choice_device_default_text:
                self.clear_layout(self.hor_lay, self.choice_device)
            else:
                self.clear_layout(self.hor_lay, self.choice_device)

                # формируем список каналов
                channel_keys = self.extract_wavech_devices(self.dict_param)
                devices, channels, wavechs = self.extract_data(channel_keys)

                current_dev = self.choice_device.currentText()

                channel_names = []
                waves_num = []
                for i in range(len(devices)):
                    if devices[i] == current_dev:
                        channel_names.append(channels[i])
                        waves_num.append(
                            len(self.dict_param[devices[i]][channels[i]][wavechs[i]])
                        )

                self.field_ch_choice.clear()
                self.sig_ch_choice.clear()
                self.field_ch_choice.addItems(channel_names)
                self.sig_ch_choice.addItems(channel_names)

                ch_check_layer, self.ch_check, self.channels_wave_choice = (
                    self.create_checkbox_layer(channel_names, waves_num)
                )
                self.hor_lay.addLayout(ch_check_layer)

    def clear_layout(self, layout, widget_to_keep):
        # Проходим по всем элементам лэйаута в обратном порядке
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if (
                    widget and widget != widget_to_keep
                ):  # Если виджет не целевой, удаляем его
                    layout.removeWidget(widget)
                    widget.deleteLater()  # Удаляем виджет из памяти
                elif item.layout():  # Если это лэйаут, очищаем и удаляем его
                    self.clear_layout(item.layout(), widget_to_keep)
                    layout.removeItem(item)  # Удаляем сам лэйаут из родителя
                    item.layout().deleteLater()  # Удаляем лэйаут из памяти

    def checked_channel(self):
        """сканирует выбранные каналы и строит соответсвующие осциллограммы"""
        # self.ch_check, self.channels_wave_choice
        if self.key:
            #self.y_values = [[], [], [], [], [], [], [], []]
            self.y_values = {}
            self.scales = {}
            self.legend_ch_names = {}
            for ch in self.ch_check:
                ch_name = ch.text()
                #print(f"{ch_name=}")
                #number = int(ch_name[3])

                if ch.isChecked():
                    device = self.choice_device.currentText()
                    num_wave = (
                        int(self.channels_wave_choice[ch.text()].currentText()) - 1
                    )
                    for key in self.dict_param[device][ch_name].keys():
                        if "wavech" in key:
                            key_wave = key
                            break
                    self.y_values[ch_name] = self.dict_param[device][ch_name][key_wave][num_wave]
                    reere = self.dict_param[device][ch_name]["scale"]
                    self.scales[ch_name] = self.dict_param[device][ch_name]["scale"][num_wave]
                    self.legend_ch_names[ch_name] = ch_name
                else:
                    self.y_values[ch_name] = []

            self.update_draw()

    def set_default(self):
        """привести класс к исходному состоянию"""
        self.graphView.plotItem.clear()
        self.graphView_loop.plotItem.clear()
        self.choice_device.clear()
        self.choice_device.addItems([self.choice_device_default_text])
        pass

    def update_draw(self):
        self.y_second_axis_label = "V"
        self.x_axis_label = "s"
        self.y_main_axis_label = "V"

        # Вместо полного очищения графика удаляем только текущие кривые
        current_curves = self.graphView.plotItem.listDataItems()
        for curve in current_curves:
            if curve not in self.list_vert_curve:
                self.graphView.plotItem.removeItem(curve)

        self.graphView.plotItem.getAxis("left").linkToView(
            self.graphView.plotItem.getViewBox()
        )
        self.graphView.plotItem.getAxis("bottom").linkToView(
            self.graphView.plotItem.getViewBox()
        )
        self.graphView.setLabel("left", self.y_main_axis_label, color="#ffffff")
        self.graphView.setLabel("bottom", self.x_axis_label, color="#ffffff")
        self.legend.clear()

        self.legend.setParentItem(self.graphView.plotItem)

        for i, key in enumerate(self.y_values.keys()):
            if len(self.y_values[key]) > 0:
                curve = self.graphView.plot(
                    [k * self.scales[key] for k in range(len(self.y_values[key]))],
                    self.y_values[key],
                    pen={
                        "color": self.contrast_colors[i],
                        "width": 1,
                        "antialias": True,
                        "symbol": "o",
                    },
                    name=f"{self.legend_ch_names[key]}",  # Укажите имя для легенды
                )
                self.legend.addItem(
                    curve, f"{self.legend_ch_names[key]}"
                )  # Добавление элемента в легенду

        self.graphView.getAxis("left").setGrid(True)
        self.graphView.getAxis("bottom").setGrid(True)

    def showToolTip_main(self, event):
        pos = event  # Позиция курсора
        x_val = round(
            self.graphView.plotItem.vb.mapSceneToView(pos).x(), 5
        )  # Координата X
        y_val = round(
            self.graphView.plotItem.vb.mapSceneToView(pos).y(), 5
        )  # Координата Y
        text = f'<p style="font-size:{10}pt">X:{x_val} Y:{y_val}</p>'
        try:
            self.tooltip.setText(text)
        except:
            pass  # лейбл удален

    def showToolTip_loop(self, event):
        pos = event  # Позиция курсора
        x_val = round(
            self.graphView_loop.plotItem.vb.mapSceneToView(pos).x(), 5
        )  # Координата X
        y_val = round(
            self.graphView_loop.plotItem.vb.mapSceneToView(pos).y(), 5
        )  # Координата Y
        text = f'<p style="font-size:{10}pt">X:{x_val} Y:{y_val}</p>'
        try:
            self.tooltip.setText(text)
        except:
            pass  # лейбл удален

    def test_3d(self, tablet_page):
        self.tab2Layout = QVBoxLayout()
        w = GLViewWidget()
        w.setWindowTitle("3D график точек с уникальными цветами по Y")
        self.tab2Layout.addWidget(w)
        tablet_page.setLayout(self.tab2Layout)

        # Создаем 3D координатную сетку
        x = np.linspace(0, 10, 10)
        y = np.linspace(0, 10, 10)
        X, Y = np.meshgrid(x, y)
        Z = np.sin(np.sqrt(X**2 + Y**2))  # Функция для высоты

        # Создаем массив точек
        points = np.array([X.flatten(), Y.flatten(), Z.flatten()]).T

        # Определяем цвета для различных значений Y
        unique_y = np.unique(points[:, 1])
        colors_dict = {
            value: (np.random.rand(), np.random.rand(), np.random.rand(), 1)
            for value in unique_y
        }  # Альфа-канал
        colors = np.zeros((points.shape[0], 4))  # 4 канала: R, G, B, A
        grouped_lines = {value: [] for value in unique_y}

        for i in range(len(points)):
            y_value = points[i, 1]
            color = colors_dict[y_value]
            colors[i] = color  # Теперь color содержит RGBA
            grouped_lines[y_value].append(points[i])  # Группируем по y

        # Создаем объект для отображения точек
        scatter = GLScatterPlotItem(pos=points, size=5, color=colors)

        # Добавляем линии для каждой уникальной координаты Y
        for y_value, line_points in grouped_lines.items():
            if line_points:
                # Преобразуем в массив NumPy и сортируем по x для последовательного соединения
                line_points = np.array(line_points)
                line_points = line_points[np.argsort(line_points[:, 0])]
                line_item = GLLinePlotItem(
                    pos=line_points, color=colors_dict[y_value], width=2
                )  # color уже содержит альфа-канал
                w.addItem(line_item)

        # Добавляем точки в сцену
        w.addItem(scatter)

        # Добавление осей X и Z
        axis = GLAxisItem()

        axis.setSize(10, 10, 10)

        w.addItem(axis)

        # Показываем график

        main_dict = {
            "device1": {"ch_1": {"time": "some_time", "param1": "some_value"}},
            "device2": {
                "ch_1": {"time": "some_time", "param1": "some_value"},
                "ch_2": {"time": "some_time", "param1": "some_value"},
                "ch_3": {"time": "some_time", "param1": "some_value"},
            },
            "device3": {
                "ch_1": {"time": "some_time", "param1": "some_value"},
                "ch_2": {
                    "time": "some_time",
                    "param1": "some_value",
                    "wavech1": [[3.2, 3.2, 3.2], [3.2, 3.2, 3.2]],
                },
            },
            "device4": {
                "ch_1": {
                    "time": "some_time",
                    "wavech1": [[3.2, 3.2, 3.2], [3.2, 3.2, 3.2]],
                    "wavech2": [[3.2, 3.2, 3.2], [3.2, 3.2, 3.2]],
                }
            },
        }

        channel_keys = self.extract_wavech_devices(main_dict)

        w.show()

    # hyst section func
    def is_coord_correct(self) -> bool:
        coord1 = self.left_coord.line_edit.text()
        coord2 = self.right_coord.line_edit.text()

        is_coord1_correct = True
        is_coord2_correct = True

        try:
            coord1 = float(coord1)
        except:
            is_coord1_correct = False

        try:
            coord2 = float(coord2)
        except:
            is_coord2_correct = False

        self.left_coord.setStyleSheet(
            "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
        )
        self.right_coord.setStyleSheet(
            "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
        )
        if is_coord1_correct:
            self.left_coord.setStyleSheet(
                "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
            )
        if is_coord2_correct:
            self.right_coord.setStyleSheet(
                "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
            )
        if is_coord1_correct and is_coord2_correct:
            if coord1 > coord2:
                self.left_coord.setStyleSheet(
                    "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
                )
                self.right_coord.setStyleSheet(
                    "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
                )
                is_coord2_correct = False
                is_coord1_correct = False

        return is_coord1_correct and is_coord2_correct

    def is_param_correct(self) -> bool:
        resistance = self.resistance.text()
        square = self.square.text()

        is_res_correct = True
        is_sq_correct = True

        try:
            resistance = float(resistance)
        except:
            is_res_correct = False

        try:
            square = float(square)
        except:
            is_sq_correct = False

        self.resistance.setStyleSheet(
            "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
        )
        self.square.setStyleSheet(
            "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
        )
        if is_res_correct:
            self.resistance.setStyleSheet(
                "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
            )
        if is_sq_correct:
            self.square.setStyleSheet(
                "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
            )

        return is_res_correct and is_sq_correct

    def is_ch_sig_field_correct(self) -> bool:
        self.sig_ch_choice.setStyleSheet(
            "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
        )
        self.field_ch_choice.setStyleSheet(
            "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
        )
        if self.sig_ch_choice.currentText() == self.field_ch_choice.currentText():
            self.sig_ch_choice.setStyleSheet(
                "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
            )
            self.field_ch_choice.setStyleSheet(
                "border: 1px solid rgb(180, 0, 0); border-radius: 5px;"
            )
            return False
        return True

    def is_all_hyst_correct(self) -> bool:
        status = self.is_ch_sig_field_correct()
        status2 = self.is_coord_correct()
        status3 = self.is_param_correct()
        return status and status2 and status3

    def find_sign_change(self, derivative):
        sign_changes = []
        for i in range(1, len(derivative)):
            # if np.sign(derivative[i]) != np.sign(derivative[i - 1]) and np.sign(derivative[i]) > 0:
            if (
                np.sign(derivative[i]) != np.sign(derivative[i - 1])
                and derivative[i] != 0
            ):
                sign_changes.append(i)

        return sign_changes

    def push_auto_button(self):

        if self.vertical_lines.is_data_setted == False:
            device = self.choice_device.currentText()
            ch_field = self.field_ch_choice.currentText()
            number_field = int(self.channels_wave_choice[ch_field].currentText()) - 1

            key_wave = None
            for key in self.dict_param[device][ch_field].keys():
                if "wavech" in key:
                    key_wave = key
                    break

            if key_wave == None:
                text = " ".join(self.dict_param[device][ch_field].keys())
                logger.error("В выбранном канале нет осциллограммы" + text)
                return

            y_val = self.dict_param[device][ch_field][key_wave][number_field]
            scale_field = self.dict_param[device][ch_field]["scale"][number_field]

            interval_index = np.array(self.find_sign_change(y_val))
            interval_values = interval_index * scale_field

            ans = self.vertical_lines.set_data(
                max_y_val=np.nanmax(y_val),
                min_y_val=np.nanmin(y_val),
                interval_values=interval_values,
            )
            if ans == False:
                print("Нельзя найти точки пересечения или она всего одна")

        if self.vertical_lines.is_data_setted == True:

            status, x_vert_1, x_vert_2 = self.vertical_lines.get_next_data()
            if status:
                self.right_coord.line_edit.setText(str(x_vert_2))
                self.left_coord.line_edit.setText(str(x_vert_1))
            else:
                self.right_coord.line_edit.setText("---")
                self.left_coord.line_edit.setText("---")

    def update_status_vert_line(self):
        if self.key:
            self.vertical_lines.reset_data()
            current_curves = self.graphView.plotItem.listDataItems()
            for curve in current_curves:
                if curve in self.list_vert_curve:
                    self.graphView.plotItem.removeItem(curve)

    def draw_vert_line(self):
        if self.ver_curve_left in self.graphView.scene().items():
            self.graphView.removeItem(self.ver_curve_left)

        if self.ver_curve_right in self.graphView.scene().items():
            self.graphView.removeItem(self.ver_curve_right)

        device = self.choice_device.currentText()
        ch_field = self.field_ch_choice.currentText()
        number_field = int(self.channels_wave_choice[ch_field].currentText()) - 1
        try:
            key_wave = None
            for key in self.dict_param[device][ch_field].keys():
                if "wavech" in key:
                    key_wave = key
                    break
            y_val = self.dict_param[device][ch_field][key_wave][number_field]
        except:
            y_val = [5]

        x_vert_1_ok = False
        x_vert_2_ok = False
        try:
            x_vert_2 = float(self.right_coord.line_edit.text())
            x_vert_2_ok = True
        except:
            pass
        try:
            x_vert_1 = float(self.left_coord.line_edit.text())
            x_vert_1_ok = True
        except:
            pass

        y_vert = [np.nanmin(y_val), np.nanmax(y_val)]

        if x_vert_1_ok:
            x_vert_1 = [x_vert_1, x_vert_1]
            self.ver_curve_left = self.graphView.plot(
                x_vert_1,
                y_vert,
                pen={
                    "color": self.contrast_colors[7],
                    "width": 1,
                    "antialias": True,
                    "symbol": "o",
                },
            )

        if x_vert_2_ok:
            x_vert_2 = [x_vert_2, x_vert_2]

            self.ver_curve_right = self.graphView.plot(
                x_vert_2,
                y_vert,
                pen={
                    "color": self.contrast_colors[9],
                    "width": 1,
                    "antialias": True,
                    "symbol": "o",
                },
            )

        self.list_vert_curve = [self.ver_curve_right, self.ver_curve_left]

    def hyst_loop_activate(self):
        if self.build_hyst_loop_check.isChecked() == True:
            self.hyst_loop_layer.setVisible(True)
            self.graphView_loop.setVisible(True)
        else:
            self.hyst_loop_layer.setVisible(False)
            self.graphView_loop.setVisible(False)

    def draw_loop(self):
        if self.is_all_hyst_correct() == True:
            device = self.choice_device.currentText()
            ch_field = self.field_ch_choice.currentText()
            ch_sig = self.sig_ch_choice.currentText()
            number_field = int(self.channels_wave_choice[ch_field].currentText()) - 1
            status = True

            
            key_wave_field = None
            for key in self.dict_param[device][ch_field].keys():
                if "wavech" in key:
                    key_wave_field = key
                    break

            key_wave_sig = None
            for key in self.dict_param[device][ch_sig].keys():
                if "wavech" in key:
                    key_wave_sig = key
                    break

            field_arr = self.dict_param[device][ch_field][key_wave_field][number_field]
            sig_arr = self.dict_param[device][ch_sig][key_wave_sig][number_field]
            sig_scale = self.dict_param[device][ch_sig]["scale"][number_field]
            field_scale = self.dict_param[device][ch_field]["scale"][number_field]
            

            if status:
                if field_scale != sig_scale:
                    status = False

            if status:
                try:
                    x_vert_2 = float(self.right_coord.line_edit.text())
                    x_vert_1 = float(self.left_coord.line_edit.text())
                except:
                    status = False

            if status:
                left_ind = int(x_vert_1 / sig_scale)
                right_ind = int(x_vert_2 / sig_scale)
                
                new_loop = hystLoop(raw_x = sig_arr[left_ind:right_ind],
                                    raw_y =  field_arr[left_ind:right_ind],
                                    resistance = float( self.resistance.text() ),
                                    wire_square = float( self.square.text()) )
                x, y = new_loop.get_loop()

                self.loops_stack.append(new_loop)

                new_loop.plot_obj = self.graphView_loop.plot(
                    x,
                    y,
                    pen={
                        "color": next(self.color_gen),
                        "width": 1,
                        "antialias": True,
                        "symbol": "o",
                    },
                )
            else:
                logger.warning("неверные данные для построения петли")
        else:
            pass

    def get_random_color(self):
        while True:
            print(f"{len(self.used_colors)=} {len(self.contrast_colors)=}")

            my_used_colors = set(self.used_colors)
            my_colors = set(self.contrast_colors)
            missing = my_colors - my_used_colors

            if len(missing) == 0:
                # Сбросить использованные цвета
                print("reset used colors")
                self.used_colors.clear()
                color = random.choice(self.contrast_colors)
            else:
                color = random.choice(list(missing))


            self.used_colors.add(color)
            yield color

    def retranslateUI(self, GraphWindow):
        _translate = QApplication.translate
        self.build_hyst_loop_check.setText(_translate("GraphWindow", "Построение петель гистерезиса") )
        self.label.setText(_translate("GraphWindow", "Отображаемый канал") )
        self.label2.setText(_translate("GraphWindow", "Номер осциллограммы") )
        self.button_hyst_loop_clear.setText(_translate("GraphWindow", "Очистить петли") )
        self.button_hyst_loop_clear_last.setText(_translate("GraphWindow", "Очистить последнюю") )
        self.button_hyst_loop.setText(_translate("GraphWindow", "Построить петлю") )
        self.resistance.setPlaceholderText(_translate("GraphWindow", "Сопротивление провода(Ом)") )
        self.square.setPlaceholderText(_translate("GraphWindow", "Площадь провода(мкм)") )
        self.right_coord.line_edit.setPlaceholderText(_translate("GraphWindow", "Координата справа") )
        self.left_coord.line_edit.setPlaceholderText(_translate("GraphWindow", "Координата слева") )
        self.auto_button.setText(_translate("GraphWindow", "Авто") )
        self.name_sig.setText(_translate("GraphWindow", "Сигнал") )
        self.name_field.setText(_translate("GraphWindow", "Поле") )
        self.import_data_button.setText(_translate("GraphWindow", "Импортировать...") )
        

class verticals_lines:

    def __init__(self) -> None:
        self.is_data_setted = False
        self.ind_intervals = 0
        self.interval_values = None
        self.max_y_val = None
        self.min_y_val = None

    def set_data(self, max_y_val, min_y_val, interval_values: list):
        if len(interval_values) > 1:
            self.max_y_val = max_y_val
            self.min_y_val = min_y_val
            self.interval_values = interval_values
            self.ind_intervals = 0
            self.is_data_setted = True
            return True
        else:
            return False

    def get_next_data(self) -> list:
        status = True
        if len(self.interval_values) > 2:
            x_vert_1 = self.interval_values[self.ind_intervals]
            x_vert_2 = self.interval_values[self.ind_intervals + 2]
        elif len(self.interval_values) == 2:
            x_vert_1 = self.interval_values[self.ind_intervals]
            x_vert_2 = self.interval_values[self.ind_intervals + 1]
        elif len(self.interval_values) == 1:
            x_vert_1 = self.interval_values[self.ind_intervals]
            x_vert_2 = x_vert_1
        else:
            status = False

        self.ind_intervals += 1
        if self.ind_intervals + 2 >= len(self.interval_values):
            self.ind_intervals = 0

        return status, x_vert_1, x_vert_2

    def reset_data(self):
        self.is_data_setted = False
        self.ind_intervals = 0
        self.interval_values = None
        self.max_y_val = None
        self.min_y_val = None


class wheelLineEdit(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.line_edit = QLineEdit()
        self.layout.addWidget(self.line_edit)
        self.setLayout(self.layout)
        self.second_line = None

    def wheelEvent(self, event):
        try:
            current_value = float(self.line_edit.text())
            current_sec_value = float(self.second_line.text())
            delta = event.angleDelta().y()

            step = np.abs((current_value - current_sec_value) * 0.01)
            if delta > 0:
                current_value += step
            else:
                current_value -= step

            self.line_edit.setText(str(current_value))
            event.accept()
        except:
            pass

    def set_second_line_widget(self, line):
        """метод принимает ссылку на парный виджет, чтобы иметь возвможность работать в паре, например,
        изменять значение числа в зависимости от разницы текущего числа и числво во втором виджете
        """
        self.second_line = line


class hystLoop:
    '''хранит данные о петле и ее исходных параметрах, содержит методы расчета петли'''
    def __init__(self, raw_x, raw_y, resistance, wire_square) -> None:
        #исходные данные для петли
        self.raw_data_x = raw_x
        self.raw_data_y = raw_y
        #отфильтрованные данные петли
        self.filtered_raw_data_x = raw_x
        self.filtered_raw_data_y = raw_y
        #объект визуального представления петли и его данные
        self.plot_obj = None
        self.data_x = None
        self.data_y = None
        self.Q2 = 1.67  # сильно влияет на форму петли. уточнить влияние, для чего она введена?
        
        self.resistance = resistance
        self.wire_square = wire_square
        
    def get_loop(self):
        if self.data_x is None or self.data_y is None:
             self.data_x, self.data_y = self.calc_loop()
             
        return self.data_x, self.data_y
        
    def calc_loop(self):
        arr1 = self.filtered_raw_data_x
        arr2 = self.filtered_raw_data_y

        data_dict = {}
        arr1 = np.array(arr1)
        arr2 = np.array(arr2)
        data_dict["CH1"] = arr1
        data_dict["CH2"] = arr2
        window_size = 50
        # weights = np.ones(window_size) / window_size
        # data_dict['CH2_mean'] = np.convolve(data_dict['CH2'], weights, mode='same')

        R = 100 + self.resistance
        # d = 14.2
        d = self.wire_square / 2 * (10 ** (-6))
        A = R * (3.1415 * 2 * d * 2)
        C = 16
        X = data_dict["CH2"] / A + C
        Y = self.calculate_results(data_dict["CH1"])

        size1 = len(X)
        size2 = len(Y)

        if size1 > size2:

            X = X[:size2]
        elif size2 > size1:
            Y = Y[:size1]


        return X, Y

    def calculate_results(self, C):

        noise_level1 = self.threshold_mean_std(C)
        noise_level2 = self.threshold_median(C)
        noise_level = noise_level2

        n = len(C)

        # Вычисление средних значений и сдвигов
        D2 = np.mean(C)
        E2 = C - D2
        F2 = np.where(np.abs(E2) > noise_level, 1, 0)

        G2 = E2 * F2
        H2 = np.mean(G2)

        # Интегрирование
        I2 = G2 - H2
        J2 = np.cumsum(I2)  # Кусковая сумма
        K2 = J2 - np.max(J2) / 2
        L2 = K2 + self.Q2

        # Нормировка
        M = np.where(L2 <= 0, L2 / np.nanmin(L2), L2 / -np.nanmax(L2))

        return M

    def threshold_mean_std(self, data):
        """Вычисляет порог на основе среднего значения и стандартного отклонения."""
        mean = np.mean(data)
        std_dev = np.std(data)
        k = 2  # Можно настроить коэффициент
        threshold = mean + k * std_dev
        return threshold

    def threshold_median(self, data):
        """Вычисляет порог на основе медианы и интерквартильного размаха."""
        Q1 = np.percentile(data, 40)
        Q3 = np.percentile(data, 60)
        IQR = Q3 - Q1
        threshold = Q3 + 1.5 * IQR  # Порог устанавливается на уровне Q3 + 1.5 * IQR
        return threshold
    