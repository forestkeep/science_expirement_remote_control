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

logger = logging.getLogger(__name__)

from Devices.interfase.base_set_window import base_settings_window


class setWinOscilloscope(base_settings_window):
    def __init__(self) -> None:
        super().__init__()
        self.setGeometry(300, 50, 500, 950)

    def setupUi(self, num_channels):
        """Удалить ненужные слои с помощью функций
        self.remove_act()
        self.remove_meas()

        добавить свои виджжеты в слои
        self.Layout_set_dev_meas
        self.Layout_set_dev_act
        """
        self.remove_act()
        # self.remove_meas()
        self.num_channels = num_channels

        self.resize(num_channels*270, 800)

        self.com_boxes = []
        self.vert_scale_boxes = []
        self.enter_scale = QtWidgets.QSlider()
        # self.enter_scale.setOrientation(Qt.Horizontal)
        self.enter_scale.setRange(1, 100)  # Устанавливаем диапазон

        self.Layout_set_dev_meas.addLayout(
            self.create_channel_activation_section(num_channels=num_channels),
            0,
            0,
            1,
            1,
        )
        self.Layout_set_dev_meas.addLayout(
            self.create_channel_settings(num_channels=num_channels), 10, 0, 1, 1
        )
        self.Layout_set_dev_meas.addLayout(
            self.create_raw_data_layer(num_channels=num_channels), 20, 0, 1, 1
        )
        self.Layout_set_dev_meas.addLayout(
            self.create_meas_check_section(), 30, 0, 4, 4
        )
        self.Layout_set_dev_meas.addLayout(
            self.create_set_time_scale_Layout(), 40, 0, 1, 1
        )
        self.Layout_set_dev_meas.addLayout(self.create_trigger_menu(), 50, 0, 1, 1)

        for i in range(len(self.checkboxes_ch)):
            self.change_state_active(self.checkboxes_ch[i], i + 1)

        #self.set_minimum_size_for_all_widgets(min_width=10, min_height=10)

        self.retranslateUi(self)

    def getWidgets(self):
        widgets = self.findChildren(QtWidgets.QWidget)
        widget_names = [widget for widget in widgets]
        return widget_names

    def retranslateUi(self, Set_window):
        _translate = QtCore.QCoreApplication.translate
        Set_window.setWindowTitle(
            _translate("Device", "настройка осциллографа")
        )
        self.title_auto_meas.setText(
            _translate("Device", "Auto Measurement") )
        self.title_act_channels.setText(
            _translate("Device","Активировать каналы:") )
        self.title_trig_menu.setText(
            _translate("Device","Меню триггера") )
        for i in range(1, self.num_channels + 1):
            self.check_save_csv[i].setText(
            _translate("Device", "загрузить csv") + f" Ch-{i}")

        self.label_time_scale = QtWidgets.QLabel("Временная развертка:")

    def create_meas_check_section(self):
        # ==========Measurement elements==================
        self.title_auto_meas = QtWidgets.QLabel()
        self.title_auto_meas.setAlignment(QtCore.Qt.AlignCenter)

        meas_main_layout = QtWidgets.QVBoxLayout()
        meas_main_layout.addWidget(self.title_auto_meas)

        # Сетка для чекбоксов (4 в строку)
        grid_layout = QtWidgets.QGridLayout()

        # Объявление чекбоксов
        self.check_VMAX = QtWidgets.QCheckBox("VMAX")
        self.check_VMIN = QtWidgets.QCheckBox("VMIN")
        self.check_VPP = QtWidgets.QCheckBox("VPP")
        self.check_VTOP = QtWidgets.QCheckBox("VTOP")
        self.check_VBASE = QtWidgets.QCheckBox("VBASE")
        self.check_VAMP = QtWidgets.QCheckBox("VAMP")
        self.check_VAVG = QtWidgets.QCheckBox("VAVG")
        self.check_VRMS = QtWidgets.QCheckBox("VRMS")
        self.check_OVERshoot = QtWidgets.QCheckBox("OVERshoot")
        self.check_MAREA = QtWidgets.QCheckBox("MAREA")
        self.check_MPAREA = QtWidgets.QCheckBox("MPAREA")
        self.check_PREShoot = QtWidgets.QCheckBox("PREShoot")
        self.check_PERIOD = QtWidgets.QCheckBox("PERIOD")
        self.check_FREQUENCY = QtWidgets.QCheckBox("FREQUENCY")
        self.check_RTIME = QtWidgets.QCheckBox("RTIME")
        self.check_FTIME = QtWidgets.QCheckBox("FTIME")
        self.check_PWIDth = QtWidgets.QCheckBox("PWIDth")
        self.check_NWIDth = QtWidgets.QCheckBox("NWIDth")
        self.check_PDUTy = QtWidgets.QCheckBox("PDUTy")
        self.check_NDUTy = QtWidgets.QCheckBox("NDUTy")
        self.check_TVMAX = QtWidgets.QCheckBox("TVMAX")
        self.check_TVMIN = QtWidgets.QCheckBox("TVMIN")
        self.check_PSLEWrate = QtWidgets.QCheckBox("PSLEWrate")
        self.check_NSLEWrate = QtWidgets.QCheckBox("NSLEWrate")
        self.check_VUPPER = QtWidgets.QCheckBox("VUPPER")
        self.check_VMID = QtWidgets.QCheckBox("VMID")
        self.check_VLOWER = QtWidgets.QCheckBox("VLOWER")
        self.check_VARIance = QtWidgets.QCheckBox("VARIance")
        self.check_PVRMS = QtWidgets.QCheckBox("PVRMS")
        self.check_PPULses = QtWidgets.QCheckBox("PPULses")
        self.check_NPULses = QtWidgets.QCheckBox("NPULses")
        self.check_PEDGes = QtWidgets.QCheckBox("PEDGes")
        self.check_NEDGes = QtWidgets.QCheckBox("NEDGes")

        # Список чекбоксов для добавления в сетку
        checkboxes = [
            self.check_VMAX,
            self.check_VMIN,
            self.check_VPP,
            self.check_VTOP,
            self.check_VBASE,
            self.check_VAMP,
            self.check_VAVG,
            self.check_VRMS,
            self.check_OVERshoot,
            self.check_MAREA,
            self.check_MPAREA,
            self.check_PREShoot,
            self.check_PERIOD,
            self.check_FREQUENCY,
            self.check_RTIME,
            self.check_FTIME,
            self.check_PWIDth,
            self.check_NWIDth,
            self.check_PDUTy,
            self.check_NDUTy,
            self.check_TVMAX,
            self.check_TVMIN,
            self.check_PSLEWrate,
            self.check_NSLEWrate,
            self.check_VUPPER,
            self.check_VMID,
            self.check_VLOWER,
            self.check_VARIance,
            self.check_PVRMS,
            self.check_PPULses,
            self.check_NPULses,
            self.check_PEDGes,
            self.check_NEDGes,
        ]

        # Добавляем чекбоксы в сетку
        for index, check_box in enumerate(checkboxes):
            grid_layout.addWidget(check_box, index // 4, index % 4)
            check_box.setMinimumSize(10, 15)

        # Добавляем сетку чекбоксов в главный лэйаут
        meas_main_layout.addLayout(grid_layout)
        return meas_main_layout

    def create_channel_activation_section(self, num_channels):
        # Создание вертикального слоя
        layout = QtWidgets.QVBoxLayout()

        # Заголовок
        self.title_act_channels = QtWidgets.QLabel()
        self.title_act_channels.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.title_act_channels)

        # Создание горизонтального слоя (для чекбоксов)
        horizontal_layout = QtWidgets.QHBoxLayout()

        # Чекбоксы в зависимости от количества каналов
        self.checkboxes_ch = []
        for i in range(1, num_channels + 1):
            checkbox = QtWidgets.QCheckBox(f"Ch-{i}")
            checkbox.setLayoutDirection(QtCore.Qt.RightToLeft)

            checkbox.stateChanged.connect(
                lambda checked, ch=i, cb=checkbox: self.change_state_active(cb, ch)
            )
            checkbox.stateChanged.connect(lambda: self.change_trigger_sourse_list())

            self.checkboxes_ch.append(checkbox)
            horizontal_layout.addWidget(checkbox)

        # Добавление горизонтального слоя с чекбоксами в вертикальный слой
        layout.addLayout(horizontal_layout)

        return layout

    def create_trigger_menu(self):
        # Создание вертикального слоя
        layout = QtWidgets.QVBoxLayout()

        # Заголовок
        self.title_trig_menu = QtWidgets.QLabel()
        self.title_trig_menu.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.title_trig_menu)

        # Список названий для QComboBox
        labels = ["Sourse", "Type", "Slope", "Sweep", "Level"]

        # Проход по названиям с добавлением QLabel и QComboBox
        self.trig_box = {}
        for label in labels:
            h_layout = QtWidgets.QHBoxLayout()

            label_widget = QtWidgets.QLabel(label)
            combo_box = QtWidgets.QComboBox()
            combo_box.setMinimumSize(50, 10)
            self.trig_box[label] = combo_box
            if label == "Level":
                combo_box2 = QtWidgets.QComboBox()
                self.trig_box["Level_factor"] = combo_box2
                h_layout.addWidget(label_widget)
                h_layout.addWidget(combo_box)
                h_layout.addWidget(combo_box2)
            else:
                h_layout.addWidget(label_widget)
                h_layout.addWidget(combo_box)
            layout.addLayout(h_layout)

        self.trig_box["Sourse"].addItems(["Hand control"])
        self.trig_box["Type"].addItems(["EDGE", "Hand control"])
        self.trig_box["Slope"].addItems(
            ["POSitive", "NEGative", "RFALl", "Hand control"]
        )
        self.trig_box["Sweep"].addItems(["AUTO", "NORMal", "SINGle", "Hand control"])
        self.trig_box["Level"].addItems(["Hand control"])
        self.trig_box["Level"].setEditable(True)
        self.trig_box["Level_factor"].addItems(["mv", "v", "Hand control"])

        return layout

    def create_channel_settings(self, num_channels):
        # Создание вертикального слоя
        layout = QtWidgets.QVBoxLayout()

        horizontal_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(horizontal_layout)
        for i in range(1, num_channels + 1):
            horizontal_layout.addLayout(self.create_channel_layer(i))

        return layout
    

    def set_minimum_size_for_all_widgets(self, min_width=100, min_height=30):
        widgets = self.findChildren(QtWidgets.QWidget)  # Получаем все дочерние виджеты
        for widget in widgets:
            print(widget)
            widget.setMinimumSize(min_width, min_height)  # Устанавливаем минимальный размер

    def create_channel_layer(self, channel_number):

        # Создание вертикального слоя
        layout = QtWidgets.QVBoxLayout()

        # Имена для QLabel
        labels = ["Coupling", "BW_Limit", "Probe", "Invert"]
        combo_boxes = {}

        # Создание строк с QLabel и QComboBox
        for label in labels:
            h_layout = QtWidgets.QHBoxLayout()

            label_widget = QtWidgets.QLabel(label)
            combo_box = QtWidgets.QComboBox()
            combo_boxes[label] = combo_box

            h_layout.addWidget(label_widget)
            h_layout.addWidget(combo_box)
            layout.addLayout(h_layout)

        layout.addLayout(self.create_set_vert_scale_Layout())

        combo_boxes["BW_Limit"].addItems(["20M", "OFF", "Hand control"])
        combo_boxes["Coupling"].addItems(["AC", "DC", "GND", "Hand control"])
        combo_boxes["Probe"].addItems(
            [
                "0.01",
                "0.02",
                "0.05",
                "0.1",
                "0.2",
                "0.5",
                "1",
                "2",
                "5",
                "10",
                "20",
                "50",
                "100",
                "200",
                "500",
                "1000",
                "Hand control",
            ]
        )
        combo_boxes["Invert"].addItems(["ON", "OFF", "Hand control"])

        self.com_boxes.append(combo_boxes)

        return layout

    def create_raw_data_layer(self, num_channels):
        layer = QtWidgets.QVBoxLayout()
        H_layer = QtWidgets.QHBoxLayout()

        # Чекбоксы в зависимости от количества каналов
        self.check_save_csv = []
        for i in range(1, num_channels + 1):
            checkbox = QtWidgets.QCheckBox()
            checkbox.setLayoutDirection(QtCore.Qt.RightToLeft)
            self.check_save_csv.append(checkbox)
            H_layer.addWidget(checkbox)

        layer.addLayout(H_layer)

        return layer

    def create_set_vert_scale_Layout(self):
        layout = QtWidgets.QHBoxLayout()

        label1 = QtWidgets.QLabel("Vscale")

        enter_vscale_number = QtWidgets.QComboBox()
        enter_vscale_number.addItems(
            ["1", "2", "5", "10", "20", "50", "100", "200", "500", "Hand control"]
        )

        enter_vscale_factor = QtWidgets.QComboBox()
        enter_vscale_factor.addItems(["mv", "v", "kv", "Hand control"])

        # Добавляем все элементы в горизонтальный слой
        layout.addWidget(label1)
        layout.addWidget(enter_vscale_number)
        layout.addWidget(enter_vscale_factor)
        self.vert_scale_boxes.append([enter_vscale_number, enter_vscale_factor])
        return layout

    def create_set_time_scale_Layout(self):
        layout = QtWidgets.QHBoxLayout()

        self.label_time_scale = QtWidgets.QLabel()

        self.enter_scale_number = QtWidgets.QComboBox()
        self.enter_scale_number.addItems(
            ["1", "2", "5", "10", "20", "50", "100", "200", "500", "Hand control"]
        )

        self.enter_scale_factor = QtWidgets.QComboBox()
        self.enter_scale_factor.addItems(["ns", "us", "ms", "s", "Hand control"])

        # Добавляем все элементы в горизонтальный слой
        layout.addWidget(self.label_time_scale)
        layout.addWidget(self.enter_scale_number)
        layout.addWidget(self.enter_scale_factor)
        return layout

    def change_state_active(self, check_obj, number_ch):

        if check_obj.isChecked() == True:
            self.check_save_csv[number_ch - 1].setEnabled(True)
            self.vert_scale_boxes[number_ch - 1][0].setEnabled(True)
            self.vert_scale_boxes[number_ch - 1][1].setEnabled(True)
            self.com_boxes[number_ch - 1]["Coupling"].setEnabled(True)
            self.com_boxes[number_ch - 1]["BW_Limit"].setEnabled(True)
            self.com_boxes[number_ch - 1]["Probe"].setEnabled(True)
            self.com_boxes[number_ch - 1]["Invert"].setEnabled(True)
        else:
            self.check_save_csv[number_ch - 1].setEnabled(False)
            self.vert_scale_boxes[number_ch - 1][0].setEnabled(False)
            self.vert_scale_boxes[number_ch - 1][1].setEnabled(False)
            self.com_boxes[number_ch - 1]["Coupling"].setEnabled(False)
            self.com_boxes[number_ch - 1]["BW_Limit"].setEnabled(False)
            self.com_boxes[number_ch - 1]["Probe"].setEnabled(False)
            self.com_boxes[number_ch - 1]["Invert"].setEnabled(False)

    def change_trigger_sourse_list(self):
        new_list = ["Hand control"]
        for i in range(len(self.checkboxes_ch)):
            if self.checkboxes_ch[i].isChecked() == True:
                new_list.append(f"Ch-{i+1}")

        old_val = self.trig_box["Sourse"].currentText()
        self.trig_box["Sourse"].clear()
        self.trig_box["Sourse"].addItems(new_list)
        if old_val in new_list:
            self.trig_box["Sourse"].setCurrentText(old_val)


if __name__ == "__main__":
    import sys

    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = setWinOscilloscope()
    a.setupUi(num_channels=2)
    # print(a.getWidgets())
    a.show()
    sys.exit(app.exec_())


"""
1 Frequency The reciprocal of the period.
2 Period The time between two consecutive threshold points of the same polarity edge.
3 Average The arithmetic mean of the entire waveform or selected area.
4 Pk-Pk The voltage value from the peak to the lowest point of the waveform.
5 RMS
That is a valid value. According to the energy converted by the AC signal in one cycle, the DC
voltage corresponding to the equivalent energy is the root mean square value.
6 Period Rms The root mean square value of the signal within 1 cycle.
7 Min The most negative peak voltage measured over the entire waveform.
8 Max The most positive peak voltage measured over the entire waveform.
9 RiseTime Measure the time between 10% and 90% of the first rising edge of the waveform.
10 FallTime Measure the time between 90% and 10% of the first falling edge of the waveform.
11 + Width
Measure the time between the first rising edge and the next falling edge at the waveform 50%
level.
12 - Width
Measure the time between the first falling edge and the next rising edge at the waveform 50%
level.
13 + Duty
Measure the first cycle waveform. Positive Duty Cycle is the ratio between positive pulse width
and period.
14 - Duty
Measure the first cycle waveform. Negative Duty Cycle is the ratio between positive pulse width
and period.
15 Vbase Measure the highest voltage over the entire waveform.
16 Vtop Measure the lowest voltage over the entire waveform.
17 Vmid Measure the voltage of the 50% level from base to top.
18 Vamp Voltage between Vtop and Vbase of a waveform.
19 Overshoot Defined as (Base - Min)/Amp x 100 %, Measured over the entire waveform.
20 Preshoot Defined as (Max - Top)/Amp x 100 %, Measured over the entire waveform.
21 PeriodAvg Calculate the arithmetic mean voltage over the first cycle in the waveform.
22 FOVShoot Defined as (Vmin-Vlow)/Vamp after the waveform falling.
23 RPREShoot Defined as (Vmin-Vlow)/Vamp before the waveform falling.
24 BWidth The duration of a burst measured over the entire waveform
25 FRR
The time between the first rising edge of source 1 and the first rising edge of source 2 of 50
voltage level.
26 FFF
The time between the first falling edge of source 1 and the first falling edge of source 2 of 50
voltage level.
27 FRF The time between the first rising edge of source 1 and the first falling edge of source 2.
28 FFR The time between the first falling edge of source 1 and the first rising edge of source 2.
29 LRR The time between the first rising edge of source 1 and the last rising edge of source 2.
30 LRF The time between the first rising edge of source 1 and the last falling edge of source 2.
31 LFR The time between the first falling edge of source 1 and the last rising edge of source 2.
32 LFF The time between the first falling edge of source 1 and the last falling edge of source 2.



"""
