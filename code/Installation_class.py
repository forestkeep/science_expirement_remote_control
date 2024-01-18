from interface.installation_window import Ui_Installation
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from maisheng_power_class import maisheng_power_class
from sr830_class import sr830_class
from pymodbus.client import ModbusSerialClient
from pymodbus.utilities import computeCRC
import serial.tools.list_ports
from datetime import datetime
import time
from Classes import device_response_to_step
import threading
from PyQt5.QtCore import QTimer


class installation_class():
    def __init__(self) -> None:
        self.pbar_percent = 0

        self.timer_for_update_pbar = QTimer()
        self.timer_for_update_pbar.timeout.connect(
            lambda: self.update_pbar())
        self.dict_device_class = {
            "Maisheng": maisheng_power_class, "Lock in": sr830_class}
        self.dict_active_device_class = {}
        self.dict_status_active_device_class = {}
        self.clients = []  # здесь хранятся классы клиентов для всех устройств, они создаются и передаются каждому устройству в установке
        # ключ, который разрешает старт эксперимента
        self.key_to_start_installation = False
        # поток в котором идет экспер мент, запускается после настройки приборов и нажатия кнопки старт
        self.experiment_thread = None
        self.stop_experiment = False  # глобальная переменная для остановки потока

    def reconstruct_installation(self, current_installation_list):
        # print(current_installation_list)
        proven_device = []
        number_device = 1
        for key in current_installation_list:  # создаем классы переданных приборов
            try:
                # self.dict_active_device_class[key+str(number_device)] = self.dict_device_class[key](
                # current_installation_list, self, name=(key+str(number_device)))

                self.dict_active_device_class[key+str(number_device)] = self.dict_device_class[key](
                    name=(key+str(number_device)), installation_class=self)
                # словарь,показывающий статус готовности приборов, запуск установки будет произведен только если все девайсы имееют статус true
                self.dict_status_active_device_class[key +
                                                     str(number_device)] = False
                proven_device.append(key+str(number_device))
                number_device = number_device+1
            except:
                print("под прибор |" + key + "| не удалось создать класс")

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
        self.installation_window.start_button.clicked.connect(
            lambda: self.experiment_start())
        self.installation_window.start_button.setStyleSheet(
            "background-color: rgb(255, 127, 127);")

        print("реконструирован класс установки")

    def testable(self, device):
        print("кнопка настройки нажата, устройство -" + str(device))
        # окно настройки
        for client in self.clients:
            try:
                client.close()
            except:
                print(
                    "не удалось закрыть клиент связи, скорее всего, этого не требовалось")

        if not self.is_experiment_running():
            self.dict_active_device_class[device].show_setting_window()
        else:
            print("запущен эксперимент, запрещено менять параметры приборов")

    def show_window_installation(self):
        self.installation_window.show()
        # sys.exit(self.app.exec_())

    def close_window_installation(self):
        print("закрыть окно установки")
        try:
            self.installation_window.close()
            print("окно установки закрыто")
        except:
            print("объект был удален и посему закрытия не получилось, оно итак закрыто")

    def message_from_device_settings(self, name_device, status_parameters, list_parameters):
        print("Настройки прибора " + str(name_device) +
              " переданы классу установка")
        if status_parameters == True:
            self.installation_window.verticalLayoutWidget[name_device].setStyleSheet(
                "background-color: rgb(180, 220, 180);")
            print("темно зеленый вкл")
            self.dict_status_active_device_class[name_device] = True
            self.show_parameters_of_device_on_label(
                name_device, list_parameters)
        else:
            self.installation_window.verticalLayoutWidget[name_device].setStyleSheet(
                "background-color: rgb(255, 140, 140);")
            self.dict_status_active_device_class[name_device] = False
            self.installation_window.label[name_device].setText("Не настроено")
        print(list_parameters)
        if self.analyse_com_ports():
            # если оказались в этой точке, значит приборы настроены корректно и нет проблем с конфликтами ком портов, если подключение не будет установлено, то ключ снова будет сброшен
            self.key_to_start_installation = True

            self.create_clients()
            self.set_clients_for_device()
            self.confirm_devices_parameters()
        else:
            self.key_to_start_installation = False

        if self.key_to_start_installation == True:
            self.installation_window.start_button.setStyleSheet(
                "background-color: rgb(127, 255, 127);")
        else:
            self.installation_window.start_button.setStyleSheet(
                "background-color: rgb(255, 127, 127);")

    # подтверждаем параметры приборам и передаем им настроенные и созданные клиенты для подключения
    def confirm_devices_parameters(self):
        for device in self.dict_active_device_class.values():
            device.confirm_parameters()

    def set_clients_for_device(self):  # передать созданные клиенты приборам
        for device, client in zip(self.dict_active_device_class.values(), self.clients):
            device.set_client(client)

    def message_from_device_status_connect(self, answer, name_device):
        if answer == True:
            self.add_text_to_log(
                name_device + " - соединение установлено")
        else:
            self.add_text_to_log(
                name_device + " - соединение не установлено, проверьте подлючение", status="err")
            self.installation_window.verticalLayoutWidget[name_device].setStyleSheet(
                "background-color: rgb(180, 180, 180);")
            self.installation_window.start_button.setStyleSheet(
                "background-color: rgb(255, 127, 127);")
            # статус прибора ставим в не настроенный
            self.dict_status_active_device_class[name_device] = False
            self.key_to_start_installation = False  # старт экспериепнта запрещаем

    def is_experiment_running(self) -> bool:
        if self.experiment_thread == None:
            return False
        else:
            if self.experiment_thread.is_alive():
                return True
            else:
                return False

    def experiment_start(self):
        #TODO проверка на тип устойств в установке, + добавить количествво шагов для измерений
        if self.is_all_device_settable() and self.key_to_start_installation and not self.is_experiment_running():
            self.installation_window.start_button.setStyleSheet(
                "background-color: rgb(255, 255, 127);")

            status = True  # последние проверки перед стартом

            if status:
                # создаем текстовый файл
                name_file = ""
                for i in self.current_installation_list:
                    name_file = name_file + str(i) + "_"
                currentdatetime = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                self.buf_file = f"{name_file + currentdatetime}.txt"
                self.write_data_to_buf_file(message="Запущена установка \n\r")
                self.write_data_to_buf_file(message="Список приборов: " +
                                            str(self.current_installation_list) + "\r\n")
                for device_class, device_name in zip(self.dict_active_device_class.values(), self.current_installation_list):
                    self.write_data_to_buf_file(
                        message="Настройки " + str(device_name) + ": \r")
                    settings = device_class.get_settings()
                    for set, key in zip(settings.values(), settings.keys()):
                        self.write_data_to_buf_file(
                            message=str(key) + " - " + str(set) + "\r")
                    self.write_data_to_buf_file(message="\n")

                print("старт эксперимента")
                self.add_text_to_log("Создан файл " + self.buf_file)
                self.add_text_to_log("Эксперимент начат")

                self.experiment_thread = threading.Thread(
                    target=self.exp_th, daemon=True)
                self.stop_experiment = False
                self.experiment_thread.start()
                self.timer_for_update_pbar.start(3000)

            else:
                pass  # TODO что делать в случае, если что-то не то

    def write_data_to_buf_file(self, message, addTime=False):
        if addTime:
            message = datetime.now().strftime("%H-%M-%S") + " " + str(message)
        message = str(message)
        with open(self.buf_file, "a") as file:
            file.write(message)
            file.close()

    def update_pbar(self) -> None:

        self.installation_window.pbar.setValue(int(self.pbar_percent))
        if self.is_experiment_running():
            self.timer_for_update_pbar.start(3000)
        else:
            self.timer_for_update_pbar.stop()

    def exp_th(self):
        status = True
        self.add_text_to_log("настройка приборов.. ")
        for dev in self.dict_active_device_class.values():
            ans = dev.setup_before_experiment()
            if ans == False:
                status = False
                print("ошибка при настройке " +
                      dev.get_name() + " перед экспериментом")
                break
            self.add_text_to_log(dev.get_name() + " настроен")
        if status == False:
            return False

        # пока работаем только по таймерам!!!!!!!!!!!!!!-----------------------------
        time_pause = []
        time_start = []

        max_exp_time = 0
        start_exp_time = 0

        for device in self.dict_active_device_class.values():
            buf_time = device.get_steps_number()
            if buf_time > max_exp_time:
                max_exp_time = buf_time
            try:
                # time_start.append(time.time())
                time_start.append(0)
                time_pause.append(float(device.get_trigger_value()))
            except:
                print("Ошибка, необходимо установить таймер!!")

        start_exp_time = time.time()
        self.installation_window.pbar.setMinimum(0)
        self.installation_window.pbar.setMaximum(100)
        error = False  # флаг ошибки, будет поднят при ошибке во время эксперимента

        while not self.stop_experiment:
            self.pbar_percent = (
                ((time.time() - start_exp_time)/max_exp_time))*100

            self.stop_experiment = False
            try:
                local_index = 0
                for dev in self.dict_active_device_class.values():
                    if time.time() - time_start[local_index] >= time_pause[local_index]:
                        ans, param, step_time = dev.do_step()
                        print(step_time)
                    # закончились шаги, заканчиваем эксперимент
                        if ans == device_response_to_step.End_list_of_steps:
                            self.stop_experiment = True
                            ans = device_response_to_step.Step_done
                        if ans == device_response_to_step.Step_done:
                            self.write_data_to_buf_file("", addTime=True)
                            for param in param:
                                self.write_data_to_buf_file(
                                    message=str(param) + "\t")
                            self.write_data_to_buf_file(message="\n")
                            pass
                        if ans == device_response_to_step.Step_fail:
                            self.stop_experiment = True
                        time_start[local_index] = time.time()
                    local_index = local_index + 1
            except:
                print("хз что случилось, тормозим эксперимент")
                error = True
                self.stop_experiment = True
        print("эксперимент завершен")
        if error:
            self.add_text_to_log("Эксперимент прерван из-за ошибки", "err")
        else:
            self.add_text_to_log("Эксперимент завершен")
        self.pbar_percent = 0  # сбрасываем прогресс бар
        # ------------------подготовка к повторному началу эксперимента---------------------
        print(self.key_to_start_installation)
        if self.analyse_com_ports():

            # если оказались в этой точке, значит приборы настроены корректно и нет проблем с конфликтами ком портов, если подключение не будет установлено, то ключ снова будет сброшен
            self.key_to_start_installation = True

            self.create_clients()
            self.set_clients_for_device()
            self.confirm_devices_parameters()
        else:
            self.key_to_start_installation = False

        if self.key_to_start_installation == True:
            self.installation_window.start_button.setStyleSheet(
                "background-color: rgb(127, 255, 127);")
        else:
            self.installation_window.start_button.setStyleSheet(
                "background-color: rgb(255, 127, 127);")

        # self.confirm_devices_parameters()
        # self.installation_window.start_button.setStyleSheet(
            # "background-color: rgb(127, 255, 127);")
        # --------------------------------------------------------------------------------

    def add_text_to_log(self, text, status=None):
        if status == "err":
            self.installation_window.log.setTextColor(QtGui.QColor('red'))
        elif status == "war":
            self.installation_window.log.setTextColor(QtGui.QColor('orange'))
        else:
            self.installation_window.log.setTextColor(QtGui.QColor('black'))

        self.installation_window.log.append(
            (str(datetime.now().strftime("%H:%M:%S")) + " : " + str(text)))

    def analyse_com_ports(self) -> bool:
        ''' анализ конфликтов ком портов и проверка их наличия'''

        status = False
        if self.is_all_device_settable():
            status = True
            list_type_connection = []
            list_COMs = []
            list_baud = []
            i = 0
            fail_ports_list = []
            for client in self.clients:
                try:
                    client.close()
                    print("клиент успешно закрыт")
                except:
                    print("не удалось закрыть клиент")
                    pass
            self.clients.clear()
            for device in self.dict_active_device_class.values():
                com = device.get_COM()
                baud = device.get_baud()
                list_type_connection.append(device.get_type_connection())
                list_COMs.append(com)
                list_baud.append(baud)
                self.installation_window.verticalLayoutWidget[self.current_installation_list[i]].setStyleSheet(
                    "background-color: rgb(180, 255, 180);")  # красим расцветку в зеленый, analyse_com_ports вызывается после подтверждения, что все девайсы настроены
                try:
                    print(com, baud)
                    buf_client = serial.Serial(com, int(baud))
                    buf_client.close()
                    buf_client = None
                except:
                    self.installation_window.verticalLayoutWidget[self.current_installation_list[i]].setStyleSheet(
                        "background-color: rgb(180, 180, 127);")
                    print("ошибка открытия порта " + str(com))
                    if com not in fail_ports_list:
                        self.add_text_to_log(
                            "не удалось открыть " + str(com) + "\n", "war")
                    fail_ports_list.append(com)
                    status = False
                i = i+1

            for i in range(len(list_baud)):
                for j in range(len(list_baud)):
                    if i == j:
                        continue
                    if list_type_connection[i] == "serial":
                        if list_COMs[i] == list_COMs[j]:
                            self.installation_window.verticalLayoutWidget[self.current_installation_list[j]].setStyleSheet(
                                "background-color: rgb(180, 180, 127);")
                            self.installation_window.verticalLayoutWidget[self.current_installation_list[i]].setStyleSheet(
                                "background-color: rgb(180, 180, 127);")
                            self.add_text_to_log(str(self.current_installation_list[i]) + " и " + str(
                                self.current_installation_list[j]) + " не могут иметь один COM порт", status="war")
                            status = False  # ошибка типы подключения сериал могут бть только в единственном экземпяре
                    if list_type_connection[i] == "modbus":
                        if list_COMs[i] == list_COMs[j]:
                            if list_baud[i] != list_baud[j]:
                                self.installation_window.verticalLayoutWidget[self.current_installation_list[j]].setStyleSheet(
                                    "background-color: rgb(180, 180, 127);")
                                self.installation_window.verticalLayoutWidget[self.current_installation_list[i]].setStyleSheet(
                                    "background-color: rgb(180, 180, 127);")
                                self.add_text_to_log(str(self.current_installation_list[i]) + " и " + str(
                                    self.current_installation_list[j]) + " не могут иметь разную скорость подключения", status="war")
                                status = False  # если модбас порты совпадают, то должны совпадать и скорости
        return status

    # функция создает клиенты для приборов с учетом того, что несколько приборов могут быть подключены к одному порту.
    def create_clients(self) -> None:
        list_type_connection = []
        list_COMs = []
        list_baud = []
        dict_modbus_clients = {}
        self.clients.clear()
        for device in self.dict_active_device_class.values():
            list_type_connection.append(device.get_type_connection())
            list_COMs.append(device.get_COM())
            list_baud.append(device.get_baud())
        for i in range(len(list_baud)):
            if list_type_connection[i] == "serial":
                ser = serial.Serial(list_COMs[i], int(list_baud[i]))
                self.clients.append(ser)
            if list_type_connection[i] == "modbus":
                if list_COMs[i] in dict_modbus_clients.keys():
                    # если клиент был создан ранее, то просто добавляем ссылку на него
                    self.clients.append(dict_modbus_clients[list_COMs[i]])
                else:  # иначе создаем новый клиент и добавляем в список клиентов и список модбас клиентов
                    dict_modbus_clients[list_COMs[i]] = ModbusSerialClient(
                        method='rtu', port=list_COMs[i], baudrate=int(list_baud[i]), stopbits=1, bytesize=8, parity='E', timeout=0.3, retries=1, retry_on_empty=True)
                    self.clients.append(dict_modbus_clients[list_COMs[i]])
            if list_type_connection[i] != "modbus" and list_type_connection[i] != "serial":
                print("нет такого типа подключения")
            print(self.clients)

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
                break
        return status

    # функция записывает параметры во временный текстовый файл в ходе эксперимента, если что-то прервется, то данные не будут потеряны, после окончания эксперимента файл вычитывается и перегоняется в нужные форматы
    def write_parameters_to_file(self, name_device, text):
        with open(self.buf_file, "a") as file:
            file.write(str(name_device) + str(text) + "\n\r")
        pass


if __name__ == "__main__":
    lst1 = ["Maisheng"]
    lst4 = ["Maisheng"]
    lst2 = ["Lock in"]
    lst = ["Maisheng", "Lock in", "fdfdfdf", "самый крутой прибор на свете"]
    app = QtWidgets.QApplication(sys.argv)
    a = installation_class()
    a.reconstruct_installation(lst2)
    a.show_window_installation()
    sys.exit(app.exec_())


# pyuic5 name.ui -o name.py
