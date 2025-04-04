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
import time
import copy
import logging
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication
from Devices.Classes import (ch_response_to_step, not_ready_style_background,
                             ready_style_background)
from Handler_manager import messageBroker

logger = logging.getLogger(__name__)

class metaDataExp( QObject ):
    def __init__(self):
        super().__init__()
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

class experimentControl(QThread):
    device_action_started = pyqtSignal(str)
    device_action_ended = pyqtSignal(str)

    device_work_ended = pyqtSignal(str)
    device_connect_checked = pyqtSignal(str)
    device_set_ended = pyqtSignal(str)

    remaining_time_updated = pyqtSignal( float | bool )

    add_log_text = pyqtSignal( str, str )

    state_updated = pyqtSignal(str)

    meta_data_exp_updated = pyqtSignal( metaDataExp )

    def __init__(self, device_classes: dict, message_broker: messageBroker, is_debug: bool, is_experiment_endless: bool, repeat_exp: int, repeat_meas: int):
        super().__init__()
        self.device_classes = device_classes
        self.message_broker = message_broker
        self.is_debug = is_debug
        self.is_experiment_endless = is_experiment_endless
        self.repeat_experiment = repeat_exp
        self.repeat_meas = repeat_meas

    def run(self):
        
        self.meta_data_exp = metaDataExp()

        logger.debug("запущен поток эксперимента")
        self.max_exp_time = 10
        self.remaining_time
        self.start_exp_time = time.perf_counter()
        
        self.write_meta_data()
        
        #=================
        #self.meta_data_exp.print_meta_data()
        #=================
        
        self.meta_data_exp_updated.emit( self.meta_data_exp )#self.exp_call_stack.set_data(self.meta_data_exp)

        #проверка соединения приборов
        status = self.check_connections()
        # print("запущен поток эксперимента")
        if status != False:
            status = self.set_settings_before_exp()

        error = not status  # флаг ошибки, будет поднят при ошибке во время эксперимента
        error_start_exp = not status

        if error is False and self.__stop_experiment is False:

            self.max_exp_time = self.calculate_exp_time()
            if self.max_exp_time is True:
                # эксперимент бесконечен
                pass
            elif self.max_exp_time is False:
                self.max_exp_time = 100000
                # не определено время

            self.start_exp_time = time.perf_counter()
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
                    self.__stop_experiment = False
                    self.set_between_experiments()
                    
                while not self.__stop_experiment and not error:

                    if not self.__is_paused:
                        self.state_updated.emit(QApplication.translate('exp_flow',"Продолжение эксперимента, приборов:") + str(number_active_device))

                        number_active_device = 0
                        number_device_which_act_while = 0

                        for device, ch in self.get_active_ch_and_device():
                            if not device.get_steps_number(ch) :
                                if not ch.do_last_step:
                                    number_device_which_act_while += 1

                            if ch.am_i_active_in_experiment:
                                number_active_device += 1
                                if device.get_trigger(ch) == QApplication.translate('exp_flow', "Таймер"):
                                    if time.perf_counter() - ch.previous_step_time >= ch.pause_time:
                                        ch.previous_step_time = time.perf_counter()
                                        device.set_status_step(ch.get_name(), True)
                                        
                        #print(f"{number_active_device=}")
                        if number_active_device == 0:
                            """остановка эксперимента, нет активных приборов"""
                            logger.info("остановка эксперимента, нет активных приборов")
                            self.state_updated.emit(QApplication.translate('exp_flow',"Остановка эксперимента") + "...")
                            self.__stop_experiment = True
                        if (
                            number_device_which_act_while == number_active_device
                            and number_active_device == 1
                        ):
                            """если активный прибор один и он работает, пока работают другие, и у него не стоит флаг последнего шага то стоп"""
                            self.__stop_experiment = True

                        target_execute = self.get_execute_part()

                        if target_execute is not False:
                            device = target_execute[0]
                            ch = target_execute[1]
                            
                            device.set_status_step(ch_name=ch.get_name(), status=False)
                            t = time.perf_counter()
                            ans_device = device.on_next_step(ch, repeat=3)

                            ans_request = False

                            if ans_device == ch_response_to_step.Step_done:
                                t = (
                                    time.perf_counter() - t
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
                                self.add_log_text.emit(
                                        text=device.get_name()
                                        + " "
                                        + str(ch.get_name()) + " "
                                        + QApplication.translate('exp_flow',"завершил работу"),
                                        status="ok"
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
                            self.meta_data_exp_updated.emit( self.meta_data_exp )#self.exp_call_stack.set_data(self.meta_data_exp)

        self.finalize_experiment(error=error, error_start_exp=error_start_exp)
        self.prepare_for_reexperiment()

    def do_act(self, device, ch):
        error = False
        step_time = 0
        self.state_updated.emit(
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
            self.add_log_text.emit(
                QApplication.translate('exp_flow',"шаг") + " "
                + device.get_name()
                + " "
                + str(ch.get_name()) + " "
                + QApplication.translate('exp_flow',"сделан за") + " "
                + str(round(step_time))
                + " s")
            
            self.remaining_time = self.calc_last_exp_time()
            self.remaining_time_updated.emit(self.remaining_time)

        elif ans == ch_response_to_step.Step_fail:
            ch.am_i_active_in_experiment = False
            self.add_log_text.emit(
                QApplication.translate('exp_flow',"Ошибка опроса") + " "
                + device.get_name()
                + str(ch.get_name()),
                "err")
            if not self.is_exp_run_anywhere:
                error = True  # ошибка при выполнении шага прибора, заканчиваем с ошибкой
        else:
            pass

        return error, ans, step_time

    def do_meas(self, device, ch):
        error = False
        ans = ch_response_to_step.Step_fail
        self.state_updated.emit(
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
                    self.add_log_text.emit(
                        device.get_name()
                        + " "
                        + str(ch.get_name())
                        + message)

                time_t = time.perf_counter() - self.start_exp_time

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
                    self.add_log_text.emit(
                        QApplication.translate('exp_flow',"шаг") + " "
                        + device.get_name()
                        + " "
                        + str(ch.get_name()) + " "
                        + QApplication.translate('exp_flow',"сделан за")+ " "
                        + str(round(step_time))
                        + " s")
                    self.remaining_time = self.calc_last_exp_time()
                    self.remaining_time_updated.emit( self.remaining_time )

                elif ans == ch_response_to_step.Step_fail:
                    self.add_log_text.emit(
                        QApplication.translate('exp_flow',"Ошибка опроса") + " "
                        + device.get_name()
                        + " "
                        + str(ch.get_name()),
                        "err")
                    if not self.is_exp_run_anywhere :
                        ch.am_i_active_in_experiment = False
                        error = True  # ошибка при выполнении шага прибора, заканчиваем с ошибкой
                    break
            else:
                self.add_log_text.emit(
                    QApplication.translate('exp_flow',"Ошибка опроса") + " "
                    + device.get_name()
                    + " "
                    + str(ch.get_name()),
                    "err")
                if not self.is_exp_run_anywhere :
                    ch.am_i_active_in_experiment = False
                    error = True  # ошибка при выполнении шага прибора, заканчиваем с ошибкой
                break

        return error, ans, step_time
    
    def set_pause(self):
        self.__is_paused = True

    def unset_pause(self):
        self.__is_paused = False

    def stop_exp(self):
        self.__stop_experiment = True

    def calc_last_exp_time(self) -> float:
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
        max_exp_time = max(buf_time) + (time.perf_counter() - self.start_exp_time)
        return max_exp_time

    def calculate_exp_time(self):
        """оценивает продолжительность эксперимента, возвращает результат в секундах, если эксперимент бесконечно долго длится, то вернется ответ True. В случае ошибки при расчете количества секунд вернется False"""
        # проверить, есть ли бесконечный эксперимент, если да, то расчет не имеет смысла, и анализ в процессе выполнения тоже
        # во время эксперимента после каждого измерения пересчитывается максимальное время каждого прибора и выбирается максимум, от этого максимума рассчитывается оставшийся процент времени

        #self.is_experiment_endless = self.analyse_endless_exp()

        if self.is_experiment_endless :
            return True  # вернем правду в случае бесконечного эксперимента

        max_exp_time = 0

        for device in self.device_classes.values():
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

    def get_execute_part(self):
        """Возващает спсок из устройства и канала, которые должны сделать действие, отбор выполняется с учетом приоритета"""

        target_execute = False
        target_priority = self.min_priority + 1
        for device in self.device_classes.values():
            for ch in device.channels:
                if ch.is_ch_active():
                    if ch.am_i_active_in_experiment:
                        if device.get_status_step(ch_name=ch.get_name()) :
                            if ch.get_priority() < target_priority:
                                target_execute = [device, ch]
                                target_priority = ch.get_priority()
        return target_execute

    def set_start_priorities(self):
        self.min_priority = 0
        priority = 1

        for device in self.device_classes.values():
            for ch in device.channels:
                if ch.is_ch_active():
                    ch.am_i_active_in_experiment = True
                    ch.do_last_step = False
                    ch.number_meas = 0
                    ch.previous_step_time = time.perf_counter()
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
                self.add_log_text.emit(
                    QApplication.translate('exp_flow',"Ошибка настройки")
                    + " "
                    + dev.get_name()
                    + " ch-"
                    + str(ch.number)
                    + " "
                    + QApplication.translate('exp_flow',"перед экспериментом. Проверьте подключение."),
                    "err"
                )
                if not self.is_debug:
                    status = False
                    self.state_updated.emit(QApplication.translate('exp_flow',"Остановка, ошибка"))
                # --------------------------------------------------------
            else:
                self.add_log_text.emit(
                    dev.get_name() + " ch-" + str(ch.number) + QApplication.translate('exp_flow'," настроен")
                )
                
        return status

    def check_connections(self):
        '''checking connection devices'''
        status = True
        for dev in self.device_classes.values():
            is_connect = dev.check_connect()

            if not is_connect:
                status = False
                logger.warning(f"Нет ответа прибора {dev.get_name()}")
                self.add_log_text.emit(
                    QApplication.translate('exp_flow',"Прибор")
                    + " " + dev.get_name() + " "
                    + QApplication.translate('exp_flow',"не отвечает"),
                    "err",
                )
            else:
                if is_connect != None:
                    self.add_log_text.emit(
                        QApplication.translate('exp_flow',"Ответ") + " " + dev.get_name() + " " + str(is_connect)
                    )

        if self.is_debug:
            status = True

        return status

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
                        self.add_log_text.emit(
                            text=dev.get_name()
                            + " "
                            + str(subscriber.get_name()) + " "
                            + QApplication.translate('exp_flow'," завершил работу"),
                            status="ok"
                        )
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
        for dev in self.device_classes.values():
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

    def set_between_experiments(self):
            for device in self.device_classes.values():
                for ch in device.channels:
                    if ch.is_ch_active():
                        ch.am_i_active_in_experiment = True
                        ch.number_meas = 0
                device.confirm_parameters()
