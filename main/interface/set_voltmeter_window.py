from PyQt5 import QtCore, QtGui, QtWidgets
import logging
logger = logging.getLogger(__name__)

class Ui_Set_voltmeter(QtWidgets.QDialog):

    def setupUi(self, window):
        window.setObjectName("Set_voltmeter")
        window.resize(302, 384)
        window.setSizeGripEnabled(False)
        window.setModal(False)

        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)

        self.gridLayout = QtWidgets.QGridLayout(window)

        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.setGeometry(QtCore.QRect(80, 340, 191, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")

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

        self.radioButton = QtWidgets.QRadioButton()
        self.radioButton.setObjectName("radioButton")

        self.range_label = QtWidgets.QLabel()
        self.range_label.setObjectName("label_4")

        self.range_enter = QtWidgets.QComboBox()
        self.range_enter.setCurrentText("")
        self.range_enter.setObjectName("type_step_enter")

        self.mode_label = QtWidgets.QLabel()
        self.mode_label.setObjectName("label_5")

        self.type_work_enter = QtWidgets.QComboBox()
        self.type_work_enter.setCurrentText("")
        self.type_work_enter.setObjectName("type_work_enter")

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
        self.gridLayout.addWidget(self.num_meas_enter, 2, 1, 1, 1)

        self.label_num_meas = QtWidgets.QLabel()
        self.label_num_meas.setObjectName("label_num_meas")

        self.label_connection = QtWidgets.QLabel()
        self.label_connection.setObjectName("connection")
        self.label_connection.setFont(font)

        self.settings_experiment = QtWidgets.QLabel()
        self.settings_experiment.setObjectName("set_exp")
        self.settings_experiment.setFont(font)

        self.settings_dev = QtWidgets.QLabel()
        self.settings_dev.setFont(font)

        self.gridLayout.addWidget(self.settings_dev, 0, 0, 1, 3)

        self.gridLayout.addWidget(self.mode_label, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.type_work_enter, 1, 1, 1, 2)

        self.gridLayout.addWidget(self.range_label, 2, 0, 1, 1)
        self.gridLayout.addWidget(self.range_enter, 2, 1, 1, 2)

        self.gridLayout.addWidget(self.settings_experiment, 3, 0, 1, 3)

        self.gridLayout.addWidget(self.trigger_label, 7, 0, 1, 1)
        self.gridLayout.addWidget(self.triger_enter, 7, 1, 1, 2)

        self.gridLayout.addWidget(self.label_sourse, 8, 0, 1, 1)
        self.gridLayout.addWidget(self.sourse_enter, 8, 1, 1, 2)

        self.gridLayout.addWidget(self.label_num_meas, 9, 0, 1, 1)
        self.gridLayout.addWidget(self.num_meas_enter, 9, 1, 1, 2)

        self.gridLayout.addWidget(self.label_connection, 10, 0, 1, 3)

        self.gridLayout.addWidget(self.COM_label, 11, 0, 1, 1)
        self.gridLayout.addWidget(self.comportslist, 11, 1, 1, 2)

        self.gridLayout.addWidget(self.baud_label, 12, 0, 1, 1)
        self.gridLayout.addWidget(self.boudrate, 12, 1, 1, 2)

        self.gridLayout.addWidget(self.buttonBox, 13, 1, 2, 2)

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
            _translate("Set_power_supply", "настройка вольтметра"))
        self.trigger_label.setText(_translate("Set_power_supply", "Триггер"))
        self.range_label.setText(_translate("Set_power_supply", "Диапазон"))
        self.mode_label.setText(_translate(
            "Set_power_supply", "Что измеряем?"))
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


if __name__ == "__main__":
    import qdarktheme
    import sys
    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = Ui_Set_voltmeter()
    a.setupUi(a)
    a.show()
    sys.exit(app.exec_())
