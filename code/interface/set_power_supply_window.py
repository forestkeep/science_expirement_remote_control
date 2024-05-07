from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Set_power_supply(QtWidgets.QDialog):

    def setupUi(self, Set_power_supply):
        Set_power_supply.setObjectName("Set_power_supply")
        Set_power_supply.resize(302, 384)
        Set_power_supply.setSizeGripEnabled(False)
        Set_power_supply.setModal(False)

        self.gridLayout = QtWidgets.QGridLayout(Set_power_supply)


        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.setGeometry(QtCore.QRect(80, 340, 191, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")

        self.triger_enter = QtWidgets.QComboBox()
        self.triger_enter.setCurrentText("")
        self.triger_enter.setObjectName("triger_enter")

        self.label_3 = QtWidgets.QLabel()
        self.label_3.setObjectName("label_3")

        self.second_value_limit_label = QtWidgets.QLabel()
        self.second_value_limit_label.setObjectName("second_value_limit_label")

        self.second_limit_enter = QtWidgets.QComboBox()
        self.second_limit_enter.setCurrentText("")
        self.second_limit_enter.setObjectName("second_limit_enter")
        self.second_limit_enter.setEditable(True)

        self.radioButton = QtWidgets.QRadioButton()
        self.radioButton.setObjectName("radioButton")

        self.label_4 = QtWidgets.QLabel()
        self.label_4.setObjectName("label_4")

        self.type_step_enter = QtWidgets.QComboBox()
        self.type_step_enter.setCurrentText("")
        self.type_step_enter.setObjectName("type_step_enter")

        self.label_5 = QtWidgets.QLabel()
        self.label_5.setObjectName("label_5")

        self.type_work_enter = QtWidgets.QComboBox()
        self.type_work_enter.setCurrentText("")
        self.type_work_enter.setObjectName("type_work_enter")

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
        self.step_enter.setStyleSheet("")
        self.step_enter.setEditable(True)
        self.step_enter.setCurrentText("")
        self.step_enter.setObjectName("step_enter")

        self.label_8 = QtWidgets.QLabel()
        self.label_8.setObjectName("label_8")
        self.label_7 = QtWidgets.QLabel()
        self.label_7.setObjectName("label_7")
        self.label_9 = QtWidgets.QLabel()
        self.label_9.setObjectName("label_9")
        self.label_10 = QtWidgets.QLabel()
        self.label_10.setObjectName("label_10")

        self.comportslist = QtWidgets.QComboBox()
        self.comportslist.setObjectName("comportslist")

        self.label_11 = QtWidgets.QLabel()
        self.label_11.setObjectName("label_11")

        self.boudrate = QtWidgets.QComboBox()
        self.boudrate.setObjectName("boudrate")

        self.label_sourse = QtWidgets.QLabel()
        self.label_sourse.setObjectName("label_sourse")

        self.sourse_enter = QtWidgets.QComboBox()
        self.sourse_enter.setCurrentText("")
        self.sourse_enter.setObjectName("sourse_enter")


        self.gridLayout.addWidget(self.label_5,0,0,1,1)
        self.gridLayout.addWidget(self.type_work_enter,0,1,1,2)

        self.gridLayout.addWidget(self.label_4,1,0,1,1)
        self.gridLayout.addWidget(self.type_step_enter,1,1,1,2)

        self.gridLayout.addWidget(self.label,2,0,1,1)
        self.gridLayout.addWidget(self.start_enter,2,1,1,2)

        self.gridLayout.addWidget(self.label_2,3,0,1,1)
        self.gridLayout.addWidget(self.stop_enter,3,1,1,2)

        self.gridLayout.addWidget(self.label_6,4,0,1,1)
        self.gridLayout.addWidget(self.step_enter,4,1,1,2)

        self.gridLayout.addWidget(self.label_7,2,4,1,1)
        self.gridLayout.addWidget(self.label_8,3,4,1,1)
        self.gridLayout.addWidget(self.label_9,4,4,1,1)

        self.gridLayout.addWidget(self.second_value_limit_label,5,0,1,1)
        self.gridLayout.addWidget(self.second_limit_enter,5,1,1,2)

        self.gridLayout.addWidget(self.radioButton,6,1,1,1)

        self.gridLayout.addWidget(self.label_3,7,0,1,1)
        self.gridLayout.addWidget(self.triger_enter,7,1,1,2)

        self.gridLayout.addWidget(self.label_sourse,8,0,1,1)
        self.gridLayout.addWidget(self.sourse_enter,8,1,1,2)

        self.gridLayout.addWidget(self.label_10,9,0,1,1)
        self.gridLayout.addWidget(self.comportslist,9,1,1,2)

        self.gridLayout.addWidget(self.label_11,10,0,1,1)
        self.gridLayout.addWidget(self.boudrate,10,1,1,2)

        self.gridLayout.addWidget(self.buttonBox,11,1,2,2)


        self.retranslateUi(Set_power_supply)
        self.buttonBox.accepted.connect(
            Set_power_supply.accept)  # type: ignore
        self.buttonBox.rejected.connect(
            Set_power_supply.reject)  # type: ignore
        QtCore.QMetaObject.connectSlotsByName(Set_power_supply)
        
    def closeEvent(self, event):  # эта функция вызывается при закрытии окна крестиком
        print("окно настройки блока закрыто крестиком")

    def retranslateUi(self, Set_power_supply):
        _translate = QtCore.QCoreApplication.translate
        Set_power_supply.setWindowTitle(
            _translate("Set_power_supply", "настройка источника питания"))
        self.label_3.setText(_translate("Set_power_supply", "Триггер"))
        self.second_value_limit_label.setText(
            _translate("Set_power_supply", "V/A не больше"))
        self.radioButton.setText(_translate(
            "Set_power_supply", "Пройти туда-обратно?"))
        # self.label_333.setText(_translate("Set_power_supply", "A"))
        self.label_4.setText(_translate("Set_power_supply", "Тип шага"))
        self.label_5.setText(_translate("Set_power_supply", "Режим работы"))
        self.label_6.setText(_translate("Set_power_supply", "Шаг"))
        self.label_2.setText(_translate(
            "Set_power_supply", "Конечное значение"))
        self.label.setText(_translate(
            "Set_power_supply", "Начальное значение"))
        self.label_7.setText(_translate("Set_power_supply", "V"))
        self.label_8.setText(_translate("Set_power_supply", "V"))
        self.label_9.setText(_translate("Set_power_supply", "V"))
        self.label_10.setText(_translate("Set_power_supply", "COM"))
        self.label_11.setText(_translate("Set_power_supply", "Baudrate"))
        self.label_sourse.setText(_translate(
            "Set_power_supply", "Время(с)"))
