import logging

from PyQt5 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)


class base_settings_window(QtWidgets.QDialog):
    def __init__(self) -> None:
        super().__init__()

        self.font = QtGui.QFont()
        self.font.setPointSize(11)
        self.font.setBold(True)

        self.setModal(False)

        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.setGeometry(QtCore.QRect(80, 340, 191, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok
        )
        self.buttonBox.setObjectName("buttonBox")

        self.triger_act_enter = QtWidgets.QComboBox()
        self.triger_meas_enter = QtWidgets.QComboBox()

        self.triger_act_label = QtWidgets.QLabel("Триг действия")
        self.triger_meas_label = QtWidgets.QLabel("Триг измерения")

        self.COM_label = QtWidgets.QLabel("COM")
        self.comportslist = QtWidgets.QComboBox()
        self.baud_label = QtWidgets.QLabel("Baudrate")
        self.boudrate = QtWidgets.QComboBox()

        self.sourse_act_label = QtWidgets.QLabel("Время(с)")
        self.sourse_meas_label = QtWidgets.QLabel("Время(с)")

        self.sourse_act_enter = QtWidgets.QComboBox()
        self.sourse_meas_enter = QtWidgets.QComboBox()

        self.num_meas_enter = QtWidgets.QComboBox()
        self.num_act_enter = QtWidgets.QComboBox()

        self.num_meas_label = QtWidgets.QLabel("Кол-во измерений")
        self.num_act_label = QtWidgets.QLabel("Кол-во действий")

        self.settings_dev = QtWidgets.QLabel("Настройки прибора")
        self.settings_dev.setFont(self.font)

        self.label_connection = QtWidgets.QLabel("Настройки подключения")
        self.label_connection.setFont(self.font)

        self.settings_act_in_exp = QtWidgets.QLabel("Set action in exp")
        self.settings_act_in_exp.setFont(self.font)

        self.settings_act_in_exp.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )

        self.settings_meas_in_exp = QtWidgets.QLabel("Set meas in exp")
        self.settings_meas_in_exp.setFont(self.font)

        self.settings_meas_in_exp.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )

        self.verticalSpacerButtonact = QtWidgets.QSpacerItem(
            15, 15, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.verticalSpacerButtonmeas = QtWidgets.QSpacerItem(
            15, 15, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        # ===Create layout==
        self.baseLayout = QtWidgets.QVBoxLayout(self)

        self.Layout_set_dev_act = QtWidgets.QGridLayout()
        self.Layout_set_triger_act = QtWidgets.QGridLayout()
        self.Layout_set_connection = QtWidgets.QGridLayout()

        self.Layout_set_dev_meas = QtWidgets.QGridLayout()
        self.Layout_set_triger_meas = QtWidgets.QGridLayout()

        self.meas_layout = QtWidgets.QVBoxLayout()
        self.act_layout = QtWidgets.QVBoxLayout()

        self.one_line_lay = QtWidgets.QHBoxLayout()
        self.two_line_lay = QtWidgets.QHBoxLayout()
        self.three_line_lay = QtWidgets.QHBoxLayout()

        self.vert_act_lay = QtWidgets.QVBoxLayout()
        self.vert_meas_lay = QtWidgets.QVBoxLayout()

        # ===Configuration layout===
        self.vert_act_lay.addLayout(self.Layout_set_dev_act)
        self.vert_meas_lay.addLayout(self.Layout_set_dev_meas)

        self.one_line_lay.addLayout(self.vert_act_lay)
        self.one_line_lay.addLayout(self.vert_meas_lay)

        self.two_line_lay.addLayout(self.Layout_set_triger_act)
        self.two_line_lay.addLayout(self.Layout_set_triger_meas)

        self.baseLayout.addLayout(self.one_line_lay)
        self.baseLayout.addLayout(self.two_line_lay)
        self.baseLayout.addLayout(self.Layout_set_connection)

        self.vert_act_lay.addItem(self.verticalSpacerButtonact)
        self.vert_meas_lay.addItem(self.verticalSpacerButtonmeas)

        self.Layout_set_triger_act.addWidget(self.settings_act_in_exp, 1, 0, 1, 3)
        self.Layout_set_triger_act.addWidget(self.triger_act_label, 2, 0, 1, 1)
        self.Layout_set_triger_act.addWidget(self.triger_act_enter, 2, 1, 1, 2)
        self.Layout_set_triger_act.addWidget(self.sourse_act_label, 3, 0, 1, 1)
        self.Layout_set_triger_act.addWidget(self.sourse_act_enter, 3, 1, 1, 2)
        self.Layout_set_triger_act.addWidget(self.num_act_label, 4, 0, 1, 1)
        self.Layout_set_triger_act.addWidget(self.num_act_enter, 4, 1, 1, 2)

        self.Layout_set_triger_meas.addWidget(self.settings_meas_in_exp, 1, 0, 1, 3)
        self.Layout_set_triger_meas.addWidget(self.triger_meas_label, 2, 0, 1, 1)
        self.Layout_set_triger_meas.addWidget(self.triger_meas_enter, 2, 1, 1, 2)
        self.Layout_set_triger_meas.addWidget(self.sourse_meas_label, 3, 0, 1, 1)
        self.Layout_set_triger_meas.addWidget(self.sourse_meas_enter, 3, 1, 1, 2)
        self.Layout_set_triger_meas.addWidget(self.num_meas_label, 4, 0, 1, 1)
        self.Layout_set_triger_meas.addWidget(self.num_meas_enter, 4, 1, 1, 2)

        self.Layout_set_connection.addWidget(self.label_connection, 0, 0, 1, 3)
        self.Layout_set_connection.addWidget(self.COM_label, 1, 0, 1, 1)
        self.Layout_set_connection.addWidget(self.comportslist, 1, 1, 1, 2)
        self.Layout_set_connection.addWidget(self.baud_label, 2, 0, 1, 1)
        self.Layout_set_connection.addWidget(self.boudrate, 2, 1, 1, 2)
        self.Layout_set_connection.addWidget(self.buttonBox, 3, 1, 2, 2)

        self.buttonBox.accepted.connect(self.accept)  # type: ignore
        self.buttonBox.rejected.connect(self.reject)  # type: ignore
        QtCore.QMetaObject.connectSlotsByName(self)

        self.rejected.connect(self.onReject)

        self.triger_act_enter.setWhatsThis(
            "Источник сигнала для проведения действия. Таймер - поведение действия через заданное количество секунд в поле ниже. Внешний сигнал - сигнал от дугих пиборов в установке "
        )
        self.num_act_enter.setWhatsThis(
            "Количество действий, которое прибор выполнит в ходе эксперимента"
        )
        self.sourse_act_enter.setWhatsThis(
            "Выберите источника сигнала или значение(в случае таймера в качестве триггера) для действия данного канала"
        )

        self.triger_meas_enter.setWhatsThis(
            "Источник сигнала для проведения измерения. Таймер - поведение измерения через заданное количество секунд в поле ниже. Внешний сигнал - сигнал от дугих пиборов в установке "
        )
        self.num_meas_enter.setWhatsThis(
            "Количество измерений, которое прибор выполнит в ходе эксперимента"
        )
        self.sourse_meas_enter.setWhatsThis(
            "Выберите источника сигнала или значение(в случае таймера в качестве триггера)"
        )

        self.comportslist.setWhatsThis(
            "Выберите интерфейс подключения, если нужный интерфейс(usb, com) не отображаются в списке для выбора, проверьте доступность этого интерфейса в диспетчере устройств вашей операционной системы."
        )
        self.boudrate.setWhatsThis(
            "Скорость обмена данными(bit per second) при выбранном интерфейсе COM-port. При другом выбранном интерфейсе данный параметр игнорируется."
        )

    def closeEvent(self, event):  # эта функция вызывается при закрытии окна крестиком
        print("окно настройки закрыто крестиком")

    def onReject(self):
        print("окно настройки закрыто через esc")

    def remove_meas(self):
        for i in reversed(range(self.Layout_set_triger_meas.count())):
            self.Layout_set_triger_meas.itemAt(i).widget().setParent(None)
        for i in reversed(range(self.Layout_set_dev_meas.count())):
            self.Layout_set_dev_meas.itemAt(i).widget().setParent(None)

    def remove_act(self):
        for i in reversed(range(self.Layout_set_triger_act.count())):
            self.Layout_set_triger_act.itemAt(i).widget().setParent(None)
        for i in reversed(range(self.Layout_set_dev_act.count())):
            self.Layout_set_dev_act.itemAt(i).widget().setParent(None)


if __name__ == "__main__":
    import sys

    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme(corner_shape="sharp")
    a = base_settings_window()
    a.show()
    sys.exit(app.exec_())
