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


class MyTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(MyTab, self).__init__()
        self.parent = parent
        self.rows = [
            ("10.16.26.25", 2),
            ("10.16.26.26", 3),
            ("10.16.26.27", 1),
            ("10.16.26.28", 4),
        ]
        self.lineEdit = QtWidgets.QLineEdit(placeholderText="Введите номер из 4х цифр")

        self.pushButton = QtWidgets.QPushButton("Создать TableWidget")
        self.pushButton1 = QtWidgets.QPushButton("трям")
        self.pushButton.clicked.connect(self.func_connect)

        self.tableWidget = QtWidgets.QTableWidget(0, 4)
        self.tableWidget.setHorizontalHeaderLabels(["IP", "Number", "SSH", "VNC"])
        self.tableWidget.horizontalHeader().setDefaultSectionSize(150)

        self.pushButton_test = QtWidgets.QPushButton("тест кнопка")
        vbox = QtWidgets.QVBoxLayout(self)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.tableWidget)
        hbox.addWidget(self.lineEdit)
        hbox.addWidget(self.pushButton)
        hbox.addWidget(self.pushButton_test)
        vbox.addLayout(hbox)
        vbox.addWidget(self.pushButton1)

    def func_connect(self):
        num = self.lineEdit.text()
        if not num.isdigit():
            self.parent.statusBar().showMessage(
                "Достустимо вводить только цифры, номер состоит из 4х цифр"
            )
            return
        if len(num) != 4:
            self.parent.statusBar().showMessage(
                "Номер состоит из 4х цифр, повторите ввод."
            )
            return
        self.parent.statusBar().showMessage("")

        self.tableWidget.setRowCount(len(self.rows))
        for row, items in enumerate(self.rows):
            self.tableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(items[0]))
            self.tableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(str(items[1])))

            button = QtWidgets.QPushButton(f"SSH {row}")
            button.clicked.connect(
                lambda ch, ip=items[0], n=items[1], btn=button: self.button_pushed_SSH(
                    ip, n, btn
                )
            )
            self.tableWidget.setCellWidget(row, 2, button)

            button = QtWidgets.QPushButton(f"VNC {row}")
            button.clicked.connect(
                lambda ch, ip=items[0], n=items[1], btn=button: self.button_pushed_VNC(
                    ip, n, btn
                )
            )
            self.tableWidget.setCellWidget(row, 3, button)
        self.tableWidget.setSortingEnabled(True)


class ps_test(QtWidgets.QDialog):
    def setupUi(self, main_window):
        main_window.setObjectName("Set_sr830")
        main_window.resize(303, 664)
        main_window.setSizeGripEnabled(False)
        main_window.setModal(True)

        # -------------------------------------
        self.verticalLayoutWidget_tab = QtWidgets.QWidget(main_window)
        self.verticalLayoutWidget_tab.setGeometry(QtCore.QRect(0, 0, 300, 300))
        self.verticalLayoutWidget_tab.setObjectName("verticalLayoutWidget_tab")
        self.tabWidget = QtWidgets.QTabWidget()
        count = self.tabWidget.count()
        self.tabWidget.insertTab(count, QtWidgets.QWidget(), "Ch 1")
        self.tabWidget.insertTab(count + 1, QtWidgets.QWidget(), "Ch 2")
        self.add_tabs(2)
        self.layout = QtWidgets.QGridLayout(self.verticalLayoutWidget_tab)
        self.layout.addWidget(self.tabWidget)
        # --------------------------------------

        self.buttonBox = QtWidgets.QDialogButtonBox(main_window)
        self.buttonBox.setGeometry(QtCore.QRect(100, 620, 191, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok
        )
        self.buttonBox.setObjectName("buttonBox")

        self.verticalLayoutWidget_11 = QtWidgets.QWidget(main_window)
        self.verticalLayoutWidget_11.setGeometry(QtCore.QRect(10, 530, 280, 80))
        self.verticalLayoutWidget_11.setObjectName("verticalLayoutWidget_11")
        self.verticalLayout_11 = QtWidgets.QVBoxLayout(self.verticalLayoutWidget_11)
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_11.setObjectName("verticalLayout_11")

        self.label_2 = QtWidgets.QLabel(self.verticalLayoutWidget_11)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_11.addWidget(self.label_2)

        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label_11 = QtWidgets.QLabel(self.verticalLayoutWidget_11)
        self.label_11.setObjectName("label_11")
        self.horizontalLayout_5.addWidget(self.label_11)
        self.boudrate = QtWidgets.QComboBox(self.verticalLayoutWidget_11)
        self.boudrate.setObjectName("boudrate")
        self.boudrate.addItem("")
        self.horizontalLayout_5.addWidget(self.boudrate)
        self.verticalLayout_11.addLayout(self.horizontalLayout_5)
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.label_10 = QtWidgets.QLabel(self.verticalLayoutWidget_11)
        self.label_10.setObjectName("label_10")
        self.horizontalLayout_4.addWidget(self.label_10)
        self.comportslist = QtWidgets.QComboBox(self.verticalLayoutWidget_11)
        self.comportslist.setObjectName("comportslist")
        self.horizontalLayout_4.addWidget(self.comportslist)
        self.verticalLayout_11.addLayout(self.horizontalLayout_4)

        self.label_10.setText("COM")
        self.label_11.setText("Baudrate")
        self.label_2.setText("Настройки подключения")
        # self.retranslateUi(main_window)
        self.buttonBox.accepted.connect(main_window.accept)  # type: ignore
        self.buttonBox.rejected.connect(main_window.reject)  # type: ignore
        # QtCore.QMetaObject.connectSlotsByName(main_window)

    def add_tabs(self, number):
        index = self.tabWidget.count() - 1
        tabPage = MyTab(self)
        self.tabWidget.insertTab(index, tabPage, f"Tab {index}")
        self.tabWidget.setCurrentIndex(index)
        tabPage.lineEdit.setFocus()

    def retranslateUi(self, Set_power_supply):
        _translate = QtCore.QCoreApplication.translate
        Set_power_supply.setWindowTitle("Dialog")
        self.label_12.setText(_translate("Set_power_supply", "Параметры генератора"))
        self.label_5.setText(_translate("Set_power_supply", "Частота(Гц)"))
        self.label_4.setText(_translate("Set_power_supply", "Амплитуда(В)"))
        self.label.setText(_translate("Set_power_supply", "Временная константа"))
        self.time_const_enter_number.setCurrentText("1")
        self.time_const_enter_number.setItemText(0, "1")
        self.time_const_enter_number.setItemText(1, "3")
        self.time_const_enter_factor.setCurrentText(
            "X1"
        )
        self.time_const_enter_factor.setItemText(
            0, "X1"
        )
        self.time_const_enter_factor.setItemText(
            1, "X10"
        )
        self.time_const_enter_factor.setItemText(
            2,"X100"
        )
        self.time_const_enter_decimal_factor.setCurrentText(
            "ks"
        )
        self.time_const_enter_decimal_factor.setItemText(
            0, "ks"
        )
        self.time_const_enter_decimal_factor.setItemText(
            1, "s"
        )
        self.time_const_enter_decimal_factor.setItemText(
            2, "ms"
        )
        self.time_const_enter_decimal_factor.setItemText(
            3, "us"
        )
        self.label_16.setText("Filter slope")
        self.Filt_slope_enter_level.setCurrentText("6")
        self.Filt_slope_enter_level.setItemText(0, "6")
        self.Filt_slope_enter_level.setItemText(1, "12")
        self.Filt_slope_enter_level.setItemText(2, "18")
        self.Filt_slope_enter_level.setItemText(3, "24")
        self.label_17.setText("SYNK < 200 Hz")
        self.SYNK_enter.setCurrentText("On")
        self.SYNK_enter.setItemText(0, "On")
        self.SYNK_enter.setItemText(1, "Off")
        self.label_13.setText(_translate("Set_power_supply", "Чувствительность"))
        self.sensitivity_enter_number.setCurrentText(
            "1"
        )
        self.sensitivity_enter_number.setItemText(
            0, "1"
        )
        self.sensitivity_enter_number.setItemText(
            1, "2"
        )
        self.sensitivity_enter_number.setItemText(
            2, "5"
        )
        self.sensitivity_enter_factor.setCurrentText(
            "X1"
        )
        self.sensitivity_enter_factor.setItemText(
            0, "X1"
        )
        self.sensitivity_enter_factor.setItemText(
            1, "X10"
        )
        self.sensitivity_enter_factor.setItemText(
            2, "X100"
        )
        self.sensitivity_enter_decimal_factor.setCurrentText(
            "V/uA"
        )
        self.sensitivity_enter_decimal_factor.setItemText(
            0, "V/uA"
        )
        self.sensitivity_enter_decimal_factor.setItemText(
            1,"mV/nA"
        )
        self.sensitivity_enter_decimal_factor.setItemText(
            2, "uV/pA"
        )
        self.sensitivity_enter_decimal_factor.setItemText(
            3, "nV/fA"
        )
        self.label_14.setText(_translate("Set_power_supply", "Вход сигнала"))
        self.input_channels_enter.setCurrentText("A")
        self.input_channels_enter.setItemText(0, "A")
        self.input_channels_enter.setItemText(
            1,"A - B"
        )
        self.input_channels_enter.setItemText(
            2, "I (10^6)"
        )
        self.input_channels_enter.setItemText(
            3, "I (10^8)"
        )
        self.input_type_enter.setCurrentText("AC")
        self.input_type_enter.setItemText(0,"AC")
        self.input_type_enter.setItemText(1, "DC")
        self.connect_ch_enter.setCurrentText("float")
        self.connect_ch_enter.setItemText(0, "float")
        self.connect_ch_enter.setItemText(1, "ground")
        self.label_18.setText("Reserve")
        self.reserve_enter.setCurrentText(
            "high reserve"
        )
        self.reserve_enter.setItemText(
            0, "high reserve"
        )
        self.reserve_enter.setItemText(1,"normal")
        self.reserve_enter.setItemText(2, "low noise")
        self.label_19.setText("Filters")
        self.filters_enter.setCurrentText("line")
        self.filters_enter.setItemText(0, "line")
        self.filters_enter.setItemText(1, "2X line")
        self.filters_enter.setItemText(2, "both")
        self.filters_enter.setItemText(3, "out")
        self.label_15.setText(_translate("Set_power_supply", "Считывание параметров"))
        self.label_sourse.setText(_translate("Set_power_supply", "Время (сек)"))
        self.label_triger.setText(_translate("Set_power_supply", "Триггер"))
        self.triger_enter.setCurrentText(_translate("Set_power_supply", "Таймер"))
        self.triger_enter.setItemText(0, _translate("Set_power_supply", "Таймер"))
        self.label_2.setText(_translate("Set_power_supply", "Настройки подключения"))
        self.label_11.setText("Baudrate")
        self.label_num_meas.setText(_translate("Set_power_supply", "Кол-во измерений"))
        self.boudrate.setItemText(0, "9600")
        self.label_10.setText("COM")


if __name__ == "__main__":
    import sys

    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = ps_test()
    a.show()
    sys.exit(app.exec_())