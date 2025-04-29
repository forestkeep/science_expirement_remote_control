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
import os
import sys
import threading
import time
import json
from datetime import datetime

import qdarktheme
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTimer, QThread
from PyQt5.QtWidgets import QApplication

from Analyse_in_installation import analyse
from Devices.Classes import (not_ready_style_background,
                             not_ready_style_border, ready_style_background)
from measurement_running import experimentControl
from Handler_manager import messageBroker
from interface.installation_window import Ui_Installation
from schematic_exp.construct_diagramexp import expDiagram
from schematic_exp.exp_time_line import callStack
from saving_data.Parse_data import process_and_export, type_save_file
from available_devices import dict_device_class, JSON_dict_device_class
from meas_session_data import measSession
from experiment_control import ExperimentBridge
from functions import get_active_ch_and_device, write_data_to_buf_file, clear_queue, clear_pipe
#from queue import Queue
from graph.online_graph import sessionController, run_graph_process
from multiprocessing import Process, Value, Array, Lock, shared_memory, Pipe, Queue


logger = logging.getLogger(__name__)

import pickle

def is_serializable(value):
    """Проверяет, можно ли сериализовать значение с помощью pickle."""
    try:
        pickle.dumps(value)
        return True
    except Exception as e:
        return False

def get_serializable_copy(obj):
    """Создает копию объекта только с сериализуемыми атрибутами."""
    # Создаем новый экземпляр класса без вызова __init__
    new_obj = obj.__class__.__new__(obj.__class__)
    
    # Собираем атрибуты исходного объекта
    attributes = {}
    if hasattr(obj, '__dict__'):
        # Для объектов с __dict__
        attributes = vars(obj).copy()
    else:
        # Для объектов без __dict__ (например, с __slots__)
        for attr_name in dir(obj):
            if attr_name.startswith('__') and attr_name.endswith('__'):
                continue  # Пропускаем служебные атрибуты
            try:
                attr_value = getattr(obj, attr_name)
                if not callable(attr_value):  # Пропускаем методы
                    attributes[attr_name] = attr_value
            except AttributeError:
                continue
    
    removed_attrs = []
    
    # Копируем только сериализуемые атрибуты
    for attr_name, attr_value in attributes.items():
        if is_serializable(attr_value):
            try:
                setattr(new_obj, attr_name, attr_value)
            except AttributeError:
                # Обработка атрибутов, которые нельзя установить (например, в __slots__)
                removed_attrs.append(attr_name)
        else:
            removed_attrs.append(attr_name)
    
    return new_obj, removed_attrs




class installation_class( ExperimentBridge, analyse):
    def __init__(self, settings_manager, version = None) -> None:
        super().__init__()

        self.settings_manager    = settings_manager
        self.version_app         = version

        self.device_selector = None

        self.dict_device_class  = dict_device_class
        self.JSON_dict_device_class = JSON_dict_device_class

        self.timer_for_pause_exp = QTimer()
        self.timer_for_pause_exp.timeout.connect(lambda: self.pause_actions())

        self.timer_for_receive_data_exp = QTimer()
        self.timer_for_receive_data_exp.timeout.connect(lambda: self.receive_data_exp())

        self.timer_for_connection_main_exp_thread = QTimer()
        self.timer_for_connection_main_exp_thread.timeout.connect( self.connection_two_thread )

        self.timer_for_open_base_instruction = QTimer()
        self.timer_for_open_base_instruction.timeout.connect(
            lambda: self.show_basic_instruction()
        )
        self.timer_for_open_base_instruction.setSingleShot(
            True
        )

        self.message_broker = (
            messageBroker()
        )

    def format_bool_settings(self, value):

        if isinstance(value, str ):
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            else:
                try:
                    value = float(value)
                except:
                    pass
        return value

    def time_decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            print(f"Метод {func.__name__} - {end_time - start_time} с")
            return result

        return wrapper

    def reconstruct_installation(self, installation_list: list, json_devices: dict = None):
        """Reconstruct installation from list of device names"""
        self.dict_active_device_class = {}
        self.graph_controller = sessionController()
        self.graph_controller.graphics_win.graph_win_close_signal.connect(self.graph_win_closed)
        self.measurement_parameters = {}
        i = 0
        for device_name in installation_list:
            try:
                device = self.dict_device_class[device_name](
                    name=f"{device_name}_{i+1}", installation_class=self
                )
                self.dict_active_device_class[f"{device_name}_{i+1}"] = device
            except Exception as e:
                logger.error(f"Failed to create instance of {device_name} {e}")
            i += 1

        if json_devices:
            for dev in json_devices.values():
                try:
                    device_class = self.JSON_dict_device_class[ dev.json_data['device_type'] ](
                        name=f"{dev.name}_{i+1}", installation_class=self
                        )
                    device_class.load_json(dev.json_data)
                    self.dict_active_device_class[f"{dev.name}_{i+1}"] = device_class
                except Exception as e:
                    logger.error(f"Failed to create instance of {dev.name} {e}")
                i += 1

        self.exp_diagram = expDiagram()
        self.exp_call_stack = callStack()
        
        self.installation_window = Ui_Installation()
        self.installation_window.setWindowTitle(
                    "Experiment control " + self.version_app
                )
        self.installation_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.installation_window.setupUi(self.installation_window, self, self.dict_active_device_class, self.exp_diagram, self.exp_call_stack)

        self.installation_window.start_button.clicked.connect(self.push_button_start)
        self.installation_window.start_button.setToolTip(
            "Start experiment will be available after all devices are set up"
        )
        self.installation_window.start_button.setStyleSheet(not_ready_style_background)
        self.installation_window.start_button.setText(QApplication.translate('main install',"Старт"))
        self.installation_window.pause_button.clicked.connect(self.pause_exp)
        self.installation_window.pause_button.setStyleSheet(not_ready_style_background)
        self.installation_window.about_autors.triggered.connect(self.show_about_autors)
        self.installation_window.version.triggered.connect(self.show_version)
        self.installation_window.open_graph_button.clicked.connect(self.open_graph_in_exp)
        self.installation_window.installation_close_signal.connect(self.close_other_windows)
        self.installation_window.general_settings.triggered.connect(self.open_general_settings)

        self.installation_window.convert_buf_button.triggered.connect(self.convert_buf_file)

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
        self.installation_window.clear_log_button.setToolTip(QApplication.translate('main install',"Очистить лог"))
        self.set_state_text( text = QApplication.translate('main install',"Ожидание настройки приборов") )
        
        self.timer_for_open_base_instruction.start()

    def set_state_ch(self, device, num_ch, state):
        logger.debug(f"передаем состояние {state} канала {num_ch} прибору {device}")
        self.dict_active_device_class[device].set_state_ch(num_ch, state)
        self.preparation_experiment()

    def preparation_experiment(self):
        logger.debug("подготовка к эксперименту")
        self.key_to_start_installation = False
        
        self.message_broker.clear_all_subscribers()
        status = self.set_depending()#setting subscribers
        
        
        #Строим схему взаимодействия приборов
        self.exp_diagram.rebuild_schematic(self, self.dict_active_device_class)

        if self.is_all_device_settable():
            ############################
            self.get_time_line_devices()
            ############################

            logger.debug("все каналы имеют статус настроен")
            if self.analyse_com_ports():

                # если оказались в этой точке, значит приборы настроены корректно и нет проблем с конфликтами ком портов, если подключение не будет установлено, то ключ снова будет сброшен
                self.confirm_devices_parameters()
                self.set_priorities()
                self.cycle_analyse()
                self.is_experiment_endless = self.analyse_endless_exp()
                self.key_to_start_installation = True
            else:
                self.key_to_start_installation = False

        if self.key_to_start_installation == True:
            self.installation_window.start_button.setStyleSheet(ready_style_background)
            self.installation_window.start_button.update_buf_style()
        else:
            self.installation_window.start_button.setStyleSheet(
                not_ready_style_background
            )
            self.installation_window.start_button.update_buf_style()

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
                QApplication.translate('main install',"Запрещено добавлять или отключать канал во время эксперимента"),
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
        self.graph_controller.graphics_win.close()
        self.stop_scan_thread = True
        self.thread_scan_resources.join()

    def graph_win_closed(self):
        pass

    # handlers button, label etc...

    def delete_device(self, device):
        if self.is_experiment_running() == False:
            for ch in self.dict_active_device_class[device].channels:
                self.message_broker.clear_my_topicks(publisher_name=ch)

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
                QApplication.translate('main install',"Запрещено удалять прибор во время эксперимента"), status="war"
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
                QApplication.translate('main install',"Запрещено менять параметры во время эксперимента"), status="war"
            )

    def set_depending(self) -> bool:
        """устанавливает зависимости одних приборов от других, добавляет подписчиков"""
        status = True
        for device, ch in get_active_ch_and_device( self.dict_active_device_class ):
            trig = device.get_trigger(ch)
            if trig != QApplication.translate('main install',"Таймер"):

                trig_val = device.get_trigger_value(ch)
                status = self.message_broker.subscribe(object=ch, name_subscribe=trig_val)
                text=QApplication.translate('main install',"{device_name} {ch_name} не имеет источника сигнала, проверьте его настройки")
                text = text.format(device_name = device.get_name(), ch_name = ch.get_name())

                if status is False:
                    self.add_text_to_log(text=text, status='war')
                    logger.warning(f"Подписки {trig_val} не существует")
        return status
    
    def action_stop_experiment(self):
            self.stoped_experiment()
            self.pause_flag = True
            self.pause_exp()
            self.installation_window.pause_button.setStyleSheet(
                not_ready_style_background
            )
            self.timer_for_pause_exp.stop()
            self.installation_window.pause_button.style_sheet = not_ready_style_background
            self.installation_window.pause_button.setText(QApplication.translate('exp_flow',"Пауза"))
            self.installation_window.start_button.setText(QApplication.translate('main install',"Остановка") + "...")

    def push_button_start(self):
        """
        slot for start button, if experiment is running, stops it, if not, starts experiment
        """

        if self.is_experiment_running():
            self.action_stop_experiment()
        else:
            self.preparation_experiment()
            if self.key_to_start_installation:

                self.create_clients()
                self.stop_experiment = True
                self.set_clients_for_device()
                self.set_state_text(text = QApplication.translate('main install',"Старт эксперимента"))
                self.installation_window.pause_button.setStyleSheet(ready_style_background)
                self.installation_window.start_button.setStyleSheet(ready_style_background)
                self.installation_window.start_button.setText(QApplication.translate('main install',"Стоп"))
                
                self.message_broker.clear_all_subscribers()
                status = self.set_depending()#setting subscribers
                
                if status:
                    self.stop_experiment = False
                    self.has_unsaved_data = False
                    
                    self.buf_file = self.create_buf_file()

                    write_data_to_buf_file(file = self.buf_file,message="installation start" + "\n\r")
                    lst_dev = ""
                    for dev in self.dict_active_device_class.values():
                        lst_dev += dev.get_name() + " "
                    write_data_to_buf_file(file = self.buf_file,message="device list: " + lst_dev + "\r\n")

                    self.write_settings_to_buf_file()

                    self.add_text_to_log(text =QApplication.translate('main install',"Создан файл") + " " + self.buf_file)
                    logger.debug("Эксперимент начат" + "Создан файл " + self.buf_file)
                    self.measurement_parameters = {}

                    self.current_session_graph_id = self.graph_controller.start_new_session(session_name=str(datetime.now()),
                                                                                            use_timestamps=True,
                                                                                            is_experiment_running=True
                                                                                            )

                    self.add_text_to_log(text = QApplication.translate('main install',"настройка приборов") + ".. ")

                    self.start_exp_time = time.perf_counter()
                    self.remaining_exp_time = 0
                    self.update_pbar(0)

                    self.timer_for_connection_main_exp_thread.start(1000)
                    self.timer_second_thread_tasks = QTimer()
                    self.timer_second_thread_tasks.timeout.connect(self.second_thread_tasks)
                    self.timer_second_thread_tasks.start(100)

                    #self.queue = Queue()
                    self.experiment_queue = Queue()
                    self.important_exp_queue = Queue()

                    self.meas_session = measSession()

                    self.pipe_exp, self.pipe_installation = Pipe()
                    self.data_exp_to_installation, self.data_from_exp = Pipe()

                    serialize_divices_classes = {}
                    for dev in self.dict_active_device_class.values():
                        dev.client.close()
                        serialize_divices_classes[dev.get_name()], unserial  = get_serializable_copy(dev)

                    self.exp_controller = experimentControl(
                        device_classes        =serialize_divices_classes,
                        message_broker        =self.message_broker,
                        is_debug              =self.is_debug,
                        is_experiment_endless =self.is_experiment_endless,
                        repeat_exp            =int(self.settings_manager.get_setting("repeat_exp")[1]),
                        repeat_meas           =int(self.settings_manager.get_setting("repeat_meas")[1]),
                        is_run_anywhere       =self.settings_manager.get_setting("is_exp_run_anywhere")[1],
                        simple_queue          =self.experiment_queue,
                        important_queue       =self.important_exp_queue,
                        buf_file              =self.buf_file,
                        pipe_installation     =self.pipe_installation,
                        data_pipe             =self.data_exp_to_installation,
                        #graph_controller      =self.graph_controller,
                        session_id            =self.current_session_graph_id
                    )

                    self.experiment_process = Process(target=self.exp_controller.run)
                    self.experiment_process.start()
                    self.timer_for_connection_main_exp_thread.start(1000)
                    self.timer_for_receive_data_exp.start(100)

    def second_thread_tasks(self):
        if not self.important_exp_queue.empty():
            event_type, data = self.important_exp_queue.get_nowait()

            if event_type == "finalize_experiment":
                self.finalize_experiment(**data)

            elif event_type == "has_data_to_save":
                self.has_unsaved_data = True

        else:

            if not self.experiment_queue.empty():
                event_type, data = self.experiment_queue.get_nowait()

                if event_type == "meta_data_exp_updated":
                    self.exp_call_stack.set_data(**data)

                elif event_type == "set_state_text":
                    self.set_state_text(**data)

                elif event_type == "update_remaining_time":
                    self.update_remaining_time(**data)
                    
                elif event_type == "add_text_to_log":
                    self.add_text_to_log(**data)
                
    def update_remaining_time(self, remaining_time: float):
        logger.debug(f"update_remaining_time {remaining_time}")
        self.remaining_exp_time = remaining_time

    def create_buf_file(self):
        name_file = ""
        for i in self.dict_active_device_class.values():
            for ch in i.channels:
                if ch.is_ch_active():
                    name_file = name_file + str(i.get_name()) + "_"
                    break

        folder_path = os.path.join(os.getenv('USERPROFILE'), "AppData", "Local", "Installation_Controller", "buf_files")
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        currentdatetime = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        return os.path.join(folder_path, f"{name_file + currentdatetime}.txt")
    
    def write_settings_to_buf_file(self):
        for device_class in self.dict_active_device_class.values():
            write_data_to_buf_file(file = self.buf_file, message="Settings " + str(device_class.get_name()) + "\r")
            settings = device_class.get_settings()
            for set, key in zip(settings.values(), settings.keys()):
                write_data_to_buf_file(file = self.buf_file,message=str(key) + " - " + str(set) + "\r")

            for ch in device_class.channels:
                if ch.is_ch_active():

                    write_data_to_buf_file(file = self.buf_file,
                        message="Settings " + str(ch.get_name()) + "\r"
                    )
                    settings = ch.get_settings()
                    for set, key in zip(settings.values(), settings.keys()):
                        write_data_to_buf_file(file = self.buf_file,
                            message=str(key) + " - " + str(set) + "\r"
                        )

            write_data_to_buf_file(file = self.buf_file,message="--------------------\n")

    def push_button_save_installation(self):
            logger.debug("нажата кнопка сохранения установки")
            if self.way_to_save_installation_file == None:
                self.push_button_save_installation_as()
            else:
                self.write_data_to_save_installation_file(
                    self.way_to_save_installation_file
                )
                self.installation_window.setWindowTitle(
                    "Experiment control - " + self.way_to_save_installation_file + " " + self.version_app
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
            self.installation_window.setWindowTitle("Experiment control - " + fileName + " " + self.version_app)

    def extract_saved_installlation(self, fileName):
        status, buffer = self.read_info_by_saved_installation(fileName)
        self.show_window_installation()
        self.timer_open = QTimer()
        self.timer_open.timeout.connect(lambda: self.timer_open_timeout(buffer))
        self.timer_open.start(800)

    def timer_open_timeout(self, buffer):
        self.timer_open.stop()
        self.add_parameter_devices(buffer)

    # Saving data functions

    def write_data_to_save_installation_file(self, file_path: str):

        """
        Сохраняет данные об установке устройств в JSON файл.

        Args:
            file_path (str): Путь к файлу для сохранения данных.
        """

        install_dict: dict[str, dict[str, any]] = {}

        for device_class in self.dict_active_device_class.values():

            dev_name = device_class.get_name()
            install_dict[dev_name] = {"settings": device_class.get_settings(), "channels": {}}

            if hasattr(device_class, "JSON_temp"):
                install_dict[dev_name]["JSON_temp"] = device_class.JSON_temp

            for ch in device_class.channels:
                ch_name = ch.get_name()
                install_dict[dev_name]["channels"][ch_name] = {"settings": ch.get_settings()}

                is_ch_active = ch.is_ch_active()
                widget = self.get_channel_widget(dev_name, ch.get_number())
                state_text = widget.label_settings_channel.text()

                if is_ch_active:
                    install_dict[dev_name]["channels"][ch_name]["state"] = (
                        "active" if state_text != QApplication.translate('main install', "Не настроено") else "not settings"
                    )
                else:
                    install_dict[dev_name]["channels"][ch_name]["state"] = "not active"

        try:
            with open(file_path, 'w') as outfile:
                json.dump(install_dict, outfile, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка при записи в файл: {e}")

    def read_info_by_saved_installation(self, filename: str) -> tuple[bool, dict[str, any]]:

        """
        Читает информацию об установке из сохраненного JSON файла.
        Args:
            filename (str): Путь к файлу.
        Returns:
            Tuple[bool, Dict[str, Any]]: Кортеж, содержащий статус (True в случае успеха) и данные из файла.
        """

        try:
            with open(filename, "r") as file:
                buffer: dict[str, any] = json.load(file)

        except FileNotFoundError:
            logger.error(f"Файл {filename} не найден.")
            return False, {}

        except json.JSONDecodeError:
            logger.error(f"Ошибка декодирования JSON в файле {filename}.")
            return False, {}

        except Exception as e:
            logger.error(f"Произошла ошибка при чтении файла: {e}")
            return False, {}

        installation_list: list[str] = []
        json_devices: dict[str, any] = {}

        for device, data in buffer.items():
            device_name = device[:-2]
            if "JSON_temp" in data:
                json_devices[device_name] = data["JSON_temp"]
            else:
                installation_list.append(device_name)

        self.dict_active_device_class.clear()
        self.message_broker.clear_all()
        logger.info(f"Закрыто окно установки {self.installation_window}, реконструируем новое")

        self.close_window_installation()

        self.reconstruct_installation(installation_list, json_devices)


        return True, buffer

    def add_parameter_devices(self, buffer: dict[str, any]):

        """
        Добавляет параметры устройств и каналов на основе данных из буфера.
        Args:
            buffer (Dict[str, Any]): Словарь с данными об устройствах и каналах.
        """

        for key, data in buffer.items():

            if key not in self.dict_active_device_class:
                logger.warning(f"Устройство с ключом {key} не найдено в dict_active_device_class.")
                continue


            device = self.dict_active_device_class[key]
            settings_dev = data["settings"]
            device.set_parameters(settings_dev)


            for ch in device.channels:

                ch_name = ch.get_name()

                if "channels" not in data or ch_name not in data["channels"]:

                    log_message = QApplication.translate(
                        'main install',
                        f"Не найдены настройки канала {ch_name} у прибора {device.get_name()}"

                    )
                    self.add_text_to_log(text=log_message, status="err")

                else:

                    ch_data = data["channels"][ch_name]
                    is_open = ch_data.get("state") != "not active"
                    self.get_device_widget(device.get_name()).set_state_ch_widget(ch.number, is_open)
                    device.set_parameters_ch(ch_name, ch_data)

            self.get_device_widget(device.get_name()).update_widgets()

    def convert_buf_file(self):
        default_path_buf = os.path.join(os.getenv('USERPROFILE'), "AppData", "Local", "Installation_Controller")

        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        buf_file, ans = QtWidgets.QFileDialog.getOpenFileName(
            self.installation_window,
            "Выберите buf файл",
            default_path_buf,
            "text(*.txt)",
            options=options,
        )
        if ans == "text(*.txt)":
            options = QtWidgets.QFileDialog.Options()
            options |= QtWidgets.QFileDialog.DontUseNativeDialog
            result_file, ans = QtWidgets.QFileDialog.getSaveFileName(
                self.installation_window,
                QApplication.translate('base_install',"укажите путь сохранения результатов"),
                "",
                "Книга Excel (*.xlsx);; Text Files(*.txt)",
                #"Text Files(*.txt);; Книга Excel (*.xlsx);;Origin (*.opju)",
                options=options,
            )

            buf_session = measSession()
            buf_session.ask_session_name_description()
            result_name = buf_session.session_name
            result_description = buf_session.session_description

            if result_file:
                if ans == "Книга Excel (*.xlsx)":
                    process_and_export(
                    buf_file,
                    result_file,
                    type_save_file.excel,
                    result_name,
                    result_description,
                    False,
                    self.answer_save_results
                )
            else:
                print("не выбран файл сохранения результатов")
        else:
            print("Не выбран баф файл")
