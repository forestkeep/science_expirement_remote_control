from interface.installation_window import Ui_Installation
import sys
import copy
from PyQt5 import QtCore, QtGui, QtWidgets
from maisheng_power_class import maishengPowerClass
from relay_class import relayPr1Class
from sr830_class import sr830Class
from pymodbus.client import ModbusSerialClient
from pymodbus.utilities import computeCRC
import serial.tools.list_ports
from datetime import datetime
import time
from Classes import ch_response_to_step
from mnipi_e7_20_class import mnipiE720Class
import threading
from PyQt5.QtCore import QTimer
from interface.save_repeat_set_window import save_repeat_set_window
from interface.About_autors_window import AboutAutorsDialog
from enum import Enum
from Parse_data import process_and_export, type_save_file
from rigol_dp832a import rigolDp832aClass
from AKIP2404 import akip2404Class
from interface.installation_check_devices import installation_Ui_Dialog
import qdarktheme
import os
import logging
from online_graph import GraphWindow
from Classes import not_ready_style_border, not_ready_style_background, ready_style_border, ready_style_background, warning_style_border, warning_style_background


logger = logging.getLogger(__name__)


class exp_th_connection():
    def __init__(self) -> None:
        self.flag_show_message = False
        self.message = ""
        self.message_status = message_status.info
        self.is_message_show = False
        self.ask_save_the_results = False
        self.is_update_pbar = False
        self.is_measurement_data_updated = False

class message_status(Enum):
    info = 1
    warning = 2
    critical = 3

class installation_class():
    def __init__(self) -> None:
        self.exp_th_connect = exp_th_connection()
        logger.debug("запуск установки")

        self.way_to_save_installation_file = None
        self.save_results_now = False

        self.is_window_save_dialog_showing = False
        self.is_debug = False
        self.down_brightness = False
        self.bright = 50
        self.pause_flag = False
        self.is_experiment_endless = False
        self.pbar_percent = 0
        self.way_to_save_file = False
        self.type_file_for_result = type_save_file.txt

        self.timer_for_pause_exp = QTimer()
        self.timer_for_pause_exp.timeout.connect(
            lambda: self.pause_actions())

        self.timer_for_connection_main_exp_thread = QTimer()
        self.timer_for_connection_main_exp_thread.timeout.connect(
            lambda: self.connection_two_thread())

        self.dict_device_class = {
            "Maisheng": maishengPowerClass, "SR830": sr830Class, "PR": relayPr1Class, "DP832A": rigolDp832aClass, "АКИП-2404":akip2404Class, "E7-20MNIPI": mnipiE720Class}
        self.dict_active_device_class = {}
        # self.dict_status_active_device_class = {}
        self.clients = []  # здесь хранятся классы клиентов для всех устройств, они создаются и передаются каждому устройству в установке
        # ключ, который разрешает старт эксперимента
        self.key_to_start_installation = False
        # поток в котором идет экспер мент, запускается после настройки приборов и нажатия кнопки старт
        self.experiment_thread = None
        self.stop_experiment = False  # глобальная переменная для остановки потока

        self.repeat_experiment = 1
        self.repeat_meas = 1
        self.way_to_save_fail = None

    def reconstruct_installation(self, current_installation_list, **kwargs):
        logger.debug(current_installation_list)
        proven_device = []
        number_device = 1
        self.dict_active_device_class = {}
        self.graph_window = None

        self.measurement_parameters = {}

        for key in current_installation_list:  # создаем классы переданных приборов
            try:
                self.dict_active_device_class[key + "_" + str(number_device)] = self.dict_device_class[key](
                    name=(key+"_"+str(number_device)), installation_class=self)

                proven_device.append(key + "_" + str(number_device))
                number_device = number_device+1
            except:
                pass
                logger.debug("под прибор |" + key + "| не удалось создать класс")

        self.current_installation_list = proven_device
        current_installation_list = self.current_installation_list
        self.installation_window = Ui_Installation()
        self.installation_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        logger.debug(f"{self.dict_active_device_class=} {self=}")
        self.installation_window.setupUi(
            self.installation_window, self, self.dict_active_device_class)
        logger.debug(f"создан класс окна установки")

        
        self.installation_window.way_save_button.clicked.connect(lambda: self.set_way_save())
        self.installation_window.start_button.clicked.connect(lambda: self.push_button_start())
        self.installation_window.start_button.setToolTip("запуск эксперимента будет доступен \n после настройки всех приборов \n в установке ")
        self.installation_window.start_button.setStyleSheet("QToolTip { background-color: lightblue; color: black; border: 1px solid black; }")
        self.installation_window.start_button.setStyleSheet(not_ready_style_background)
        self.installation_window.start_button.setText("Старт")
        self.installation_window.pause_button.clicked.connect(lambda: self.pause_exp())
        self.installation_window.pause_button.setStyleSheet(not_ready_style_background)
        self.installation_window.about_autors.triggered.connect(lambda: self.show_about_autors())
        self.installation_window.open_graph_button.clicked.connect(lambda: self.open_graph_in_exp())
        self.installation_window.installation_close_signal.connect(self.close_other_windows)
        

        self.installation_window.save_installation_button.triggered.connect(
            lambda: self.push_button_save_installation())
        self.installation_window.save_installation_button_as.triggered.connect(
            lambda: self.push_button_save_installation_as())
        self.installation_window.open_installation_button.triggered.connect(
            lambda: self.push_button_open_installation())
        
        self.installation_window.add_device_button.triggered.connect(
            lambda: self.add_new_device())
        
        self.installation_window.develop_mode.triggered.connect(lambda: self.change_check_debug())

        self.installation_window.clear_log_button.clicked.connect(
            lambda: self.clear_log())
        self.installation_window.clear_log_button.setToolTip("Очистить лог")
        self.installation_window.clear_log_button.setStyleSheet("QToolTip { background-color: lightblue; color: black; border: 1px solid black; }")
        self.set_state_text("Ожидание настройки приборов")
        logger.debug("реконструирован класс установки")

    def change_check_debug(self):
        if not self.is_experiment_running():
            if not self.is_debug:
                self.is_debug = True
                self.installation_window.develop_mode.setText("Выкл режим разработчика")
                self.add_text_to_log("Режим разработчика включен. В этом режиме корректность показаний с приборов не гарантируется",status="war")
            else:
                self.installation_window.develop_mode.setText("Вкл режим разработчика")
                self.add_text_to_log("Режим разработчика выключен")
                self.is_debug = False
            
            for dev in self.dict_active_device_class.values():
                dev.set_debug(self.is_debug)

        self.preparation_experiment()

    def get_channel_widget(self, name_device, num_channel):
        return self.installation_window.devices_lay[name_device].channels[num_channel]
    
    def get_device_widget(self, name_device):
        return self.installation_window.devices_lay[name_device]

    def clear_log(self):
        self.installation_window.log.clear()

    def set_state_text(self, text):
        self.installation_window.label_state.setText(text)

    def pause_exp(self):
        if self.is_experiment_running():
            if self.pause_flag:
                self.pause_flag = False
                self.installation_window.pause_button.setText("Пауза")
                self.timer_for_pause_exp.stop()
                self.installation_window.pause_button.setStyleSheet(
                    ready_style_background)
                try:
                    self.start_exp_time += time.time() - self.pause_start_time
                except:
                    pass

            else:
                self.installation_window.pause_button.setText("Возобновить")
                self.pause_flag = True
                self.set_state_text("Ожидание продолжения...")
                self.timer_for_pause_exp.start(50)
                self.pause_start_time = time.time()

    def pause_actions(self):
        '''функция срабатывает по таймеру во время паузы эксперимента'''

        step = 15
        if self.down_brightness:
            self.bright = self.bright - step
            if self.bright < 30:
                self.bright = 0
                self.down_brightness = False
        else:
            self.bright += step
            if self.bright > 255:
                self.bright = 255
                self.down_brightness = True

        style = "background-color: rgb(" + str(self.bright) + \
            "," + "255" + "," + str(self.bright) + ");"

        self.installation_window.pause_button.setStyleSheet(
            style)

    def stoped_experiment(self):
        self.stop_experiment = True
        self.set_state_text("Остановка...")

    def set_state_ch(self, device, num_ch, state):
        logger.debug(f"передаем состояние {state} канала {num_ch} прибору {device}")
        self.dict_active_device_class[device].set_state_ch(num_ch, state)
        self.preparation_experiment()

    def show_window_installation(self):
        logger.debug(f"вызвана функция показать окно установки")
        self.installation_window.show()

    def show_information_window(self, message):
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Info")
        msg.setText(message)
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.exec_()

    def show_warning_window(self, message):
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Warning")
        msg.setText(message)
        # { NoIcon, Question, Information, Warning, Critical }
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.exec_()

    def show_critical_window(self, message):
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Error")
        msg.setText(message)
        # { NoIcon, Question, Information, Warning, Critical }
        msg.setIcon(QtWidgets.QMessageBox.Critical)
        msg.exec_()

    def close_window_installation(self):
        # print("закрыть окно установки")
        try:
            self.installation_window.close()
            self.installation_window.setParent(None)
            logger.debug("окно установки закрыто")
        except:
            pass

    def message_from_device_settings(self, name_device, num_channel, status_parameters, list_parameters):
        logger.debug(f"Настройки канала {num_channel}  прибора " + str(name_device) + " переданы классу установка, статус - " + str(status_parameters))

        if status_parameters == True:
            self.set_border_color_device(device_name=name_device, status_color = ready_style_border, num_ch=num_channel)
            self.show_parameters_of_device_on_label(name_device, num_channel, list_parameters)
        else:
            self.set_border_color_device(device_name=name_device, status_color = not_ready_style_border, num_ch=num_channel)

            self.get_channel_widget(
                name_device, num_channel).label_settings_channel.setText("Не настроено")
        self.dict_active_device_class[name_device].set_status_settings_ch(
            num_channel, status_parameters)
        
        self.preparation_experiment()

    def preparation_experiment(self):
        logger.debug("подготовка к эксперименту")
        #print("подготовка к эксперименту")
        self.key_to_start_installation = False
        
        if self.is_all_device_settable():
            logger.debug("все каналы имеют статус настроен")
            if self.analyse_com_ports():
                
                # если оказались в этой точке, значит приборы настроены корректно и нет проблем с конфликтами ком портов, если подключение не будет установлено, то ключ снова будет сброшен
                self.confirm_devices_parameters()
                self.set_priorities()
                self.cycle_analyse()
                self.create_clients()
                self.set_clients_for_device()
                self.analyse_endless_exp()
                self.key_to_start_installation = True

        if self.key_to_start_installation == True:
            self.installation_window.start_button.setStyleSheet(
                ready_style_background)
        else:
            self.installation_window.start_button.setStyleSheet(
                not_ready_style_background)
        self.installation_window.start_button.setText("Старт")

    def confirm_devices_parameters(self):
        '''подтверждаем параметры приборам и передаем им настроенные и созданные клиенты для подключения'''
        for device in self.dict_active_device_class.values():
            device.confirm_parameters()

    def add_new_channel(self, device, num_ch):
        if self.is_experiment_running() == False:
            for ch in self.dict_active_device_class[device].channels:
                if ch.number == num_ch:
                    if ch.is_ch_seted():
                        pass
                    else:
                        self.set_border_color_device(device_name=device, status_color = not_ready_style_border, num_ch=num_ch)
            #print(f"добавлен новый канал {num_ch} устройство {device}")
        else:
            self.add_text_to_log("Запрещено добавлять или отключать канал во время эксперимента",status="war")

    def set_clients_for_device(self):  # передать созданные клиенты приборам
        for device, client in zip(self.dict_active_device_class.values(), self.clients):
            if client is not False:
                device.set_client(client)

    def message_from_device_status_connect(self, answer, name_device):
        if answer == True:
            self.add_text_to_log(
                name_device + " - соединение установлено")
        else:
            self.add_text_to_log(
                name_device + " - соединение не установлено, проверьте подлючение", status="err")
            self.set_border_color_device(device_name=name_device, status_color = not_ready_style_border)
            self.installation_window.start_button.setStyleSheet(
                not_ready_style_background)
            self.installation_window.start_button.setText("Старт")
            # статус прибора ставим в не настроенный
            # self.dict_status_active_device_class[name_device] = False
            self.key_to_start_installation = False  # старт экспериепнта запрещаем

    def is_experiment_running(self) -> bool:
        return self.experiment_thread is not None and self.experiment_thread.is_alive()

    def get_signal_list(self, name_device, num_ch) -> tuple:
        buf_list = []
        # print(name_device, num_ch)
        for dev in self.dict_active_device_class.values():
            for ch in dev.channels:
                if dev.name != name_device or ch.number != num_ch:
                    if ch.is_ch_active():
                        buf_list.append([dev.name, ch.number])
        return buf_list
        
    def write_data_to_buf_file(self, message, addTime=False):
        message = f"{datetime.now().strftime('%H:%M:%S') + ' ' if addTime else ''}{message.replace('.', ',')}"
        with open(self.buf_file, "a") as file:
            file.write(str(message))

    def connection_two_thread(self):
        '''функция для связи основного потока и потока эксперимента, поток эксперимента выставляет значения/флаги/сообщения, а основной поток их обрабатывает'''
        if self.is_experiment_running():
            #self.installation_window.open_graph_button.setEnabled(True)
            self.timer_for_connection_main_exp_thread.start(1000)
            self.installation_window.label_time.setText("")

            if not self.pause_flag:
                if self.exp_th_connect.is_update_pbar == True:
                    self.pbar_percent = (((time.time() - self.start_exp_time)/self.max_exp_time))*100
                else:
                    self.pbar_percent = 0
                if self.max_exp_time - (time.time() - self.start_exp_time) > 0:
                    min = int( (self.max_exp_time - (time.time() - self.start_exp_time))/60 )
                    sec = int( (self.max_exp_time - (time.time() - self.start_exp_time))%60 )
                else:
                    min = 0
                    sec = 0
                self.installation_window.label_time.setText(f"Осталось {min}:{sec} мин")
                self.update_pbar()
            else:
                self.installation_window.label_time.setText("Осталось -- мин")
            self.show_th_window()


            if self.exp_th_connect.is_measurement_data_updated and self.graph_window is not None:
                self.exp_th_connect.is_measurement_data_updated = False
                self.graph_window.update_dict_param(self.measurement_parameters)
        else:
            self.timer_for_connection_main_exp_thread.stop()
            self.installation_window.pbar.setValue(0)
            self.preparation_experiment()
            self.installation_window.label_time.setText("")

    def show_th_window(self):
        if self.exp_th_connect.flag_show_message == True:
            self.exp_th_connect.flag_show_message = False
            if self.exp_th_connect.message_status == message_status.info:
                self.show_information_window(self.exp_th_connect.message)
            elif self.exp_th_connect.message_status == message_status.warning:
                self.show_warning_window(self.exp_th_connect.message)
            elif self.exp_th_connect.message_status == message_status.critical:
                self.show_critical_window(self.exp_th_connect.message)
            self.exp_th_connect.is_message_show = True
        if self.exp_th_connect.ask_save_the_results:
            self.exp_th_connect.ask_save_the_results = False
            self.save_results_now = True
            self.set_way_save()

    def update_pbar(self) -> None:
        self.installation_window.pbar.setValue(int(self.pbar_percent))

    def name_to_class(self, name):
        '''возвращает экземпляр класса прибора'''
        for dev in self.dict_active_device_class.keys():
            if name == dev:
                return self.dict_active_device_class[dev]
        return False

    def analyse_endless_exp(self) -> bool:
        '''определяет зацикливания по сигналам и выдает предупреждение о бесконечном эксперименте'''

        '''эксперимент будет бесконечен:
        - в случае, если есть минимум 2 канала с тригером таймером и количеством шагов, равном "пока активны другие приборы"
        - в случае, если в зацикленной линии ни один прибор не имеет конечное количество шагов"'''
        sourses = self.cycle_analyse()
        if sourses:
            for sourse in sourses:
                first = sourse

        first_array = copy.deepcopy(self.current_installation_list)
        name = []
        sourse = []
        for dev in first_array:
            name.append(dev)
        i = 0
        sourse_lines = []
        array = name
        cycle_device = []

        # ----------анадиз по таймерам-----------------------
        experiment_endless = False
        mark_device_number = []
        for device, ch in self.get_active_ch_and_device():
                    if device.get_trigger(ch.number) == "Таймер" and device.get_steps_number(ch.number) == False:
                        mark_device_number.append(
                            device.get_name() + str(ch.number))
                        if len(mark_device_number) >= 2:
                            # print("бесконечный эксперимент", mark_device_number)
                            message = "каналы "
                            for n in mark_device_number:
                                # cycle_device.append(n.get_name())
                                message = message + n + " "
                            message = message + "будут работать бесконечно"
                            self.add_text_to_log(
                                message, status="err")
                            experiment_endless = True
                            break
        # --------------------------------------------------

        # -----------------анализ других случаев------------
        sourses = self.cycle_analyse()
        if sourses:
            #print("зацикливание:", sourses)
            for sourse in sourses:
                dev, ch = sourse.split()[0], sourse.split()[1]
                first_ch = ch[3:4:1]
                first_dev = self.name_to_class(name=dev)
                branch = [sourse]

                subscriber_dev = first_dev
                subscriber_ch = first_ch
                while True:
                    # print(subscriber_dev)
                    ans = subscriber_dev.get_trigger_value(subscriber_ch)
                    # print("подписчик",ans)
                    if ans is not False:
                        dev, ch = ans.split()[0], ans.split()[1]
                        subscriber_ch = ch[3:4:1]
                        subscriber_dev = self.name_to_class(name=dev)
                        branch.append(ans)
                    else:
                        break

                    # print(subscriber_dev.get_name(),subscriber_dev.get_steps_number(subscriber_ch))
                    if subscriber_dev.get_steps_number(subscriber_ch) != False:
                        break

                    elif subscriber_dev == first_dev and subscriber_ch == first_ch:
                        experiment_endless = True
                        message = "зацикливание по ветке "
                        for n in branch:
                            message = message + n + " "
                        message += "эксперимент будет продолжаться бесконечно"
                        self.add_text_to_log(
                            message, status="err")
                        logger.debug("бесконечный эксперимент, зацикливание с бесконечным количеством шагов")
                        break  # прошли круг

        return experiment_endless

    def set_priorities(self):
        '''устаанвливает приоритеты в эксперименте всем активным каналам во всех приборах'''

        priority = 1
        for dev, ch in self.get_active_ch_and_device():
                    ch.set_priority(priority = priority)
                    priority += 1

    def get_sourse_line(self, line) -> list:
        out = []
        for c in line:
            if c != False:
                dev, ch = c.split()[0], c.split()[1]
                ch_num = ch[3:4:1]
                dev = self.name_to_class(name=dev)
                if dev.get_trigger(ch_num) == "Внешний сигнал":
                    s = dev.get_trigger_value(ch_num)
                else:
                    s = False
                out.append(s)
            else:
                out.append(False)
        return out

    def cycle_analyse(self):
        '''проводим анализ на предмет зацикливания, если оно обнаружено, то необходимо установить флаг готовности одного прибора из цикла, чтобы цикл начался.'''
        names = copy.deepcopy(self.current_installation_list)
        sourse = []
        i = 0
        sourse_lines = []
        array = names

        for dev, ch in self.get_active_ch_and_device():
                    if dev.get_trigger(ch.number) == "Внешний сигнал":
                        s = dev.get_trigger_value(ch.number)
                    else:
                        s = False
                    sourse.append(s)
        matrix_sourse = [copy.deepcopy(sourse)]
        while i < len(sourse):  # получаем матрицу источников сигналов с количеством столбцом равным количеству каналов в установке и количеством строк на 1 больше, чем столбцом
            matrix_sourse.append(self.get_sourse_line(matrix_sourse[i]))
            i += 1
        #for m in matrix_sourse:
        #    print(m)

        # ищем зацикливания, запоминаем первый элемент в столбце и идем по столбцу, если встретим такоц же элемент, то зацикливание обнаружено(кроме false)
        transposed_matrix = []

        for i in range(len(matrix_sourse[0])):
            transposed_row = []
            for row in matrix_sourse:
                transposed_row.append(row[i])
            transposed_matrix.append(transposed_row)

        setted_dev = []  # массмив для хранения источников, которые уже были обнаружены в зацикливании и для которых установлена готовность шага
        for row in (transposed_matrix):
            for i in range(1, len(row), 1):
                if row[0] == False or row[i] in setted_dev:
                    break
                if row[0] == row[i]:
                    #print("зацикливание по строке ", row)
                    setted_dev.append(row[0])
                    dev, ch = row[0].split()[0], row[0].split()[1]
                    ch_num = ch[3:4:1]
                    dev = self.name_to_class(name=dev)

                    dev.set_status_step(ch_num, True)
                    break
        return setted_dev

    def calculate_exp_time(self):
        '''оценивает продолжительность эксперимента, возвращает результат в секундах, если эксперимент бесконечно долго длится, то вернется ответ True. В случае ошибки при расчете количества секунд вернется False'''
        # проверить, есть ли бесконечный эксперимент, если да, то расчет не имеет смысла, и анализ в процессе выполнения тоже
        # во время эксперимента после каждого измерения пересчитывается максимальное время каждого прибора и выбирается максимум, от этого максимума рассчитывается оставшийся процент времени

        self.is_experiment_endless = self.analyse_endless_exp()
        if self.is_experiment_endless == True:
            return True  # вернем правду в случае бесконечного эксперимента

        max_exp_time = 0

        for device in self.dict_active_device_class.values():
            for ch in device.channels:
                buf_time = False
                if ch.is_ch_active():
                    trig = device.get_trigger(ch.number)
                    if trig == "Таймер":
                        steps = device.get_steps_number(ch.number)
                        if steps is not False:
                            buf_time = (steps * \
                                (device.get_trigger_value(
                                    ch.number) + ch.base_duration_step))*float(self.installation_window.repeat_measurement_enter.currentText())

                    elif trig == "Внешний сигнал":
                        # TODO: рассчитать время в случае срабатывания цепочек приборов. Найти корень цепочки и смотреть на его параметры, значение таймера и количество повторов, затем рассчитать длительность срабатывания цепочки и сравнить со значением таймера, вернуть наибольшее
                        continue
                    else:
                        continue

                if buf_time is not False:

                    if buf_time > max_exp_time:
                        max_exp_time = copy.deepcopy(buf_time)

        return max_exp_time

    def get_subscribers(self, signals, trig) -> tuple:
        '''возвращает массив пар [имя прибора, номер канала] подписчиков данного сигнала-триггера и всех последующих подписчиков, рекурсивная функция'''
        # print("---вошли----", signals)

        subscribers = signals
        for device, ch in self.get_active_ch_and_device():
                    if device.get_trigger(ch.number).lower() == "внешний сигнал":
                        stroka = device.get_trigger_value(ch.number)
                        # print(stroka)
                        sourse = [stroka.split()[0], int(
                            stroka.split()[1][-1])]
                        # print(device.get_name(), sourse)
                        if [device.get_name(), ch.number] in signals:
                            continue
                        for sig in signals:
                            if sourse == sig:
                                subscribers.append(
                                    [device.get_name(), ch.number])
                                self.get_subscribers(subscribers, sourse)
            # print("---вышли---", subscribers)
        ret_sub = []
        for dev in subscribers:
            if trig == dev:
                continue
            ret_sub.append(dev)

        return ret_sub

    def calc_last_exp_time(self):
        buf_time = []
        for device, ch in self.get_active_ch_and_device():
            if ch.am_i_active_in_experiment == True:
                trig = device.get_trigger(ch.number)
                if trig == "Таймер":
                    steps = device.get_steps_number(ch.number) - ch.number_meas 
                    if steps is not False:
                        t = steps * (device.get_trigger_value(ch.number) + ch.last_step_time)*float(self.installation_window.repeat_measurement_enter.currentText())                                                                                      
                        buf_time.append(t)
        self.max_exp_time = max(buf_time)+(time.time() - self.start_exp_time)
    
    def get_active_ch_and_device(self):
        for device in self.dict_active_device_class.values():
            for channel in device.channels:
                if channel.is_ch_active():
                    yield device, channel

    def exp_th(self):
        def update_parameters(data, entry, time):
            device, channel = entry[0].split()
            parameter_pairs = entry[1:]
            status = True

            for parameter_pair in parameter_pairs:
                name, value = parameter_pair[0].split('=')
                try:
                    value = float(value)
                except:
                    status = False
                    break
            if status:
                if device not in data:
                    data[device] = {}
                if channel not in data[device]:
                    data[device][channel] = {}
                
                for parameter_pair in parameter_pairs:
                    name, value = parameter_pair[0].split('=')
                    value = float(value)
                    
                    if name not in data[device][channel]:
                        data[device][channel][name] = []
                    data[device][channel][name].append(value)

                if 'time' not in data[device][channel]:
                    data[device][channel]['time'] = []
                data[device][channel]['time'].append(time)
            return status, data




        status = True
        self.start_exp_time = time.time()
        self.max_exp_time = 10000
        self.installation_window.pbar.setMinimum(0)
        self.installation_window.pbar.setMaximum(100)
        self.add_text_to_log("настройка приборов.. ")
        logger.debug("запущен поток эксперимента")
        #print("запущен поток эксперимента")


        for dev, ch in self.get_active_ch_and_device():
                    #print(ch.number, "канал состояние")
                    ans = dev.action_before_experiment(ch.number)
                    if ans == False:
                        logger.debug("ошибка при настройке " + dev.get_name() + " перед экспериментом")
                        #print("ошибка при настройке " + dev.get_name() + " перед экспериментом")

                        if not self.is_debug:
                            status = False
                            self.set_state_text("Остановка, ошибка")
                            break

                        # --------------------------------------------------------

                    self.add_text_to_log(
                        dev.get_name() + " ch-" + str(ch.number) + " настроен")

        error = not status  # флаг ошибки, будет поднят при ошибке во время эксперимента
        # error = False
        # print(status, "статус")
        logger.debug(status, "статус")

        if error is False and self.stop_experiment == False:


            self.max_exp_time = self.calculate_exp_time()
            if self.max_exp_time == True:
                # эксперимент бесконечен
                pass
            elif self.max_exp_time == False:
                self.max_exp_time = 100000
                # не определено время

            #print("общее время эксперимента", self.max_exp_time)
            logger.debug("общее время эксперимента = "+ str(self.max_exp_time))

            self.start_exp_time = time.time()
            self.installation_window.pbar.setMinimum(0)
            self.installation_window.pbar.setMaximum(100)

            min_priority = 0
            priority = 1

            for device in self.dict_active_device_class.values():
                for ch in device.channels:
                    if ch.is_ch_active():
                        ch.am_i_active_in_experiment = True
                        ch.number_meas = 0
                        ch.previous_step_time = time.time()
                        ch.pause_time = device.get_trigger_value(ch.number)
                        priority += 1
                        min_priority+=1

        number_active_device = 0
        target_execute = False
        sr = time.time()
        self.exp_th_connect.is_update_pbar = True
        while not self.stop_experiment and error == False:

            if self.pause_flag:
                pass
                # TODO: пауза эксперимента. остановка таймеров
            else:
                self.set_state_text("Продолжение эксперимента")
                # ----------------------------
                if time.time() - sr > 2:
                    sr = time.time()
                    #print("активных приборов - ", number_active_device)
                # -----------------------------------
                
                number_active_device = 0
                number_device_which_act_while = 0

                for device, ch in self.get_active_ch_and_device():
                    if device.get_steps_number(ch.number) == False:
                        number_device_which_act_while += 1

                    if ch.am_i_active_in_experiment:
                        number_active_device += 1
                        if device.get_trigger(ch.number) == "Таймер":
                            if time.time() - ch.previous_step_time >= ch.pause_time:
                                ch.previous_step_time = time.time()
                                device.set_status_step(ch.number, True)

                if number_active_device == 0:
                    '''остановка эксперимента, нет активных приборов'''
                    logger.debug('остановка эксперимента, нет активных приборов')
                    self.set_state_text("Остановка эксперимента...")
                    self.stop_experiment = True
                    #print("не осталось активных приборов, эксперимент остановлен")
                if number_device_which_act_while == number_active_device and number_active_device == 1:
                    '''если активный прибор один и он работает, пока работают другие, то стоп'''
                    self.stop_experiment = True

                target_execute = False
                target_priority = min_priority+1
                for device in self.dict_active_device_class.values():
                    for ch in device.channels:
                        if ch.is_ch_active():
                            if device.get_status_step(ch.number) == True:
                                if ch.get_priority() < target_priority:
                                    target_execute = [device, ch]
                                    target_priority = ch.get_priority()

                if target_execute is not False:
                    device = target_execute[0]
                    ch = target_execute[1]
                    self.set_state_text(
                        "Выполняется действие " + device.get_name() + " ch-" + str(ch.number))
                    logger.debug("Выполняется действие " + device.get_name() + " ch-" + str(ch.number))
                    device.set_status_step(ch.number, False)
                    t = time.time()
                    ans, param, step_time = device.do_meas(ch.number)

                    status, buffer_meas = update_parameters(data=self.measurement_parameters, entry=param, time=time.time() - self.start_exp_time)
                    if status:
                        self.measurement_parameters = buffer_meas
                        self.exp_th_connect.is_measurement_data_updated = True

                    if device.on_next_step(ch.number, repeat = 3) == ch_response_to_step.Step_done:
                        ch.number_meas += 1
                        repeat_counter = 0
                        t = time.time() - t#вычисляем время, необходимое на выставление шага
                        while repeat_counter < self.repeat_meas:
                            repeat_counter += 1
                            ans, param, step_time = device.do_meas(ch.number)
                            status, buffer_meas = update_parameters(data=self.measurement_parameters, entry=param, time=time.time() - self.start_exp_time)
                            if status:
                                self.measurement_parameters = buffer_meas
                                self.exp_th_connect.is_measurement_data_updated = True
                            #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                            def print_data(data):
                                for device, channels in data.items():
                                    print(f"Device: {device}")
                                    for channel, parameters in channels.items():
                                        print(f"Channel: {channel}")
                                        for parameter, values in parameters.items():
                                            if parameter == 'time':
                                                print(f"  {parameter}: {values}")
                                            else:
                                                print(f"  {parameter}: {', '.join([str(value) for value in values])}")
                            #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                            #print_data(self.measurement_parameters)
                            

                            ch.last_step_time = step_time + t

                            self.write_data_to_buf_file("", addTime=True)
                            for param in param:
                                self.write_data_to_buf_file(
                                    message=str(param) + "\t")
                            self.write_data_to_buf_file(message="\n")

                            if ans == ch_response_to_step.Step_done:
                                self.add_text_to_log("шаг " + device.get_name() + " ch-" + str(ch.number) + " сделан за " + str(round(step_time)) + " сек" )
                                self.calc_last_exp_time()
                            if ans == ch_response_to_step.Step_fail:
                                ch.am_i_active_in_experiment = False
                                error = True  # ошибка при выполнении шага прибора, заканчиваем с ошибкой
                                break
                    
                    else:
                        ch.am_i_active_in_experiment = False

                    if device.get_steps_number(ch.number) is not False:
                        if ch.number_meas >= device.get_steps_number(ch.number):
                            ch.am_i_active_in_experiment = False

                    subscribers = self.get_subscribers([[device.get_name(), ch.number]], [
                                                       device.get_name(), ch.number])

                    #print(device.get_name(), "подписчики", subscribers)

                    if ch.am_i_active_in_experiment == False:
                        '''останавливаем всех подписчиков'''
                        for subscriber in subscribers:
                            dev = self.name_to_class(subscriber[0])
                            for chann in dev.channels:
                                if chann.number == subscriber[1]:
                                    chann.am_i_active_in_experiment = False

                    else:
                        for subscriber in subscribers:
                            '''передаем сигнал всем подписчикам'''
                            self.name_to_class(
                                subscriber[0]).set_status_step(subscriber[1], True)

                    for dev in self.dict_active_device_class.values():
                        for channel in dev.channels:
                            if channel.is_ch_active():
                                #print(dev, channel.number, "приоритет = "+ str(channel.get_priority()))
                                if dev == device and ch.number == channel.number:
                                    continue
                                else:
                                    if channel.get_priority() > ch.get_priority():
                                        channel.increment_priority()
                    ch.set_priority(priority = min_priority)

   # -----------------------------------------------------------
        for dev, ch in self.get_active_ch_and_device():
            ans = dev.action_end_experiment(ch.number)
            if ans == False:
                pass
                #print("ошибка при действии " + dev.get_name() + " после эксперимента")
        self.pbar_percent = 0  # сбрасываем прогресс бар

        if error:
            self.add_text_to_log("Эксперимент прерван из-за ошибки", "err")
            logger.debug("Эксперимент прерван из-за ошибки")
            # вывод окна с сообщением в другом потоке
            self.exp_th_connect.is_message_show = False
            self.exp_th_connect.message = "Эксперимент прерван из-за ошибки. Знаем, бесят такие расплывчатые формулировки, прям ЪУЪ!!!. Мы пока не успели допилить анализ ошибок, простите"
            self.exp_th_connect.message_status = message_status.critical
            self.exp_th_connect.flag_show_message = True

            # self.show_critical_window("эксперимент прерван из-за ошибки")
            # TODO: из-за какой ошибки прерван эксперимент, вывести в сообщение
        else:
            self.add_text_to_log("Эксперимент завершен")
            logger.debug("Эксперимент завершен")
            # self.show_information_window("Эксперимент завершен")
            self.exp_th_connect.is_message_show = False
            self.exp_th_connect.message = "Эксперимент завершен"
            self.exp_th_connect.message_status = message_status.info
            self.exp_th_connect.flag_show_message = True

        # ждем, пока ббудет показано сообщение в основном потоке
        while self.exp_th_connect.is_message_show == False:
            pass
        self.set_state_text("Сохранение результатов")

        try:
            self.save_results()
        except:
            #print("не удалось сохранить результаты")
            logger.debug("не удалось сохранить результаты", self.buf_file)
        self.set_state_text("Подготовка к эксперименту")

        # ------------------подготовка к повторному началу эксперимента---------------------
        self.is_experiment_endless = False
        self.stop_experiment = False
        self.installation_window.start_button.setText("Старт")
        self.pause_flag = True
        self.pause_exp()
        self.installation_window.pause_button.setStyleSheet(
            not_ready_style_background)
        for device in self.dict_active_device_class.values():
            device.am_i_active_in_experiment = True
        self.exp_th_connect.is_update_pbar = False
        #self.installation_window.open_graph_button.setEnabled(False)

        # -----------------------------------------------------------------------

        if self.analyse_com_ports():

            # если оказались в этой точке, значит приборы настроены корректно и нет проблем с конфликтами ком портов, если подключение не будет установлено, то ключ снова будет сброшен
            self.key_to_start_installation = True
            self.set_state_text("Ожидание старта эксперимента")

            self.create_clients()
            self.set_clients_for_device()
            self.confirm_devices_parameters()
        else:
            self.key_to_start_installation = False

        if self.key_to_start_installation == True:
            self.installation_window.start_button.setStyleSheet(
                ready_style_background)
        else:
            self.installation_window.start_button.setStyleSheet(
                not_ready_style_background)

    def add_text_to_log(self, text, status=None):
        if status == "err":
            self.installation_window.log.setTextColor(QtGui.QColor('red'))
        elif status == "war":
            self.installation_window.log.setTextColor(QtGui.QColor('orange'))
        else:
            self.installation_window.log.setTextColor(QtGui.QColor('white'))

        self.installation_window.log.append(
            (str(datetime.now().strftime("%H:%M:%S")) + " : " + str(text)))
        self.installation_window.log.ensureCursorVisible()

    def analyse_com_ports(self) -> bool:
        '''анализ конфликтов COM-портов и их доступности'''
        status = True
        
        if not self.is_all_device_settable():
            return False

        list_COMs = []
        list_device_name = []
        fail_ports_list = []

        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients.clear()

        for device in self.dict_active_device_class.values():
            is_dev_active = any(ch.is_ch_active() for ch in device.channels)
            
            if not is_dev_active:
                continue
            
            com = device.get_COM()
            baud = device.get_baud()
            list_COMs.append(com)
            list_device_name.append(device.get_name())

            try:
                buf_client = serial.Serial(com, int(baud))
                buf_client.close()
            except:
                self.set_border_color_device(device_name=device.get_name(), status_color = not_ready_style_border)
                self.add_text_to_log(f"Не удалось открыть порт {com}\n", "war")
                logger.debug(f"Не удалось открыть порт {com}\n")
                if com not in fail_ports_list:
                    fail_ports_list.append(com)
                status = False

        for i in range(len(list_COMs)):
            for j in range(len(list_COMs)):
                if i == j:
                    continue

                if list_COMs[i] == list_COMs[j]:
                    for device_name in [list_device_name[i], list_device_name[j]]:
                        self.set_border_color_device(device_name=device_name, status_color = warning_style_border)
                    
                    if self.dict_active_device_class[list_device_name[i]].get_type_connection() == "serial":
                        self.add_text_to_log(f"{list_device_name[i]} и {list_device_name[j]} не могут иметь один COM порт", status="war")
                    elif self.dict_active_device_class[list_device_name[i]].get_type_connection() == "modbus" and self.dict_active_device_class[list_device_name[i]].get_baud() != self.dict_active_device_class[list_device_name[j]].get_baud():
                        self.add_text_to_log(f"{list_device_name[i]} и {list_device_name[j]} не могут иметь разную скорость подключения", status="war")
                    
                    status = False

        if self.is_debug:
            status = True
        return status
    
    def set_border_color_device(self, device_name, status_color = not_ready_style_border,  num_ch = None, is_only_device_lay = False):
        '''устанавливает цвет границ для канала устройства или для всего устройства в случае, если не указан канал'''
        if is_only_device_lay:
            self.installation_window.devices_lay[device_name].name_device.setStyleSheet(status_color)
        else:
            if num_ch == None:
                self.installation_window.devices_lay[device_name].name_device.setStyleSheet(status_color)
                for ch in self.dict_active_device_class[device_name].channels:
                    self.get_channel_widget(device_name, ch.number).setStyleSheet(status_color)
                    self.get_channel_widget(device_name, ch.number).label_settings_channel.setStyleSheet(status_color)
            else:
                self.get_channel_widget(device_name, num_ch).setStyleSheet(status_color)
                self.get_channel_widget(device_name, num_ch).label_settings_channel.setStyleSheet(status_color)

    def create_clients(self) -> None:
        """функция создает клиенты для приборов с учетом того, что несколько приборов могут быть подключены к одному порту."""
        list_type_connection = []
        list_COMs = []
        list_baud = []
        dict_modbus_clients = {}
        dict_serial_clients = {}
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        for device in self.dict_active_device_class.values():
            is_dev_active = False
            for ch in device.channels:
                if ch.is_ch_active():
                    is_dev_active = True
                    break
            if is_dev_active:
                list_type_connection.append(device.get_type_connection())
                list_COMs.append(device.get_COM())
                list_baud.append(device.get_baud())
            else:
                list_type_connection.append(False)
                list_COMs.append(False)
                list_baud.append(False)
        for i in range(len(list_baud)):
            if list_type_connection[i] == "serial":
                if list_COMs[i] in dict_serial_clients.keys():
                    self.clients.append(dict_serial_clients[list_COMs[i]])
                else:
                    ser = serial.Serial(list_COMs[i], int(list_baud[i]), timeout=1)
                    dict_serial_clients[list_COMs[i]] = ser
                    self.clients.append(ser)
            elif list_type_connection[i] == "modbus":
                if list_COMs[i] in dict_modbus_clients.keys():
                    # если клиент был создан ранее, то просто добавляем ссылку на него
                    self.clients.append(dict_modbus_clients[list_COMs[i]])
                else:  # иначе создаем новый клиент и добавляем в список клиентов и список модбас клиентов
                    dict_modbus_clients[list_COMs[i]] = ModbusSerialClient(
                        method='rtu', port=list_COMs[i], baudrate=int(list_baud[i]), stopbits=1, bytesize=8, parity='E', timeout=0.3, retries=1, retry_on_empty=True)
                    self.clients.append(dict_modbus_clients[list_COMs[i]])
            elif list_type_connection[i] != "modbus" and list_type_connection[i] != "serial":
                self.clients.append(False)
                #print("нет такого типа подключения")
        #print(list_type_connection, )

    def show_parameters_of_device_on_label(self, device, num_channel, list_parameters):
        labeltext = ""
        for i in list_parameters:
            labeltext = labeltext + str(i) + ":" + \
                str(list_parameters[i])+"\n\r"
        self.get_channel_widget(
            device, num_channel).label_settings_channel.setText(labeltext)
        # self.installation_window.label[device].setWordWrap(True)
        # self.installation_window.label[device].setText(labeltext)

    def is_all_device_settable(self) -> bool:
        status = True
        if len(self.dict_active_device_class.values()) == 0:
            status = False
        
        active_channels = 0

        for dev in self.dict_active_device_class.values():
            channels_count = 0
            status_dev = True
            for ch in dev.channels:
                if ch.is_ch_active():
                    active_channels+=1
                    if not ch.is_ch_seted():
                        status_dev = False
                        status = False
                        break
                    else:
                        channels_count += 1
                        self.set_border_color_device(device_name=dev.get_name(), status_color = ready_style_border, num_ch=ch.number)
                else:
                    self.set_border_color_device(device_name=dev.get_name(), status_color = not_ready_style_border, num_ch=ch.number)

            if channels_count == 0:  # прибор активен, но нет включенных каналов
                status_dev = False
                
            if status_dev:
                #print("красим слой в зеленый")
                self.set_border_color_device(device_name=dev.get_name(), status_color = ready_style_border, is_only_device_lay=True)
            else:
                #print("красим слой в красный")
                self.set_border_color_device(device_name=dev.get_name(), status_color = not_ready_style_border, is_only_device_lay=True)
            # установить для устройства зеленый лейбл
        if active_channels == 0:
            status = False

        return status

    def write_parameters_to_file(self, name_device, text):
        '''функция записывает параметры во временный текстовый файл в ходе эксперимента, если что-то прервется, то данные не будут потеряны, после окончания эксперимента файл вычитывается и перегоняется в нужные форматы'''
        with open(self.buf_file, "a") as file:
            file.write(str(name_device) + str(text) + "\n\r")

    def set_way_save(self):
        self.is_window_save_dialog_showing = True
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, ans = QtWidgets.QFileDialog.getSaveFileName(self.installation_window,
                                                              "укажите путь сохранения результатов", "", "Text Files(*.txt);; Книга Excel (*.xlsx);;Origin (*.opju)", options=options)
        if fileName:
            if ans == "Origin (*.opju)":
                if fileName.find(".opju") == -1:
                    fileName = fileName + ".opju"
                self.type_file_for_result = type_save_file.origin
                pass
            elif ans == "Книга Excel (*.xlsx)":
                if fileName.find(".xlsx") == -1:
                    fileName = fileName + ".xlsx"
                self.type_file_for_result = type_save_file.excel
                pass
            else:
                if fileName.find(".txt") == -1:
                    fileName = fileName + ".txt"
                self.type_file_for_result = type_save_file.txt
                pass

            self.way_to_save_file = fileName
            self.installation_window.way_save_text.setText(str(fileName))
            if self.save_results_now == True:
                process_and_export(
                    self.buf_file, self.way_to_save_file, self.type_file_for_result)
                self.save_results_now = False
        else:
            self.type_file_for_result = False
        self.is_window_save_dialog_showing = False

#handlers button, label etc...
    def delete_device(self, device):
        if self.is_experiment_running() == False:
            del self.dict_active_device_class[device]

            buf_dev = {}
            buf_wid = {}
            i = 1
            for key in self.dict_active_device_class.keys():
                dev = self.dict_active_device_class[key]
                wid = self.installation_window.devices_lay[key]
                buf_dev[key[:-1]+str(i)] = dev
                buf_wid[key[:-1]+str(i)] = wid
                dev.set_name(key[:-1]+str(i))
                self.get_device_widget(key).name_device.setText(key[:-1]+str(i))
                for ch in self.get_device_widget(key).channels.values():
                    ch.name_device = key[:-1]+str(i)
                i+=1

            self.installation_window.devices_lay = buf_wid
            self.dict_active_device_class = buf_dev
            self.preparation_experiment()
        else:
            self.add_text_to_log("Запрещено удалять прибор во время эксперимента",status="war")

    def click_set(self, device, num_ch):
        logger.debug("кнопка настройки нажата, устройство -" +str(device) + " " + str(num_ch))
        # print("кнопка настройки нажата, устройство -" +
        #      str(device) + " " + str(num_ch))
        # окно настройки

        if not self.is_experiment_running():
            for client in self.clients:
                try:
                    client.close()
                except:
                    #print("не удалось закрыть клиент связи, скорее всего, этого не требовалось")
                    pass
            # print(self.dict_active_device_class[device])
            self.dict_active_device_class[device].show_setting_window(num_ch)
        else:
            self.add_text_to_log("Запрещено менять параметры во время эксперимента",status="war")

    def push_button_start(self):
        if self.is_experiment_running():
            self.stoped_experiment()
            self.pause_flag = False
            self.pause_exp()
            self.installation_window.pause_button.setStyleSheet(
                not_ready_style_background)
            self.installation_window.start_button.setText("Остановка...")
        else:
            self.preparation_experiment()
            if self.key_to_start_installation:
                self.stop_experiment = True
                self.set_state_text("Старт эксперимента")
                self.installation_window.pause_button.setStyleSheet(
                    ready_style_background)

                self.installation_window.start_button.setStyleSheet(
                    ready_style_background)
                self.installation_window.start_button.setText("Стоп")

                status = True  # последние проверки перед стартом
                if status:
                    self.stop_experiment = False
                    # создаем текстовый файл
                    name_file = ""
                    for i in self.dict_active_device_class.values():
                        for ch in i.channels:
                            if ch.is_ch_active():
                                name_file = name_file + str(i.get_name()) + "_"
                                break

                    folder_path = "buf_files"
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                    currentdatetime = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                    self.buf_file = f"buf_files\{name_file + currentdatetime}.txt"
                    self.write_data_to_buf_file(
                        message="Запущена установка \n\r")
                    lst_dev = ""
                    for dev in self.dict_active_device_class.values():
                        lst_dev += dev.get_name() + " "
                    self.write_data_to_buf_file(message="Список_приборов: " +
                                                lst_dev + "\r\n")
                    for device_class in self.dict_active_device_class.values():
                        for ch in device_class.channels:
                            if ch.is_ch_active():
                                self.write_data_to_buf_file(
                                    message="Настройки " + str(device_class.get_name()) + " ch-" + str(ch.number) + "\r")
                                settings = device_class.get_settings(ch.number)
                                for set, key in zip(settings.values(), settings.keys()):
                                    self.write_data_to_buf_file(
                                        message=str(key) + " - " + str(set) + "\r")
                                self.write_data_to_buf_file(
                                    message="--------------------\n")

                    # print("старт эксперимента")
                    self.repeat_experiment = int(
                        self.installation_window.repeat_exp_enter.currentText())
                    self.repeat_meas = int(
                        self.installation_window.repeat_measurement_enter.currentText())
                    self.add_text_to_log("Создан файл " + self.buf_file)
                    self.add_text_to_log("Эксперимент начат")
                    logger.debug("Эксперимент начат" + "Создан файл " + self.buf_file)
                    self.measurement_parameters = {}#при новонм эксперименте стираем старые параметры
                    if self.graph_window is not None:
                        self.graph_window.set_default()
                    self.experiment_thread = threading.Thread(
                        target=self.exp_th, daemon=True)
                    self.experiment_thread.start()
                    self.timer_for_connection_main_exp_thread.start(1000)

    def push_button_save_installation(self):
        # print("нажата кнопка сохранения установки")
        logger.debug("нажата кнопка сохранения установки")
        if self.way_to_save_installation_file == None:
            self.push_button_save_installation_as()
        else:
            self.write_data_to_save_installation_file(
                self.way_to_save_installation_file)
            self.installation_window.setWindowTitle("Experiment control - " + self.way_to_save_installation_file)

    def push_button_save_installation_as(self):
        # print("нажата кнопка сохранения установки с выбором пути")
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, ans = QtWidgets.QFileDialog.getSaveFileName(self.installation_window,
                                                              "Save File", "", "Text Files(*.txt)", options=options)
        if ans == "Text Files(*.txt)":
            if ".txt" in fileName:
                self.way_to_save_installation_file = fileName
            else:
                self.way_to_save_installation_file = fileName + ".txt"
            # print(fileName)
            self.push_button_save_installation()

    def push_button_open_installation(self):
        # print("нажата кнопка открыть установку")
        logger.debug("нажата кнопка открыть установку")
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, ans = QtWidgets.QFileDialog.getOpenFileName(
            self.installation_window)
        if fileName is not None:
            try:
                self.read_info_by_saved_installation(fileName)
                self.way_to_save_installation_file = fileName
                self.installation_window.setWindowTitle("Experiment control - " + fileName)
            except:
                pass
                logger.debug("не удалось открыть установку")
                #print("не удалось открыть установку")

#Saving data functions

    def write_data_to_save_installation_file(self, way):
        with open(way, 'w') as file:
            file.write(str(len(self.dict_active_device_class.keys())))
            for dev in self.dict_active_device_class.keys():
                file.write("|")
                file.write(dev[0:len(dev):1])
            file.write("\n")

            for dev in self.dict_active_device_class.values():
                for ch in dev.channels:
                        file.write(dev.get_name() + " " + str(ch.number) + "\n")
                        if ch.is_ch_active():
                            file.write(self.get_channel_widget(dev.get_name(), ch.number).label_settings_channel.text().replace("\n", "") + "\n")
                        else:
                            file.write("not active" + "\n")
                        file.write("---------------------")
                        file.write("\n")

    def read_info_by_saved_installation(self, filename):
        logger.debug(f"парссим файл {filename}")
        with open(filename, 'r') as file:
            buffer = file.readlines()

        for i in range(len(buffer)):
            buffer[i] = buffer[i][:-1]
        buffer[0] = buffer[0].split("|")
        new_installation_list = {}
        count = 0
        for device in buffer[0][1::]:
            if device[:-2] not in self.dict_device_class.keys():
                logger.warning(fr"ошибка, прибора {device} нет в списке доступных приборов, не удалось открыть установку")
                self.add_text_to_log(
                    fr"ошибка, прибора {device} нет в списке доступных приборов, не удалось открыть установку", status="err")
                return
            else:
                #new_installation_list[count] = device
                new_installation_list[device] = {}#создаем в качестве значения список, сюда поместим словари с каналами в виде ключей
            count += 1

        settings_devices = []

        is_create_ch = True
        is_add_info = False
        for i in range(1, len(buffer), 1):
            if is_add_info and not(buffer[i] == "---------------------"):
                new_installation_list[name_dev][ch].append(buffer[i])
            if is_create_ch:
                is_create_ch = False
                name_dev = buffer[i].split()[0]
                ch = buffer[i].split()[1]
                new_installation_list[name_dev][ch] = []
                is_add_info = True
            if buffer[i] == "---------------------":
                is_add_info = False
                is_create_ch = True

        for key in new_installation_list.keys():
            for ch in new_installation_list[key].keys():
                    new_dict = {}
                    for data in new_installation_list[key][ch]:
                        if ":" in data:
                            data = data.split(":")
                            try:
                                new_dict[data[0]] = data[1]
                            except:
                                logger.warning(f"ошибка добавления параметра {data} прибор {key} канал {ch}")
                        else:
                            if data == "Не настроено" or data == "not active":
                                new_dict[data] = data
                                break
                    new_installation_list[key][ch] = new_dict

        new_install = []
        for dev in new_installation_list.keys():
            new_install.append(dev[:-2])

        self.dict_active_device_class = {}  # обнуляем словарь с классами приборов


        self.close_window_installation()
        logger.debug(f"закрыто окно установки {self.installation_window}, реконструируем новое")

        self.reconstruct_installation(new_install)
        self.show_window_installation()


        for device in self.dict_active_device_class.values():
            for ch in device.channels:
                open_ch = True
                for param in new_installation_list[device.get_name()][str(ch.number)]:
                    if open_ch == True:
                        open_ch = False
                        if param == "not active":
                            self.get_device_widget(device.get_name()).set_state_ch_widget(ch.number, False)
                        else:
                            self.get_device_widget(device.get_name()).set_state_ch_widget(ch.number, True)

                device.set_parameters(int(ch.number) ,new_installation_list[device.get_name()][str(ch.number)])

            self.get_device_widget(device.get_name()).update_widgets()

    def add_new_device(self):
        logger.debug("нажата кнопка добавления нового прибора")
        #print("нажата кнопка добавления нового прибора")
        self.new_window = QtWidgets.QDialog()
        self.ui_window = installation_Ui_Dialog()
        self.ui_window.setupUi(self.new_window, self)
        self.key_to_new_window_installation = True
        self.new_window.show()

    def message_from_new_installation(self, device_list):
        #print(device_list)
        if device_list:
            pass
            #self.current_installation_list = device_list
            #self.current_installation_class.reconstruct_installation(self.current_installation_list)
            #self.current_installation_class.show_window_installation()
            #self.current_installation_class.installation_window.installation_close_signal.connect(self.unlock_to_create_new_installation)
    
    def save_results(self):
        if self.way_to_save_file != False:  # если выбран путь для сохранения результатов
            #print("путь сохранения результата", self.way_to_save_file)

            if self.type_file_for_result == type_save_file.origin:
                pass
                #print("выбран тип origin для сохранения результата")

            elif self.type_file_for_result == type_save_file.excel:
                pass
                #print("выбран тип файла excel для сохранения результата")
            elif self.type_file_for_result == type_save_file.txt:
                pass
                #print("выбран текстовый тип файла для сохранения результата")
            else:
                self.type_file_for_result = type_save_file.txt
                #print("тип файла для сохранения результата не определен, сохраняем в txt")
            process_and_export(self.buf_file, self.way_to_save_file, self.type_file_for_result)
            # process_and_export(fr"C:\Users\User\YandexDisk\hobby\remoteControl\remote_control\code\Maisheng 1_SR830 2_2024-02-27 18-58-02.txt",
            #                   self.way_to_save_file, self.type_file_for_result)
            # self.buf_file - переменная хранит путь к файлу с данными эксперимента, парсим его
        else:
            # выставляем флаг сохроанения результатов и ждем
            self.exp_th_connect.ask_save_the_results = True

            while self.exp_th_connect.ask_save_the_results == True:
                pass
    
    def show_about_autors(self):
        dialog = AboutAutorsDialog()
        dialog.exec_()

    def open_graph_in_exp(self):
        if self.graph_window is not None:
            pass
        else:
            self.graph_window = GraphWindow()
            self.graph_window.graph_win_close_signal.connect(self.graph_win_closed)
            self.graph_window.update_dict_param(self.measurement_parameters)
        self.graph_window.show()

    def close_other_windows(self):
        if self.graph_window is not None:
            self.graph_window.close()

    def graph_win_closed(self):#закрыто окно с графиком
        pass


if __name__ == "__main__":

    import os
    import logging
    from logging.handlers import RotatingFileHandler
    logger = logging.getLogger(__name__)
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)

    folder_path = "log_files"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    file_handler = RotatingFileHandler('log_files\logfile.log', maxBytes=100000, backupCount=3)

    logging.basicConfig(encoding='utf-8', format=FORMAT, level=logging.INFO, handlers=[file_handler, console])

    #auto-py-to-exe
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    lst = ["Maisheng", "SR830", "PR", "DP832A", "АКИП-2404", "E7-20MNIPI"]
    lst5 = ["Maisheng","АКИП-2404"]
    lst4 = ["DP832A", "Maisheng"]
    lst11 = ["E7-20MNIPI", "АКИП-2404", "DP832A", "PR"]

    app = QtWidgets.QApplication(sys.argv)

    qdarktheme.setup_theme(corner_shape="sharp")

    a = installation_class()
    a.reconstruct_installation(lst4)
    a.show_window_installation()
    sys.exit(app.exec_())


# pyuic5 name.ui -o name.py
