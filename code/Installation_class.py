from installation_window import Ui_Installation
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from maisheng_power_class import maisheng_power_class
from sr830_class import sr830_class


class installation_class():
    def __init__(self) -> None:
        print("класс установки создан")
        self.dict_device_class = {
            "Maisheng": maisheng_power_class, "Lock in": sr830_class}
        self.dict_active_device_class = {}
        self.dict_status_active_device_class = {}

    def reconstruct_installation(self, current_installation_list):
        print(current_installation_list)
        proven_device = []

        for key in current_installation_list:  # создаем классы переданных приборов
            try:
                self.dict_active_device_class[key] = self.dict_device_class[key](
                    current_installation_list, self, name=key)
                # словарь,показывающий статус готовности приборов, запуск установки будет произведен только если все девайсы имееют статус true
                self.dict_status_active_device_class[key] = False
                proven_device.append(key)
            except:
                print("под прибор " + key + " не удалось найти класс")

        self.current_installation_list = proven_device
        current_installation_list = proven_device

        self.installation_window = Ui_Installation()
        self.installation_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installation_window.setupUi(
            self.installation_window, current_installation_list)
        if len(current_installation_list) > 0:
            self.installation_window.change_device_button[current_installation_list[0]].clicked.connect(
                lambda: self.testable(current_installation_list[0]))
        if len(current_installation_list) > 1:
            self.installation_window.change_device_button[current_installation_list[1]].clicked.connect(
                lambda: self.testable(current_installation_list[1]))
        if len(current_installation_list) > 2:
            self.installation_window.change_device_button[current_installation_list[2]].clicked.connect(
                lambda: self.testable(current_installation_list[2]))
        if len(current_installation_list) > 3:
            self.installation_window.change_device_button[current_installation_list[3]].clicked.connect(
                lambda: self.testable(current_installation_list[3]))
        if len(current_installation_list) > 4:
            self.installation_window.change_device_button[current_installation_list[4]].clicked.connect(
                lambda: self.testable(current_installation_list[4]))
        if len(current_installation_list) > 5:
            self.installation_window.change_device_button[current_installation_list[5]].clicked.connect(
                lambda: self.testable(current_installation_list[5]))
        '''
		for i in range(len(current_installation_list)):
			self.installation_window.change_device_button[current_installation_list[0]].clicked.connect(lambda : self.testable(i))
		'''

        print("реконструирован класс установки")

    def testable(self, device):
        print("кнопка нажата, устройство -" + str(device))
        # окно настройки
        self.dict_active_device_class[device].show_setting_window()

    def show_window_installation(self):
        print("показать окно класса установки")
        self.installation_window.show()
        # sys.exit(self.app.exec_())

    def close_window_installation(self):
        print("закрыть окно установки")
        try:
            self.installation_window.close()
            print("окно закрылось")
        except:
            print("объект был удален и посему закрытия не получилось, оно итак закрыто")

    def message_from_device_settings(self, name_device, status_parameters, list_parameters):
        print("сообщение из класса установка")
        if status_parameters == True:
            self.installation_window.verticalLayoutWidget[name_device].setStyleSheet(
                "background-color: rgb(180, 255, 180);")
            self.dict_status_active_device_class[name_device] = True
            self.show_parameters_of_device_on_label(
                name_device, list_parameters)
        else:
            self.installation_window.verticalLayoutWidget[name_device].setStyleSheet(
                "background-color: rgb(255, 140, 140);")
            self.dict_status_active_device_class[name_device] = False
        # TODO анализ на типы подключения и ком порты
        self.dict_active_device_class[name_device].confirm_parameters(
            True, "client")

    def experiment(self):
        pass

    def show_parameters_of_device_on_label(self, device, list_parameters):
        labeltext = ""
        for i in list_parameters:
            labeltext = labeltext + str(i) + ":" + \
                str(list_parameters[i])+"\n\r"
        self.installation_window.label[device].setWordWrap(True)
        self.installation_window.label[device].setText(labeltext)

    def is_all_device_settable(self) -> bool:
        status = True
        for i in self.current_installation_list:
            if self.dict_status_active_device_class[i] == False:
                status = False
                return status
        return status


if __name__ == "__main__":
    lst = ["Maisheng", "Lock in", "fdfdfdf"]
    app = QtWidgets.QApplication(sys.argv)
    a = installation_class()
    a.reconstruct_installation(lst)
    a.show_window_installation()
    sys.exit(app.exec_())


# pyuic5 name.ui -o name.py
