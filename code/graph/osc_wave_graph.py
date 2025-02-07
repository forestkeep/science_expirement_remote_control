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
import logging
import time

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                             QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QSizePolicy,
                             QSplitter, QVBoxLayout, QWidget)

try:
    from colors import GColors
    from curve_data import hystLoop, oscData
    from Link_data_import_win import Check_data_import_win
    from Message_graph import messageDialog
except:
    from graph.colors import GColors
    from graph.curve_data import hystLoop, oscData
    from graph.Link_data_import_win import Check_data_import_win
    from graph.Message_graph import messageDialog

logger = logging.getLogger(__name__)

def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result
    return wrapper

class graphOsc:
    def __init__(self, tablet_page, main_class):
        self.page = tablet_page
        self.legend = pg.LegendItem(size=(80, 60), offset=(10, 10))
        self.is_show_warning = True
        self.key_to_update_plot = True
        self.x = []
        self.y = []
        self.dict_param = {}

        self.stack_osc = {}

        self.main_class = main_class

        self.used_colors = set()
        self.colors_class = GColors()
        self.color_gen = self.colors_class.get_random_color()

        self.y_main_axis_label = ""
        self.x_axis_label = ""

        self.y_second_axis_label = "V"
        self.x_axis_label = "dots"
        self.y_main_axis_label = "V"

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

        self.label = QLabel() 
        self.label2 = QLabel() 

        self.list_vert_curve = []
        self.initUI()

    def update_dict_param(self, new: dict, is_exp_stop = False):
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

        if self.main_class.experiment_controller is not None:
            if self.main_class.experiment_controller.is_experiment_running():
                self.main_class.show_tooltip( QApplication.translate("GraphWindow","Дождитесь окончания эксперимента"), timeout=3000)
                return
        
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

                df = df.dropna(axis=1, how='all')

                window = Check_data_import_win([col for col in df.columns], self.update_dict_param)
                ans = window.exec_()
                if ans == QDialog.Accepted: 
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

                    text = QApplication.translate("GraphWindow","В столбцах {res} обнаружены данные,\n которые не получается преобразовать в числа.\n При построение эти точки будут пропущены.")
                    text = text.format(res = res)
                    self.main_class.show_tooltip( text, timeout=4000)

                selected_channels.pop()

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
                df = df[[col for col in df.columns if col in selected_channels]]
                for col in selected_channels:
                    df[col] = (pd.to_numeric(df[col], errors='coerce'))
                df = df.dropna()
                for col in selected_channels:
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
        self.choice_device.addItems([""])

        self.choice_device.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.choice_device.setMaximumSize(150, 20)

        self.choice_device.currentTextChanged.connect(lambda: self.new_dev_checked())
        self.choice_device.currentIndexChanged.connect(lambda: self.new_dev_checked())

        self.hor_lay.addWidget(self.choice_device)

        self.graphView = self.setupGraphView()

        self.graphView.scene().sigMouseMoved.connect(self.showToolTip_main)
        self.graphView.scene().sigMouseClicked.connect(self.click_scene_main_graph)
        self.graphView.scene().setClickRadius(20)
        self.legend.setParentItem(self.graphView.plotItem)


        self.graphView.setLabel("left", self.y_main_axis_label, color="#ffffff")
        self.graphView.setLabel("bottom", self.x_axis_label, color="#ffffff")
        self.graphView.getAxis("left").setGrid(True)
        self.graphView.getAxis("bottom").setGrid(True)

        self.import_data_button = QPushButton(
            QApplication.translate('graph_win',"Импорт данных")
        )

        self.import_data_button.setMaximumSize(150, 30)
        self.import_data_button.clicked.connect(self.import_data)

        self.tab1Layout.addLayout(self.hor_lay)
        self.tab1Layout.addWidget(self.build_hyst_loop_check)
        self.tab1Layout.addWidget(self.import_data_button)

        splitter = QSplitter()
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        splitter.setOrientation(1)

        self.graphView_loop = self.setupGraphView()

        self.graphView_loop.scene().sigMouseMoved.connect(self.showToolTip_loop)
        self.graphView_loop.scene().sigMouseClicked.connect(self.click_scene_loop_graph)

        splitter.addWidget(self.graphView)
        splitter.addWidget(self.graphView_loop)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)  
        self.tab1Layout.addWidget(splitter)
        self.graphView_loop.hide()

        self.hyst_loop_layer = self.create_hyst_calc_layer()
        self.hyst_loop_layer.hide()
        self.tab1Layout.addWidget(self.hyst_loop_layer)
        self.page.setLayout(self.tab1Layout)

        self.page.subscribe_to_key_press(key = Qt.Key_Delete, callback = self.delete_key_press)

        self.page.subscribe_to_key_press(key = Qt.Key_Escape, callback = self.reset_filters)

        '''
        Escape: Qt.Key_Escape
        Space: Qt.Key_Space
        Enter: Qt.Key_Return или Qt.Key_Enter
        Control: Qt.Key_Control
        Shift: Qt.Key_Shift
        Minus: Qt.Key_Minus
        Plus: Qt.Key_Plus
        '''
        self.retranslateUI(self.page)

    def click_scene_main_graph(self, event):
        #print(len(self.graphView.scene().itemsNearEvent(event)))
        self.__callback_click_scene(self.stack_osc.values())

    def click_scene_loop_graph(self, event):
        #print(len(self.graphView.scene().itemsNearEvent(event)))
        self.__callback_click_scene(self.loops_stack)

    def __callback_click_scene(self, focus_objects: list):
        is_click_plot = True
        for graph in focus_objects:
            if graph.i_am_click_now:
                graph.i_am_click_now = False
                is_click_plot = False

        if is_click_plot:
            for graph in focus_objects:
                if graph.current_highlight:
                        graph.current_highlight = False
                        graph.plot_obj.setPen(graph.saved_pen)

    def reset_filters(self):
        for loop in self.loops_stack:
            if loop.current_highlight:
                loop.filtered_x_data = loop.raw_data_x
                loop.filtered_y_data = loop.raw_data_y
                x, y = loop.recalc_data()
                loop.plot_obj.setData(x, y)

        for osc in self.stack_osc.values():
            if osc.current_highlight:
                osc.filtered_x_data = osc.raw_data_x
                osc.filtered_y_data = osc.raw_data_y

                osc.plot_obj.setData(osc.filtered_x_data, osc.filtered_y_data)

        
    def delete_key_press(self):
        self.clear_highlight_loop()

    def setupGraphView(self):
        graphView = pg.PlotWidget(title="")

        graphView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        graphView.plotItem.getAxis("left").linkToView(graphView.plotItem.getViewBox())
        graphView.plotItem.getAxis("bottom").linkToView(graphView.plotItem.getViewBox())

        my_font = QFont("Times", 13)
        graphView.getAxis("bottom").label.setFont(my_font)
        graphView.getAxis("left").label.setFont(my_font)

        graphView.setMinimumSize(300, 200)

        return graphView

    def create_checkbox_layer(self, channels, waves_num):
        # waves_num = список, в элементах которого указано количество осциллограмм для соответствующего канала
        layout = QGridLayout()
        checkboxes = []
        channels_wave_forms = {}

        for index, name_ch in enumerate(channels):
            col = index // 4
            row = (
                index % 4 + 1
            )  # Строка для размещения чекбокса и комбобокса, смещение на 1 для лейблов

            if row == 1:  # Лейбл добавляется в первую строку
                lay = QHBoxLayout()
                self.label = QLabel()
                self.label2 = QLabel()
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
            )  
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

        self.name_field = QLabel(QApplication.translate("GraphWindow","Поле"))
        self.field_ch_choice = QComboBox()

        self.name_sig = QLabel(QApplication.translate("GraphWindow","Сигнал"))
        
        self.sig_ch_choice = QComboBox()

        self.sig_ch_choice.setMaximumSize(250, 40)
        self.field_ch_choice.setMaximumSize(250, 40)

        self.sig_ch_choice.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.field_ch_choice.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.auto_button = QPushButton(QApplication.translate("GraphWindow","Авто"))
        self.auto_button.setMaximumSize(130, 100)

        self.avg_loop_button = QPushButton(QApplication.translate("GraphWindow","Усреднить петли"))
        self.avg_loop_button.setMaximumSize(130, 100)
        
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

        self.avg_loop_button.clicked.connect(lambda: self.avg_loop())

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
        buttons_lay.addLayout(buttons3_lay)

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
        main_lay.addLayout(buttons_lay)

        return self.hyst_loop_layer
    
    def avg_loop(self):
        buf = []

        for loop in self.loops_stack:
            buf.append(loop)

        if len(self.loops_stack) > 1:

            new_loop = self.calc_avg_loop(loops_stack=buf)

            if new_loop is not False:
                #self.clear_all_loops()
                x, y = new_loop.get_xy_data()

                new_pen = {
                        "color": next(self.color_gen),
                        "width": 1,
                        "antialias": True,
                        "symbol": "o",
                        }

                self.loops_stack.append(new_loop)
                plot_obj = self.graphView_loop.plot(
                        x,
                        y,
                        pen=new_pen,

                        )
                new_loop.set_plot_obj(plot_obj, new_pen, highlight=True)

    def calc_avg_loop(self, loops_stack):
        '''вернет объект петли, полученный усреднением стека петель'''
        if len(loops_stack) == 0:
            return False
        elif len(loops_stack) == 1:
            return loops_stack[0]
        
        new_loop = loops_stack[0]
        for i in range(1, len(loops_stack)):
            new_loop = self.calc_avg_two_loops(new_loop, loops_stack[i])  
        
        return new_loop
    
    def average_arrays(self, arr1, arr2):

        len1, len2 = len(arr1), len(arr2)
        min_len = min(len1, len2)
        
        average_part = (arr1[:min_len] + arr2[:min_len]) / 2
        
        if len1 > len2:
            result = np.concatenate((average_part, arr1[min_len:]))
        elif len2 > len1:
            result = np.concatenate((average_part, arr2[min_len:]))
        else:
            result = average_part
        
        return result
            
    def calc_avg_two_loops(self, loop1, loop2):
        if loop1.time_scale != loop2.time_scale:
            print("невозможно вычислить среднее между петлями, временной шаг должен быть одинаковым")
            return False
        
        mean_resistance  = (loop1.resistance + loop2.resistance)/2
        mean_wire_square = (loop1.wire_square + loop2.wire_square)/2
        
        mean_sig = self.average_arrays(loop2.filtered_x_data,
                                       loop1.filtered_x_data)
        
        mean_field = self.average_arrays(loop2.filtered_y_data,
                                         loop1.filtered_y_data)
                               
        new_loop = hystLoop(raw_x        =mean_sig,
                            raw_y        =mean_field,
                            time_scale   =loop1.time_scale,
                            resistance   =mean_resistance,
                            wire_square  =mean_wire_square
                            )
        return new_loop
                     
    def clear_highlight_loop(self):
        if len(self.loops_stack) > 0:
            for index in range(len(self.loops_stack) - 1, -1, -1):
                loop = self.loops_stack[index]
                if loop.current_highlight:
                    self.graphView_loop.removeItem(loop.plot_obj)
                    del self.loops_stack[index]
        else:
            print("no loops")

    def clear_all_loops(self):
        if len(self.loops_stack) > 0:
            for loop in self.loops_stack:
                self.graphView_loop.removeItem(loop.plot_obj)
            self.loops_stack.clear()
        else:
            print("no loops")

    def update_num_waveforms(self):

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
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if (
                    widget and widget != widget_to_keep
                ):
                    layout.removeWidget(widget)
                    widget.deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout(), widget_to_keep)
                    layout.removeItem(item)
                    item.layout().deleteLater()

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

                device = self.choice_device.currentText()
                num_wave = (
                        int(self.channels_wave_choice[ch.text()].currentText()) - 1
                )

                key_stack = str(device) + str(ch_name) + str(num_wave)

                if ch.isChecked():
                    
                    if self.stack_osc.get(key_stack, None) == None:

                        for key in self.dict_param[device][ch_name].keys():
                            if "wavech" in key:
                                key_wave = key
                                break

                        self.y_values[ch_name] = self.dict_param[device][ch_name][key_wave][num_wave]
                        self.scales[ch_name] = self.dict_param[device][ch_name]["scale"][num_wave]
                        self.legend_ch_names[ch_name] = ch_name

                        scale = self.dict_param[device][ch_name]["scale"][num_wave]

                        #TODO:добавить десятичные приставки к подписям осей, вертикальной и горизонтальной

                        y = np.array(self.dict_param[device][ch_name][key_wave][num_wave])
                        x = np.array([scale*i for i in range(1, len(y)+1)])

                        new_osc = oscData( raw_x  = x, 
                                           raw_y  = y, 
                                           device = device, 
                                           ch     = ch_name, 
                                           name   = key_wave, 
                                           number = num_wave)
                        
                        self.stack_osc[key_stack] = new_osc

                    for key in self.stack_osc.keys():
                        if key != key_stack:
                            if str(device) + str(ch_name) in key:
                                self.stack_osc[key].is_draw = False
                                self.stack_osc[key].current_highlight = False

                    self.stack_osc[key_stack].is_draw = True                
            
                else:
                    self.y_values[ch_name] = []

                    if self.stack_osc.get(key_stack, None) != None:
                        self.stack_osc[key_stack].is_draw = False

                        self.stack_osc[key_stack].current_highlight = False

            self.update_draw()

    def set_default(self):
        """привести класс к исходному состоянию"""
        self.graphView.plotItem.clear()
        self.graphView_loop.plotItem.clear()
        self.choice_device.clear()
        self.choice_device.addItems([self.choice_device_default_text])

    def update_draw(self):

        self.legend.clear()
        #===================================================
        for obj in self.stack_osc.values():
            if obj.is_draw:
                if obj.plot_obj == None:

                    if obj.saved_pen == None:
                        buf_pen = {
                            "color": next(self.color_gen),
                            "width": 1,
                            "antialias": True,  
                            "symbol": "o",
                        }
                    else:
                        buf_pen = obj.saved_pen

                    graph = self.graphView.plot(obj.filtered_x_data, 
                                                obj.filtered_y_data, 
                                                pen  = buf_pen,
                                                name = obj.legend_name
                                                )

                    obj.set_plot_obj(plot_obj = graph,
                                    pen       = buf_pen)
                    
                legend_name = obj.legend_name
                self.legend.addItem(
                        obj.plot_obj, obj.legend_name
                )

            else:
                if obj.plot_obj != None:
                    self.graphView.removeItem(obj.plot_obj)
                    obj.plot_obj = None
                
    def showToolTip_main(self, event):
        pos = event

        #==============показываются кривые, когда курсор находится в квадрате графика, квадрат очерчен вокруг графика, 
        '''
        from pyqtgraph.graphicsItems.PlotCurveItem import PlotCurveItem
        items = self.graphView.scene().items(pos)  # Получаем все элементы под курсором
        plot_items = [item for item in items if isinstance(item, PlotCurveItem)]
        if plot_items:
            print("PlotItem под курсором:", plot_items)
        else:
            print("Нет PlotItem под курсором")
        '''
        #==================================================================

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
        pos = event  # Получаем позицию курсора

        x_val = round(
            self.graphView_loop.plotItem.vb.mapSceneToView(pos).x(), 5
        )
        y_val = round(
            self.graphView_loop.plotItem.vb.mapSceneToView(pos).y(), 5
        )
        text = f'<p style="font-size:{10}pt">X:{x_val} Y:{y_val}</p>'
        try:
            self.tooltip.setText(text)
        except:
            pass  # лейбл удален

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
                    "color": next(self.color_gen),
                    "width": 1,
                    "antialias": True,
                    "symbol": "o",
                }
            )

        if x_vert_2_ok:
            x_vert_2 = [x_vert_2, x_vert_2]

            self.ver_curve_right = self.graphView.plot(
                x_vert_2,
                y_vert,
                pen={
                    "color": next(self.color_gen),
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
                    print("time scale сигнала и поля должны быть равны")
                    
            if status:
                try:
                    x_vert_2 = float(self.right_coord.line_edit.text())
                    x_vert_1 = float(self.left_coord.line_edit.text())
                except:
                    status = False

            if status:
                left_ind = int(x_vert_1 / sig_scale)
                right_ind = int(x_vert_2 / sig_scale)
                
                raw_x = sig_arr[left_ind:right_ind]
                raw_y = field_arr[left_ind:right_ind]
                  
                if len(raw_y) > len(raw_x):
                    raw_y = raw_y[0: len(raw_x)]
                elif len(raw_y) < len(raw_x):
                    raw_x = raw_x[0: len(raw_y)]
                
                new_loop = hystLoop(raw_x = raw_x,
                                    raw_y =  raw_y,
                                    time_scale=field_scale,
                                    resistance = float( self.resistance.text() ),
                                    wire_square = float( self.square.text())
                                      )
                x, y = new_loop.get_xy_data()

                self.loops_stack.append(new_loop)

                new_pen = {
                        "color": next(self.color_gen),
                        "width": 1,
                        "antialias": True,
                        "symbol": "o",
                        }

                plot_obj = self.graphView_loop.plot(
                    x,
                    y,
                    pen=new_pen,
                )

                new_loop.set_plot_obj( plot_obj, new_pen )

            else:
                logger.warning("неверные данные для построения петли")
        else:
            pass

    def set_filters(self, filter_func):
        for loop in self.loops_stack:
            if loop.current_highlight:
                loop.filtered_x_data, _ = filter_func(loop.filtered_x_data)
                loop.filtered_y_data, _ = filter_func(loop.filtered_y_data)

                self.graphView_loop.removeItem(loop.plot_obj)

                x, y = loop.recalc_data()

                plot_obj = self.graphView_loop.plot(
                    x,
                    y,
                    pen=loop.saved_pen,
                )

                loop.set_plot_obj( plot_obj, loop.saved_pen)

        for osc in self.stack_osc.values():
            if osc.current_highlight:

                osc.filtered_y_data, _ = filter_func(osc.filtered_y_data)
                osc.filtered_x_data = osc.filtered_x_data[-len(osc.filtered_y_data):]

                osc.plot_obj.setData(osc.filtered_x_data, osc.filtered_y_data)

    def retranslateUI(self, GraphWindow):
        _translate = QApplication.translate
        self.build_hyst_loop_check.setText(_translate("GraphWindow", "Построение петель гистерезиса") )
        self.label.setText(_translate("GraphWindow", "Отображаемый канал") )
        self.label2.setText(_translate("GraphWindow", "Номер осциллограммы") )
        self.button_hyst_loop_clear.setText(_translate("GraphWindow", "Очистить все") )
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


    