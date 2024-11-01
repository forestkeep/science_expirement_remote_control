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

import copy
import logging
import math
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import serial
import serial.tools.list_ports

from Devices.Classes import (base_ch, base_device, ch_response_to_step,
                     not_ready_style_border,
                     ready_style_border,
                     which_part_in_ch)
from Devices.interfase.Set_immitance_window import Ui_Set_immitans

logger = logging.getLogger(__name__)

class CommandsMNIPI:
    def __init__(self) -> None:
        self.PUSH_MENU = 1
        self.PUSH_RIGHT = b''
        self.PUSH_Z = b''
        self.PUSH_R = b''
        self.PUSH_DOWN = b''
        self.PUSH_ENTER = b''
        self.PUSH_UP = b''
        self.PUSH_L = b''
        self.PUSH_CALL = b''
        self.PUSH_LEFT = b''
        self.PUSH_I = b''
        self.PUSH_C = b''
        self.CHANGE_SHIFT=b''
        self.CHANGE_FREQ=  ''
        self.CHANGE_LEVEL=b''
        self.CHANGE_RANGE = b''  # = 

class mnipiE720Class(base_device):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "serial", installation_class)

        self.part_ch = which_part_in_ch.only_meas#указываем, из каких частей состоиит канал в данном приборе 
        self.setting_window = Ui_Set_immitans()
        self.base_settings_window()

        self.setting_window.frequency_enter.setEditable(True)
        self.setting_window.frequency_enter.addItems(["400"])
        self.setting_window.level_enter.setEditable(True)
        self.setting_window.level_enter.addItems(["1"])
        self.setting_window.shift_enter.setEditable(True)
        self.setting_window.shift_enter.addItems(["0"])

            
        self.commands = CommandsMNIPI()
        self.ch1_meas = ch_mnipi_class(1, self)
        self.channels = self.create_channel_array()
        self.device = None  # класс прибора будет создан при подтверждении параметров,

        self.counter = 0
        self.dict_meas_param = {'|Z|':self.commands.PUSH_Z,
                                "Rp" :self.commands.PUSH_R,
                                "Lp" :self.commands.PUSH_L,
                                'I'  :self.commands.PUSH_I,
                                'Ср' :self.commands.PUSH_C
        }
        # сюда при подтверждении параметров будет записан класс команд с клиентом
        self.command = None

    @base_device.base_show_window
    def show_setting_window(self, number_of_channel):
            
            self.switch_channel(number_of_channel)
            self.key_to_signal_func = False

            # ============установка текущих параметров=======================

            self.setting_window.shift_enter.setCurrentText(str(self.active_channel_meas.dict_buf_parameters["offset"]))
            self.setting_window.frequency_enter.setCurrentText(str(self.active_channel_meas.dict_buf_parameters["frequency"]))
            self.setting_window.level_enter.setCurrentText(str(self.active_channel_meas.dict_buf_parameters["level"]))
            
            self.setting_window.check_capacitance.setChecked(self.active_channel_meas.dict_buf_parameters["meas C"] == True)
            self.setting_window.check_resistance.setChecked(self.active_channel_meas.dict_buf_parameters["meas R"] == True)
            self.setting_window.check_impedance.setChecked(self.active_channel_meas.dict_buf_parameters["meas Z"] == True)
            self.setting_window.check_inductor.setChecked(self.active_channel_meas.dict_buf_parameters["meas L"] == True)
            self.setting_window.check_current.setChecked(self.active_channel_meas.dict_buf_parameters["meas I"] == True)

            self.key_to_signal_func = True  # разрешаем выполенение функций
            self._action_when_select_trigger()
            self._is_correct_parameters()
            self.setting_window.show()

    @base_device.base_is_correct_parameters
    def _is_correct_parameters(self) -> bool:  # менять для каждого прибора
        if self.key_to_signal_func:
            # print("проверить параметры")

            is_shift_correct = True
            is_level_correct = True
            is_freq_correct = True
            is_num_steps_correct = True
            is_time_correct = True

            try:
                float(self.setting_window.level_enter.currentText())
            except:
                is_level_correct = False
            try:
                float(self.setting_window.frequency_enter.currentText())
            except:
                is_freq_correct = False

            try:
                float(self.setting_window.shift_enter.currentText())
            except:
                is_shift_correct = False

            if is_level_correct:
                if float(self.setting_window.level_enter.currentText()) > 100 or float(self.setting_window.level_enter.currentText()) < 0:
                    is_level_correct = False
            if is_freq_correct:
                if float(self.setting_window.frequency_enter.currentText()) > 1000000 or float(self.setting_window.frequency_enter.currentText()) < 25:
                    is_freq_correct = False
            if is_shift_correct:
                if float(self.setting_window.shift_enter.currentText()) > 40 or float(self.setting_window.shift_enter.currentText()) < 0:
                    is_shift_correct = False
            # ----------------------------------------
            
            self.setting_window.shift_enter.setStyleSheet(ready_style_border)
            self.setting_window.level_enter.setStyleSheet(ready_style_border)
            self.setting_window.frequency_enter.setStyleSheet(ready_style_border)
  
            is_meas_checked = False
            if self.setting_window.check_capacitance.isChecked():
                is_meas_checked = True
            if self.setting_window.check_resistance.isChecked():
                is_meas_checked = True
            if self.setting_window.check_impedance.isChecked():
                is_meas_checked = True
            if self.setting_window.check_inductor.isChecked():
                is_meas_checked = True
            if self.setting_window.check_current.isChecked():
                is_meas_checked = True

            if is_meas_checked == False:
                self.setting_window.check_current.setStyleSheet(not_ready_style_border)
                self.setting_window.check_inductor.setStyleSheet(not_ready_style_border)
                self.setting_window.check_impedance.setStyleSheet(not_ready_style_border)
                self.setting_window.check_resistance.setStyleSheet(not_ready_style_border)
                self.setting_window.check_capacitance.setStyleSheet(not_ready_style_border)
            else:
                self.setting_window.check_current.setStyleSheet(ready_style_border)
                self.setting_window.check_inductor.setStyleSheet(ready_style_border)
                self.setting_window.check_impedance.setStyleSheet(ready_style_border)
                self.setting_window.check_resistance.setStyleSheet(ready_style_border)
                self.setting_window.check_capacitance.setStyleSheet(ready_style_border)

            if not is_shift_correct:
                self.setting_window.shift_enter.setStyleSheet(not_ready_style_border)
            if not is_freq_correct:
                self.setting_window.frequency_enter.setStyleSheet(not_ready_style_border)
            if not is_level_correct:
                self.setting_window.level_enter.setStyleSheet(not_ready_style_border)
            if not is_time_correct:
                self.setting_window.sourse_meas_enter.setStyleSheet(not_ready_style_border)

            return (is_shift_correct and is_level_correct and is_freq_correct and is_num_steps_correct and is_time_correct and is_meas_checked)

        return False

    @base_device.base_add_parameters_from_window
    def add_parameters_from_window(self):

        if self.key_to_signal_func:
            #self.base_add_parameters_from_window()
            self.active_channel_meas.dict_buf_parameters["offset"] = float(self.setting_window.shift_enter.currentText())
            self.active_channel_meas.dict_buf_parameters["frequency"] = float(self.setting_window.frequency_enter.currentText())
            self.active_channel_meas.dict_buf_parameters["level"] = float(self.setting_window.level_enter.currentText())
            self.active_channel_meas.dict_buf_parameters["meas L"] = self.setting_window.check_inductor.isChecked() 
            self.active_channel_meas.dict_buf_parameters["meas R"] = self.setting_window.check_resistance.isChecked()
            self.active_channel_meas.dict_buf_parameters["meas I"] = self.setting_window.check_current.isChecked()
            self.active_channel_meas.dict_buf_parameters["meas C"] = self.setting_window.check_capacitance.isChecked()
            self.active_channel_meas.dict_buf_parameters["meas Z"] = self.setting_window.check_impedance.isChecked()


    def send_signal_ok(self):  # действие при подтверждении настроек, передать парамтры классу инсталляции, проверить и окрасить в цвет окошко, вписать паарметры
        self.add_parameters_from_window()
        # те же самые настройки, ничего не делаем
        if (self.active_channel_meas.dict_buf_parameters == self.active_channel_meas.dict_settable_parameters and self.dict_buf_parameters == self.dict_settable_parameters):
            pass
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.active_channel_meas.dict_settable_parameters = copy.deepcopy(self.active_channel_meas.dict_buf_parameters)

        is_parameters_correct = True
        if self.dict_buf_parameters["COM"] == 'Нет подключенных портов':
            is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

        if not self._is_correct_parameters():
            is_parameters_correct = False

        self.installation_class.message_from_device_settings(
            name_device = self.name,
            num_channel = self.active_channel_meas.number,
            status_parameters = is_parameters_correct,
            list_parameters_device = self.dict_settable_parameters,
            #list_parameters_act = self.active_channel_act.dict_settable_parameters,
            list_parameters_meas = self.active_channel_meas.dict_settable_parameters
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
        #print(f"настройка канала {number_of_channel} прибора "+ str(self.name)+ " перед экспериментом..")
        logger.debug(f"настройка канала {number_of_channel} прибора "+ str(self.name)+ " перед экспериментом..")
        pause = 0.1
        status = True
        #TODO: настройка перед экспериментов, установить частоту, уровень и смещение
        return status

    def do_meas(self, ch):
        '''прочитать текущие и настроенные значения'''
        self.switch_channel(ch_name=ch.get_name())
        #print("делаем измерение", self.name)

        start_time = time.time()
        parameters = [self.name + " " + str(ch.get_name())]
        is_correct = True

        if self.active_channel_meas.dict_settable_parameters["meas L"] == True:
                self.open_port()
                val, val2, status = self.meas_focus_parameter(focus_val="Lp", attempts=10)
                parameters.append(val)
                parameters.append(val2)
                self.client.close()

        if self.active_channel_meas.dict_settable_parameters["meas R"] == True:
                self.open_port()
                val, val2, status = self.meas_focus_parameter(focus_val="Rp", attempts=10)
                parameters.append(val)
                parameters.append(val2)
                self.client.close()

        if self.active_channel_meas.dict_settable_parameters["meas I"] == True:
                self.open_port()
                val, val2, status = self.meas_focus_parameter(focus_val='I', attempts=10)
                parameters.append(val)
                parameters.append(val2)
                self.client.close()

        if self.active_channel_meas.dict_settable_parameters["meas C"] == True:
                self.open_port()
                val, val2, status = self.meas_focus_parameter(focus_val='Ср', attempts=10)
                parameters.append(val)
                parameters.append(val2)
                self.client.close()

        if self.active_channel_meas.dict_settable_parameters["meas Z"] == True:
                self.open_port()
                val, val2, status = self.meas_focus_parameter(focus_val='|Z|', attempts=10)
                parameters.append(val)
                parameters.append(val2)
                self.client.close()

        if self.is_debug:
            is_correct = True

        if is_correct:
            #print("сделан шаг", self.name)
            ans = ch_response_to_step.Step_done
        else:
            #ans = ch_response_to_step.Step_fail
            ans = ch_response_to_step.Step_done

        return ans, parameters, time.time() - start_time


    def meas_focus_parameter(self, focus_val, attempts):
                logger.debug(f"измеряем {focus_val}")
                i=0
                if focus_val not in self.dict_meas_param.keys():
                    i = attempts#False

                while i < attempts:
                    self.client.write(self.dict_meas_param[focus_val])
                    print(f"{self.dict_meas_param[focus_val]=}")
                    param = False
                    param = self.read_parameters(self.client, self.is_debug)
                    logger.debug(f"попытка {i+1}, ответ {param}")
                    if param is not False:
                        if param[6] == focus_val:
                            val = [f"{focus_val}=" + str(param[9])]
                            val2 = [f"{param[7]}=" + str(param[8])]
                            return val, val2, True
                    i+=1

                val = [f"{focus_val}=" + "fail"]
                val2 = [f"sec=" + "fail"]
                return val, val2, False
                    
    def decode_parameters(self, buffer):
        def process_block_sec_param(BlockIn):
            switcher = {
                0: (1, 'k'), 1: (2, 'k'), 2: (3, 'k'), 3: (4, 'M'), 4: (3, 'M'),
                5: (4, 'M'), 6: (2, 'G'), 7: (3, 'G'), 8: (4, 'G'), 9: (2, 'T'),
                10: (3, 'T'), 11: (4, 'T'), 12: (2, 'T'), 13: (3, 'T'), 14: (4, 'T'),
                255: (4, ' '), 254: (3, ' '), 253: (2, ' '), 252: (1, 'm'), 251: (4, 'm'),
                250: (3, 'm'), 249: (2, 'mk'), 248: (1, 'mk'), 247: (2, 'mk'), 246: (4, 'n'),
                245: (3, 'n'), 244: (2, 'n'), 243: (4, 'p'), 242: (3, 'p'), 241: (2, 'p'),
                240: (1, 'f'), 239: (2, 'f'), 238: (3, 'f'), 237: (4, 'f'), 236: (1, 'f'), 235: (2, 'f')
            }
            multipliers_dict = {
                                    'k': 1000,
                                    'M': 1000000,
                                    'G': 1000000000,
                                    'T': 1000000000000,
                                    'P': 1000000000000000,
                                    'm': 0.001,
                                    'mk': 0.000001,
                                    'n': 0.000000001,
                                    'p': 0.000000000001,
                                    'f': 0.000000000000001
                                }
            if (BlockIn[14] & 128) != 0:
                BlockIn[12] ^= 255
                BlockIn[13] ^= 255
                BlockIn[14] ^= 255
                DQVal = -1 - BlockIn[12] - (BlockIn[13] + BlockIn[14] * 256) * 256
            else:
                DQVal = BlockIn[12] + (BlockIn[13] + BlockIn[14] * 256) * 256

            m, Text = switcher.get(BlockIn[15], (0, ''))
            DQVal /= 10 ** (5 - m)
            if Text in multipliers_dict.keys():
                DQVal*=multipliers_dict[Text]
            else:
                DQVal = 999999999
            return DQVal
        
        def process_block_pry_param(BlockIn):
            switcher = {
                0: (2, 'k'), 1: (3, 'k'), 2: (4, 'k'),
                3: (2, 'M'), 4: (3, 'M'), 5: (4, 'M'),
                6: (2, 'G'), 7: (3, 'G'), 8: (4, 'G'),
                9: (2, 'T'), 10: (3, 'T'), 11: (4, 'T'),
                12: (2, 'P'), 13: (3, 'P'), 14: (4, 'P'),
                255: (4, ' '), 254: (3, ' '), 253: (2, ' '),
                252: (4, 'm'), 251: (3, 'm'), 250: (2, 'm'),
                249: (4, 'mk'), 248: (3, 'mk'), 247: (2, 'mk'),
                246: (4, 'n'), 245: (3, 'n'), 244: (2, 'n'),
                243: (4, 'p'), 242: (3, 'p'), 241: (2, 'p'),
                240: (4, 'f'), 239: (3, 'f'), 238: (2, 'f'),
                237: (4, 'f'), 236: (3, 'f'), 235: (2, 'f')
            }
            multipliers_dict = {
                                    'k': 1000,
                                    'M': 1000000,
                                    'G': 1000000000,
                                    'T': 1000000000000,
                                    'P': 1000000000000000,
                                    ' ': 1,
                                    'm': 0.001,
                                    'mk': 0.000001,
                                    'n': 0.000000001,
                                    'p': 0.000000000001,
                                    'f': 0.000000000000001
                                }
            
            m, Text = switcher.get(BlockIn[19], (0, ''))
            if (BlockIn[18] & 128) != 0:
                BlockIn[16] ^= 255
                BlockIn[17] ^= 255
                BlockIn[18] ^= 255
                DQVal = -1 - BlockIn[16] - (BlockIn[17] + BlockIn[18] * 256) * 256
            else:
                DQVal = BlockIn[16] + (BlockIn[17] + BlockIn[18] * 256) * 256

            DQVal /= 10 ** (5 - m)
            if Text in multipliers_dict.keys():
                DQVal*=multipliers_dict[Text]
            else:
                DQVal = 999999999
            return DQVal

        if len(buffer) != 22:
            return False
        dict_param ={
            0x0 : "Ср", 0x1 : "Lp", 0x2 : "Rp",
            0x3 : "Gp", 0x4 : "Bp", 0x5 : "|Y|",  0x6 : "Q", 0x7 : "Cs",
            0x8 : "Ls", 0x9 : "Rs", 0xA : "fi",   0xB : "Xs",0xC : "|Z|",
            0xD : "D",  0xE : "I",
        }
        #      0xAA,     Offset,     Level,   Frequency,   Flags,   Mode,    Limit, ImParam,    SecParam,    SecParam_Value,     ImParam_Value,    onChange,    CS   
        #     [170,     0,     0,     100,     6, 0, 3,     23,      1,       5,        1,         6,        33, 0,  0,  252,    99, 0, 0, 253,       4,       188]
        #       0       1      2       3       4  5  6       7       8        9        10          11        12  13  14  15      16  17 18  19        20        21
        offset = int(buffer[2]<<8 | buffer[1])/100
        level = int(buffer[3])#  от 0 до 100 mV

        frequency = buffer[5]<<8
        frequency = int(frequency | buffer[4])*math.pow(10,buffer[6])
        flags = buffer[7]
        mode = buffer[8]
        limit = buffer[9]
        imparam = dict_param[buffer[10]]
        secparam = dict_param[buffer[11]]

        secparam_value = process_block_sec_param(buffer)
        imparam_value = process_block_pry_param(buffer)

        onchange = buffer[20]
        crc = buffer[21]
        #print(buffer)
        
        #print(f"{offset=} mv")
        #print(f"{level=} mv")
        #print(f"{limit=}")
        #print(f"{frequency=}")
        #print(f"imparam {imparam} = {imparam_value}")
        #print(f"secparam {secparam} = {secparam_value}")

        return [offset, level, frequency, flags, mode, limit, imparam, secparam, secparam_value, imparam_value, onchange, crc]
    
    def read_parameters(self, client, is_debug):
            is_reading = True
            timeout = 1#sec
            timestamp = time.time()
            parameters =[]
            first_read_byte = False
            status_read = False
            while is_reading:
                data = client.read(1)  # Читаем один байт данных
                if data:
                    binary_data = int.from_bytes(data, byteorder='big')  # Конвертируем байт в двоичное представление
                    if binary_data == 170:
                        if first_read_byte:
                            first_read_byte = False
                            is_reading = False
                            status_read = True
                        else:
                            first_read_byte = True

                    if first_read_byte:
                        parameters.append(binary_data)
                if is_debug:
                    is_reading = False

                if time.time() - timestamp >= timeout:
                    is_reading = False

            #============================
            #status_read = True
            #parameters = [170, 0, 0, 100, 1, 0, 3, 21, 1, 5, 0, 13, 91, 0, 0, 252, 163, 115, 1, 246, 8, 166]
            #============================
            if status_read == True and parameters != []:
                logger.debug(f"принята строка {parameters}")
                parameters = self.decode_parameters(parameters)
                if parameters is not False:
                    return parameters
                else:
                    return False
            else:
                logger.debug(f"строка не принята")
                return False
            
class ch_mnipi_class(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number, ch_type = "meas", device_class=device_class)
        #print(f"канал {number} создан")
        self.base_duration_step = 2#у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.dict_buf_parameters["meas L"] = False  
        self.dict_buf_parameters["meas R"] = False
        self.dict_buf_parameters["meas I"] = False
        self.dict_buf_parameters["meas C"] = False
        self.dict_buf_parameters["meas Z"] = False
        self.dict_buf_parameters["frequency"] = "1000"
        self.dict_buf_parameters["level"] = "1"
        self.dict_buf_parameters["offset"] = "0"
        
#print(globals().keys())
#print(dir(PyQt5.QtWidgets))

#[170, 0, 0, 100, 1, 0, 3, 21, 1, 5, 0, 13, 91, 0, 0, 252, 163, 115, 1, 246, 8, 166]  9514.7nF D = 0.0091
#[170, 22, 0, 94, 1, 0, 3, 21, 1, 5, 2, 6, 4, 0, 0, 252, 2, 59, 0, 254, 4, 132]  151.06 ом D = 0,0004


## [163, 115, 1, 246] - это старший, средний, младший байты и байт множителя 10  в дополнительном коде. Чему равно результирующее число?
if __name__ == "__main__":
        
        mnipi = mnipiE720Class(2112,4545)

        comm = [b'', b'', b'', b'']
        timeout = 5#sec
        #dev = mnipi_e7_20_class("name", 1)
        buf = [170, 22, 0, 94, 1, 0, 3, 21, 1, 5, 2, 6, 4, 0, 0, 252, 2, 59, 0, 254, 4, 132]
        buf = [170, 0, 0, 100, 1, 0, 3, 21, 1, 5, 0, 13, 91, 0, 0, 252, 163, 115, 1, 246, 8, 166]
        #print(mnipiE720Class.decode_parameters(self= 1,buffer = buf))
        client = serial.Serial("COM5", 9600, timeout=1)
        while True:
            for com in comm:
                time.sleep(1)
                client.write(com)
        #time.sleep(210)
        client = serial.Serial("COM5", 9600, timeout=1)
        mass =[]
        i = 0
        for com in comm:
            client.write(com)
            #print(f"{com=}")
            is_reading = True
            flag = False
            status_read = False
            i = 0
            timestamp = time.time()
            while is_reading:
                data = client.read()  # Читаем один байт данных
                if data:
                    binary_data = int.from_bytes(data, byteorder='big')  # Конвертируем байт в двоичное представление
                    i+=1
                    if binary_data == 170:
                        flag = True
                        i = 0
                        mnipiE720Class.decode_parameters(mass)
                        mass = []

                    if flag:
                        mass.append(binary_data)
                if time.time() - timestamp >= timeout:
                    is_reading = False

#0xAA 1, Offset 2, Level 1, Frequency 3, Flags 1, Mode 1, Limit 1, ImParam 1, SecParam 1, SecParam_Value 4, ImParam_Value 4, onChange 1, CS1,
#[170,     0, 0,     100,     6, 0, 3,     23,      1,       5,        1,         6,       33, 0, 0, 252,    99, 0, 0, 253,     4,       188] 22
#          мл ст            мл ст множ10

'''
- при нажатии кнопки L – параметры L, Q;
- при нажатии кнопки C – параметры C,D;
- при нажатии кнопки R – параметры R,Q;
- при нажатии кнопки I – параметр I;
- при нажатии кнопки Z – параметры Z , .


'''



'''
		ImParam – измеряемый параметр:
		0х0 – Ср;
		0х1 – Lp;
		0x2 – Rp;
		0x3 – Gp;
		0x4 – Bp;
		0x5 – |Y|; 
		0x6 – Q;
		0x7 – Cs;
		0x8 – Ls;
		0x9 – Rs;
		0xA – ;
		0xB – Xs;
		0xC – |Z|;
		0xD – D;
		0xE – I;
		'''
'''
		input_string = "\xaa'b'\x00'b'\x00'b'c'b'\xe5'b'\x03'b'\x00'b'\x17'b'\x01'b'\x01'b'\x01'b'\x06'b'\x8c'b'\xf0'b'\xff'b'\xfc'b'\t'b'\x00'b'\x00'b'\x03'b'\x04'b'\x9c'b'"
		result_array = extract_bytes(input_string)
		#print(result_array)
     
		ascii_code = ord(PUSH_DOWN)

		# Преобразование ASCII кода в двоичное представление
		binary_representation = bin(ascii_code)

		print(binary_representation)
     

	 	# Двоичное представление символа 'A'
		binary_representation = 'c'
		# Преобразование двоичного представления в ASCII код и затем в символ
		ascii_code = int(binary_representation, 16)
		#client.write(chr(ascii_code))
		character = chr(ascii_code)
		print(ascii_code)
          
		original_string = "Это строка с символом \x54 для удаления"

# Удаление символа '\' из строки
		new_string = original_string.replace('\\', '')

		print(new_string)
		print(b'\xaa')
		data = b'\xaa'
		binary_data = bin(int.from_bytes(data, byteorder='big'))  # Конвертируем байт в двоичное представление
		print(binary_data)
              


	#decode_parameter(string)
	#print("\xf0")
#client = serial.Serial("COM16", 9600, timeout=1)

#client.write(CHANGE_RANGE)


#0xAA,     Offset, Level, Frequency, Flags, Mode, Limit, ImParam, SecParam, SecParam_Value, ImParam_Value, onChange, CS

#\xaa'b'\x00'b'\x00'b'c'b'\xe5'b'\x03'b'\x00'b'\x17'b'\x01'b'\x01'b'\x01'b'\x06'b'\x8c'b'\xf0'b'\xff'b'\xfc'b'\t'b'\x00'b'\x00'b'\x03'b'\x04'b'\x9c'b'
##\xaa'b'\x00'b'\x00'b'c'b'\xe5'b'\x03'b'\x00'b'\x17'b'\x01'b'\x01'b'\x01'b'\x06'b'\x8c'b'\xf0'b'\xff'b'\xfc'b'\t'b'\x00'b'\x00'b'\x03'b'\x04'b'\x9c'



#\xaa'b'\x00'b'\x00'b'c'b'\x04'b'\x00'b'\x03'b'\x17'b'\x01'b'\x02'b'\x02'b'\x06'b'\x84'b'C'b'\x00'b'\xfc'b'\t'b'\x00'b'\x00'b'\x08'b'\x04'b'\x0e'b'
#\xaa'b'\x00'b'\x00'b'c'b'\x04'b'\x00'b'\x03'b'\x17'b'\x01'b'\x02'b'\x02'b'\x06'b'\x84'b'C'b'\x00'b'\xfc'b'\t'b'\x00'b'\x00'b'\x08'b'\x04'b'\x0e'b'
'''
'''
Прибор принимает однобайтные команды соответствующие нажатию клавиш управления:
0х0 – Меню;
0х1 – Вправо;
0х2 – Z/;
0х3 – режим R;
0х4 – Вниз;
0х5 – Ввод;
0х6 – Вверх;
0х7 – режим L;
0х8 – калибровка;
0х9 – Влево;
0хА – режим I;
0хВ – режим С;
0хС – изменение смещения;
0хD – изменение частоты;
0xE – изменение уровня сигнала;
0xF – изменение поддиапазона.

'''
