from interface.installation_window import Ui_Installation
import sys
import copy
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
from interface.save_repeat_set_window import save_repeat_set_window
import save_in_file
from enum import Enum


class type_save_file(Enum):
    txt = 1
    excel = 2
    origin = 3


class installation_class():
    def __init__(self) -> None:
        self.pbar_percent = 0
        self.way_to_save_file = False
        self.type_file_for_result = type_save_file.txt

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

        self.repeat_experiment = 1
        self.repeat_meas = 1
        self.way_to_save_fail = None

    def reconstruct_installation(self, current_installation_list):
        # print(current_installation_list)
        proven_device = []
        number_device = 1
        for key in current_installation_list:  # создаем классы переданных приборов
            try:
                # self.dict_active_device_class[key+str(number_device)] = self.dict_device_class[key](
                # current_installation_list, self, name=(key+str(number_device)))
                self.dict_active_device_class[key + str(number_device)] = self.dict_device_class[key](
                    name=(key+str(number_device)), installation_class=self)

                print(self.dict_active_device_class[key + str(number_device)])
                # словарь,показывающий статус готовности приборов, запуск установки будет произведен только если все девайсы имееют статус true
                self.dict_status_active_device_class[key +
                                                     str(number_device)] = False
                proven_device.append(key+str(number_device))
                number_device = number_device+1
            except:
                print("под прибор |" + key + "| не удалось создать класс")

        self.current_installation_list = proven_device
        current_installation_list = self.current_installation_list

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

        self.installation_window.way_save_button.clicked.connect(
            lambda: self.set_way_save())

        '''
		for i in range(len(current_installation_list)):
			self.installation_window.change_device_button[current_installation_list[0]].clicked.connect(lambda : self.testable(i))
		'''
        self.installation_window.start_button.clicked.connect(
            lambda: self.experiment_start())
        self.installation_window.start_button.setStyleSheet(
            "background-color: rgb(255, 127, 127);")
        self.installation_window.pause_button.clicked.connect(
            lambda: self.pause_exp())
        self.installation_window.cancel_button.clicked.connect(
            lambda: self.stoped_experiment())

        print("реконструирован класс установки")

    def pause_exp(self):
        pass

    def stoped_experiment(self):
        self.stop_experiment = True

    def testable(self, device):
        # print("кнопка настройки нажата, устройство -" + str(device))
        # окно настройки

        if not self.is_experiment_running():
            for client in self.clients:
                try:
                    client.close()
                except:
                    print(
                        "не удалось закрыть клиент связи, скорее всего, этого не требовалось")
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
        # print("Настройки прибора " + str(name_device) +" переданы классу установка, статус - ", status_parameters)
        if status_parameters == True:
            self.installation_window.verticalLayoutWidget[name_device].setStyleSheet(
                "background-color: rgb(180, 220, 180);")
            self.dict_status_active_device_class[name_device] = True
            self.show_parameters_of_device_on_label(
                name_device, list_parameters)
        else:
            self.installation_window.verticalLayoutWidget[name_device].setStyleSheet(
                "background-color: rgb(255, 140, 140);")
            self.dict_status_active_device_class[name_device] = False
            self.installation_window.label[name_device].setText("Не настроено")

        # ---------------------------
        self.analyse_signals()
        self.separate_by_trigger()
        print("подписчики", name_device, " - ",
              self.get_subscribers([name_device], name_device))
        # ---------------------------
        if self.is_all_device_settable():

            if self.analyse_com_ports() or True:
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

    def get_signal_list(self, name_device) -> tuple:
        buf_list = []
        for i in self.current_installation_list:
            if i != name_device:
                buf_list.append(i)

        return buf_list

    def experiment_start(self):
        # TODO проверка на тип устойств в установке, + добавить количествво шагов для измерений
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

                # print("старт эксперимента")
                self.repeat_experiment = int(
                    self.installation_window.repeat_exp_enter.currentText())
                self.repeat_meas = int(
                    self.installation_window.repeat_measurement_enter.currentText())
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

    def name_to_class(self, name):
        for dev in self.dict_active_device_class.keys():
            if name == dev:
                return self.dict_active_device_class[dev]
        return False

    def separate_by_trigger(self):
        '''разделяет приборы в установке по типу триггеров и создает два отдельных массива'''
        self.timer_signals_list = []
        self.other_signals_list = []
        for name in self.current_installation_list:
            try:
                sourse = self.dict_active_device_class[name].get_trigger()
            except:
                continue

            if sourse == "Таймер":  # если триггером является таймер, то добавляем этот прибор в соответствующий список
                self.timer_signals_list.append(name)
            elif sourse == "Внешний сигнал":
                self.other_signals_list.append(name)
            else:
                pass
                # print("прибор ", name, " не настроен")

    def analyse_signals(self):
        '''определяет зацикливания по сигналам и выдает предупреждение о бесконечном эксперименте'''
        first_array = copy.deepcopy(self.current_installation_list)
        name = []
        sourse = []
        for dev in first_array:
            name.append(dev)
        i = 0
        sourse_lines = []
        array = name

        # потенциально "проблемные приборы, которые могут работать бесконечно"
        mark_device_number = []
        for device in self.dict_active_device_class.values():
            print(device.get_trigger(), device.get_steps_number())
            if device.get_trigger() == "Таймер" and device.get_steps_number() == False:
                mark_device_number.append(device)
                if len(mark_device_number) >= 2:
                    print("бесконечный эксперимент", mark_device_number)
                    message = "приборы "
                    for n in mark_device_number:
                        message = message + n.get_name() + " "
                    self.add_text_to_log(
                        message + "будут работать бесконечно", status="err")
                    break  # два прибора, у которых тригер таймер, и условие остановки неактивные другие приборы будут работать бесконечно, предупреждаем об этом

        while i < len(array):  # формируем линии источников
            sourse = []
            for dev in array:
                s = self.name_to_class(name=dev)
                if s is not False:
                    if s.get_steps_number() == "Пока активны другие приборы":
                        s = s.get_trigger_value()
                    else:
                        s = False
                sourse.append(s)
            i += 1
            array = sourse
            sourse_lines.append(array)
            # print("линия источников", i, array)

        dev_in_cycle = []
        buf_dev = []
        for name, i in zip(name, range(len(sourse_lines))):
            if name not in dev_in_cycle:
                buf_dev.append(name)
                for sourses in sourse_lines:
                    if name == sourses[i]:
                        print("зацикливание по ветке", name, buf_dev)
                        message = "зацикливание по ветке "
                        for n in buf_dev:
                            message = message + n + " "
                        self.add_text_to_log(
                            message + "эксперимент будет продолжаться бесконечно", status="err")
                        for h in buf_dev:
                            dev_in_cycle.append(h)
                        break
                    buf_dev.append(sourses[i])
                buf_dev = []
        self.set_priority()

    def set_priority(self):
        # создается два массива, с таймерами и с другими источниками
        self.separate_by_trigger()
        i = 1

        for device in self.timer_signals_list:  # задаем приоритеты приборам, работающим по таймеру
            self.name_to_class(device).set_priority(i)
            i += 1

        i = 1
        for device in self.other_signals_list:  # задаем приоритеты приборам, работающим по сигналам не от таймера
            self.name_to_class(device).set_priority(i)
            i += 1

        # проводим анализ на предмет зацикливания, если оно обнаружено, то необходимо установить флаг готовности одного прибора из цикла, чтобы цикл начался.
        names = copy.deepcopy(self.current_installation_list)
        sourse = []
        i = 0
        sourse_lines = []
        array = names
        while i < len(array):  # формируем линии источников
            sourse = []
            for dev in array:
                s = self.name_to_class(name=dev)
                if s is not False:
                    if s.get_trigger() == "Внешний сигнал":
                        s = s.get_trigger_value()
                    else:
                        s = False
                sourse.append(s)
            i += 1
            array = sourse
            sourse_lines.append(array)
            # print("линия источников", i, array)

        dev_in_cycle = []
        buf_dev = []
        for name, i in zip(names, range(len(sourse_lines))):
            if name not in dev_in_cycle:
                buf_dev.append(name)
                for sourses in sourse_lines:
                    if name == sourses[i]:
                        # print("зацикливание по ветке", name, buf_dev)
                        # При старте эксперимента этот прибор ответит, что должен делать шаг
                        self.name_to_class(name).set_status_step(True)
                        for h in buf_dev:
                            dev_in_cycle.append(h)
                        break
                    buf_dev.append(sourses[i])
                buf_dev = []
        print("имя \t", "триг\t", "исттриг\t", "приор\t", "статус")
        for name in self.current_installation_list:
            print(name, "\t", self.name_to_class(name).get_trigger(), "\t", self.name_to_class(name).get_trigger_value(
            ), "\t", self.name_to_class(name).get_priority(), "\t", self.name_to_class(name).get_status_step())

    def calculate_exp_time(self) -> str:
        '''оценивает продолжительность эксперимента, возвращает результат в секундах'''
        max_exp_time = 0
        for device in self.dict_active_device_class.values():
            buf_time = device.get_steps_number()
            if buf_time > max_exp_time:
                max_exp_time = buf_time
        return max_exp_time

    def get_subscribers(self, signals, trig) -> tuple:
        '''возвращает массив имен подписчиков данного сигнала-триггера и всех последующих подписчиков, рекурсивная функция'''
        # print("---вошли----", signals)

        subscribers = signals

        for device in self.dict_active_device_class.values():
            sourse = device.get_trigger_value()
            # print(device.get_name(), sourse)
            if device.get_name() in signals:
                continue
            for sig in signals:
                if sourse == sig:
                    subscribers.append(device.get_name())
                    self.get_subscribers(subscribers, sourse)
        # print("---вышли---", subscribers)
        ret_sub = []
        for dev in subscribers:
            if trig == dev:
                continue
            ret_sub.append(dev)

        return ret_sub

    def exp_th(self):
        status = True
        self.add_text_to_log("настройка приборов.. ")
        print("запущен поток эксперимента")

        for dev in self.dict_active_device_class.values():
            ans = dev.action_before_experiment()
            if ans == False:

                print("ошибка при настройке " +
                      dev.get_name() + " перед экспериментом")
                # -----------РАСКОММЕНТИРОВАТЬ ПОСЛЕ ОТЛАДКИ---------------
                # status = False
                # break
                # --------------------------------------------------------
            self.add_text_to_log(dev.get_name() + " настроен")

        error = not status  # флаг ошибки, будет поднят при ошибке во время эксперимента
        error = False
        if error is False:
            max_exp_time = self.calculate_exp_time()

            start_exp_time = time.time()
            self.installation_window.pbar.setMinimum(0)
            self.installation_window.pbar.setMaximum(100)

            min_priority = len(self.current_installation_list)
            priority = 1
            for device in self.dict_active_device_class.values():
                device.am_i_should_do_step = False
                device.set_priority(priority)
                device.am_i_active_in_experiment = True
                device.number_meas = 0
                device.previous_step_time = time.time()
                device.pause_time = device.get_trigger_value()
                priority += 1

            self.stop_experiment = False
        # -------------------------------
        for device in self.dict_active_device_class.values():
            pass
            # print(device.priority)
            # print(device.pause_time)

        # ------------------------------------------
        number_active_device = 0
        target_execute = False
        sr = time.time()
        while not self.stop_experiment and error == False:
            # ----------------------------
            if time.time() - sr > 2:
                sr = time.time()
                print("активных приборов - ", number_active_device)
            # -----------------------------------

            self.pbar_percent = (
                ((time.time() - start_exp_time)/max_exp_time))*100

            number_active_device = 0
            number_device_which_act_while = 0
            for device in self.dict_active_device_class.values():
                if device.get_steps_number() == False:
                    number_device_which_act_while += 1

                if device.am_i_active_in_experiment:
                    number_active_device += 1
                    if device.get_trigger() == "Таймер":
                        if time.time() - device.previous_step_time >= device.pause_time:
                            device.previous_step_time = time.time()
                            device.set_status_step(True)

            if number_active_device == 0:
                '''остановка эксперимента, нет активных приборов'''
                self.stop_experiment = True
                print("не осталось активных приборов, эксперимент остановлен")
            if number_device_which_act_while == number_active_device and number_active_device == 1:
                '''если активный прибор один и он работает, пока работают другие, то стоп'''
                self.stop_experiment = True

            target_execute = False
            target_priority = min_priority+1
            for device in self.dict_active_device_class.values():
                if device.get_status_step() == True:
                    print(device.get_name(), "приоритет", device.get_priority())
                    if device.get_priority() < target_priority:
                        target_execute = device
                        target_priority = device.get_priority()

            if target_execute is not False:
                target_execute.set_status_step(False)
                if target_execute.on_next_step() is not False:
                    target_execute.number_meas += 1
                    print("кол-во измерений", target_execute.get_name(),
                          target_execute.number_meas)
                    repeat_counter = 0
                    while repeat_counter < self.repeat_meas:
                        repeat_counter += 1
                        ans, param, step_time = target_execute.do_meas()

                        self.write_data_to_buf_file("", addTime=True)
                        for param in param:
                            self.write_data_to_buf_file(
                                message=str(param) + "\t")
                        self.write_data_to_buf_file(message="\n")

                        if ans == device_response_to_step.Step_done:
                            pass
                        if ans == device_response_to_step.Step_fail:
                            target_execute.am_i_active_in_experiment = False
                            break

                else:
                    target_execute.am_i_active_in_experiment = False

                if target_execute.get_steps_number() is not False:
                    if target_execute.number_meas >= target_execute.get_steps_number():
                        target_execute.am_i_active_in_experiment = False

                subscribers = self.get_subscribers(
                    [target_execute.get_name()], target_execute.get_name())
                print(target_execute.get_name(), "подписчики", subscribers)

                if target_execute.am_i_active_in_experiment == False:
                    '''останавливаем всех подписчиков'''
                    for subscriber in subscribers:
                        self.name_to_class(
                            subscriber).am_i_active_in_experiment = False

                else:
                    for subscriber in subscribers:
                        '''передаем сигнал всем подписчикам'''
                        self.name_to_class(subscriber).set_status_step(True)

                for device in self.dict_active_device_class.values():
                    if target_execute == device:
                        continue
                    else:
                        if device.get_priority() > target_execute.get_priority():
                            device.increment_priority()
                target_execute.set_priority(min_priority)

   # -----------------------------------------------------------

        if error:
            self.add_text_to_log("Эксперимент прерван из-за ошибки", "err")
        else:
            self.add_text_to_log("Эксперимент завершен")

        self.save_results()

        self.pbar_percent = 0  # сбрасываем прогресс бар
        # ------------------подготовка к повторному началу эксперимента---------------------
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
                    # print(com, baud)
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
                ser = serial.Serial(list_COMs[i], int(list_baud[i]), timeout=1)
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

    def save_results(self):
        if self.type_file_for_result != False:  # если выбран путь для сохранения результатов
            print("путь сохранения результата", self.way_to_save_file)
            if self.type_file_for_result == type_save_file.origin:
                # TODO: сохранить результат в ориджин
                print("выбран текстовый тип origin для сохранения результата")
                pass
            elif self.type_file_for_result == type_save_file.excel:
                # TODO: сохранить результат в эксель
                print("выбран тип файла excel для сохранения результата")
                pass
            elif self.type_file_for_result == type_save_file.txt:
                # TODO: сохранить результат в текстовый
                print("выбран текстовый тип файла для сохранения результата")
                pass
            else:
                # TODO: сохранить результат в текстовый
                print(
                    "тип файла для сохранения результата не определен, сохраняем в txt")
            # self.buf_file - переменная хранит путь к файлу с данными эксперимента, парсим его

            with open(self.buf_file, "r") as file:
                input_strings = file.readlines()
                result = save_in_file.process_input_strings(input_strings)
                save_in_file.print_instruments_data(result)
        else:
            # TODO: попросить пользователя ваыбрать путь для сохранения данных. блокирующая функция
            '''попросить пользователя выбрать путь для сохранения'''

    def set_way_save(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, ans = QtWidgets.QFileDialog.getSaveFileName(self.installation_window,
                                                              "Save File", "", "Text Files(*.txt);; Книга Excel (*.xlsx);;Origin (*.opju)", options=options)

        if fileName:
            if ans == "Origin (*.opju)":
                self.type_file_for_result = type_save_file.origin
                print("origin added")
                pass
            elif ans == "Книга Excel (*.xlsx)":
                self.type_file_for_result = type_save_file.excel
                print("excel added")
                pass
            else:
                self.type_file_for_result = type_save_file.txt
                print("txt added")
                pass

            print(fileName)
            self.way_to_save_file = fileName
            self.installation_window.way_save_text.setText(str(fileName))
        else:
            self.type_file_for_result = False


if __name__ == "__main__":

    lst1 = ["Lock in"]
    lst4 = ["Maisheng"]
    lst2 = ["Lock in", "Lock in",
            "Lock in", "Lock in",
            "Lock in"]
    lst = ["Maisheng", "Lock in"]
    app = QtWidgets.QApplication(sys.argv)
    a = installation_class()
    a.reconstruct_installation(lst)
    a.show_window_installation()
    sys.exit(app.exec_())


# pyuic5 name.ui -o name.py
