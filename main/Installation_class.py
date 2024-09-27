import logging
import os
import sys
import threading
import time
from datetime import datetime

import qdarktheme
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTimer

from Analyse_in_installation import analyse
from Classes import (not_ready_style_background, not_ready_style_border,
                     ready_style_background)
from experiment_control import experimentControl
from Handler_manager import messageBroker
from interface.installation_window import Ui_Installation

logger = logging.getLogger(__name__)


class installation_class(experimentControl, analyse):
    def __init__(self, settings, dict_device_class) -> None:
        super().__init__()
        logger.info("запуск установки")

        self.settings = settings
        self.load_settings()  # reading settings

        self.dict_device_class = dict_device_class

        self.timer_for_pause_exp = QTimer()
        self.timer_for_pause_exp.timeout.connect(lambda: self.pause_actions())

        self.timer_for_connection_main_exp_thread = QTimer()
        self.timer_for_connection_main_exp_thread.timeout.connect(
            lambda: self.connection_two_thread()
        )

        self.timer_for_open_base_instruction = QTimer()
        self.timer_for_open_base_instruction.timeout.connect(
            lambda: self.show_basic_instruction()
        )
        self.timer_for_open_base_instruction.setSingleShot(
            True
        )  # Установить таймер на однократное срабатывание

        self.message_broker = (
            messageBroker()
        )  # обработчик событий работает как хаб для подписчиков на сигналы и источников сигналов

    def load_settings(self):
        self.is_exp_run_anywhere = self.settings.value(
            "is_exp_run_anywhere", defaultValue=False
        )
        self.is_delete_buf_file = self.settings.value(
            "is_delete_buf_file", defaultValue=True
        )
        self.is_show_basic_instruction_again = self.settings.value(
            "is_show_basic_instruction_again", defaultValue=True
        )
        # self.is_show_basic_instruction_again = True
        logger.info("settings readed")

    def time_decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            print(f"Метод {func.__name__} - {end_time - start_time} с")
            return result

        return wrapper

    def reconstruct_installation(self, installation_list):
        """Reconstruct installation from list of device names"""
        self.dict_active_device_class = {}
        self.graph_window = None
        self.measurement_parameters = {}

        for i, device_name in enumerate(installation_list):
            try:
                device = self.dict_device_class[device_name](
                    name=f"{device_name}_{i+1}", installation_class=self
                )
                self.dict_active_device_class[f"{device_name}_{i+1}"] = device
            except:
                logger.error(f"Failed to create instance of {device_name}")

        self.installation_window = Ui_Installation()
        self.installation_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installation_window.setupUi(self.installation_window, self, self.dict_active_device_class)

        self.installation_window.way_save_button.clicked.connect(self.set_way_save)
        self.installation_window.start_button.clicked.connect(self.push_button_start)
        self.installation_window.start_button.setToolTip(
            "Start experiment will be available after all devices are set up"
        )
        self.installation_window.start_button.setStyleSheet(not_ready_style_background)
        self.installation_window.start_button.setText("Start")
        self.installation_window.pause_button.clicked.connect(self.pause_exp)
        self.installation_window.pause_button.setStyleSheet(not_ready_style_background)
        self.installation_window.about_autors.triggered.connect(self.show_about_autors)
        self.installation_window.open_graph_button.clicked.connect(self.open_graph_in_exp)
        self.installation_window.installation_close_signal.connect(self.close_other_windows)
        self.installation_window.general_settings.triggered.connect(self.open_general_settings)

        self.installation_window.save_installation_button.triggered.connect(
            self.push_button_save_installation
        )
        self.installation_window.save_installation_button_as.triggered.connect(
            self.push_button_save_installation_as
        )
        self.installation_window.open_installation_button.triggered.connect(
            self.push_button_open_installation
        )

        self.installation_window.add_device_button.triggered.connect(self.add_new_device)

        self.installation_window.develop_mode.triggered.connect(self.change_check_debug)

        self.installation_window.clear_log_button.clicked.connect(self.clear_log)
        self.installation_window.clear_log_button.setToolTip("Очистить лог")
        self.set_state_text("Ожидание настройки приборов")
        self.timer_for_open_base_instruction.start()

    def set_state_ch(self, device, num_ch, state):
        logger.info(f"передаем состояние {state} канала {num_ch} прибору {device}")
        self.dict_active_device_class[device].set_state_ch(num_ch, state)
        self.preparation_experiment()
        logger.warning(f"set_state_ch\n")

    def preparation_experiment(self):
        logger.debug("подготовка к эксперименту")
        self.key_to_start_installation = False

        if self.is_all_device_settable():
            ############################
            #self.get_time_line_devices()
            ############################

            logger.debug("все каналы имеют статус настроен")
            if self.analyse_com_ports():

                # если оказались в этой точке, значит приборы настроены корректно и нет проблем с конфликтами ком портов, если подключение не будет установлено, то ключ снова будет сброшен
                self.confirm_devices_parameters()
                self.set_priorities()
                self.cycle_analyse()
                self.is_experiment_endless = self.analyse_endless_exp()
                self.key_to_start_installation = True

        if self.key_to_start_installation == True:
            self.installation_window.start_button.setStyleSheet(ready_style_background)
        else:
            self.installation_window.start_button.setStyleSheet(
                not_ready_style_background
            )
        self.installation_window.start_button.setText("Старт")

    def add_new_channel(self, device, num_ch):
        if self.is_experiment_running() == False:
            for ch in self.dict_active_device_class[device].channels:
                if ch.number == num_ch:
                    if ch.is_ch_seted():
                        pass
                    else:
                        self.set_border_color_device(
                            device_name=device,
                            status_color=not_ready_style_border,
                            num_ch=num_ch,
                        )
        else:
            self.add_text_to_log(
                "Запрещено добавлять или отключать канал во время эксперимента",
                status="war",
            )

    def set_border_color_device(
        self,
        device_name,
        status_color=not_ready_style_border,
        num_ch=None,
        is_only_device_lay=False,
    ):
        """устанавливает цвет границ для канала устройства или для всего устройства в случае, если не указан канал"""
        if is_only_device_lay:
            self.installation_window.devices_lay[device_name].name_device.setStyleSheet(
                status_color
            )
        else:
            if num_ch == None:
                self.installation_window.devices_lay[
                    device_name
                ].name_device.setStyleSheet(status_color)
                for ch in self.dict_active_device_class[device_name].channels:
                    self.get_channel_widget(device_name, ch.number).setStyleSheet(
                        status_color
                    )
                    self.get_channel_widget(
                        device_name, ch.number
                    ).label_settings_channel.setStyleSheet(status_color)
            else:
                self.get_channel_widget(device_name, num_ch).setStyleSheet(status_color)
                self.get_channel_widget(
                    device_name, num_ch
                ).label_settings_channel.setStyleSheet(status_color)

    def show_parameters_of_device_on_label(
        self,
        device,
        num_channel,
        list_parameters_device,
        list_parameters_act=None,
        list_parameters_meas=None,
    ):
        labeltext = ""
        for i in list_parameters_device:
            labeltext = (
                labeltext + str(i) + ":" + str(list_parameters_device[i]) + "\n\r"
            )
        if list_parameters_act is not None:
            labeltext = labeltext + "Action" + ":\n\r"
            for i in list_parameters_act:
                labeltext = (
                    labeltext + str(i) + ":" + str(list_parameters_act[i]) + "\n\r"
                )
        if list_parameters_meas is not None:
            labeltext = labeltext + "Measurement" + ":\n\r"
            for i in list_parameters_meas:
                labeltext = (
                    labeltext + str(i) + ":" + str(list_parameters_meas[i]) + "\n\r"
                )

        self.get_channel_widget(device, num_channel).label_settings_channel.setText(
            labeltext
        )
        # self.installation_window.label[device].setWordWrap(True)
        # self.installation_window.label[device].setText(labeltext)

    def write_parameters_to_file(self, name_device, text):
        """функция записывает параметры во временный текстовый файл в ходе эксперимента, если что-то прервется, то данные не будут потеряны, после окончания эксперимента файл вычитывается и перегоняется в нужные форматы"""
        with open(self.buf_file, "a") as file:
            file.write(str(name_device) + str(text) + "\n\r")

    def close_other_windows(self):
        if self.graph_window is not None:
            self.graph_window.close()

        self.stop_scan_thread = True
        self.thread_scan_resources.join()

    def graph_win_closed(self):
        pass

    # handlers button, label etc...

    def delete_device(self, device):
        if self.is_experiment_running() == False:
            del self.dict_active_device_class[device]

            buf_dev = {}
            buf_wid = {}
            i = 1
            for key in self.dict_active_device_class.keys():
                dev = self.dict_active_device_class[key]
                wid = self.installation_window.devices_lay[key]
                buf_dev[key[:-1] + str(i)] = dev
                buf_wid[key[:-1] + str(i)] = wid
                dev.set_name(key[:-1] + str(i))
                self.get_device_widget(key).name_device.setText(key[:-1] + str(i))
                for ch in self.get_device_widget(key).channels.values():
                    ch.name_device = key[:-1] + str(i)
                i += 1

            self.installation_window.devices_lay = buf_wid
            self.dict_active_device_class = buf_dev
            self.preparation_experiment()
            logger.info("выход из функции удаления прибора")
        else:
            self.add_text_to_log(
                "Запрещено удалять прибор во время эксперимента", status="war"
            )

    def click_set(self, device, num_ch):
        logger.debug(
            "кнопка настройки нажата, устройство -" + str(device) + " " + str(num_ch)
        )

        if not self.is_experiment_running():
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.dict_active_device_class[device].show_setting_window(num_ch)
        else:
            self.add_text_to_log(
                "Запрещено менять параметры во время эксперимента", status="war"
            )

    def set_depending(self) -> bool:
        """устанавливает зависимости одних приборов от других, добавляет подписчиков"""
        for device, ch in self.get_active_ch_and_device():
            trig = device.get_trigger(ch)
            if trig != "Таймер":
                trig_val = device.get_trigger_value(ch)
                self.message_broker.subscribe(object=ch, name_subscribe=trig_val)
        return True
    
    def action_stop_experiment(self):
            self.stoped_experiment()
            self.pause_flag = False
            self.pause_exp()
            self.installation_window.pause_button.setStyleSheet(
                not_ready_style_background
            )
            self.installation_window.start_button.setText("Остановка...")

    def push_button_start(self):
        if self.is_experiment_running():
            self.action_stop_experiment()
        else:
            self.preparation_experiment()
            if self.key_to_start_installation:
                self.stop_experiment = True
                self.create_clients()
                self.set_clients_for_device()
                self.set_state_text("Старт эксперимента")
                self.installation_window.pause_button.setStyleSheet(
                    ready_style_background
                )

                self.installation_window.start_button.setStyleSheet(
                    ready_style_background
                )
                self.installation_window.start_button.setText("Стоп")
                status = self.set_depending()

                if status:
                    self.stop_experiment = False
                    
                    self.buf_file = self.create_buf_file()
                    self.write_data_to_buf_file(message="Запущена установка \n\r")
                    lst_dev = ""
                    for dev in self.dict_active_device_class.values():
                        lst_dev += dev.get_name() + " "
                    self.write_data_to_buf_file(
                        message="Список_приборов: " + lst_dev + "\r\n"
                    )
                    self.write_settings_to_buf_file()

                    self.repeat_experiment = int(
                        self.installation_window.repeat_exp_enter.currentText()
                    )
                    self.repeat_meas = int(
                        self.installation_window.repeat_measurement_enter.currentText()
                    )
                    self.add_text_to_log("Создан файл " + self.buf_file)
                    self.add_text_to_log("Эксперимент начат")
                    logger.debug("Эксперимент начат" + "Создан файл " + self.buf_file)
                    self.measurement_parameters = {}
                    if self.graph_window is not None:
                        self.graph_window.set_default()
                    self.experiment_thread = threading.Thread(
                        target=self.exp_th, daemon=True
                    )
                    self.experiment_thread.start()
                    self.timer_for_connection_main_exp_thread.start(1000)
    
    def create_buf_file(self):
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
        return f"buf_files/{name_file + currentdatetime}.txt"
    
    def write_settings_to_buf_file(self):
        for device_class in self.dict_active_device_class.values():
            self.write_data_to_buf_file(
                message="Настройки " + str(device_class.get_name()) + "\r"
            )
            settings = device_class.get_settings()
            for set, key in zip(settings.values(), settings.keys()):
                self.write_data_to_buf_file(
                    message=str(key) + " - " + str(set) + "\r"
                )

            for ch in device_class.channels:
                if ch.is_ch_active():

                    self.write_data_to_buf_file(
                        message="Настройки " + str(ch.get_name()) + "\r"
                    )
                    settings = ch.get_settings()
                    for set, key in zip(settings.values(), settings.keys()):
                        self.write_data_to_buf_file(
                            message=str(key) + " - " + str(set) + "\r"
                        )

            self.write_data_to_buf_file(message="--------------------\n")

    def push_button_save_installation(self):
            logger.debug("нажата кнопка сохранения установки")
            if self.way_to_save_installation_file == None:
                self.push_button_save_installation_as()
            else:
                self.write_data_to_save_installation_file(
                    self.way_to_save_installation_file
                )
                self.installation_window.setWindowTitle(
                    "Experiment control - " + self.way_to_save_installation_file
                )

    def push_button_save_installation_as(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, ans = QtWidgets.QFileDialog.getSaveFileName(
            self.installation_window,
            "Save File",
            "",
            "Installation(*.ns)",
            options=options,
        )
        if ans == "Installation(*.ns)":
            if ".ns" in fileName:
                self.way_to_save_installation_file = fileName
            else:
                self.way_to_save_installation_file = fileName + ".ns"
            # print(fileName)
            self.push_button_save_installation()

    def push_button_open_installation(self):
        logger.debug("нажата кнопка открыть установку")
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, ans = QtWidgets.QFileDialog.getOpenFileName(
            self.installation_window,
            "Open File",
            "",
            "Installation(*.ns)",
            options=options,
        )
        if ans == "Installation(*.ns)":
            install_list = self.extract_saved_installlation(fileName=fileName)
            # self.add_parameter_devices(install_list)
            self.way_to_save_installation_file = fileName
            self.installation_window.setWindowTitle("Experiment control - " + fileName)

    def extract_saved_installlation(self, fileName):
        status, install_list = self.read_info_by_saved_installation(fileName)
        self.show_window_installation()
        self.timer_open = QTimer()
        self.timer_open.timeout.connect(lambda: self.timer_open_timeout(install_list))
        self.timer_open.start(100)

    def timer_open_timeout(self, install_list):
        self.timer_open.stop()
        self.add_parameter_devices(install_list)

    # Saving data functions

    def write_data_to_save_installation_file(self, way):
        with open(way, "w") as file:
            file.write(str(len(self.dict_active_device_class.keys())))
            for dev in self.dict_active_device_class.keys():
                file.write("|")
                file.write(dev[0 : len(dev) : 1])
            file.write("\n")

            for device_class in self.dict_active_device_class.values():

                file.write("Настройки " + str(device_class.get_name()) + "\r")
                settings = device_class.get_settings()
                for set, key in zip(settings.values(), settings.keys()):
                    file.write(str(key) + "|" + str(set) + "\r")

                for ch in device_class.channels:
                    file.write("Настройки " + str(ch.get_name()) + "\r")
                    if ch.is_ch_active():
                        if (
                            self.get_channel_widget(
                                device_class.get_name(), ch.get_number()
                            ).label_settings_channel.text()
                            == "Не настроено"
                        ):
                            file.write("Не настроено" + "\n")
                        else:
                            settings = ch.get_settings()
                            for set, key in zip(settings.values(), settings.keys()):
                                file.write(str(key) + "|" + str(set) + "\r")
                    else:
                        file.write("not active" + "\n")
                # file.write("--------------------\n")

    def read_info_by_saved_installation(self, filename):
        logger.info(f"парсим файл {filename}")
        with open(filename, "r") as file:
            buffer = file.readlines()

        for i in range(len(buffer)):
            buffer[i] = buffer[i][:-1]
        buffer[0] = buffer[0].split("|")
        new_installation_list = {}
        count = 0
        for device in buffer[0][1::]:
            if device[:-2] not in self.dict_device_class.keys():
                logger.warning(
                    rf"ошибка, прибора {device} нет в списке доступных приборов, не удалось открыть установку"
                )
                self.add_text_to_log(
                    rf"ошибка, прибора {device} нет в списке доступных приборов, не удалось открыть установку",
                    status="err",
                )
                self.show_critical_window(
                    message="Ошибка при открытии сохраненной установки.\n Вероятно, содержимое файла имеет не верный формат."
                )
                raise ValueError(
                    rf"ошибка, прибора {device} нет в списке доступных приборов, не удалось открыть установку"
                )
            else:
                # создаем в качестве значения список, сюда поместим словари с каналами в виде ключей
                new_installation_list[device] = {}
                new_installation_list[device]["set"] = []
            count += 1

        settings_devices = []
        is_set_dev_added = False
        adding_set_dev = False
        adding_set_ch = False
        is_create_ch = True
        is_add_info = False
        for i in range(1, len(buffer), 1):

            if "Настройки" in buffer[i]:
                name = buffer[i].split()[1]
                if "ch-" in name:
                    name_ch = name
                    adding_set_ch = True
                    adding_set_dev = False
                    new_installation_list[name_dev][name_ch] = {}
                    new_installation_list[name_dev][name_ch]["set"] = []
                    logger.info("настройки канала при считывании в файл " + name_ch)
                else:
                    name_dev = name
                    adding_set_dev = True
                    adding_set_ch = False
                    logger.info("настройки прибора при считывании в файл " + name_dev)
                continue

            if adding_set_dev:
                buf = buffer[i].split("|")
                # print(buf)
                if len(buf) != 2:
                    pass
                else:
                    new_installation_list[name_dev]["set"].append([buf[0], buf[1]])

            elif adding_set_ch:
                if buffer[i] == "not active" or buffer[i] == "Не настроено":
                    new_installation_list[name_dev][name_ch]["set"].append(buffer[i])
                else:
                    buf = buffer[i].split("|")
                    if len(buf) != 2:
                        logger.warning(
                            "Ошибка определения ключа и значение параметра"
                            + str(buffer[i])
                        )
                        self.show_critical_window(
                            message="Ошибка при открытии сохраненной установки.\n Вероятно, содержимое файла имеет не верный формат."
                        )
                        raise ValueError(
                            "Ошибка определения ключа и значение параметра"
                            + str(buffer[i])
                        )
                    else:
                        new_installation_list[name_dev][name_ch]["set"].append(
                            [buf[0], buf[1]]
                        )

        if True:
            new_install = []
            for dev in new_installation_list.keys():
                new_install.append(dev[:-2])

            self.dict_active_device_class = {}  # обнуляем словарь с классами приборов
            self.message_broker.clear_all()
            logger.info(
                f"закрыто окно установки {self.installation_window}, реконструируем новое"
            )

            self.close_window_installation()

            self.reconstruct_installation(new_install)
            return True, new_installation_list

    def add_parameter_devices(self, new_installation_list):
        for key in new_installation_list.keys():  # заполняем параметры приборов
            device = self.dict_active_device_class[key]
            for ch in new_installation_list[key].keys():
                if ch == "set":  ##установка настроек прибора
                    for param in new_installation_list[key][ch]:
                        device.dict_buf_parameters[param[0]] = param[1]
                        device.dict_settable_parameters[param[0]] = param[1]
                else:
                    for chann in device.channels:
                        if chann.get_name() == ch:
                            parameters = {}
                            set_open = True
                            for param in new_installation_list[key][ch]["set"]:
                                if param == "not active":
                                    parameters[param] = ""
                                    if set_open:
                                        set_open = False
                                        self.get_device_widget(
                                            device.get_name()
                                        ).set_state_ch_widget(chann.number, False)
                                        # self.get_device_widget(device.get_name()).click_change_ch(num = chann.number, is_open = False)
                                elif param == "Не настроено":
                                    parameters[param] = ""
                                    if set_open:
                                        set_open = False
                                        self.get_device_widget(
                                            device.get_name()
                                        ).set_state_ch_widget(chann.number, True)
                                        # self.get_device_widget(device.get_name()).click_change_ch(num = chann.number, is_open = True)
                                else:
                                    parameters[param[0]] = param[1]
                                    if set_open:
                                        set_open = False
                                        self.get_device_widget(
                                            device.get_name()
                                        ).set_state_ch_widget(chann.number, True)
                                        # self.get_device_widget(device.get_name()).click_change_ch(num = chann.number, is_open = True)
                            device.set_parameters(
                                channel_name=chann.get_name(), parameters=parameters
                            )
            self.get_device_widget(device.get_name()).update_widgets()


if __name__ == "__main__":
    import logging
    import os
    from logging.handlers import RotatingFileHandler

    logger = logging.getLogger(__name__)
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
    console = logging.StreamHandler()
    folder_path = "log_files"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    file_handler = RotatingFileHandler(
        "log_files\logfile.log", maxBytes=100000, backupCount=3
    )

    logging.basicConfig(
        encoding="utf-8",
        format=FORMAT,
        level=logging.INFO,
        handlers=[file_handler, console],
    )
    console.setLevel(logging.WARNING)

    settings = QtCore.QSettings(
        QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, "misis", "exp_control"
    )

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    lst = ["SR830", "SR830"]
    lst5 = ["PR", "Maisheng"]
    lst4 = ["DP832A", "Maisheng"]
    lst11 = ["E7-20MNIPI", "АКИП-2404", "DP832A", "PR"]
    lst22 = ["SR830", "SR830", "DS1104Z"]
    lst21 = ["Maisheng", "Maisheng", "Maisheng", "Maisheng", "Maisheng", "Maisheng"]
    lst50 = ["E7-20MNIPI", "E7-20MNIPI"]
    lst55 = ["DS1104Z"]

    app = QtWidgets.QApplication(sys.argv)

    qdarktheme.setup_theme(corner_shape="sharp")
    from available_devices import dict_device_class

    a = installation_class(settings=settings, dict_device_class=dict_device_class)
    a.reconstruct_installation(lst)
    a.show_window_installation()
    sys.exit(app.exec_())


# pyuic5 name.ui -o name.py
