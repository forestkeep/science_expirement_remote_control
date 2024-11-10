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
import math
import time
from enum import Enum
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer


logger = logging.getLogger(__name__)

not_ready_style_border = "border: 1px solid rgb(180, 0, 0); border-radius: 5px; QToolTip { color: #ffffff; background-color: rgb(100, 50, 50); border: 1px solid white;}"
not_ready_style_background = "background-color: rgb(100, 50, 50);  QToolTip { color: #ffffff; background-color: rgb(100, 50, 50); border: 1px solid white;}"

ready_style_border = "border: 1px solid rgb(0, 150, 0); border-radius: 5px; QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white;}"
ready_style_background = "background-color: rgb(50, 100, 50); QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white;}" 

warning_style_border = "border: 1px solid rgb(180, 180, 0); border-radius: 5px; QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white;}"
warning_style_background = "background-color: rgb(150, 160, 0); QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white;}"

not_ready_style_border_all_window = """
            QComboBox {
                border: 1px solid rgb(180, 0, 0);
                border-radius: 5px;
            }
            QCheckBox {
                border: 1px solid rgb(180, 0, 0);
                border-radius: 5px;
            }
            QToolTip { 
                color: #ffffff; 
                background-color: rgb(100, 50, 50); 
                border: 1px solid white;}
            """

ready_style_border_all_window = """
            QComboBox {
                border: 1px solid rgb(0, 150, 0);
                border-radius: 5px;
            }
            QCheckBox {
                border: 1px solid rgb(0, 150, 0);
                border-radius: 5px;
            }
            QToolTip { 
                color: #ffffff; 
                background-color: rgb(100, 50, 50); 
                border: 1px solid white;}
            """

class which_part_in_ch(Enum):
    bouth = 0
    only_meas = 1
    only_act = 2

class ch_response_to_step(Enum):
    End_list_of_steps = 0
    Step_done = 1
    Step_fail = 2
    Incorrect_ch = 3

class control_in_experiment():
    def __init__(self) -> None:
        self.priority = 1
        self.am_i_should_do_step = False
        self.am_i_active_in_experiment = False
        self.previous_step_time = False
        self.pause_time = False
        self.number_meas = 0
        self.setting_window = None
        self.time_of_action = 3# время, необходимое для совершения одного шага
        self.step_index = -1
        self.last_step_time = 5#хранит время, затраченное на последний сделанной шаг в эксперименте. Необходимо для подстройки продолжительности эксперимента

    def set_priority(self, priority: int) -> bool:
        self.priority = priority
        return True

    def get_priority(self) -> int:
        return self.priority

    def increment_priority(self):
        if self.priority > 1:
            self.priority = self.priority - 1
        else:
            self.priority = 1

    def get_status_step(self):
        return (self.am_i_should_do_step==True)


class base_device():
    """"base class for devices which used in installation"""

    def __init__(self, name, type_connection, installation_class) -> None:
        super().__init__()

        self.device_type = None
        self.is_debug = False
        self.is_test = False #флаг переводит прибор в режим теста, выдаются сырые данные от функций передачи и приема
        self.timer_for_scan_com_port = QTimer()
        self.timer_for_scan_com_port.timeout.connect(lambda: self._scan_com_ports())
        self.type_connection = type_connection
        self.installation_class = installation_class
        self.name = name
        self.setting_window = None

        self.message_broker = installation_class.message_broker

        self.number_steps = "3"

        self.client = None
        self.dict_buf_parameters = {
                                    "baudrate": "9600",
                                    "COM": None
                                    } 
        self.dict_settable_parameters = {}
        self.active_ports = []
        self.channels = []

        self.key_to_signal_func = False
        logger.debug(f"класс {self.name} создан")

    def set_name(self, name):
        self.name = name

    def get_object_ch(self, ch_name):
        for ch in self.channels:
            if ch.get_name() == ch_name:
                return ch
        return False
    
    def check_connect(self) -> bool: 
        """проверяет подключение прибора, если прибор отвечает возвращает True, иначе False"""
        response = "not defined"
        try:
            self.client.write(f"*IDN?\r\n")
            response = self.client.read()
        except:
            logger.info(f"у прибора {self.name} не определена функция проверки подключения")
        print(f"{response=}")
        return response if response not in [b'', b'\r\n', None] else False

    def base_settings_window(self):
            '''установка базовых параметров для окна настройки прибора'''
            if self.device_type == "oscilloscope":
                self.setting_window.setupUi(num_channels=self.total_number_of_channels)
            else:
                self.setting_window.setupUi()

            self.setting_window.boudrate.addItems(["50","75","110","150","300","600","1200","2400","4800","9600","19200","38400","57600","115200",])
            self.setting_window.setStyleSheet(ready_style_border_all_window)

            for combo in self.setting_window.findChildren(QtWidgets.QComboBox):
                combo.currentIndexChanged.connect(lambda: self._is_correct_parameters())
                combo.editTextChanged.connect(lambda: self._is_correct_parameters())
                combo.currentTextChanged.connect(lambda: self._is_correct_parameters())

            for check in self.setting_window.findChildren(QtWidgets.QCheckBox):
                check.stateChanged.connect(lambda: self._is_correct_parameters())

            if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_meas:
                self.setting_window.triger_meas_enter.addItems(["Таймер", "Внешний сигнал"])
                self.setting_window.triger_meas_enter.setEnabled(True)
                self.setting_window.triger_meas_enter.setStyleSheet(ready_style_border)

                self.setting_window.sourse_meas_enter.setStyleSheet(ready_style_border + "background-color: rgb(0, 0, 0);" )
                self.setting_window.num_meas_enter.setStyleSheet(ready_style_border)
                self.setting_window.num_meas_enter.setEditable(True)
                self.setting_window.num_meas_enter.addItems(["1"])

            if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_act:
                self.setting_window.triger_act_enter.addItems(["Таймер", "Внешний сигнал"])
                self.setting_window.triger_act_enter.setEnabled(True)
                self.setting_window.triger_act_enter.setStyleSheet(ready_style_border)

                self.setting_window.sourse_act_enter.setStyleSheet(ready_style_border)
                self.setting_window.sourse_act_enter.setStyleSheet(ready_style_border + "background-color: rgb(0, 0, 0);" )
                try:
                    self.setting_window.num_act_enter.setStyleSheet(ready_style_border)
                    self.setting_window.num_act_enter.setEditable(True)
                    self.setting_window.num_act_enter.addItems(["3"])
                except:
                    pass

            # =======================прием сигналов от окна==================
            if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_meas:
                self.setting_window.triger_meas_enter.currentIndexChanged.connect(lambda: self._action_when_select_trigger())
                self.setting_window.sourse_meas_enter.currentTextChanged.connect(lambda: self._is_correct_parameters())
                self.setting_window.num_meas_enter.currentTextChanged.connect(lambda: self._is_correct_parameters())

            if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_act:
                self.setting_window.triger_act_enter.currentIndexChanged.connect(lambda: self._action_when_select_trigger())
                self.setting_window.sourse_act_enter.currentTextChanged.connect(lambda: self._is_correct_parameters())
                try:
                    self.setting_window.num_act_enter.currentTextChanged.connect(lambda: self._is_correct_parameters())
                except:
                    pass#такого поля в приборе не предусмотрено
            self.setting_window.comportslist.currentTextChanged.connect(lambda: self._is_correct_parameters())
            self.setting_window.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.send_signal_ok)

    def base_show_window(func):
        def wrapper(self, *args, **kwargs):
            '''Устанавливает базовые параметры для канала действий при запуске окна'''

            #print(args[0])
            self.switch_channel(number=args[0])
            self.key_to_signal_func = False
            self.active_ports = []
            self.timer_for_scan_com_port.start(500)
            # Установка текущих параметров
            self.setting_window.comportslist.setCurrentText(self.dict_buf_parameters["COM"])
            self.setting_window.boudrate.setCurrentText(self.dict_buf_parameters["baudrate"])
            self.key_to_signal_func = True

            #print(f"{self.active_channel_act=}")
            #print(f"{self.active_channel_meas=}")

            if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_act:
                self.setting_window.triger_act_enter.setCurrentText(self.active_channel_act.dict_buf_parameters["trigger"])
                self.setting_window.sourse_act_enter.setCurrentText(str(self.active_channel_act.dict_buf_parameters["sourse/time"]))
                try:
                    num_act_list = ["5","10","20","50"]
                    if self.installation_class.get_signal_list(self.name, self.active_channel_act) != []:
                        num_act_list.append("Пока активны другие приборы")
                    self.setting_window.num_act_enter.clear()
                    self.setting_window.num_act_enter.addItems(num_act_list)
                    self.setting_window.num_act_enter.setCurrentText(str(self.active_channel_act.dict_buf_parameters["num steps"]))
                except:
                    pass

            if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_meas:
                self.setting_window.triger_meas_enter.setCurrentText(self.active_channel_meas.dict_buf_parameters["trigger"])
                self.setting_window.sourse_meas_enter.setCurrentText(str(self.active_channel_meas.dict_buf_parameters["sourse/time"]))
                num_meas_list = ["5","10","20","50"]
                if self.installation_class.get_signal_list(self.name, self.active_channel_meas) != []:
                    num_meas_list.append("Пока активны другие приборы")
                self.setting_window.num_meas_enter.clear()
                self.setting_window.num_meas_enter.addItems(num_meas_list)
                self.setting_window.num_meas_enter.setCurrentText(str(self.active_channel_meas.dict_buf_parameters["num steps"]))

            return func(self, *args, **kwargs)
        return wrapper

    def base_add_parameters_from_window(func):
        '''Добавляет базовые параметры из окна в локальный буфер класса прибора'''
        def wrapper(self, *args, **kwargs):
            if self.key_to_signal_func:
                if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_meas:
                        self.active_channel_meas.dict_buf_parameters["num steps"] = self.setting_window.num_meas_enter.currentText()
                        self.active_channel_meas.dict_buf_parameters["trigger"] = (self.setting_window.triger_meas_enter.currentText())
                        self.active_channel_meas.dict_buf_parameters["sourse/time"] = (self.setting_window.sourse_meas_enter.currentText())

                if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_act:
                    try:
                        self.active_channel_act.dict_buf_parameters["num steps"] = self.setting_window.num_act_enter.currentText()
                    except:
                        pass
    
                    self.active_channel_act.dict_buf_parameters["trigger"] = (self.setting_window.triger_act_enter.currentText())
                    self.active_channel_act.dict_buf_parameters["sourse/time"] = (self.setting_window.sourse_act_enter.currentText())

                self.dict_buf_parameters["baudrate"] = (self.setting_window.boudrate.currentText())
                self.dict_buf_parameters["COM"] = (self.setting_window.comportslist.currentText())
                return func(self, *args, **kwargs)
        return wrapper
    
    def base_is_correct_parameters(func) -> bool: 
        def wrapper(self, *args, **kwargs):
            if self.key_to_signal_func:
                func_result = func(self, *args, **kwargs)
                connnecting_sourse_correct = True

                if self.setting_window.comportslist.currentText() == "Нет подключенных портов":
                    connnecting_sourse_correct = False

                if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_meas:
                    self.active_channel_meas.is_num_steps_meas_correct = True
                    self.active_channel_meas.is_time_meas_correct = True
                    if self.setting_window.triger_meas_enter.currentText() == "Таймер":
                            try:
                                if int(self.setting_window.sourse_meas_enter.currentText()) < 1:
                                    self.active_channel_meas.is_time_meas_correct = False
                            except:
                                self.active_channel_meas.is_time_meas_correct = False

                    try:
                        if int(self.setting_window.num_meas_enter.currentText()) < 1:
                            self.active_channel_meas.is_num_steps_meas_correct = False
                    except:
                            try:
                                if self.setting_window.num_meas_enter.currentText() == "Пока активны другие приборы" \
                                    and self.installation_class.get_signal_list(self.name, self.active_channel_meas) != []:
                                    pass
                                else:
                                    self.active_channel_meas.is_num_steps_meas_correct = False
                            except:
                                pass
                    
                    self.setting_window.num_meas_enter.setStyleSheet(ready_style_border)

                    self.setting_window.sourse_meas_enter.setStyleSheet(ready_style_border)

                    if not self.active_channel_meas.is_time_meas_correct:
                            self.setting_window.sourse_meas_enter.setStyleSheet(not_ready_style_border)
                    try:
                        if not self.active_channel_meas.is_num_steps_meas_correct:
                                self.setting_window.num_meas_enter.setStyleSheet(not_ready_style_border)
                    except:
                        pass

                if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_act:
                    self.active_channel_act.is_num_steps_act_correct = True
                    self.active_channel_act.is_time_act_correct = True

                    if self.setting_window.triger_act_enter.currentText() == "Таймер":
                            try:
                                if int(self.setting_window.sourse_act_enter.currentText()) < 1:
                                    self.active_channel_act.is_time_act_correct = False
                            except:
                                self.active_channel_act.is_time_act_correct = False

                    if True:
                        try:
                            if int(self.setting_window.num_act_enter.currentText()) < 1:
                                self.active_channel_act.is_num_steps_act_correct = False
                        except:
                                if self.setting_window.num_act_enter.currentText() == "Пока активны другие приборы" \
                                and self.installation_class.get_signal_list(self.name, self.active_channel_act) != []:
                                    pass
                                else:
                                    self.active_channel_act.is_num_steps_act_correct = False
            
                        self.setting_window.num_act_enter.setStyleSheet(ready_style_border)

                    self.setting_window.sourse_act_enter.setStyleSheet(ready_style_border)

                    if not self.active_channel_act.is_time_act_correct:
                            self.setting_window.sourse_act_enter.setStyleSheet(not_ready_style_border)
                    try:
                        if not self.active_channel_act.is_num_steps_act_correct:
                                self.setting_window.num_act_enter.setStyleSheet(not_ready_style_border)
                    except:
                        pass

                if connnecting_sourse_correct == False:
                    self.setting_window.comportslist.setStyleSheet(not_ready_style_border)
                else:
                    self.setting_window.comportslist.setStyleSheet(ready_style_border)

                if self.part_ch == which_part_in_ch.bouth:
                    return      self.active_channel_act.is_num_steps_act_correct \
                            and self.active_channel_act.is_time_act_correct \
                            and self.active_channel_meas.is_num_steps_meas_correct \
                            and self.active_channel_meas.is_time_meas_correct \
                            and func_result
                elif self.part_ch == which_part_in_ch.only_meas:
                    return self.active_channel_meas.is_num_steps_meas_correct \
                            and self.active_channel_meas.is_time_meas_correct \
                            and func_result
                elif self.part_ch == which_part_in_ch.only_act:
                    return self.active_channel_meas.is_num_steps_act_correct \
                            and self.active_channel_meas.is_time_act_correct \
                            and func_result
                
            func_result = func(self, *args, **kwargs)
            return False and func_result
        return wrapper

    def set_debug(self, state):
        self.is_debug = state

    def create_channel_array(self):
        channels = []
        channels = self.create_act_channel_array(channels)
        channels = self.create_meas_channel_array(channels)
        return channels

    def create_meas_channel_array(self, channels):
        for i in range(1, 8): 
            channel_attr = f'ch{i}_meas'
            channel = getattr(self, channel_attr, None)
            if channel:
                channels.append(channel)
        if len(channels) > 0:
            self.ch1_meas.is_active = True#по умолчанию для каждого прибора включен первый канал
            self.active_channel_meas = self.ch1_meas #поле необходимо для записи параметров при настройке в нужный канал
        return channels
    
    def create_act_channel_array(self, channels):
        for i in range(1, 8): 
            channel_attr = f'ch{i}_act'
            channel = getattr(self, channel_attr, None)
            if channel:
                channels.append(channel)
        if len(channels) > 0:
            self.ch1_act.is_active = True#по умолчанию для каждого прибора включен первый канал
            self.active_channel_act = self.ch1_act #поле необходимо для записи параметров при настройке в нужный канал
        return channels

    def set_status_step(self, ch_name, status):
        '''сообщаем каналу прибору статус шага, должен проводить измерение или нет'''
        self.switch_channel(ch_name=ch_name)
        self.active_channel.am_i_should_do_step = status
        return True
    
    def get_label_parameters(self, number_ch):
        meas_param = None
        act_param = None
        if self.part_ch == which_part_in_ch.only_meas or self.part_ch == which_part_in_ch.bouth:
            for ch in self.channels:
                if ch.get_number() == number_ch and ch.get_type() == "meas":
                    meas_param = ch.dict_settable_parameters
                    break
        if self.part_ch == which_part_in_ch.only_act or self.part_ch == which_part_in_ch.bouth:
            for ch in self.channels:
                if ch.get_number() == number_ch and ch.get_type() == "act":
                    act_param = ch.dict_settable_parameters
                    break

        return act_param, meas_param, self.dict_settable_parameters
    
    def get_status_step(self, ch_name):
        """возвращает ответ на вопрос, "должен ли канал сделать шаг?" """
        self.switch_channel(ch_name = ch_name)
        return self.active_channel.get_status_step()

    def set_state_ch(self, ch_num, state):
        '''устанавливаем состояние канала в эксперименте, участвует или нет'''
        for ch in self.channels:
            if ch.get_number() == ch_num:
                ch.is_active = state

    def set_status_settings_ch(self, ch_num, state):
        '''устанавливаем статус настроек канала, если все ок, то ставим true, если нет, то false'''
        for ch in self.channels:
            if ch.get_number() == ch_num:
                ch.i_am_seted = state

    def switch_channel(self, number = None, ch_name = None):
            '''переключает активный канала либо по номеру, либо по имени. Если переключение по имени, то актвный канал будет доступен в 
            self.active_channel, если по номеру, то канала измерений будет в self.active_channel_meas, а канал действий в self.active_channel_act'''
            #print(f"{number=}")
            if number is not None:
                try:
                    number = int(number)
                except:
                    return False
                
                status = False
                for ch in self.channels:
                    #print(f"{ch=}")
                    if number == ch.number:
                        status = True
                        if ch.ch_type == "meas":
                            self.active_channel_meas = ch
                        if ch.ch_type == "act":
                            self.active_channel_act = ch

                return status
            
            elif ch_name is not None:
                for ch in self.channels:
                    if ch_name == ch.get_name():
                        self.active_channel = ch
                        return True
                return False
            
            return False
      
    def on_next_step(self, ch, repeat = 1):
        '''активирует следующий шаг канала прибора'''
        print(f"{self.name=} {ch.step_index = }")
        answer = ch_response_to_step.Step_done
        if ch.dict_settable_parameters["num steps"] == "Пока активны другие приборы":
            return answer
        if int(ch.step_index) < int(ch.dict_settable_parameters["num steps"])-1:
            ch.step_index = ch.step_index + 1
        else:
            print("конец списка шагов")
            answer = ch_response_to_step.End_list_of_steps  # след шага нет
        return answer

    def sin_wave(self, freq, amplitude, phase_shift, sample_rate):
            t = 0
            while True:
                value = amplitude * math.sin(2 * math.pi * freq * t + phase_shift)
                yield str(value)
                t += 1 / sample_rate

    def natural_log_generator(self):
        x = 0
        while True:
            yield str(math.log(1 + x))  # Рассчитываем натуральный логарифм для x
            x+=1

    def exponential_function_generator(self):
        x = 1
        try:
            while True:
                yield str(math.exp(x))
                x += 1
        except GeneratorExit:
            return 1
        
    def multiple_function_generator(self, degree):
        x = 0
        while True:
            yield str(x**degree)
            x+=1

    def get_name(self) -> str:
        return str(self.name)

    def _scan_com_ports(self):
        '''проверяет наличие ком портов в системе'''
        self.timer_for_scan_com_port.stop()

        local_list_com_ports = self.installation_class.get_list_resources()
        #print(f"{local_list_com_ports}")
        stop = False
        if local_list_com_ports == []:
            try:
                local_list_com_ports.append("Нет подключенных портов")
                self.setting_window.comportslist.setStyleSheet(not_ready_style_border)
            except:
                pass

        if local_list_com_ports == self.active_ports:
            pass
        else:
            try:
                current_val = self.setting_window.comportslist.currentText()
                self.setting_window.comportslist.clear()
                self.setting_window.comportslist.addItems(local_list_com_ports)
                self.setting_window.comportslist.setStyleSheet(ready_style_border)
                self.setting_window.comportslist.setStyleSheet(ready_style_border)
                self.setting_window.comportslist.setCurrentText(current_val)
            except:
                stop = True
        try:
            AllItems = [self.setting_window.comportslist.itemText(i) for i in range(self.setting_window.comportslist.count())]
            
            for i in range(1,len(AllItems), 1):
                if AllItems[i] == self.setting_window.comportslist.currentText() and i != self.setting_window.comportslist.currentIndex():
                    self.setting_window.comportslist.removeItem(i)
        except:
            pass

        if self.setting_window.comportslist.currentText() == "Нет подключенных портов" \
            or self.setting_window.comportslist.currentText() == "":
                self.setting_window.comportslist.setStyleSheet(not_ready_style_border)
        else:
                self.setting_window.comportslist.setStyleSheet(ready_style_border)
        
        self.active_ports = local_list_com_ports

        try:
            self.setting_window.isVisible()
        except:
            stop = True

        if not stop:
            self.timer_for_scan_com_port.start(1000)

    def get_type_connection(self) -> str:
        return self.type_connection

    def get_COM(self):
        try:
            answer = self.dict_settable_parameters["COM"]
        except:
            answer = False
        return answer

    def get_baud(self):
        try:
            answer = self.dict_settable_parameters["baudrate"]
        except:
            answer = False
        return answer

    def get_trigger_value(self, ch):
        '''возвращает источник сигнала или время в секундах, если в качестве триггера выбран таймер, в случае ошибки возвращает False'''
        trigger = self.get_trigger(ch)
        if trigger is None:
            logger.info(f"Ошибка при воозвате типа трриггера {trigger=}")
            answer = False

        elif trigger.lower() == "таймер":
            try:
                answer = int(ch.dict_settable_parameters["sourse/time"])
            except:
                answer = False
        elif trigger.lower() == "внешний сигнал":
            answer = ch.dict_settable_parameters["sourse/time"]
            
        else:
            answer = False
        
        return answer

    def get_trigger(self, ch):
        '''возвращает тип триггера, таймер или внешний сигнал'''
        #try:
        answer = None
        if "trigger" in ch.dict_settable_parameters.keys():
            answer = ch.dict_settable_parameters["trigger"]
        #except:
            #answer = None
        return answer

    def set_client(self, client):
        logger.info(f"установка клиента {self.name=} {client=}")
        self.client = client

    def get_steps_number(self, ch):
        '''возвращает число шагов прибора, если число не ограничено, то возвращает False'''
        try:
            answer = int(ch.dict_settable_parameters["num steps"])
        except:
            answer = False
        return answer

    def get_settings(self):
        return self.dict_settable_parameters

    def _action_when_select_trigger(self):
        if self.key_to_signal_func:
            if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_act:
                self.active_channel_act.dict_buf_parameters["sourse/time"] = self.setting_window.sourse_act_enter.currentText()
                if self.setting_window.triger_act_enter.currentText() == "Таймер":
                    try:
                        buf = int(self.active_channel_act.dict_buf_parameters["sourse/time"])
                    except:
                        buf = 5
                    self.setting_window.sourse_act_enter.clear()
                    self.setting_window.sourse_act_enter.setEditable(True)
                    self.setting_window.sourse_act_enter.addItems([str(buf), "10", "30", "60", "120"])
                    self.setting_window.sourse_act_enter.setCurrentText(str(buf))
                    self.setting_window.sourse_act_label.setText("Время(с)")
                else:
                    buf = self.active_channel_act.dict_buf_parameters["sourse/time"]
                    self.setting_window.sourse_act_enter.clear()
                    self.setting_window.sourse_act_enter.setEditable(False)
                    # предоставьте список сигналов, я прибор под именем self.name канал self.active_channel.name
                    #self.active_channel_act.signal_list = self.installation_class.get_signal_list(self.name, self.active_channel_act)
                    self.active_channel_act.signal_list = self.message_broker.get_subscribe_list(object = self.active_channel_act)

                    self.setting_window.sourse_act_enter.addItems(self.active_channel_act.signal_list)
                    if buf in self.active_channel_act.signal_list:
                        self.setting_window.sourse_act_enter.setCurrentText(buf)
                    self.setting_window.sourse_act_label.setText("Источник сигнала")
                current_style = self.setting_window.sourse_act_enter.styleSheet()
                self.setting_window.sourse_act_enter.setStyleSheet(current_style + "background-color: rgb(70, 70, 70);" )

            if self.part_ch == which_part_in_ch.bouth or self.part_ch == which_part_in_ch.only_meas:
                self.active_channel_meas.dict_buf_parameters["sourse/time"] = self.setting_window.sourse_meas_enter.currentText()
                if self.setting_window.triger_meas_enter.currentText() == "Таймер":
                    try:
                        buf = int(self.active_channel_meas.dict_buf_parameters["sourse/time"])
                        #print(f"{buf=}")
                    except:
                        buf = 5
                    self.setting_window.sourse_meas_enter.clear()
                    self.setting_window.sourse_meas_enter.setEditable(True)
                    self.setting_window.sourse_meas_enter.addItems([str(buf), "10", "30", "60", "120"])
                    self.setting_window.sourse_meas_enter.setCurrentText(str(buf))
                    self.setting_window.sourse_meas_label.setText("Время(с)")
                else:
                    buf = self.active_channel_meas.dict_buf_parameters["sourse/time"]
                    self.setting_window.sourse_meas_enter.clear()
                    self.setting_window.sourse_meas_enter.setEditable(False)
                    # предоставьте список сигналов, я прибор под именем self.name канал self.active_channel.number
                    #print(f"{self.message_broker.get_subscribe_list(object = self.active_channel_meas)=}")
                    #self.active_channel_meas.signal_list = self.installation_class.get_signal_list(self.name, self.active_channel_meas)
                    self.active_channel_meas.signal_list = self.message_broker.get_subscribe_list(object = self.active_channel_meas)


                    self.setting_window.sourse_meas_enter.addItems(self.active_channel_meas.signal_list)
                    if buf in self.active_channel_meas.signal_list:
                        self.setting_window.sourse_meas_enter.setCurrentText(buf)
                    self.setting_window.sourse_meas_label.setText("Источник сигнала")
                current_style = self.setting_window.sourse_meas_enter.styleSheet()
                self.setting_window.sourse_meas_enter.setStyleSheet(current_style + "background-color: rgb(70, 70, 70);" )

    def set_test_mode(self):
        self.is_test = True

    def reset_test_mode(self):
        self.is_test = False

    def action_end_experiment(self, ch) -> bool:
        '''плавное выключение прибора, возват к исходному состоянию'''
        self.switch_channel(ch_name=ch.get_name())
        status = True
        if ch.get_type() == "act":
            #===Действия по окончании работы прибора для канала действий===
            #self.active_channel.do_something()
            pass
            #==========end==========
        elif ch.get_type() == "meas":
            #===Действия по окончании работы прибора для канала измерений===
            pass
            #==========end==========

        return status

    def open_port(self):
        self.client.open()

    def set_parameters(self, channel_name, parameters):
        """функция необходима для настройки параметров канала в установке при добавлении прибора извне или при открытии сохраненной установки, передаваемый словарь гарантированно должен содержать параметры именно для данного канала"""
        self.switch_channel(ch_name = channel_name)
        status = True
        for param in parameters.keys():
            if param == "Не настроено":
                self.active_channel.set_active(True)
                status = False
                continue
            elif param == "not active":
                status = False
                self.active_channel.set_active(False)
                break
            else:
                self.active_channel.set_active(True)
                if parameters[param] == "False":
                    self.active_channel.dict_buf_parameters[param] = False
                elif parameters[param] == "True":
                    self.active_channel.dict_buf_parameters[param] = True
                else:
                    self.active_channel.dict_buf_parameters[param] = parameters[param]


                self.active_channel.dict_settable_parameters = self.active_channel.dict_buf_parameters
        if self.part_ch == which_part_in_ch.bouth:
            self.installation_class.message_from_device_settings(
                name_device = self.name,
                num_channel = self.active_channel.number,
                status_parameters = status,
                list_parameters_device = self.dict_settable_parameters,
                list_parameters_act = self.active_channel_act.dict_settable_parameters,
                list_parameters_meas = self.active_channel_meas.dict_settable_parameters
            )
        elif self.part_ch == which_part_in_ch.only_meas:
            self.installation_class.message_from_device_settings(
                name_device = self.name,
                num_channel = self.active_channel.number,
                status_parameters = status,
                list_parameters_device = self.dict_settable_parameters,
                list_parameters_meas = self.active_channel_meas.dict_settable_parameters
            )
        elif self.part_ch == which_part_in_ch.only_act:
            self.installation_class.message_from_device_settings(
                name_device = self.name,
                num_channel = self.active_channel.number,
                status_parameters = status,
                list_parameters_device = self.dict_settable_parameters,
                list_parameters_act = self.active_channel_act.dict_settable_parameters,
            )
        else:
            logger.warning("Неопределенный тип канала устройства" + self.get_name())

    def get_number_channels(self) -> int:
        return len(self.channels)
        
class base_ch(control_in_experiment):
    '''базовый класс канала устройства'''
    def __init__(self, number, ch_type, device_class, is_activate_standart_publish = True) -> None:
        super().__init__()
        self.device_class = device_class
        self.ch_type = ch_type
        self.number = number
        self.ch_name = f"ch-{self.number}_{self.ch_type}"
        self.i_am_seted = False
        self.is_active = False#канал включен или выключен(используется или нет)
        self.signal_list = []
        self.dict_settable_parameters = {}  # текущие параметры канала действий
        self.dict_buf_parameters = {"trigger": "Таймер",
                                    "sourse/time": str(10),  # секунды
                                    "num steps": "1",
                                    }

        self.message_broker = device_class.message_broker
        if is_activate_standart_publish:
            self.do_operation_trigger = f"{self.device_class.get_name()} {self.ch_name} do_operation"
            self.end_operation_trigger = f"{self.device_class.get_name()} {self.ch_name} end_work"
            self.message_broker.create_subscribe(name_subscribe = self.do_operation_trigger, publisher = self, description = "Канал прибора сделал какое-то действие или измерение")
            self.message_broker.create_subscribe(name_subscribe = self.end_operation_trigger, publisher = self, description = "Канал прибора закончил работу в эксперименте")



    def get_name(self):
        return self.ch_name
    
    def receive_message(self, message):
        '''функция приема сигнала от издателя, в данный момент по приему сообщения выставляется готовность сделать действие'''
        #print(message)
        self.am_i_should_do_step = True

    def get_settings(self):
        return self.dict_settable_parameters

    def set_active(self, state):
        self.is_active = state
    
    def is_ch_active(self) -> bool:
        return (self.is_active == True)
    
    def is_ch_seted(self) -> bool:
        return (self.i_am_seted == True)
    
    def get_number(self):
        return self.number
    
    def get_type(self):
        return self.ch_type
    

def time_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Метод {func.__name__} - {end_time - start_time} с")
        return result
    return wrapper

    
