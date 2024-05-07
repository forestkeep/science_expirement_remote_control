from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Set_immitans(QtWidgets.QDialog):

    def setupUi(self, window):
        window.setObjectName("Set_immitans")
        window.resize(302, 384)
        window.setSizeGripEnabled(False)
        window.setModal(False)

        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)

        self.gridLayout = QtWidgets.QVBoxLayout(window)
        self.Layout_set_dev = QtWidgets.QGridLayout()
        self.Layout_set_trigger = QtWidgets.QGridLayout()
        self.Layout_set_connection = QtWidgets.QGridLayout()

        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.setGeometry(QtCore.QRect(80, 340, 191, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")



        self.check_resistance = QtWidgets.QCheckBox('Сопротивление')
        self.check_capacitance = QtWidgets.QCheckBox('Емкость')
        self.check_inductor = QtWidgets.QCheckBox('Индуктивность')
        self.check_impedance = QtWidgets.QCheckBox('Импеданс')
        self.check_current = QtWidgets.QCheckBox('Ток утечки')
        

        self.triger_enter = QtWidgets.QComboBox()
        self.triger_enter.setCurrentText("")
        self.triger_enter.setObjectName("triger_enter")

        self.trigger_label = QtWidgets.QLabel()
        self.trigger_label.setObjectName("label_3")

        self.second_value_limit_label = QtWidgets.QLabel()
        self.second_value_limit_label.setObjectName("second_value_limit_label")

        self.second_limit_enter = QtWidgets.QComboBox()
        self.second_limit_enter.setCurrentText("")
        self.second_limit_enter.setObjectName("second_limit_enter")
        self.second_limit_enter.setEditable(True)

        self.shift_label = QtWidgets.QLabel()
        self.shift_enter = QtWidgets.QComboBox()

        self.radioButton = QtWidgets.QRadioButton()
        self.radioButton.setObjectName("radioButton")

        self.level_label = QtWidgets.QLabel()
        self.level_label.setObjectName("label_4")

        self.level_enter = QtWidgets.QComboBox()
        self.level_enter.setCurrentText("")
        self.level_enter.setObjectName("level_enter")

        self.frequency_label = QtWidgets.QLabel()
        self.frequency_label.setObjectName("label_5")

        self.frequency_enter = QtWidgets.QComboBox()
        self.frequency_enter.setCurrentText("")
        self.frequency_enter.setObjectName("freq_enter")

        self.COM_label = QtWidgets.QLabel()
        self.COM_label.setObjectName("label_10")

        self.comportslist = QtWidgets.QComboBox()
        self.comportslist.setObjectName("comportslist")

        self.baud_label = QtWidgets.QLabel()
        self.baud_label.setObjectName("label_11")

        self.boudrate = QtWidgets.QComboBox()
        self.boudrate.setObjectName("boudrate")

        self.label_sourse = QtWidgets.QLabel()
        self.label_sourse.setObjectName("label_sourse")

        self.sourse_enter = QtWidgets.QComboBox()
        self.sourse_enter.setCurrentText("")
        self.sourse_enter.setObjectName("sourse_enter")

        self.num_meas_enter = QtWidgets.QComboBox()
        self.num_meas_enter.setCurrentText("")
        self.num_meas_enter.setObjectName("sourse_enter1")

        self.label_num_meas = QtWidgets.QLabel()
        self.label_num_meas.setObjectName("label_num_meas")

        self.label_connection = QtWidgets.QLabel()
        self.label_connection.setObjectName("connection")
        self.label_connection.setFont(font)

        self.label_what_is_meas = QtWidgets.QLabel()

        self.settings_experiment = QtWidgets.QLabel()
        self.settings_experiment.setObjectName("set_exp")
        self.settings_experiment.setFont(font)

        self.settings_dev = QtWidgets.QLabel()
        self.settings_dev.setFont(font)

        self.Layout_set_dev.addWidget(self.settings_dev, 0, 0, 1, 3)

        self.Layout_set_dev.addWidget(self.frequency_label, 1, 0, 1, 1)
        self.Layout_set_dev.addWidget(self.frequency_enter, 1, 1, 1, 2)

        self.Layout_set_dev.addWidget(self.level_label, 2, 0, 1, 1)
        self.Layout_set_dev.addWidget(self.level_enter, 2, 1, 1, 2)

        self.Layout_set_dev.addWidget(self.shift_label, 3, 0, 1, 1)
        self.Layout_set_dev.addWidget(self.shift_enter, 3, 1, 1, 2)


        self.Layout_set_dev.addWidget(self.label_what_is_meas, 4, 0, 1, 1)

        self.Layout_set_dev.addWidget(self.check_resistance, 4, 1, 1, 1)
        self.Layout_set_dev.addWidget(self.check_capacitance, 5, 1, 1, 1)
        self.Layout_set_dev.addWidget(self.check_inductor, 6, 1, 1, 1)
        self.Layout_set_dev.addWidget(self.check_impedance, 7, 1, 1, 1)
        self.Layout_set_dev.addWidget(self.check_current, 8, 1, 1, 1)
        

        self.Layout_set_trigger.addWidget(self.settings_experiment, 1, 0, 1, 3)

        self.Layout_set_trigger.addWidget(self.trigger_label, 2, 0, 1, 1)
        self.Layout_set_trigger.addWidget(self.triger_enter, 2, 1, 1, 2)

        self.Layout_set_trigger.addWidget(self.label_sourse, 3, 0, 1, 1)
        self.Layout_set_trigger.addWidget(self.sourse_enter, 3, 1, 1, 2)

        self.Layout_set_trigger.addWidget(self.label_num_meas, 4, 0, 1, 1)
        self.Layout_set_trigger.addWidget(self.num_meas_enter, 4, 1, 1, 2)

        self.Layout_set_connection.addWidget(self.label_connection, 0, 0, 1, 3)

        self.Layout_set_connection.addWidget(self.COM_label, 1, 0, 1, 1)
        self.Layout_set_connection.addWidget(self.comportslist, 1, 1, 1, 2)

        self.Layout_set_connection.addWidget(self.baud_label, 2, 0, 1, 1)
        self.Layout_set_connection.addWidget(self.boudrate, 2, 1, 1, 2)

        self.Layout_set_connection.addWidget(self.buttonBox, 3, 1, 2, 2)

        self.gridLayout.addLayout(self.Layout_set_dev)
        self.gridLayout.addLayout(self.Layout_set_trigger)
        self.gridLayout.addLayout(self.Layout_set_connection)


        self.retranslateUi(window)
        self.buttonBox.accepted.connect(
            window.accept)  # type: ignore
        self.buttonBox.rejected.connect(
            window.reject)  # type: ignore
        QtCore.QMetaObject.connectSlotsByName(window)

    def closeEvent(self, event):  # эта функция вызывается при закрытии окна крестиком
        print("окно настройки блока закрыто крестиком")

    def retranslateUi(self, Set_power_supply):
        _translate = QtCore.QCoreApplication.translate
        Set_power_supply.setWindowTitle(
            _translate("Set_power_supply", "настройка измерителя иммитанса"))
        self.trigger_label.setText(_translate("Set_power_supply", "Триггер"))
        self.level_label.setText(_translate("Set_power_supply", "Уровень"))
        self.frequency_label.setText(_translate(
            "Set_power_supply", "Частота"))
        self.COM_label.setText(_translate("Set_power_supply", "COM"))
        self.baud_label.setText(_translate("Set_power_supply", "Baudrate"))
        self.label_sourse.setText(_translate(
            "Set_power_supply", "Время(с)"))
        self.label_num_meas.setText(_translate(
            "Set_power_supply", "Кол-во измерений"))
        self.label_connection.setText(_translate(
            "Set_power_supply", "Параметры подключения"))
        self.settings_experiment.setText(_translate(
            "Set_power_supply", "Настройки работы в эксперименте"))
        self.settings_dev.setText(_translate(
            "Set_power_supply", "Настройки прибора"))
        self.shift_label.setText(_translate(
            "Set_power_supply", "Смещение"))
        self.label_what_is_meas.setText(_translate(
            "Set_power_supply", "Параметры для измерения"))



if __name__ == "__main__":
    import qdarktheme
    import sys
    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = Ui_Set_immitans()
    a.setupUi(a)
    a.show()
    sys.exit(app.exec_())