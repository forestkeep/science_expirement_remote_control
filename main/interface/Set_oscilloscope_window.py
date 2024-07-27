from PyQt5 import QtCore, QtGui, QtWidgets
import logging
logger = logging.getLogger(__name__)
if __name__ == "__main__":
    from base_set_window import base_settings_window
else:
    from interface.base_set_window import base_settings_window

class Ui_Set_immitans(base_settings_window):
    def __init__(self) -> None:
        super().__init__()

    def setupUi(self, window):
        '''Удалить ненужные слои с помощью функций
        self.remove_act()
        self.remove_meas()

        добавить свои виджжеты в слои
        self.Layout_set_dev_meas
        self.Layout_set_dev_act 
        '''

        self.remove_act()
        #self.remove_meas()

        self.level_trigger_label = QtWidgets.QLabel("Уровень захвата триггера")
        self.level_trigger_enter = QtWidgets.QComboBox()

        self.check_parameters = QtWidgets.QCheckBox('Загрузка измеренных параметров')
        self.check_csv = QtWidgets.QCheckBox('Загрузка CSV')


        self.Layout_set_dev_meas.addWidget(self.settings_dev, 0, 0, 1, 3)

        self.Layout_set_dev_meas.addWidget(self.level_trigger_label, 1, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.level_trigger_enter, 1, 1, 1, 2)
        self.Layout_set_dev_meas.addWidget(self.check_parameters, 5, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.check_csv, 6, 0, 1, 1)

        self.retranslateUi(self)

    def getWidgets(self):
            widgets = self.findChildren(QtWidgets.QWidget)
            widget_names = [widget for widget in widgets]
            return widget_names

    def retranslateUi(self, Set_window):
        _translate = QtCore.QCoreApplication.translate
        Set_window.setWindowTitle(
            _translate("Set_power_supply", "настройка осциллографа"))



if __name__ == "__main__":
    import qdarktheme
    import sys
    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = Ui_Set_immitans()
    a.setupUi(a)
    #print(a.getWidgets())
    a.show()
    sys.exit(app.exec_())




'''
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



'''