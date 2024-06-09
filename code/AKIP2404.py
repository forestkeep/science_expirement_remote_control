#MEAS?
#MEAS2?

from interface.set_voltmeter_window import Ui_Set_voltmeter
from PyQt5 import QtCore, QtWidgets
import PyQt5.sip
import serial.tools.list_ports
from PyQt5.QtCore import QTimer, QDateTime
import serial
from pymeasure.instruments.srs import SR830
from pymeasure.adapters import SerialAdapter
import copy
from commandsSR830 import commandsSR830
import time
from Classes import ch_response_to_step, base_device, ch_response_to_step, base_ch
from Classes import not_ready_style_border, not_ready_style_background, ready_style_border, ready_style_background, warning_style_border, warning_style_background
import logging
logger = logging.getLogger(__name__)

'''

Команда	                               Описание
[:SENSe]:VOLTage:AC:CH1	               Установить канал CH1 напряжения AC
[:SENSe]:VOLTage:AC:CH2	               Установить канал CH2 напряжения AC
[:SENSe]:VOLTage:AC:RANGe[:UPPer] 	   Выбрать диапазон (верхняя граница)
[:SENSe]:VOLTage:AC:RANGe[:UPPer]?	   Запросить текущий диапазон
[:SENSe]:VOLTage:AC:FILTer 	           Выбрать режим отображения 3½ или 4½
[:SENSe]:VOLTage:AC:FILTer?	           Запросить статус фильтра
[:SENSe]:VOLTage:AC:GND 	           Включить/выключить заземление
[:SENSe]:VOLTage:AC:GND?	           Проверить статус заземления
[:SENSe]:VOLTage:AC:RANGe:AUTO 	       Включить/выключить авторазбор диапазона
[:SENSe]:VOLTage:AC:RANGe:AUTO?	       Проверить статус авторазбора диапазона
:CALCulate:FUNCtion ""	               Выполнить математическую функцию
:CALCulate:FUNCtion?	               Запросить текущую математическую функцию
:SYSTem:VERSion?	                   Получить версию системы
IDN?	                               Получить строку идентификации прибора
*RST	                               Сбросить конфигурацию до включения
:TRG	                               Однократное запуск измерения
:TRIGger:SOURce { BUS	IMMediate}     Установить триггер начала измерения.  BUS - по команде с шины данных
:READ?	                               Получить измеренные данные
'''


class akip2404Class(base_device):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "serial", installation_class)
        #print("класс вольтметра")
        self.ch1 = ch_akip_class(1, self)
        self.ch2 = ch_akip_class(2, self)
        self.channels=[self.ch1, self.ch2]
        self.ch1.is_active = True#по умолчанию для каждого прибора включен первый канал
        self.active_channel = self.ch1 #поле необходимо для записи параметров при настройке в нужный канал
        self.device = None  # класс прибора будет создан при подтверждении параметров,
        # переменная хранит все возможные источники сигналов , сделать функцию, формирующую этот список в зависимости от структуры установки
        self.counter = 0
        # сюда при подтверждении параметров будет записан класс команд с клиентом
        self.command = None

    def get_number_channels(self) -> int:
        return len(self.channels)
    
    def show_setting_window(self, number_of_channel):
            
            self.switch_channel(number_of_channel)

            self.timer_for_scan_com_port = QTimer()
            self.timer_for_scan_com_port.timeout.connect(
                lambda: self._scan_com_ports())
            # при новом запуске окна настроек необходимо обнулять активный порт для продолжения сканирования
            self.active_ports = []

            # self.is_window_created - True
            self.setting_window = Ui_Set_voltmeter()
            self.setting_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            self.setting_window.setupUi(self.setting_window)

            # +++++++++++++++++выбор ком порта+++++++++++++
            self._scan_com_ports()
            # ++++++++++++++++++++++++++++++++++++++++++

            self.setting_window.boudrate.addItems(
                ["50", "75", "110", "150", "300", "600", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])

            #self.setting_window.sourse_enter.setStyleSheet(
             #   "background-color: rgb(255, 255, 255);")

            # self.setting_window.sourse_enter.setEditable(True)
            # self.setting_window.sourse_enter.addItems(
            # ["5", "10", "30", "60", "120"])
            self.setting_window.triger_enter.addItems(["Таймер", "Внешний сигнал"])
            
            self.setting_window.range_enter.addItems(
                ["Auto","3mV", "30mV", "300mV", "3V", "30V", "300V"])
            
            self.setting_window.type_work_enter.addItems(
                ["Напряжение"])

            self.setting_window.triger_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.sourse_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.comportslist.setStyleSheet(
                ready_style_border)
            self.setting_window.boudrate.setStyleSheet(
                ready_style_border)
            self.setting_window.num_meas_enter.setStyleSheet(
                ready_style_border)
            
            self.setting_window.type_work_enter.setStyleSheet(
                ready_style_border)
            
            self.setting_window.range_enter.setStyleSheet(
                ready_style_border)


            self.setting_window.num_meas_enter.setEditable(True)
            self.setting_window.num_meas_enter.addItems(
                ["3"])

            # =======================прием сигналов от окна==================

            self.setting_window.triger_enter.currentIndexChanged.connect(
                lambda: self._action_when_select_trigger())

            self.setting_window.num_meas_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.sourse_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())

            self.setting_window.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(
                self.send_signal_ok)
            # ======================================================
            self.setting_window.show()
            self.key_to_signal_func = False
            # ============установка текущих параметров=======================

            self.setting_window.type_work_enter.setCurrentText(self.active_channel.dict_buf_parameters["type_meas"])
            self.setting_window.range_enter.setCurrentText(self.active_channel.dict_buf_parameters["range"])

            self.setting_window.sourse_enter.setCurrentText(self.active_channel.dict_buf_parameters["sourse/time"])
            self.setting_window.boudrate.setCurrentText(self.dict_buf_parameters["baudrate"])

            self.setting_window.comportslist.addItem(self.dict_buf_parameters["COM"])
            self.setting_window.triger_enter.setCurrentText(self.active_channel.dict_buf_parameters["trigger"])
            num_meas_list = ["5","10","20","50"]
            if self.installation_class.get_signal_list(self.name, self.active_channel.number) != []:#если в списке сигналов пусто, то и других активных приборов нет, текущий прибор в установке один
                num_meas_list.append("Пока активны другие приборы")
            self.setting_window.num_meas_enter.addItems(num_meas_list)
            self.setting_window.num_meas_enter.setCurrentText(
                str(self.number_steps))

            self.setting_window.sourse_enter.setCurrentText(
                self.active_channel.dict_buf_parameters["sourse/time"])

            self.key_to_signal_func = True  # разрешаем выполенение функций
            self._action_when_select_trigger()

    def _is_correct_parameters(self) -> bool:  # менять для каждого прибора
        if self.key_to_signal_func:
            # print("проверить параметры")
            is_num_steps_correct = True
            is_time_correct = True
# число илии нет
            try:
                int(self.setting_window.num_meas_enter.currentText())
            except:
                if self.setting_window.num_meas_enter.currentText() == "Пока активны другие приборы" and self.installation_class.get_signal_list(self.name, self.active_channel.number) != []:
                    pass
                else:
                    is_num_steps_correct = False

            if self.setting_window.triger_enter.currentText() == "Таймер":
                try:
                    int(self.setting_window.sourse_enter.currentText())
                except:
                    is_time_correct = False


            self.setting_window.num_meas_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.sourse_enter.setStyleSheet(
                ready_style_border)

            if not is_num_steps_correct:
                self.setting_window.num_meas_enter.setStyleSheet(
                    not_ready_style_border)

            if not is_time_correct:
                self.setting_window.sourse_enter.setStyleSheet(
                    not_ready_style_border)

            if is_num_steps_correct and is_time_correct:
                return True
            else:
                return False

    def change_units(self):
        pass

    def add_parameters_from_window(self):
        try:
            self.number_steps = int(
                self.setting_window.num_meas_enter.currentText())
        except:
            if self.setting_window.num_meas_enter.currentText() == "":
                self.number_steps = self.setting_window.num_meas_enter.currentText()
            else:
                self.number_steps = "Пока активны другие приборы"

        if self.key_to_signal_func:

            self.active_channel.dict_buf_parameters["num steps"] = self.number_steps

            self.active_channel.dict_buf_parameters["type_meas"] = self.setting_window.type_work_enter.currentText(
            )

            self.active_channel.dict_buf_parameters["range"] = self.setting_window.range_enter.currentText(
            )

            self.active_channel.dict_buf_parameters["trigger"] = self.setting_window.triger_enter.currentText(
            )
            self.active_channel.dict_buf_parameters["sourse/time"] = self.setting_window.sourse_enter.currentText()

            self.dict_buf_parameters["baudrate"] = self.setting_window.boudrate.currentText(
            )
            self.dict_buf_parameters["COM"] = self.setting_window.comportslist.currentText(
            )

    def send_signal_ok(self):  # действие при подтверждении настроек, передать парамтры классу инсталляции, проверить и окрасить в цвет окошко, вписать паарметры
        self.add_parameters_from_window()
        # те же самые настройки, ничего не делаем
        if (self.active_channel.dict_buf_parameters == self.active_channel.dict_settable_parameters and self.dict_buf_parameters == self.dict_settable_parameters):
            #return
            pass
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.active_channel.dict_settable_parameters = copy.deepcopy(self.active_channel.dict_buf_parameters)

        is_parameters_correct = True
        if self.dict_buf_parameters["COM"] == 'Нет подключенных портов':
            is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

        if not self._is_correct_parameters():
            is_parameters_correct = False

        if is_parameters_correct:
            pass
        else:
            pass

        self.installation_class.message_from_device_settings(
            self.name,
            self.active_channel.number,
            is_parameters_correct,
            {
                **self.dict_settable_parameters,
                **self.active_channel.dict_settable_parameters,
            },
        )

    # фцункция подтверждения корректности параметров от контроллера установкию. установка проверяет ком порты, распределяет их между устройствами и отдает каждому из устройств
    def confirm_parameters(self):
        #print(str(self.name) +
        #      " получил подтверждение настроек, рассчитываем шаги")
        if True:

            for ch in self.channels:
                if ch.is_ch_active():
                    ch.step_index = -1
        else:
            pass
    # настройка прибора перед началом эксперимента, переопределяется при каждлом старте эксперимента

    def action_before_experiment(self, number_of_channel) -> bool:  # менять для каждого прибора
        self.switch_channel(number_of_channel)
        self.select_channel(channel = self.active_channel.number)
        print(
            f"настройка канала {number_of_channel} прибора "
            + str(self.name)
            + " перед экспериментом.."
        )
        
        status = True
        if self.active_channel.dict_settable_parameters["range"] != "Auto":
            try:
                strip = self.active_channel.dict_buf_parameters["range"][-2:]
                if strip == "mV":
                    val = float(self.active_channel.dict_buf_parameters["range"][0:-2:])/1000
                else:
                    val = float(self.active_channel.dict_buf_parameters["range"][0:-1:])
                ans = self.set_parameter(command = ':SENSe:VOLTage:AC:RANGe:UPPer',timeout = 1,param = val)
                print(f"{ans=}")
                if ans == False:
                    status = False
            except ValueError as e:
                print("Ошибка преобразования строки в число(АКИП2404):", e)
        else:
            pass
            #TODO: проверить, включен ли режим авто, если нет, то включить
            #[:SENSe]:VOLTage:AC:RANGe:AUTO 	Включить/выключить авторазбор диапазона
            #[:SENSe]:VOLTage:AC:RANGe:AUTO?

        return status

    def action_end_experiment(self, number_of_channel) -> bool:
        '''плавное выключение прибора'''
        self.switch_channel(number_of_channel)
        return True

    def do_meas(self, number_of_channel):
        '''прочитать текущие и настроенные значения'''
        self.switch_channel(number_of_channel)
        print("делаем измерение", self.name)

        start_time = time.time()
        parameters = [self.name + " ch-" + str(self.active_channel.number)]
        is_correct = True

        is_stop_analyze = False
        count = 0
        result_analyze = False
        if not self.is_debug:
            pass
            
        
        voltage = self._get_current_voltage(self.active_channel.number)
        if voltage is not False:
            val = ["voltage=" + str(voltage)]
            parameters.append(val)
        else:
            is_correct = False

        # -----------------------------
        if self.is_debug:
            if is_correct == False:
                is_correct = True
                parameters.append(["voltage=" + str(254)])
        # -----------------------------

        if is_correct:
            print("сделан шаг", self.name)
            ans = ch_response_to_step.Step_done
        else:
            print("Ошибка шага", self.name)
            val = ["voltage=" + "fail"]
            parameters.append(val)

            ans = ch_response_to_step.Step_fail

        return ans, parameters, time.time() - start_time

    def _get_current_voltage(self, ch_num) -> float:
        '''возвращает значение установленного напряжения канала'''
        self.open_port()
        self.select_channel(ch_num)
        response = self.get_parameter('READ', 1)
        print("ответ на запрос v",response )
        if response is not False:
            num, ed = response[:6], response[6:].strip() if response != False else (None, None)
        try:
            response = float(num) / 1000 if ed == "mV" else float(num)
        except:
            response = False
        self.client.close()
        return  response
    
    def set_parameter(self, command, timeout, param):
        self.open_port()
        param = str(param)
        self.client.write(bytes(command, "ascii") +
                              b' ' + bytes(param, "ascii") + b'\r\n')
        
        print(bytes(command, "ascii") + b' ' + bytes(param, "ascii") + b'\r\n')

        start_time = time.time()
        while time.time() - start_time < timeout:
            line = self.client.readline().decode().strip()
            if line:
                print("Received:", line)
                return line
        return False

    def get_parameter(self, command, timeout, param=False):
        self.open_port()
        if param == False:
            self.client.write(bytes(command, "ascii") + b'?\r\n')
        else:
            param = str(param)
            self.client.write(bytes(command, "ascii") +
                              b'? ' + bytes(param, "ascii") + b'\r\n')
        if param != False:
            print("чтение параметров", bytes(command, "ascii") +
                  b'? ' + bytes(param, "ascii") + b'\r\n')
        else:
            print(bytes(command, "ascii") + b'?\r\n')

        start_time = time.time()
        while time.time() - start_time < timeout:
            line = self.client.readline().decode().strip()
            if line:
                print("Received:", line)
                return line
        return False
    
    def check_connect(self) -> bool:
        line = self.get_parameter("*IDN", timeout=1)
        ver = self.get_parameter(":SYSTem:VERSion", timeout=1)
        if line is not False and ver is not False:
            print(line + " "+ ver)
            return True
        return False

    def open_port(self):
        if self.client.is_open == False:
            self.client.open()

    def select_channel(self, channel):
        self.open_port()	
        self.client.write(f':VOLTage:AC:CH{channel}\n'.encode())

class ch_akip_class(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number)
        #print(f"канал {number} создан")
        #print(self.am_i_should_do_step, "ацаыввыаваываываывыаывываываываываываывавыаывыыв")
        self.base_duration_step = 0.1#у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.dict_buf_parameters["type_meas"] = "Напряжение"  # секунды
        self.dict_buf_parameters["range"] = "Auto"  # dB
        self.dict_buf_parameters["num steps"] = "1"
        
if __name__ == "__main__":


    
    pass