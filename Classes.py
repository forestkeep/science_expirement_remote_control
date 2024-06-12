from enum import Enum
import pyvisa
import serial.tools.list_ports
from PyQt5.QtCore import QTimer, QDateTime
import copy
import logging
from Adapter import instrument
logger = logging.getLogger(__name__)


not_ready_style_border = "border: 1px solid rgb(180, 0, 0); border-radius: 5px; QToolTip { background-color: lightblue; color: black; border: 1px solid black; }"
not_ready_style_background = "background-color: rgb(100, 50, 50); QToolTip { background-color: lightblue; color: black; border: 1px solid black; }"

ready_style_border = "border: 1px solid rgb(0, 150, 0); border-radius: 5px;"
ready_style_background = "background-color: rgb(50, 100, 50);" 

warning_style_border = "border: 1px solid rgb(180, 180, 0); border-radius: 5px;"
warning_style_background = "background-color: rgb(150, 160, 0);"

class ch_response_to_step(Enum):
    End_list_of_steps = 0
    Step_done = 1
    Step_fail = 3

class control_in_experiment():
    def __init__(self) -> None:
        self.priority = 1
        self.am_i_should_do_step = False
        self.am_i_active_in_experiment = False
        self.previous_step_time = False
        self.pause_time = False
        self.number_meas = 0
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
        self.is_debug = False
        self.is_test = False #флаг переводит прибор в режим теста, выдаются сырые данные от функций передачи и приема
        self.timer_for_scan_com_port = QTimer()
        self.timer_for_scan_com_port.timeout.connect(
            lambda: self._scan_com_ports())
        # показывает тип подключения устройства, нужно для анализа, какие устройства могут быть подключены к одному ком порту
        #а так же для использования соответствуюшего модуля pyvisa или serial
        self.type_connection = type_connection
        self.installation_class = installation_class
        self.name = name
        self.setting_window = None

        # показывает количество шагов, сюда же сохраняется параметр из окна считывания настроек. В случае источников питания это поле просто не используется. Количество шагов вычисляется по массиву токов или напряжений
        self.number_steps = "3"

        self.client = None
        self.dict_buf_parameters = {
                                    "baudrate": "9600",
                                    "COM": None
                                    }  # потенциальные параметры прибора, вводятся когда выбираются значения в настройках, применяются только после подтверждения пользователем и прохождении проверок
        self.dict_settable_parameters = {}  # текущие параметры прибора
        # переменная хранит список доступных ком-портов
        self.active_ports = []
        self.channels = []
        # разрешает исполнение кода в функциях, срабатывающих по сигналам
        self.key_to_signal_func = False
        logger.debug(f"класс {self.name} создан")

    def set_name(self, name):
        self.name = name

    def set_debug(self, state):
        self.is_debug = state

    def set_status_step(self, ch_num, status):
        '''сообщаем каналу прибору статус шага, должен проводить измерение или нет'''
        self.switch_channel(ch_num)
        self.active_channel.am_i_should_do_step = status
        return True
    
    def get_status_step(self, ch_num):
        """возвращает ответ на вопрос, "должен ли канал сделать шаг?" """
        self.switch_channel(ch_num)
        return self.active_channel.get_status_step()

    def set_state_ch(self, ch_num, state):
        '''устанавливаем состояние канала в эксперименте, участвует или нет'''
        self.switch_channel(ch_num)
        self.active_channel.is_active = state

    def set_status_settings_ch(self, ch_num, state):
        '''устанавливаем статус настроек канала, если все ок, то ставим true, если нет, то false'''
        self.switch_channel(ch_num)
        self.active_channel.i_am_seted = state

    def switch_channel(self, number):
            try:
                number = int(number)
            except:
                return False
            
            for ch in self.channels:
                if number == ch.number:
                    self.active_channel = ch
                    return True
            return False
    
    def on_next_step(self, number_of_channel, repeat = 1):  #в случае активных приборов(например, источник питания) функция переопределяется в классе прибора
        '''активирует следующий шаг канала прибора'''
        self.switch_channel(number_of_channel)
        answer = ch_response_to_step.Step_done
        if self.active_channel.dict_buf_parameters["num steps"] == "Пока активны другие приборы":
            return answer
        if int(self.active_channel.step_index) < int(self.active_channel.dict_buf_parameters["num steps"])-1:
            self.active_channel.step_index = self.active_channel.step_index + 1
        else:
            answer = ch_response_to_step.End_list_of_steps  # след шага нет

        return answer

    def get_name(self) -> str:
        return str(self.name)

    def _scan_com_ports(self):
        '''проверяет наличие ком портов в системе'''
        self.timer_for_scan_com_port.stop()
        #ports = serial.tools.list_ports.comports()
        local_list_com_ports = instrument.get_resourses()
        #local_list_com_ports = []
        stop = False
        '''
        for port in ports:
            try:
                # Попытаемся открыть порт
                ser = serial.Serial(port.device)
                # Если порт успешно открыт, добавляем его в список активных портов
                local_list_com_ports.append(port.device)
                # Закрываем порт
                ser.close()
            except (OSError, serial.SerialException):
                pass

        rm = pyvisa.ResourceManager()

            # Получение списка всех доступных ресурсов
        resources = rm.list_resources()

        for resource in resources:
            try:
                # Создание соединения с каждым ресурсом
                instrument = rm.open_resource(resource)
                local_list_com_ports.append(resource)
                instrument.close()
            except:
                pass
        '''
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
            except:
                stop = True
        try:
            AllItems = [self.setting_window.comportslist.itemText(i) for i in range(self.setting_window.comportslist.count())]
            
            for i in range(1,len(AllItems), 1):
                if AllItems[i] == self.setting_window.comportslist.currentText() and i != self.setting_window.comportslist.currentIndex():
                    self.setting_window.comportslist.removeItem(i)
        except:
            pass
        
        self.active_ports = local_list_com_ports

        try:
            self.setting_window.isVisible()
        except:
            stop = True

        if not stop:
            self.timer_for_scan_com_port.start(1500)

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

    def get_trigger_value(self, number_of_channel):
        '''возвращает источник сигнала или время в секундах, если в качестве триггера выбран таймер, в случае ошибки возвращает False'''
        self.switch_channel(number_of_channel)
        trigger = self.get_trigger(number_of_channel)

        if trigger == "Таймер":
            try:
                answer = int(self.active_channel.dict_settable_parameters["sourse/time"])
            except:
                answer = False
        elif trigger == "Внешний сигнал":
            answer = self.active_channel.dict_settable_parameters["sourse/time"]
        else:
            answer = False
        
        return answer

    def get_trigger(self, number_of_channel):
        '''возвращает тип триггера, таймер или внешний сигнал'''
        self.switch_channel(number_of_channel)
        try:
            answer = self.active_channel.dict_settable_parameters["trigger"]
        except:
            answer = False
        return answer

    def set_client(self, client):
        self.client = client

    def get_steps_number(self, number_of_channel):
        '''возвращает число шагов прибора, если число не ограничено, то возвращает False'''
        self.switch_channel(number_of_channel)
        try:
            answer = int(self.active_channel.dict_settable_parameters["num steps"])
        except:
            answer = False
        return answer

    def get_settings(self, number_of_channel):
        self.switch_channel(number_of_channel)
        return {**self.dict_settable_parameters, **self.active_channel.dict_settable_parameters}

    def _action_when_select_trigger(self):
        if self.key_to_signal_func:
            if self.setting_window.triger_enter.currentText() == "Таймер":
                try:
                    buf = int(self.active_channel.dict_buf_parameters["sourse/time"])
                except:
                    buf = 5
                self.setting_window.sourse_enter.clear()
                self.setting_window.sourse_enter.setEditable(True)
                self.setting_window.sourse_enter.addItems(
                    [str(buf), "10", "30", "60", "120"])
                self.setting_window.sourse_enter.setCurrentText(str(buf))
                self.setting_window.label_sourse.setText("Время(с)")
            else:
                # buf = self.setting_window.sourse_enter.currentText()
                buf = self.active_channel.dict_buf_parameters["sourse/time"]
                self.setting_window.sourse_enter.clear()
                self.setting_window.sourse_enter.setEditable(False)
                # предоставьте список сигналов, я прибор под именем self.name канал self.active_channel.number
                self.active_channel.signal_list = self.installation_class.get_signal_list(
                    self.name, self.active_channel.number)
                signals = []
                for sig in self.active_channel.signal_list:
                    signals.append(str(sig[0])+" ch-"+str(sig[1]))
                self.setting_window.sourse_enter.addItems(signals)
                if buf in self.active_channel.signal_list:
                    self.setting_window.sourse_enter.setCurrentText(buf)
                self.setting_window.label_sourse.setText("Источник сигнала")
            # self.add_parameters_from_window()

    def set_test_mode(self):
        self.is_test = True

    def reset_test_mode(self):
        self.is_test = False

    def open_port(self):
        if self.client.is_open == False:
            self.client.open()

    def set_parameters(self,number_of_channel, parameters):
        """функция необходима для настройки параметров прибора в установке при добавлении прибора извне или при открытии сохраненной установки, передаваемый словарь гарантированно должен содержать параметры именно для данного прибора"""
        self.switch_channel(number_of_channel)
        status = True
        for param in parameters.keys():
            if param == "Не настроено":
                self.active_channel.set_active(True)
                status = False
                break
            elif param == "not active":
                status = False
                self.active_channel.set_active(False)
                break
            else:
                self.active_channel.set_active(True)
                
            if param == "COM" or param == "baudrate":
                self.dict_buf_parameters[param] = parameters[param]
                self.dict_settable_parameters[param] = parameters[param]
            else:
                self.active_channel.dict_buf_parameters[param] = parameters[param]
                self.active_channel.dict_settable_parameters[param] = parameters[param]

        self.installation_class.message_from_device_settings(
            self.name,self.active_channel.number, status, {**self.dict_settable_parameters, **self.active_channel.dict_settable_parameters})
        
class base_ch(control_in_experiment):
    '''базовый класс канала устройства'''
    def __init__(self, number) -> None:
        super().__init__()
        self.number = number
        self.i_am_seted = False
        self.is_active = False#канал включен или выключен(используется или нет)
        self.signal_list = []
        self.dict_buf_parameters = {"trigger": "Таймер",
                                    "sourse/time": str(10),  # секунды
                                    "num steps": 0,
                                    } 
        self.dict_settable_parameters = {}  # текущие параметры канала

    def set_active(self, state):
        self.is_active = state
    
    def is_ch_active(self) -> bool:
        return (self.is_active == True)
    
    def is_ch_seted(self) -> bool:
        return (self.i_am_seted == True)
    
