import os
clear = lambda: os.system('cls')
clear()

PUSH_MENU = 1
PUSH_RIGHT = b''
PUSH_Z = b''
PUSH_R = b''
PUSH_DOWN = b''
PUSH_ENTER = b''
PUSH_UP = b''
PUSH_L = b''
PUSH_CALL = b''
PUSH_LEFT = b''
PUSH_I = b''
PUSH_C = b''
CHANGE_SHIFT=b''
CHANGE_FREQ=  ''
CHANGE_LEVEL=b''
CHANGE_RANGE = b''  # = 


from interface.Set_immitance_window import Ui_Set_immitans
from PyQt5 import QtCore, QtWidgets
import PyQt5.sip
import serial.tools.list_ports
from PyQt5.QtCore import QTimer, QDateTime
import serial
import copy
import time
from Classes import ch_response_to_step, base_device, ch_response_to_step, base_ch
from Classes import is_debug
from Classes import not_ready_style_border, not_ready_style_background, ready_style_border, ready_style_background, warning_style_border, warning_style_background


class mnipi_e7_20_class(base_device):
    def __init__(self, name, installation_class) -> None:
        super().__init__(name, "serial", installation_class)
        print("класс измерителя создан")
        self.ch1 = ch_mnipi_class(1, self)
        self.channels=[self.ch1]
        self.ch1.is_active = True # по умолчанию для каждого прибора включен первый канал
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
            self.setting_window = Ui_Set_immitans()
            self.setting_window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            self.setting_window.setupUi(self.setting_window)

            # +++++++++++++++++выбор ком порта+++++++++++++
            self._scan_com_ports()
            # ++++++++++++++++++++++++++++++++++++++++++

            self.setting_window.boudrate.addItems(
                ["50", "75", "110", "150", "300", "600", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])

            #self.setting_window.sourse_enter.setStyleSheet(
            #  "background-color: rgb(255, 255, 255);")

            #self.setting_window.sourse_enter.setEditable(True)
            #self.setting_window.sourse_enter.addItems(
            #["5", "10", "30", "60", "120"])
            self.setting_window.triger_enter.addItems(["Таймер", "Внешний сигнал"])

            self.setting_window.triger_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.sourse_enter.setStyleSheet(
                ready_style_border)
            
            self.setting_window.shift_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.frequency_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.level_enter.setStyleSheet(
                ready_style_border)

            self.setting_window.comportslist.setStyleSheet(
                ready_style_border)
            self.setting_window.boudrate.setStyleSheet(
                ready_style_border)
            self.setting_window.num_meas_enter.setStyleSheet(
                ready_style_border)

            
            self.setting_window.frequency_enter.setEditable(True)
            self.setting_window.frequency_enter.addItems(
                ["400"])
            self.setting_window.level_enter.setEditable(True)
            self.setting_window.level_enter.addItems(
                ["1"])
            self.setting_window.shift_enter.setEditable(True)
            self.setting_window.shift_enter.addItems(
                ["0"])
            

            self.setting_window.num_meas_enter.setEditable(True)
            self.setting_window.num_meas_enter.addItems(
                ["3"])

            # =======================прием сигналов от окна==================

            self.setting_window.shift_enter.currentIndexChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.level_enter.currentIndexChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.frequency_enter.currentIndexChanged.connect(
                lambda: self._is_correct_parameters())
            

            self.setting_window.triger_enter.currentIndexChanged.connect(
                lambda: self._action_when_select_trigger())

            
            self.setting_window.level_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.frequency_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            self.setting_window.shift_enter.currentTextChanged.connect(
                lambda: self._is_correct_parameters())
            

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

            self.setting_window.boudrate.setCurrentText(self.dict_buf_parameters["baudrate"])
            
            self.setting_window.shift_enter.setCurrentText(
                str(self.active_channel.dict_buf_parameters["offset"]))
            self.setting_window.frequency_enter.setCurrentText(
                str(self.active_channel.dict_buf_parameters["frequency"]))
            self.setting_window.level_enter.setCurrentText(
                str(self.active_channel.dict_buf_parameters["level"]))
            
            self.setting_window.comportslist.addItem(self.dict_buf_parameters["COM"])
            self.setting_window.triger_enter.setCurrentText(self.active_channel.dict_buf_parameters["trigger"])
            num_meas_list = ["5","10","20","50"]
            if self.installation_class.get_signal_list(self.name, self.active_channel.number) != []:#если в списке сигналов пусто, то и других активных приборов нет, текущий прибор в установке один
                num_meas_list.append("Пока активны другие приборы")
            self.setting_window.num_meas_enter.addItems(num_meas_list)
            self.setting_window.num_meas_enter.setCurrentText(
                str(self.number_steps))
            




            self.setting_window.check_capacitance.setChecked(False)
            self.setting_window.check_resistance.setChecked(False)
            self.setting_window.check_impedance.setChecked(False)
            self.setting_window.check_inductor.setChecked(False)
            self.setting_window.check_current.setChecked(False)

            if self.active_channel.dict_buf_parameters["meas C"] == True:
                self.setting_window.check_capacitance.setChecked(True)
            if self.active_channel.dict_buf_parameters["meas R"] == True:
                self.setting_window.check_resistance.setChecked(True)
            if self.active_channel.dict_buf_parameters["meas Z"] == True:
                self.setting_window.check_impedance.setChecked(True)
            if self.active_channel.dict_buf_parameters["meas L"] == True:
                self.setting_window.check_inductor.setChecked(True)
            if self.active_channel.dict_buf_parameters["meas I"] == True:
                self.setting_window.check_current.setChecked(True)


            self.setting_window.sourse_enter.setCurrentText(
                self.active_channel.dict_buf_parameters["sourse/time"])

            self.key_to_signal_func = True  # разрешаем выполенение функций
            self._action_when_select_trigger()

    def _is_correct_parameters(self) -> bool:  # менять для каждого прибора
        if self.key_to_signal_func:
            # print("проверить параметры")

            is_shift_correct = True
            is_level_correct = True
            is_freq_correct = True
            is_num_steps_correct = True
            is_time_correct = True

# число илии нет
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
                if float(self.setting_window.level_enter.currentText()) > 3 or float(self.setting_window.level_enter.currentText()) < 0:
                    is_level_correct = False
            if is_freq_correct:
                if float(self.setting_window.frequency_enter.currentText()) > 1000000 or float(self.setting_window.frequency_enter.currentText()) < 25:
                    is_freq_correct = False
            if is_shift_correct:
                if float(self.setting_window.shift_enter.currentText()) > 40 or float(self.setting_window.shift_enter.currentText()) < 0:
                    is_shift_correct = False
            # ----------------------------------------
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



            self.setting_window.shift_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.level_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.frequency_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.num_meas_enter.setStyleSheet(
                ready_style_border)
            self.setting_window.sourse_enter.setStyleSheet(
                ready_style_border)


            if not is_shift_correct:
                self.setting_window.shift_enter.setStyleSheet(
                    not_ready_style_border)

            if not is_freq_correct:
                self.setting_window.frequency_enter.setStyleSheet(
                    not_ready_style_border)
            if not is_level_correct:
                self.setting_window.level_enter.setStyleSheet(
                    not_ready_style_border)

            if not is_num_steps_correct:
                self.setting_window.num_meas_enter.setStyleSheet(
                    not_ready_style_border)

            if not is_time_correct:
                self.setting_window.sourse_enter.setStyleSheet(
                    not_ready_style_border)

            if is_shift_correct and is_level_correct and is_freq_correct and is_num_steps_correct and is_time_correct:
                return True
            else:
                return False

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

            self.active_channel.dict_buf_parameters["offset"] = float(self.setting_window.shift_enter.currentText())
            self.active_channel.dict_buf_parameters["frequency"] = float(self.setting_window.frequency_enter.currentText())
            self.active_channel.dict_buf_parameters["level"] = float(self.setting_window.level_enter.currentText())
            self.active_channel.dict_buf_parameters["num steps"] = self.number_steps
            self.active_channel.dict_buf_parameters["trigger"] = self.setting_window.triger_enter.currentText(
            )
            self.active_channel.dict_buf_parameters["sourse/time"] = self.setting_window.sourse_enter.currentText()

            self.dict_buf_parameters["baudrate"] = self.setting_window.boudrate.currentText(
            )
            self.dict_buf_parameters["COM"] = self.setting_window.comportslist.currentText(
            )

            self.active_channel.dict_buf_parameters["meas L"] = False  
            self.active_channel.dict_buf_parameters["meas R"] = False
            self.active_channel.dict_buf_parameters["meas I"] = False
            self.active_channel.dict_buf_parameters["meas C"] = False
            self.active_channel.dict_buf_parameters["meas Z"] = False
            if self.setting_window.check_capacitance.isChecked():
                self.active_channel.dict_buf_parameters["meas C"] = True
            if self.setting_window.check_resistance.isChecked():
                self.active_channel.dict_buf_parameters["meas R"] = True
            if self.setting_window.check_impedance.isChecked():
                self.active_channel.dict_buf_parameters["meas Z"] = True
            if self.setting_window.check_inductor.isChecked():
                self.active_channel.dict_buf_parameters["meas L"] = True
            if self.setting_window.check_current.isChecked():
                self.active_channel.dict_buf_parameters["meas I"] = True

    def send_signal_ok(self):  # действие при подтверждении настроек, передать парамтры классу инсталляции, проверить и окрасить в цвет окошко, вписать паарметры
        self.add_parameters_from_window()
        # те же самые настройки, ничего не делаем
        if (self.active_channel.dict_buf_parameters == self.active_channel.dict_settable_parameters and self.dict_buf_parameters == self.dict_settable_parameters):
            return
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
        print(
            f"настройка канала {number_of_channel} прибора "
            + str(self.name)
            + " перед экспериментом.."
        )
        pause = 0.1
        status = True
        if not self.command._set_filter_slope(
                slope=self.active_channel.dict_settable_parameters["filter_slope"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_input_conf(
                conf=self.active_channel.dict_settable_parameters["input_channel"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_input_type_conf(
                type_conf=self.active_channel.dict_settable_parameters["input_type"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_input_type_connect(
                input_ground=self.active_channel.dict_settable_parameters["input_connect"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_line_filters(
                type=self.active_channel.dict_settable_parameters["filters"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_reserve(
                reserve=self.active_channel.dict_settable_parameters["reserve"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_time_const(
                time_constant=self.active_channel.dict_settable_parameters["time_const"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_sens(
                sens=self.active_channel.dict_settable_parameters["sensitivity"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_frequency(
                freq=self.active_channel.dict_settable_parameters["frequency"]):
            status = False
        print((status))
        time.sleep(pause)
        if not self.command._set_amplitude(
                ampl=self.active_channel.dict_settable_parameters["amplitude"]):
            status = False
        print((status))
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
        if not is_debug:
            while not is_stop_analyze:
                self.command.push_autophase()
                buf_display_value = []
                for i in range(10):
                    disp2 = self.command.get_parameter(self.command.COMM_DISPLAY, timeout=1, param=2)
                    print(disp2)
                    if not disp2:
                        continue
                    else:
                        buf_display_value.append(float(disp2))
                        #val = ["disp2=" + str(disp2)]
                        #parameters.append(val)
                    #time.sleep(0.05)
                if len(buf_display_value) > 3:
                    if max(buf_display_value) < 2 and min(buf_display_value) > -2:#выход за границы
                        if len(buf_display_value) >= 5:
                            for i in range(len(buf_display_value)-2):#анализ монотонности
                                if buf_display_value[i] >= buf_display_value[i+1] and buf_display_value[i+1] <= buf_display_value[i+2]:
                                    is_stop_analyze = True
                                    result_analyze = True
                                    break
                                if buf_display_value[i] <= buf_display_value[i+1] and buf_display_value[i+1] >= buf_display_value[i+2]:
                                    is_stop_analyze = True
                                    result_analyze = True
                                    break
            
                count+=1
                print("счетчик повторов нажатий кнопки автофаза",count)
                if count >= 10:
                    is_stop_analyze = True
            

        if result_analyze == True:
            print("удалось устаканить фазу, измеряем...")
            disp1 = self.command.get_parameter(
                command=self.command.COMM_DISPLAY, timeout=1, param=1)
            if not disp1:
                is_correct = False
            else:
                val = ["disp1=" + str(disp1)]
                parameters.append(val)

            disp2 = self.command.get_parameter(
                self.command.COMM_DISPLAY, timeout=1, param=2)
            if not disp2:
                is_correct = False
            else:
                val = ["disp2=" + str(disp2)]
                parameters.append(val)

            phase = self.command.get_parameter(
                self.command.PHASE, timeout=1)
            if not phase:
                is_correct = False
            else:
                val = ["phase=" + str(phase)]
                parameters.append(val)
        else:
            print("Не получилось обнулить фазу, ставим прочерки", self.name)
            val = ["disp1=" + "fail"]
            parameters.append(val)
            val = ["disp2=" + "fail"]
            parameters.append(val)
            val = ["phase=" + "fail"]
            parameters.append(val)

        # -----------------------------
        if is_debug:
            if is_correct == False:
                is_correct = True
                parameters.append(["disp1=" + str(254)])
                parameters.append(["disp2=" + str(847)])
                parameters.append(["phase=" + str(777)])
        # -----------------------------

        if is_correct:
            print("сделан шаг", self.name)
            ans = ch_response_to_step.Step_done
        else:
            print("Ошибка шага", self.name)
            val = ["disp1=" + "fail"]
            parameters.append(val)
            val = ["disp2=" + "fail"]
            parameters.append(val)
            val = ["phase=" + "fail"]
            parameters.append(val)

            ans = ch_response_to_step.Step_fail

        return ans, parameters, time.time() - start_time

    def check_connect(self) -> bool:
        line = self.command.get_parameter(self.command.COMM_ID, timeout=1)
        if line is not False:
            print(line)
            return True
        return False


class ch_mnipi_class(base_ch):
    def __init__(self, number, device_class) -> None:
        super().__init__(number)
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


def decode_parameters(buffer):
	import math
	dict_param ={
        0x0 : "Ср",
		0x1 : "Lp",
		0x2 : "Rp",
		0x3 : "Gp",
		0x4 : "Bp",
		0x5 : "|Y|", 
		0x6 : "Q",
		0x7 : "Cs",
		0x8 : "Ls",
		0x9 : "Rs",
		0xA : "fi",
		0xB : "Xs",
		0xC : "|Z|",
		0xD : "D",
		0xE : "I",

	}
	offset = buffer[2]<<8
	offset = int(offset | buffer[1])/100
	level = int(buffer[3])

	print((offset))
	Frequency = buffer[5]<<8
	Frequency = int(Frequency | buffer[4])*math.pow(10,buffer[6])
	print(Frequency)
	flags = buffer[7]
	mode = buffer[8]
	limit = buffer[9]
	imparam = dict_param[buffer[10]]
	print(imparam)
	secparam = dict_param[buffer[11]]
	print(secparam)
	secparam_value = int((buffer[12]<<16) | (buffer[13]<<8) | buffer[14]) * math.pow(10,buffer[15])
	print(secparam_value)
	imparam_value = int((buffer[16]<<16) | (buffer[17]<<8) | buffer[18]) * math.pow(10,buffer[19])
	print(imparam_value)
	onchange = buffer[20]
	crc = buffer[21]



if __name__ == "__main__":
		buf = [170,     0, 0,     100,     6, 0, 3,     23,      1,       5,        1,         6,       33, 0, 0, 252,    99, 0, 0, 253,     4,       188]
		decode_parameters(buf)
		client = serial.Serial("COM11", 9600, timeout=1)
		#client.write(PUSH_DOWN)
		mass =[]
		i = 0
		flag = False
		while True:
			data = client.read()  # Читаем один байт данных
			if data:
				#binary_data = bin(int.from_bytes(data, byteorder='big'))  # Конвертируем байт в двоичное представление
				binary_data = int.from_bytes(data, byteorder='big')  # Конвертируем байт в двоичное представление
				##mass.append(binary_data)
				i+=1
				#print(binary_data)
				#'0b10101010' = 170
				if binary_data == 170:
					flag = True
					i = 0
					print(mass, len(mass))
					mass = []

				if flag:
					mass.append(binary_data)

#0xAA 1, Offset 2, Level 1, Frequency 3, Flags 1, Mode 1, Limit 1, ImParam 1, SecParam 1, SecParam_Value 4, ImParam_Value 4, onChange 1, CS1,
#[170,     0, 0,     100,     6, 0, 3,     23,      1,       5,        1,         6,       33, 0, 0, 252,    99, 0, 0, 253,     4,       188] 22
#          мл ст            мл ст множ10

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
