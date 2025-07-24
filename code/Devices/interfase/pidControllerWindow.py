import logging

from PyQt5 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)

from Devices.interfase.base_set_window import base_settings_window

class UiSetPidController(base_settings_window):
    def __init__(self, add_id_select=False) -> None:
        super().__init__(add_id_select=add_id_select)

    def setupUi(self):

        # self.remove_act()
        # self.remove_meas()

        self.resize(800, 600)

        #прописываем конфигурацию интерфейса

        self.label_3 = QtWidgets.QLabel()
        self.label_3.setObjectName("label_3")

        self.radioButton = QtWidgets.QCheckBox()
        self.radioButton.setObjectName("radioButton")

        self.is_soft_start = QtWidgets.QCheckBox()
        self.is_soft_stop = QtWidgets.QCheckBox()

        self.label_4 = QtWidgets.QLabel()
        self.label_4.setObjectName("label_4")

        self.type_step_enter = QtWidgets.QComboBox()
        self.type_step_enter.setCurrentText("")
        self.type_step_enter.setObjectName("type_step_enter")

        self.label_6 = QtWidgets.QLabel()
        self.label_6.setObjectName("label_6")

        self.label_2 = QtWidgets.QLabel()
        self.label_2.setObjectName("label_2")

        self.label = QtWidgets.QLabel()
        self.label.setObjectName("label")

        self.start_enter = QtWidgets.QComboBox()
        self.start_enter.setEditable(True)
        self.start_enter.setCurrentText("")
        self.start_enter.setObjectName("start_enter")

        self.stop_enter = QtWidgets.QComboBox()
        self.stop_enter.setEditable(True)
        self.stop_enter.setCurrentText("")
        self.stop_enter.setObjectName("stop_enter")

        self.step_enter = QtWidgets.QComboBox()
        self.step_enter.setEditable(True)

        self.label_8 = QtWidgets.QLabel()
        self.label_7 = QtWidgets.QLabel()
        self.label_9 = QtWidgets.QLabel()
        self.label_10 = QtWidgets.QLabel()
        self.label_11 = QtWidgets.QLabel()

        self.acts_label = QtWidgets.QLabel()
        self.acts_label.setFont(self.font)

        self.temp_meas = QtWidgets.QCheckBox()
        self.set_temp_meas = QtWidgets.QCheckBox()
        self.power_percent = QtWidgets.QCheckBox()

        self.meas_label = QtWidgets.QLabel()
        self.meas_label.setFont(self.font)

        self.Layout_set_dev_act.addWidget(self.acts_label, 0, 0, 1, 1)

        self.Layout_set_dev_act.addWidget(self.label_4, 2, 0, 1, 1)
        self.Layout_set_dev_act.addWidget(self.type_step_enter, 2, 1, 1, 2)

        self.Layout_set_dev_act.addWidget(self.label, 3, 0, 1, 1)
        self.Layout_set_dev_act.addWidget(self.start_enter, 3, 1, 1, 2)

        self.Layout_set_dev_act.addWidget(self.label_2, 4, 0, 1, 1)
        self.Layout_set_dev_act.addWidget(self.stop_enter, 4, 1, 1, 2)

        self.Layout_set_dev_act.addWidget(self.label_6, 5, 0, 1, 1)
        self.Layout_set_dev_act.addWidget(self.step_enter, 5, 1, 1, 2)

        self.Layout_set_dev_act.addWidget(self.label_7, 3, 4, 1, 1)
        self.Layout_set_dev_act.addWidget(self.label_8, 4, 4, 1, 1)
        self.Layout_set_dev_act.addWidget(self.label_9, 5, 4, 1, 1)

        self.Layout_set_dev_act.addWidget(self.radioButton, 7, 1, 1, 1)

        self.Layout_set_dev_meas.addWidget(self.meas_label)
        self.Layout_set_dev_meas.addWidget(self.temp_meas, 1, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.set_temp_meas, 2, 0, 1, 1)
        self.Layout_set_dev_meas.addWidget(self.power_percent, 3, 0, 1, 1)

        self.retranslateUi(self)


    def retranslateUi(self, Set_power_supply):

        #здесь прописываем установки наименований всем виджетам
        _translate = QtCore.QCoreApplication.translate
        Set_power_supply.setWindowTitle(
            _translate("Set_pid_controller", "настройка пид регулятора")
        )
        self.label_3.setText(_translate("Set_pid_controller", "Триггер"))

        self.radioButton.setText(_translate("Set_pid_controller", "Пройти туда-обратно?"))

        self.label_4.setText(_translate("Set_pid_controller", "Тип шага"))
        self.label_6.setText(_translate("Set_pid_controller", "Шаг"))
        self.label_2.setText(_translate("Set_pid_controller", "Конечное значение"))
        self.label.setText(_translate("Set_pid_controller", "Начальное значение"))
        self.label_7.setText("С")
        self.label_8.setText("С")
        self.label_9.setText("С")

        self.meas_label.setText(_translate("Set_pid_controller", "Измерения"))
        self.temp_meas.setText(_translate("Set_pid_controller", "Текущая температура"))
        self.set_temp_meas.setText(_translate("Set_pid_controller", "Установка температуры"))
        self.power_percent.setText(_translate("Set_pid_controller", "% мощности"))

        self.acts_label.setText(_translate("Set_pid_controller", "Действия"))


if __name__ == "__main__":
    import sys

    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = UiSetPidController()
    a.setupUi()
    a.show()
    sys.exit(app.exec_())
