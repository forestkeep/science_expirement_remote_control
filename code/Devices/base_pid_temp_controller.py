import copy
import logging
import random
import time

from PyQt5.QtWidgets import QApplication

try:
    from Devices.Classes import (base_ch, base_device, ch_response_to_step,
                             not_ready_style_border, ready_style_border,
                             which_part_in_ch)
    from Devices.interfase.pidControllerWindow import UiSetPidController
except:
    from Classes import (base_ch, base_device, ch_response_to_step,
                             not_ready_style_border, ready_style_border,
                             which_part_in_ch)
    from interfase.pidControllerWindow import UiSetPidController
    
logger = logging.getLogger(__name__)


class chActPidController(base_ch):
    def __init__(
        self,
        number,
        device_class_name,
        message_broker,
        max_temp,
        min_temp,   
        min_step_t=0.01,
    ) -> None:
        super().__init__(number, ch_type="act", device_class_name=device_class_name, message_broker=message_broker)
        #здесь определяются параметры активного канала, они складываются в self.dict_buf_parameters
        self.base_duration_step = 10  # у каждого канала каждого прибора есть свое время. необходимое для выполнения шага
        self.steps_temp = []
        self.max_temp = max_temp
        self.min_temp = min_temp
        self.min_step_t = min_step_t
        self.dict_buf_parameters["type_step"] = "Заданный шаг"
        self.dict_buf_parameters["high_limit"] = str(5)
        self.dict_buf_parameters["low_limit"] = str(self.min_step_t)
        self.dict_buf_parameters["step"] = "1"
        self.dict_buf_parameters["repeat_reverse"] = False

        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)


class chMeasPidController(base_ch):
    def __init__(self, number, device_class_name, message_broker) -> None:
        super().__init__(number, ch_type="meas", device_class_name=device_class_name, message_broker=message_broker)
        self.base_duration_step = 10  # у каждого канала каждого прибора есть свое время. необходимое для выполнения шага

        #здесь определяются параметры  канала измерений, они складываются в self.dict_buf_parameters
        self.dict_buf_parameters["meas_temp"] = False
        self.dict_buf_parameters["meas_set_temp"] = False
        self.dict_buf_parameters["meas_power"] = False

        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)

class basePidController(base_device):

    def __init__(self, name, type_connection, installation_class) -> None:
        super().__init__(name, type_connection, installation_class)
        self.part_ch = (which_part_in_ch.bouth)
        self.setting_window = UiSetPidController()#заменить на свой класс фронта для пользователя, они лежат в interfase
        self.base_settings_window()
        
        self.setting_window.type_step_enter.addItems([ QApplication.translate("Device","Заданный шаг") ])

        # =======================прием сигналов от окна==================
        #прописать свои приемы сигналов от окна

        self.setting_window.type_step_enter.currentIndexChanged.connect(
            lambda: self._action_when_select_step()
        )
        self.setting_window.type_step_enter.currentIndexChanged.connect(
            lambda: self._action_when_select_trigger()
        )
        self.setting_window.type_step_enter.setToolTip(
            QApplication.translate("Device","Доступен фиксированный шаг. Адаптивный находится в разработке.")
        )
        self.setting_window.radioButton.setToolTip(
            QApplication.translate("Device","При активации этого пункта источник питания пройдет по шагам от стартого значения до конечного и обратно.")
        )
        self.setting_window.num_act_label.setParent(None)
        self.setting_window.num_act_enter.setParent(None)

    def time_decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            logger.info(f"Метод {func.__name__} выполнялся {end_time - start_time} с")
            return result

        return wrapper

    @base_device.base_show_window
    def show_setting_window(self, number_of_channel):
        self.switch_channel(number=number_of_channel)
        # запрещаем исполнение функций во время инициализации
        self.key_to_signal_func = False
        # self.base_show_window()

        # ============установка текущих параметров=======================
        #прописать процедуру установки параметров окна, они сохранены в self.dict_buf_parameters, там они лежат между вызовами окна
        self.setting_window.type_step_enter.setCurrentText(
            self.active_channel_act.dict_buf_parameters["type_step"]
        )
        self.setting_window.start_enter.setCurrentText(
            str(self.active_channel_act.dict_buf_parameters["low_limit"])
        )
        self.setting_window.stop_enter.setCurrentText(
            str(self.active_channel_act.dict_buf_parameters["high_limit"])
        )
        self.setting_window.step_enter.setCurrentText(
            str(self.active_channel_act.dict_buf_parameters["step"])
        )

        self.setting_window.radioButton.setChecked(
            self.active_channel_act.dict_buf_parameters["repeat_reverse"] == True
        )

        self.setting_window.radioButton.setChecked(self.active_channel_act.dict_buf_parameters["repeat_reverse"] == True) 
            
        self.setting_window.temp_meas.setChecked(
            self.active_channel_meas.dict_buf_parameters["meas_temp"] == True
        )
        self.setting_window.set_temp_meas.setChecked(
            self.active_channel_meas.dict_buf_parameters["meas_set_temp"] == True
        )
        self.setting_window.power_percent.setChecked(
            self.active_channel_meas.dict_buf_parameters["meas_power"] == True
        )
        self.key_to_signal_func = True

        self._action_when_select_trigger()
        self._is_correct_parameters()
        self.setting_window.show()

    @base_device.base_is_correct_parameters
    def _is_correct_parameters(self):  # менять для каждого прибора
        if self.key_to_signal_func:
            #сюда подключены сигналы изменения параметров в окне пользователя. необходимо для сообщений пользователю о некорректных параметрах. Сообщается о некорректном параметре установкой красной рамки вокруг целевого параметра

            low_value = 0
            high_value = 0
            enter_step = 0

            self.active_channel_act.is_stop_value_correct = True
            self.active_channel_act.is_start_value_correct = True
            self.active_channel_act.is_step_correct = True
            # проверка число или не число

            try:
                low_value = float(self.setting_window.start_enter.currentText())
            except:
                self.active_channel_act.is_start_value_correct = False
            try:
                high_value = float(self.setting_window.stop_enter.currentText())
            except:
                self.active_channel_act.is_stop_value_correct = False
            try:
                enter_step = float(self.setting_window.step_enter.currentText())
            except:
                self.active_channel_act.is_step_correct = False

            # ---------------------------
            # минимум и максимум не выходят за границы

            max = self.active_channel_act.max_temp
            min = self.active_channel_act.min_temp

            if self.active_channel_act.is_stop_value_correct:
                if high_value < min or high_value > max:
                    self.active_channel_act.is_stop_value_correct = False

            if self.active_channel_act.is_start_value_correct:
                if low_value < min or low_value > max:
                    self.active_channel_act.is_start_value_correct = False

            if self.active_channel_act.is_step_correct:
                if (
                    self.active_channel_act.is_start_value_correct
                    and self.active_channel_act.is_stop_value_correct
                ):
                    if self.active_channel_act.is_step_correct:
                        if enter_step > abs(high_value - low_value) or enter_step < min:
                            self.active_channel_act.is_step_correct = False

            if self.active_channel_act.is_stop_value_correct:
                self.setting_window.stop_enter.setStyleSheet(ready_style_border)
            else:
                self.setting_window.stop_enter.setStyleSheet(not_ready_style_border)

            if self.active_channel_act.is_start_value_correct:
                self.setting_window.start_enter.setStyleSheet(ready_style_border)
            else:
                self.setting_window.start_enter.setStyleSheet(not_ready_style_border)

            if self.active_channel_act.is_step_correct:
                if (
                    self.setting_window.type_step_enter.currentText()
                    == QApplication.translate("Device","Адаптивный шаг")
                ):
                    self.setting_window.step_enter.setStyleSheet(
                        "background-color: rgb(180, 180, 180)"
                    )
                else:
                    self.setting_window.step_enter.setStyleSheet(ready_style_border)
            else:
                if (
                    self.setting_window.type_step_enter.currentText()
                    == QApplication.translate("Device","Адаптивный шаг")
                ):
                    self.setting_window.step_enter.setStyleSheet(
                        "background-color: rgb(180, 180, 180)"
                    )
                else:
                    self.setting_window.step_enter.setStyleSheet(not_ready_style_border)

            #print(f"{self.active_channel_act.is_stop_value_correct} {self.active_channel_act.is_start_value_correct} {self.active_channel_act.is_step_correct}")
            return (
                self.active_channel_act.is_stop_value_correct
                and self.active_channel_act.is_start_value_correct
                and self.active_channel_act.is_step_correct
            )

        return False

    def _action_when_select_step(self):
        #не нужно
        if self.key_to_signal_func:
            if self.setting_window.type_step_enter.currentText() == QApplication.translate("Device","Адаптивный шаг"):
                self.setting_window.step_enter.setEnabled(False)
                self.setting_window.step_enter.setStyleSheet(
                    "background-color: rgb(180, 180, 180)"
                )
                self.setting_window.triger_meas_enter.clear()
                self.setting_window.triger_meas_enter.addItems([ QApplication.translate("Device","Внешний сигнал") ])
            else:
                self.setting_window.step_enter.setEnabled(True)
                self.setting_window.triger_meas_enter.addItems([ QApplication.translate("Device","Таймер") ])

    @base_device.base_add_parameters_from_window
    def add_parameters_from_window(self):  # менять для каждого прибора
        #эта функция вызывается при нажатии пользователем кнопки окей, параметры сохраняются
        if self.key_to_signal_func:
            self.active_channel_act.dict_buf_parameters["type_step"] = (
                self.setting_window.type_step_enter.currentText()
            )
            self.active_channel_act.dict_buf_parameters["high_limit"] = (
                self.setting_window.stop_enter.currentText()
            )
            self.active_channel_act.dict_buf_parameters["low_limit"] = (
                self.setting_window.start_enter.currentText()
            )
            self.active_channel_act.dict_buf_parameters["step"] = (
                self.setting_window.step_enter.currentText()
            )

            self.active_channel_act.dict_buf_parameters["repeat_reverse"] = (
                self.setting_window.radioButton.isChecked()
            )

            self.active_channel_meas.dict_buf_parameters["meas_temp"] = (
                self.setting_window.temp_meas.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["meas_set_temp"] = (
                self.setting_window.set_temp_meas.isChecked()
            )
            self.active_channel_meas.dict_buf_parameters["meas_power"] = (
                self.setting_window.power_percent.isChecked()
            )


    def send_signal_ok(
        self,
    ):
        "вызывается только после закрытия окна настроек"
        self.add_parameters_from_window()
        # те же самые настройки, ничего не делаем
        
        self.dict_settable_parameters = copy.deepcopy(self.dict_buf_parameters)
        self.active_channel_act.dict_settable_parameters = copy.deepcopy(self.active_channel_act.dict_buf_parameters)
        self.active_channel_meas.dict_settable_parameters = copy.deepcopy(self.active_channel_meas.dict_buf_parameters)
        is_parameters_correct = True

        if self.dict_buf_parameters["COM"] == QApplication.translate("Device","Нет подключенных портов") :
            is_parameters_correct = False
        self.timer_for_scan_com_port.stop()

        if is_parameters_correct:
            is_parameters_correct = self._is_correct_parameters()

        #здесь последние проверки параметров перед сохранением
        try:
            float(self.setting_window.stop_enter.currentText())
            float(self.setting_window.start_enter.currentText())
            float(self.setting_window.step_enter.currentText())
            float(self.setting_window.boudrate.currentText())
        except:
            is_parameters_correct = False

        self.installation_class.message_from_device_settings(
            name_device=self.name,
            num_channel=self.active_channel_meas.number,
            status_parameters=is_parameters_correct,
            list_parameters_device=self.dict_settable_parameters,
            list_parameters_act=self.active_channel_act.dict_settable_parameters,
            list_parameters_meas=self.active_channel_meas.dict_settable_parameters,
        )

    def confirm_parameters(self):  # менять для каждого прибора
        """метод подтверждения корректности параметров от контроллера установки. установка проверяет ком порты, распределяет их между устройствами и отдает каждому из устройств"""
        #выбрали параметры - нажали окей. класс установки принял настройки прибора, если нет конфликтов на его стороне он вызывает эту функцию, здесь приготовления к процедуре эксперимента, например, массив последовательных установок температуры
        for ch in self.channels:
            if ch.is_ch_active():
                ch.step_index = -1
                self.switch_channel(ch.number)
            else:
                continue

            self.active_channel_act.steps_temp.clear()
            

            if (
                self.active_channel_act.dict_settable_parameters["type_step"]
                == QApplication.translate("Device","Заданный шаг")
            ):
                    self.active_channel_act.steps_temp = self.__fill_arrays(
                    float(
                        self.active_channel_act.dict_settable_parameters[
                            "low_limit"
                        ]
                    ),
                    float(
                        self.active_channel_act.dict_settable_parameters[
                            "high_limit"
                        ]
                    ),
                    float(self.active_channel_act.dict_settable_parameters["step"]),
                )

            if self.active_channel_act.dict_buf_parameters["repeat_reverse"] == True:
                buf_temp = copy.deepcopy(self.active_channel_act.steps_temp)
                buf_temp = buf_temp[::-1]  # разворот списка

                buf_temp = buf_temp[1 : len(buf_temp)]

                for cur in buf_temp:
                    self.active_channel_act.steps_temp.append(cur)

            self.active_channel_act.dict_settable_parameters["num steps"] = int(
                len(self.active_channel_act.steps_temp)
            )

            print(self.active_channel_act.steps_temp)

    # действия перед стартом эксперимента, включить, настроить, подготовить и т.д.
    def action_before_experiment(self, number_of_channel) -> bool:
        """устанавливает значения тока и напряжения, включает выход прибора"""

        self.switch_channel(number_of_channel)
        is_correct = True


        #переопределить действия. необходимые перед экспериментом
        if ( self._set_voltage( self.active_channel_act.number, self.active_channel_act.min_step_t ) == False ):
            logger.warning("ошибка установки тока")
            is_correct = False

        if is_correct:
            #в случае некорректной установки нужно выключить прибор
            self._output_switching_on( self.active_channel_act.number )
            return True
        else:
            return False

    def action_end_experiment( self, ch ) -> bool:
        """выключение прибора"""
        self.switch_channel(ch_name=ch.get_name())
        status = True
        if ch.get_type() == "act":

            #реализовать свою процедуру действий по окончании эксперимента
            if self.active_channel_act.dict_buf_parameters["soft_off"] == True:
                count = 3
                is_voltage_read = False

                while count > 0:
                    voltage = self._get_current_voltage(self.active_channel_act.number)
                    if voltage == False:
                        count -= 1
                    else:
                        is_voltage_read = True
                        count = 0
                if is_voltage_read:
                    step = min(int(voltage / 5), 1)

                    while voltage > step:
                        voltage -= step
                        self._set_voltage(self.active_channel_act.number, voltage)
                        time.sleep(3)
                else:
                    status = False

            self._output_switching_off(self.active_channel_act.number)
        return status

    def soft_start( self, number_of_channel, repeat=3 ):
        """плавное включение прибора"""

        #скорее всего, для пид регулятора это не нужно. Мягкий старт - это постепенной подход к стартовому значению установки. В случае блока питания это может быть критично.
        self.switch_channel(number_of_channel)
        logger.debug("Плавное выключение источника питания")

        if (
            self.active_channel_act.dict_buf_parameters["type_of_work"]
            == QApplication.translate("Device","Стабилизация напряжения")
        ):
            focus_funk = self._set_voltage
            step = min(int(self.active_channel_act.steps_voltage[0] / 5), 1)
        elif (
            self.active_channel_act.dict_buf_parameters["type_of_work"]
            == QApplication.translate("Device","Стабилизация тока")
        ):
            focus_funk = self._set_current
            step = min(int(self.active_channel_act.steps_current[0] / 5), 1)
            
        else:
            return False
        param = 0
        while param < step * 5:
            param += step
            count = repeat
            time.sleep(1)
            status = False
            while count > 0:
                buf_par = focus_funk(self.active_channel_act.number, param)
                if buf_par == False:
                    count -= 1
                    time.sleep(0.2)
                else:
                    count = 0
                    status = True
            if status == False:
                return False
        return True

    def do_action( self, ch, repeat=3 ) -> bool:
        """активирует следующие значение тока, напряжения прибора, если текущие значения максимальны, то возвращает ложь"""

        #эта функция отвечает за выполнения действия активным каналом, переключить  значение температуры
        parameters = [self.name + " " + str(ch.get_name())]
        start_time = time.perf_counter()
        if ch.get_type() == "act":
            if ch.step_index < len(ch.steps_voltage) - 1:
                if (
                    ch.step_index == 0
                    and ch.dict_settable_parameters["soft_start"] == True
                ):
                    if (
                        self.soft_start(number_of_channel=ch.get_number(), repeat=3)
                        == False
                    ):
                        """ошибка плавного старта"""
                        return (
                            ch_response_to_step.Step_fail,
                            parameters,
                            time.perf_counter() - start_time,
                        )

                i = 0
                answer = ch_response_to_step.Step_fail
                while i - 1 < repeat and answer == ch_response_to_step.Step_fail:
                    time.sleep(0.2)
                    i += 1
                    if (
                        self._set_voltage(
                            ch.get_number(), ch.steps_voltage[ch.step_index]
                        )
                        == True
                    ):
                        answer = ch_response_to_step.Step_done

                    else:
                        answer = ch_response_to_step.Step_fail
                        if self.is_debug:
                            answer = ch_response_to_step.Step_done
                        continue

                    if (
                        self._set_current(
                            ch.get_number(), ch.steps_current[ch.step_index]
                        )
                        == True
                    ):
                        answer = ch_response_to_step.Step_done
                    else:
                        answer = ch_response_to_step.Step_fail
                        if self.is_debug:
                            answer = ch_response_to_step.Step_done
                        continue

            else:
                answer = ch_response_to_step.End_list_of_steps  # след шага нет

            if self.is_debug:
                if answer != ch_response_to_step.End_list_of_steps:
                    answer = ch_response_to_step.Step_done

            return answer, parameters, time.perf_counter() - start_time
        return ch_response_to_step.Incorrect_ch, parameters, time.perf_counter() - start_time

    def do_meas( self, ch ):
        """прочитать текущие и настроенные значения"""
        start_time = time.perf_counter()
        parameters = [self.name + " " + str(ch.get_name())]
        if ch.get_type() == "meas":

            #реализовать процедуру считывания фокусных параметров с измерительного канала устройства. Это могут быть статусы, температура, значение пид регулятора и т.п. Здесь важно их записывать в таком же формате, как ниже. Это потом пишется в файл. после эксперимента парсится и сохраняется в выбранном пользователем виде
            is_correct = True
            current_actual = None
            voltage_actual = None

            if ch.dict_settable_parameters["meas_set_vol"] == True:
                voltage = self._get_setting_voltage(ch.get_number())
                if voltage is not False:
                    val = ["voltage_set=" + str(voltage)]
                    parameters.append(val)
                else:
                    is_correct = False
                    if self.is_debug:
                        is_correct = True
                        parameters.append(["voltage_set=" + str(random.random())])
                    else:
                        val = ["voltage_set=" + "fail"]
                        parameters.append(val)

            if ch.dict_settable_parameters["meas_vol"] == True:
                voltage = self._get_current_voltage(ch.number)
                if voltage is not False:
                    val = ["voltage_rel=" + str(voltage)]
                    voltage_actual = voltage
                    parameters.append(val)
                else:
                    is_correct = False
                    if self.is_debug:
                        is_correct = True
                        parameters.append(["voltage_rel=" + str(random.random() * 30)])
                    else:
                        val = ["voltage_rel=" + "fail"]
                        parameters.append(val)

            if ch.dict_settable_parameters["meas_set_cur"] == True:
                current = self._get_setting_current(ch.get_number())
                if current is not False:
                    val = ["current_set=" + str(current)]
                    parameters.append(val)
                else:
                    is_correct = False
                    if self.is_debug:
                        is_correct = True
                        parameters.append(["current_set=" + str(random.random())])
                    else:
                        val = ["current_set=" + "fail"]
                        parameters.append(val)

            if ch.dict_settable_parameters["meas_cur"] == True:
                current = self._get_current_current(ch.get_number())
                if current is not False:
                    val = ["current_rel=" + str(current)]
                    current_actual = current
                    parameters.append(val)
                else:
                    is_correct = False
                    if self.is_debug:
                        is_correct = True
                        parameters.append(["current_rel=" + str(random.random() * 30)])
                    else:
                        val = ["current_rel=" + "fail"]
                        parameters.append(val)

            if voltage_actual != None and current_actual != None and current_actual > 0:
                val = ["R_rel=" + str(voltage_actual / current_actual)]
                parameters.append(val)
                val = ["W_rel=" + str(voltage_actual * current_actual)]
                parameters.append(val)

            if is_correct:
                ans = ch_response_to_step.Step_done
            else:
                ans = ch_response_to_step.Step_fail

            return ans, parameters, time.perf_counter() - start_time

        return ch_response_to_step.Incorrect_ch, parameters, time.perf_counter() - start_time

    def __fill_arrays( self, start_value, stop_value, step):
        steps_1 = []
        if start_value > stop_value:
            step = step * (-1)

        current_value = start_value

        steps_1.append(current_value)
        while abs(step) < abs(stop_value - current_value):
            current_value = current_value + step
            current_value *= 100000
            current_value = round(current_value, 2)
            current_value /= 100000
            steps_1.append(current_value)
            if current_value == stop_value:
                steps_1.append(current_value)
                break
        else:
            steps_1.append(stop_value)
        return steps_1

    def set_test_mode( self ):
        """переводит прибор в режим теста, выдаются сырые данные от функций передачи и приема"""
        self.is_test = True

    def reset_test_mode( self ):
        self.is_test = False

    def _set_voltage(self, ch_num, voltage) -> bool:
        """установить значение напряжения канала"""
        logger.warning(f"устанавливаем напряжение {voltage} канала {ch_num}")
        self.select_channel(ch_num)
        self.client.write( self.set_volt_cmd.format(voltage = voltage) )
        time.sleep(0.2)
        response = self._get_setting_voltage(ch_num=ch_num)
        return response == voltage

    def _set_current(self, ch_num, current) -> bool:
        """установить значение тока канала"""
        logger.debug(f"устанавливаем ток {current} канала {ch_num}")
        self.select_channel(ch_num)
        self.client.write( self.set_cur_cmd.format(current = current))
        time.sleep(0.2)
        response = self._get_setting_current(ch_num=ch_num)
        return response == current
        
    def _output_switching_on(self, ch_num) -> bool:
        """включить канал"""
        self.client.write( self.ON_CH_cmd.format(ch_num = ch_num) )
        self.client.close()

    def _output_switching_off(self, ch_num) -> bool:
        """выключить канал"""
        self.client.write( self.OFF_CH_cmd.format(ch_num = ch_num) )
        self.client.close()

    def _get_current_voltage(self, ch_num) -> float:
        """возвращает значение установленного напряжения канала"""
        self.select_channel(ch_num)
        # self.client.write(f'MEAS:VOLT?\n'.encode())
        self.client.write( self.meas_volt_cmd )
        time.sleep(0.2)
        try:
            response = self.client.readline().decode().strip()
            response = float(response)
        except Exception as e:
            logger.warning(f"ошибка запроса напряжения: {str(e)}")
            response = False
        self.client.close()
        return response

    def _get_current_current(self, ch_num) -> float:
        """возвращает значение измеренного тока канала"""
        self.select_channel(ch_num)
        # self.client.write(f'MEAS:CURR?\n'.encode())
        self.client.write( self.meas_cur_cmd )
        time.sleep(0.2)
        try:
            response = self.client.readline().decode().strip()
            response = float(response)
        except Exception as e:
            logger.warning(f"ошибка запроса тока {str(e)}")
            response = False
        self.client.close()
        return response

    def _get_setting_voltage(self, ch_num) -> float:
        """возвращает значение установленного напряжения канала"""
        self.select_channel(ch_num)
        self.client.write( self.ask_volt_cmd )
        time.sleep(0.2)
        try:
            response = self.client.readline().decode().strip()
            response = float(response)
        except Exception as e:
            logger.warning(f"ошибка запроса напряжения {str(e)}")
            response = False
        self.client.close()
        return response

    def _get_setting_current(self, ch_num) -> float:
        """возвращает значение установленного тока канала"""
        self.select_channel(ch_num)
        self.client.write( self.ask_volt_cmd )
        time.sleep(0.2)
        try:
            response = self.client.readline().decode().strip()
            response = float(response)
        except Exception as e:
            logger.warning(f"ошибка запроса тока {str(e)}")
            response = False
        self.client.close()
        return response
    
    def _get_setting_state(self, ch_num) -> bool:
        """возвращает состояние канала вкл(true) или выкл(false)"""
        pass

    def select_channel(self, channel):
        self.client.write(self.select_CH_cmd.format(ch_num = channel))

if __name__ == "__main__":
    pass