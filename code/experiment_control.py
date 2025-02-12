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
import enum
import logging
import time

import numpy
from PyQt5.QtWidgets import QApplication

from Analyse_in_installation import analyse
from Devices.Classes import (ch_response_to_step, not_ready_style_background,
                             ready_style_background)

logger = logging.getLogger(__name__)


class exp_th_connection:
    def __init__(self) -> None:
        self.flag_show_message           = False
        self.message                     = ""
        self.message_status              = message_status.info
        self.is_message_show             = False
        self.ask_save_the_results        = False
        self.is_update_pbar              = False
        self.is_measurement_data_updated = False
        self.start_exp_time              = 0


class message_status(enum.Enum):
    info = 1
    warning = 2
    critical = 3


class experimentControl(analyse):
    def __init__(self) -> None:
        super().__init__()
        self.exp_th_connect    = exp_th_connection()
        self.experiment_thread = None
        self.stop_experiment   = False
        self.pause_start_time  = 0
        
        self.meta_data_exp = metaDataExp()

    def is_experiment_running(self) -> bool:
        return self.experiment_thread is not None and self.experiment_thread.is_alive()

    def connection_two_thread(self):
        """функция для связи основного потока и потока эксперимента, поток эксперимента выставляет значения/флаги/сообщения, а основной поток их обрабатывает"""
        if self.is_experiment_running():
            # self.installation_window.open_graph_button.setEnabled(True)
            self.timer_for_connection_main_exp_thread.start(1000)
            self.installation_window.label_time.setText("")

            if not self.pause_flag:
                if self.is_experiment_endless:
                    self.pbar_percent = 50
                    self.installation_window.label_time.setText(
                        QApplication.translate('exp_flow',"Бесконечный эксперимент")
                    )
                    self.update_pbar()
                else:

                    if self.exp_th_connect.is_update_pbar :
                        self.pbar_percent = (
                            ((time.time() - self.start_exp_time) / self.max_exp_time)
                        ) * 100
                    else:
                        self.pbar_percent = 0
                    if self.max_exp_time - (time.time() - self.start_exp_time) > 0:
                        min = int(
                            (self.max_exp_time - (time.time() - self.start_exp_time))
                            / 60
                        )
                        sec = int(
                            (self.max_exp_time - (time.time() - self.start_exp_time))
                            % 60
                        )
                    else:
                        min = 0
                        sec = 0
                    self.installation_window.label_time.setText(
                        QApplication.translate('exp_flow',f"Осталось {min}:{sec} мин")
                    )
                    self.update_pbar()
            else:
                self.installation_window.label_time.setText(QApplication.translate('exp_flow',"Осталось -- мин"))
            self.show_th_window()

            if (
                self.exp_th_connect.is_measurement_data_updated
                and self.graph_window is not None
            ):
                self.exp_th_connect.is_measurement_data_updated = False
                self.graph_window.update_graphics(self.measurement_parameters)
        else:
            self.timer_for_connection_main_exp_thread.stop()
            self.installation_window.pbar.setValue(0)
            self.preparation_experiment()
            self.installation_window.label_time.setText("")

    def stoped_experiment(self):
        self.stop_experiment = True
        self.set_state_text(QApplication.translate('exp_flow',"Остановка") + "...")

    def pause_exp(self):
        if self.is_experiment_running():
            if self.pause_flag:
                self.pause_flag = False
                self.installation_window.pause_button.setText(QApplication.translate('exp_flow',"Пауза"))
                self.timer_for_pause_exp.stop()
                self.installation_window.pause_button.setStyleSheet(
                    ready_style_background
                )

                self.start_exp_time += time.time() - self.pause_start_time
                for device, ch in self.get_active_ch_and_device():
                    if ch.am_i_active_in_experiment:
                        if device.get_trigger(ch) == QApplication.translate('exp_flow', "Таймер"):
                            ch.previous_step_time += time.time() - self.pause_start_time

            else:
                self.installation_window.pause_button.setText(QApplication.translate('exp_flow',"Возобновить"))
                self.pause_flag = True
                self.set_state_text(QApplication.translate('exp_flow',"Ожидание продолжения") + "...")
                self.timer_for_pause_exp.start(50)
                self.pause_start_time = time.time()

    def show_th_window(self):
        if self.exp_th_connect.flag_show_message :
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

    def calc_last_exp_time(self):
        buf_time = [0]
        for device, ch in self.get_active_ch_and_device():
            if ch.am_i_active_in_experiment :
                trig = device.get_trigger(ch)
                if trig == QApplication.translate('exp_flow', "Таймер"):
                    steps = device.get_steps_number(ch) - ch.number_meas
                    if steps is not False:
                        t = (
                            steps
                            * (device.get_trigger_value(ch) + ch.last_step_time)
                            * float(self.repeat_meas)
                        )
                        buf_time.append(t)
        self.max_exp_time = max(buf_time) + (time.time() - self.start_exp_time)

    def update_pbar(self) -> None:
        self.installation_window.pbar.setValue(int(self.pbar_percent))

    def calculate_exp_time(self):
        """оценивает продолжительность эксперимента, возвращает результат в секундах, если эксперимент бесконечно долго длится, то вернется ответ True. В случае ошибки при расчете количества секунд вернется False"""
        # проверить, есть ли бесконечный эксперимент, если да, то расчет не имеет смысла, и анализ в процессе выполнения тоже
        # во время эксперимента после каждого измерения пересчитывается максимальное время каждого прибора и выбирается максимум, от этого максимума рассчитывается оставшийся процент времени

        self.is_experiment_endless = self.analyse_endless_exp()
        if self.is_experiment_endless :
            return True  # вернем правду в случае бесконечного эксперимента

        max_exp_time = 0

        for device in self.dict_active_device_class.values():
            for ch in device.channels:
                buf_time = False
                if ch.is_ch_active():
                    trig = device.get_trigger(ch)
                    if trig == QApplication.translate('exp_flow', "Таймер"):
                        steps = device.get_steps_number(ch)
                        if steps is not False:
                            buf_time = (
                                steps
                                * (device.get_trigger_value(ch) + ch.base_duration_step)
                            ) * float(self.repeat_meas) * float(self.repeat_experiment)

                    elif trig == QApplication.translate('exp_flow', "Внешний сигнал"):
                        # TODO: рассчитать время в случае срабатывания цепочек приборов. Найти корень цепочки и смотреть на его параметры, значение таймера и количество повторов, затем рассчитать длительность срабатывания цепочки и сравнить со значением таймера, вернуть наибольшее
                        continue
                    else:
                        continue

                if buf_time is not False:

                    max_exp_time = max(max_exp_time, buf_time)

        return max_exp_time

    def pause_actions(self):
        """функция срабатывает по таймеру во время паузы эксперимента"""

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

        style = (
            "background-color: rgb("
            + str(self.bright)
            + ","
            + "255"
            + ","
            + str(self.bright)
            + ");"
        )

        self.installation_window.pause_button.setStyleSheet(style)

    def get_execute_part(self):
        """Возващает спсок из устройства и канала, которые должны сделать действие, отбор выполняется с учетом приоритета"""

        target_execute = False
        target_priority = self.min_priority + 1
        for device in self.dict_active_device_class.values():
            for ch in device.channels:
                if ch.is_ch_active():
                    if ch.am_i_active_in_experiment:
                        if device.get_status_step(ch_name=ch.get_name()) :
                            if ch.get_priority() < target_priority:
                                target_execute = [device, ch]
                                target_priority = ch.get_priority()
        return target_execute
    
    def update_parameters(self, data, entry, time):
            try:
                device, channel = entry[0].split()
            except:
                device, channel = "unknown_dev_1", "unknown_ch-1"
            parameter_pairs = entry[1:]
            status = True

            if "pig_in_a_poke" in device:
                #костыль, этот тип прибора обрабатываем отдельно, потому что знаем, 
                #что в качестве первого параметра он всегда будет иметь строку
                #и потом остальные значения не попадут в числовые отображаемые параметры см. ниже
                new_pairs = []
                for index, pair in enumerate(parameter_pairs):
                    if (index+1)%2==0:
                        new_pairs.append(pair)
                parameter_pairs = new_pairs

            for parameter_pair in parameter_pairs:
                name, value = parameter_pair[0].split("=")
                if "wavech" in name:  # oscilloscope wave
                    value = value.split("|")
                    for val in value:
                        try:
                            val = float(val)
                        except:
                            status = False
                            break
                else:
                    try:
                        value = float(value)
                    except:
                        # Этот блок необходим потому, что все полученные данные имеют одинаковую метку времени, а она записывается в отдельный массив
                        # если хоть один из них не преобразовывается в число,
                        # а другие преобразовываются. то в будущем возникнет сдвиг в данных.
                        # Это не учтено при обработке.
                        #TODO: проанализировать, можно ли преобразовывать данные в числа и добавлять в файл результатов, если хотя бы один из них не преобразуется в число
                        #исправить это
                        status = False
                        break
            if status:
                if device not in data:
                    data[device] = {}
                if channel not in data[device]:
                    data[device][channel] = {}

                for parameter_pair in parameter_pairs:
                    name, value = parameter_pair[0].split("=")
                    if "wavech" in name:  # oscilloscope wave
                        value = value.split("|")
                        buf = []
                        for val in value:
                            buf.append(float(val))
                        value = numpy.array(buf)

                    else:
                        value = float(value)

                    if name not in data[device][channel]:
                        data[device][channel][name] = []
                    data[device][channel][name].append(value)

                if "time" not in data[device][channel]:
                    data[device][channel]["time"] = []
                data[device][channel]["time"].append(time)
            return status, data

    def set_start_priorities(self):
        self.min_priority = 0
        priority = 1

        for device in self.dict_active_device_class.values():
            for ch in device.channels:
                if ch.is_ch_active():
                    ch.am_i_active_in_experiment = True
                    ch.do_last_step = False
                    ch.number_meas = 0
                    ch.previous_step_time = time.time()
                    ch.pause_time = device.get_trigger_value(ch)
                    priority += 1
                    self.min_priority += 1
    
    def set_settings_before_exp(self):
        ch_done = {}
        status = True
        for dev, ch in self.get_active_ch_and_device():

            if ch.number in ch_done.values() and dev.get_name() in ch_done.keys():
                continue

            ch_done[dev.get_name()] = ch.number

            try:
                ans = dev.action_before_experiment(ch.number)
            except Exception as ex:
                ans = False
                logger.warning(
                    f"Ошибка действия прибора {dev} перед экспериментом: {str(ex)}"
                )
            if not ans:
                logger.debug(
                    "ошибка при настройке " + dev.get_name() + " перед экспериментом"
                )
                self.add_text_to_log(
                    QApplication.translate('exp_flow',"Ошибка настройки")
                    + " "
                    + dev.get_name()
                    + " ch-"
                    + str(ch.number)
                    + " "
                    + QApplication.translate('exp_flow',"перед экспериментом"),
                    "err",
                )
                if not self.is_debug:
                    status = False
                    self.set_state_text(QApplication.translate('exp_flow',"Остановка, ошибка"))
                    break
                # --------------------------------------------------------
            else:
                self.add_text_to_log(
                    dev.get_name() + " ch-" + str(ch.number) + QApplication.translate('exp_flow'," настроен")
                )
                
        return status

    def check_connections(self):
        '''checking connection devices'''
        status = True
        for dev in self.dict_active_device_class.values():
            is_connect = dev.check_connect()


            if not is_connect:
                status = False
                logger.warning(f"Нет ответа прибора {dev.get_name()}")
                self.add_text_to_log(
                    QApplication.translate('exp_flow',"Прибор")
                    + " " + dev.get_name() + " "
                    + QApplication.translate('exp_flow',"не отвечает"),
                    "err",
                )
            else:
                if is_connect != None:
                    self.add_text_to_log(
                        QApplication.translate('exp_flow',"Ответ") + " " + dev.get_name() + " " + str(is_connect)
                    )

        if self.is_debug:
            status = True

        return status
    
    def write_meta_data(self):
        self.meta_data_exp.exp_start_time = self.start_exp_time
        
        number = 1
        for dev, ch in self.get_active_ch_and_device():
            self.meta_data_exp.actors_classes[number] = ch
            self.meta_data_exp.actors_names[number] = dev.name + " " + ch.ch_name
            self.meta_data_exp.numbers[ch] = number
            number+=1
            
            for nm, val in ch.__dict__.items():
                print(nm, val)
        
    def exp_th(self):
        
        self.meta_data_exp = metaDataExp()

        logger.debug("запущен поток эксперимента")
        self.max_exp_time = 10
        self.start_exp_time = time.time()
        
        self.write_meta_data()
        
        #=================
        #self.meta_data_exp.print_meta_data()
        #=================
        
        self.exp_call_stack.set_data(self.meta_data_exp)

        #проверка соединения приборов
        status = self.check_connections()
        # print("запущен поток эксперимента")
        if status != False:
            status = self.set_settings_before_exp()

        error = not status  # флаг ошибки, будет поднят при ошибке во время эксперимента
        error_start_exp = not status

        if error is False and self.stop_experiment is False:

            self.max_exp_time = self.calculate_exp_time()
            if self.max_exp_time is True:
                # эксперимент бесконечен
                pass
            elif self.max_exp_time is False:
                self.max_exp_time = 100000
                # не определено время

            self.start_exp_time = time.time()
            self.installation_window.pbar.setMinimum(0)
            self.installation_window.pbar.setMaximum(100)

            self.set_start_priorities()

        target_execute = False
        self.exp_th_connect.is_update_pbar = True
        number_active_device = 4
        #----------------------------------------------------------------------------------------------
        if not error_start_exp:
            for i in range(self.repeat_experiment):
                if error :
                    break
                if i > 0:
                    logger.info("подготовка к повтору эксперименте")
                    self.stop_experiment = False
                    self.set_between_experiments()
                    
                while not self.stop_experiment and not error:

                    if not self.pause_flag:
                        self.set_state_text(QApplication.translate('exp_flow',"Продолжение эксперимента, приборов:") + str(number_active_device))

                        number_active_device = 0
                        number_device_which_act_while = 0

                        for device, ch in self.get_active_ch_and_device():
                            if not device.get_steps_number(ch) :
                                if not ch.do_last_step:
                                    number_device_which_act_while += 1

                            if ch.am_i_active_in_experiment:
                                number_active_device += 1
                                if device.get_trigger(ch) == QApplication.translate('exp_flow', "Таймер"):
                                    if time.time() - ch.previous_step_time >= ch.pause_time:
                                        ch.previous_step_time = time.time()
                                        device.set_status_step(ch.get_name(), True)
                                        
                        #print(f"{number_active_device=}")
                        if number_active_device == 0:
                            """остановка эксперимента, нет активных приборов"""
                            logger.info("остановка эксперимента, нет активных приборов")
                            self.set_state_text(QApplication.translate('exp_flow',"Остановка эксперимента") + "...")
                            self.stop_experiment = True
                        if (
                            number_device_which_act_while == number_active_device
                            and number_active_device == 1
                        ):
                            """если активный прибор один и он работает, пока работают другие, и у него не стоит флаг последнего шага то стоп"""
                            self.stop_experiment = True

                        target_execute = self.get_execute_part()

                        if target_execute is not False:
                            device = target_execute[0]
                            ch = target_execute[1]
                            
                            device.set_status_step(ch_name=ch.get_name(), status=False)
                            t = time.time()
                            ans_device = device.on_next_step(ch, repeat=3)

                            ans_request = False

                            if ans_device == ch_response_to_step.Step_done:
                                t = (
                                    time.time() - t
                                )  # вычисляем время, необходимое на выставление шага
                                ch.number_meas += 1

                                if ch.get_type() == "act":
                                    error, ans_request, time_step = self.do_act(device=device, ch=ch)

                                elif ch.get_type() == "meas":
                                    error, ans_request, time_step = self.do_meas(device=device, ch=ch)

                            elif ans_device == ch_response_to_step.End_list_of_steps:
                                ch.am_i_active_in_experiment = False
                            else:
                                ch.am_i_active_in_experiment = False

                            if device.get_steps_number(ch) is not False:#проверка останвки по количеству шагов
                                if (ch.number_meas >= device.get_steps_number(ch) ):
                                    ch.am_i_active_in_experiment = False

                            if ch.do_last_step:#был сделан последний шаг
                                ch.am_i_active_in_experiment = False
                                ch.do_last_step = False

                            if not ch.am_i_active_in_experiment:
                                self.add_text_to_log(
                                        text=device.get_name()
                                        + " "
                                        + str(ch.get_name()) + " "
                                        + QApplication.translate('exp_flow',"завершил работу"),
                                        status="ok",
                                    )
                            current_priority = ch.get_priority()
                            self.manage_subscribers(ch = ch)
                            self.update_actors_priority(exclude_dev = device, exclude_ch = ch)

                            self.meta_data_exp.exp_queue.append( self.meta_data_exp.numbers[ch] )
                            self.meta_data_exp.queue_info.append( f'''\n\r 
                                                                {device.get_name()} {ch.get_name()} \n\r
                                                                 Status request = {ans_request} \n\r
                                                                 Step time = {round(time_step, 3)} s\n\r
                                                                 Номер шага = {ch.number_meas} \n\r
                                                                 Приоритет = {current_priority}\n\r
                                                                ''' )
                            self.exp_call_stack.set_data(self.meta_data_exp)

        self.finalize_experiment(error=error, error_start_exp=error_start_exp)
        self.prepare_for_reexperiment()

    def manage_subscribers(self, ch):
        subscribers_do_operation = self.message_broker.get_subscribers(
            publisher=ch, name_subscribe=ch.do_operation_trigger
        )

        if not ch.am_i_active_in_experiment :
            """останавливаем подписчиков, которые срабатывали по завершению операции"""

            for subscriber in subscribers_do_operation:
                
                if subscriber.am_i_active_in_experiment :
                    
                    dev = subscriber.device_class
                    if "do_operation" in dev.get_trigger_value(subscriber):
                        
                        self.add_text_to_log(
                            text=dev.get_name()
                            + " "
                            + str(subscriber.get_name()) + " "
                            + QApplication.translate('exp_flow'," завершил работу"),
                            status="ok",
                        )
                        #subscriber.am_i_active_in_experiment = False
                        subscriber.do_last_step = True


            # испускаем сигнал о том, что работа закончена
            self.message_broker.push_publish(
                name_subscribe=ch.end_operation_trigger, publisher=ch
            )
            subscribers_end_operation = self.message_broker.get_subscribers(
                publisher=ch, name_subscribe=ch.end_operation_trigger
            )
            for subscriber in subscribers_end_operation:
                subscriber.do_last_step = True
        

        """передаем сигнал всем подписчикам о том, что операция произведена"""
        self.message_broker.push_publish(
            name_subscribe=ch.do_operation_trigger, publisher=ch
        )

    def update_actors_priority(self, exclude_dev, exclude_ch):
        for dev in self.dict_active_device_class.values():
            for channel in dev.channels:
                if channel.is_ch_active():
                    if (
                        dev == exclude_dev
                        and exclude_ch.get_name() == channel.get_name()
                    ):
                        continue
                    else:
                        if channel.get_priority() > exclude_ch.get_priority():
                            channel.increment_priority()
        exclude_ch.set_priority(priority=self.min_priority)

    def do_act(self, device, ch):
        error = False
        step_time = 0
        self.set_state_text(
            QApplication.translate('exp_flow',"Выполняется действие") + " "
            + device.get_name()
            + str(ch.get_name())
        )
        try:
            ans, param, step_time = device.do_action(ch)
        except Exception as ex:
            ans = ch_response_to_step.Step_fail
            logger.warning(
                f"Ошибка действия прибора {device} в эксперименте: {str(ex)}"
            )

        if ans == ch_response_to_step.Incorrect_ch:
            pass
        elif ans == ch_response_to_step.Step_done:
            self.add_text_to_log(
                QApplication.translate('exp_flow',"шаг") + " "
                + device.get_name()
                + " "
                + str(ch.get_name()) + " "
                + QApplication.translate('exp_flow',"сделан за") + " "
                + str(round(step_time))
                + " s"
            )
            self.calc_last_exp_time()
        elif ans == ch_response_to_step.Step_fail:
            ch.am_i_active_in_experiment = False
            self.add_text_to_log(
                QApplication.translate('exp_flow',"Ошибка опроса") + " "
                + device.get_name()
                + str(ch.get_name()),
                "err",
            )
            if not self.is_exp_run_anywhere:
                error = True  # ошибка при выполнении шага прибора, заканчиваем с ошибкой
        else:
            pass

        return error, ans, step_time

    def do_meas(self, device, ch):
        error = False
        ans = ch_response_to_step.Step_fail
        self.set_state_text(
            QApplication.translate('exp_flow',"Выполняется измерение") + " "
            + device.get_name()
            + str(ch.get_name())
        )
        logger.info(
            "Выполняется измерение "
            + device.get_name()
            + str(ch.get_name())
        )
        repeat_counter = 0
        step_time = 0
        while repeat_counter < self.repeat_meas:
            repeat_counter += 1
            try:
                result = device.do_meas(ch)
            except Exception as ex:
                result = ch_response_to_step.Step_fail
                logger.warning(
                    f"Ошибка измерения прибора {device} в эксперименте: {str(ex)}"
                )

            if result != ch_response_to_step.Step_fail:
                if len(result) == 3:
                    ans, param, step_time = result
                    message = False
                elif len(result) == 4:
                    ans, param, step_time, message = result
                else:
                    logger.warning(f"неправильная структура ответа прибора result = {result}")
                if ans == ch_response_to_step.Incorrect_ch:
                    break

                if message != False:
                    self.add_text_to_log(
                        device.get_name()
                        + " "
                        + str(ch.get_name())
                        + message
                    )

                time_t = time.time() - self.start_exp_time

                if device.device_type == "oscilloscope":
                    par = copy.deepcopy(param)
                    par = device.distribute_parameters(par)
                    status_update = False
                    for val in par.values():
                        status_update, buffer_meas = self.update_parameters(
                            data=self.measurement_parameters,
                            entry=val,
                            time=time_t,
                        )
                else:
                    status_update, buffer_meas = self.update_parameters(
                        data=self.measurement_parameters,
                        entry=param,
                        time=time_t,
                    )

                if status_update:
                    self.measurement_parameters = buffer_meas
                    self.exp_th_connect.is_measurement_data_updated = (
                        True
                    )

                ch.last_step_time = step_time

                self.write_data_to_buf_file("", addTime=True)
                for param in param:
                    self.write_data_to_buf_file(
                        message=str(param) + "\t"
                    )
                self.write_data_to_buf_file(message="\n")

                if ans == ch_response_to_step.Step_done:
                    self.add_text_to_log(
                        QApplication.translate('exp_flow',"шаг") + " "
                        + device.get_name()
                        + " "
                        + str(ch.get_name()) + " "
                        + QApplication.translate('exp_flow',"сделан за")+ " "
                        + str(round(step_time))
                        + " s"
                    )
                    self.calc_last_exp_time()

                elif ans == ch_response_to_step.Step_fail:
                    self.add_text_to_log(
                        QApplication.translate('exp_flow',"Ошибка опроса") + " "
                        + device.get_name()
                        + " "
                        + str(ch.get_name()),
                        "err",
                    )
                    if not self.is_exp_run_anywhere :
                        ch.am_i_active_in_experiment = False
                        error = True  # ошибка при выполнении шага прибора, заканчиваем с ошибкой
                    break

        return error, ans, step_time
    
    def finalize_experiment(self, error=False, error_start_exp=False):
        for dev, ch in self.get_active_ch_and_device():
            ans = dev.action_end_experiment(ch)

        self.pbar_percent = 0  # сбрасываем прогресс бар
         
        self.meta_data_exp.exp_stop_time = time.time()
        
        if self.graph_window is not None:
            self.graph_window.update_graphics(self.measurement_parameters, is_exp_stop = True)#сообщаем окну просмотра, что эксперимент завершен

        if error:
            self.add_text_to_log(QApplication.translate('exp_flow',"Эксперимент прерван из-за ошибки"), "err")
            logger.debug("Эксперимент прерван из-за ошибки")
            # вывод окна с сообщением в другом потоке
            if error_start_exp :
                self.exp_th_connect.message = (
                    QApplication.translate('exp_flow',"Эксперимент прерван из-за ошибки при настройке прибора")
                )
            else:
                self.exp_th_connect.message = (
                    QApplication.translate('exp_flow',"Эксперимент прерван из-за ошибки при опросе прибора")
                )
            self.exp_th_connect.message_status = message_status.critical

        else:
            self.add_text_to_log(QApplication.translate('exp_flow',"Эксперимент завершен"))
            logger.debug("Эксперимент завершен")
            self.exp_th_connect.message = QApplication.translate('exp_flow',"Эксперимент завершен")
            self.exp_th_connect.message_status = message_status.info
        # ждем, пока ббудет показано сообщение в основном потоке
        self.exp_th_connect.is_message_show = False
        self.exp_th_connect.flag_show_message = True
        while not self.exp_th_connect.is_message_show:
            pass
        self.set_state_text(QApplication.translate('exp_flow',"Сохранение результатов"))
        if not error_start_exp :
            try:
                self.save_results()
            except:
                logger.debug("не удалось сохранить результаты", self.buf_file)

    def prepare_for_reexperiment(self):
        # ------------------подготовка к повторному началу эксперимента---------------------
        self.set_state_text(QApplication.translate('exp_flow',"Подготовка к эксперименту"))
        self.message_broker.clear_all_subscribers()
        self.is_experiment_endless = False
        self.stop_experiment = False
        self.installation_window.start_button.setText(QApplication.translate('exp_flow',"Старт"))
        self.pause_flag = True
        self.pause_exp()
        self.installation_window.pause_button.setStyleSheet(not_ready_style_background)
        #for device in self.dict_active_device_class.values():
        #    device.am_i_active_in_experiment = True
        self.exp_th_connect.is_update_pbar = False
        # self.installation_window.open_graph_button.setEnabled(False)
        self.set_state_text(QApplication.translate('exp_flow',"Ожидание старта"))
        self.is_search_resources = True#разрешение на сканирование ресурсов

    def set_between_experiments(self):
        for device in self.dict_active_device_class.values():
            for ch in device.channels:
                if ch.is_ch_active():
                    ch.am_i_active_in_experiment = True
                    ch.number_meas = 0
            device.confirm_parameters()

def print_data(data):
    for device, channels in data.items():
        print(f"Device: {device}")
        for channel, parameters in channels.items():
            print(f"Channel: {channel}")
            for parameter, values in parameters.items():
                if parameter == "time":
                    print(f"  {parameter}: {values}")
                else:
                    print(
                        f"  {parameter}: {', '.join([str(value) for value in values])}"
                    )

class metaDataExp():
    def __init__(self):
        self.actors_names   = {}
        self.actors_classes = {}
        self.numbers        = {}
        self.exp_queue      = []
        self.queue_info     = []
        self.exp_start_time = 0
        self.exp_stop_time  = 0
        
    def get_meta_data(self):
        pass
    
    def print_meta_data(self):
        print("number: \t name: \t steps:")
        for num, obj in self.actors_classes.items():
            name = self.actors_names[num]
            num_steps = obj.dict_settable_parameters["num steps"]
            print(f"{num} \t { name } \t { num_steps }")
            
        print("exp queue:")
        print(self.exp_queue)
        
        print("queue info:")
        print(self.queue_info)
        
        print(f"time exp = {self.exp_stop_time - self.exp_start_time} sec")
        
        max_chars = max(  len(act) for act in self.actors_names.values()  )
        
        for num_actor in self.actors_names.keys():
            buf = []
            name = self.actors_names[num_actor]
            for act in self.exp_queue:
                if num_actor == act:
                    buf.append("###")
                else:
                    buf.append("...")
            print(name.ljust(max_chars),  "".join(buf))
            
    