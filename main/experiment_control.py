import copy
import enum
import logging
import time

import numpy

from Analyse_in_installation import analyse
from Classes import (
    ch_response_to_step,
    not_ready_style_background,
    ready_style_background,
)

logger = logging.getLogger(__name__)


class exp_th_connection:
    def __init__(self) -> None:
        self.flag_show_message = False
        self.message = ""
        self.message_status = message_status.info
        self.is_message_show = False
        self.ask_save_the_results = False
        self.is_update_pbar = False
        self.is_measurement_data_updated = False
        self.start_exp_time = 0


class message_status(enum.Enum):
    info = 1
    warning = 2
    critical = 3


class experimentControl(analyse):
    def __init__(self) -> None:
        super().__init__()
        self.exp_th_connect = exp_th_connection()
        self.experiment_thread = None
        self.stop_experiment = False
        self.pause_start_time = 0

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
                        "Бесконечный эксперимент"
                    )
                    self.update_pbar()
                else:

                    if self.exp_th_connect.is_update_pbar == True:
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
                        f"Осталось {min}:{sec} мин"
                    )
                    self.update_pbar()
            else:
                self.installation_window.label_time.setText("Осталось -- мин")
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
        self.set_state_text("Остановка...")

    def pause_exp(self):
        if self.is_experiment_running():
            if self.pause_flag:
                self.pause_flag = False
                self.installation_window.pause_button.setText("Пауза")
                self.timer_for_pause_exp.stop()
                self.installation_window.pause_button.setStyleSheet(
                    ready_style_background
                )

                self.start_exp_time += time.time() - self.pause_start_time
                for device, ch in self.get_active_ch_and_device():
                    if ch.am_i_active_in_experiment:
                        if device.get_trigger(ch) == "Таймер":
                            ch.previous_step_time += time.time() - self.pause_start_time

            else:
                self.installation_window.pause_button.setText("Возобновить")
                self.pause_flag = True
                self.set_state_text("Ожидание продолжения...")
                self.timer_for_pause_exp.start(50)
                self.pause_start_time = time.time()

    def show_th_window(self):
        if self.exp_th_connect.flag_show_message == True:
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
            if ch.am_i_active_in_experiment == True:
                trig = device.get_trigger(ch)
                if trig == "Таймер":
                    steps = device.get_steps_number(ch) - ch.number_meas
                    if steps is not False:
                        t = (
                            steps
                            * (device.get_trigger_value(ch) + ch.last_step_time)
                            * float(
                                self.installation_window.repeat_measurement_enter.currentText()
                            )
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
        if self.is_experiment_endless == True:
            return True  # вернем правду в случае бесконечного эксперимента

        max_exp_time = 0

        for device in self.dict_active_device_class.values():
            for ch in device.channels:
                buf_time = False
                if ch.is_ch_active():
                    trig = device.get_trigger(ch)
                    if trig == "Таймер":
                        steps = device.get_steps_number(ch)
                        if steps is not False:
                            buf_time = (
                                steps
                                * (device.get_trigger_value(ch) + ch.base_duration_step)
                            ) * float(
                                self.installation_window.repeat_measurement_enter.currentText()
                            )

                    elif trig == "Внешний сигнал":
                        # TODO: рассчитать время в случае срабатывания цепочек приборов. Найти корень цепочки и смотреть на его параметры, значение таймера и количество повторов, затем рассчитать длительность срабатывания цепочки и сравнить со значением таймера, вернуть наибольшее
                        continue
                    else:
                        continue

                if buf_time is not False:

                    if buf_time > max_exp_time:
                        max_exp_time = copy.deepcopy(buf_time)

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
                        if device.get_status_step(ch_name=ch.get_name()) == True:
                            if ch.get_priority() < target_priority:
                                target_execute = [device, ch]
                                target_priority = ch.get_priority()
        # if target_execute is not False:
        #    print(f"{target_execute=}")
        return target_execute
    
    def update_parameters(self, data, entry, time):
            try:
                device, channel = entry[0].split()
            except:
                pass
            parameter_pairs = entry[1:]
            status = True

            # checking number
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
            #print(f"{data=}")
            return status, data

    def set_start_priorities(self):
        self.min_priority = 0
        priority = 1

        for device in self.dict_active_device_class.values():
            for ch in device.channels:
                if ch.is_ch_active():
                    ch.am_i_active_in_experiment = True
                    ch.number_meas = 0
                    ch.previous_step_time = time.time()
                    ch.pause_time = device.get_trigger_value(ch)
                    priority += 1
                    self.min_priority += 1
    
    def exp_th(self):

        status = True
        self.start_exp_time = time.time()
        self.max_exp_time = 100
        self.installation_window.pbar.setMinimum(0)
        self.installation_window.pbar.setMaximum(100)
        self.add_text_to_log("настройка приборов.. ")
        logger.debug("запущен поток эксперимента")
        # print("запущен поток эксперимента")

        for dev, ch in self.get_active_ch_and_device():
            # print(ch.number, "канал состояние")
            try:
                ans = dev.action_before_experiment(ch.number)
            except Exception as ex:
                ans = False
                logger.warning(
                    f"Ошибка действия прибора {dev} перед экспериментом: {str(ex)}"
                )
            if ans == False:
                logger.debug(
                    "ошибка при настройке " + dev.get_name() + " перед экспериментом"
                )
                self.add_text_to_log(
                    "Ошибка настройки "
                    + dev.get_name()
                    + " ch-"
                    + str(ch.number)
                    + " перед экспериментом",
                    "err",
                )
                if not self.is_debug:
                    status = False
                    self.set_state_text("Остановка, ошибка")
                    break
                # --------------------------------------------------------
            else:
                self.add_text_to_log(
                    dev.get_name() + " ch-" + str(ch.number) + " настроен"
                )

        error = not status  # флаг ошибки, будет поднят при ошибке во время эксперимента
        error_start_exp = not status
        if error is False and self.stop_experiment == False:

            self.max_exp_time = self.calculate_exp_time()
            if self.max_exp_time == True:
                # эксперимент бесконечен
                pass
            elif self.max_exp_time == False:
                self.max_exp_time = 100000
                # не определено время

            self.start_exp_time = time.time()
            self.installation_window.pbar.setMinimum(0)
            self.installation_window.pbar.setMaximum(100)

            self.set_start_priorities()

        target_execute = False
        self.exp_th_connect.is_update_pbar = True
        if not error_start_exp:
            while not self.stop_experiment and error == False:

                if self.pause_flag:
                    pass

                else:
                    self.set_state_text("Продолжение эксперимента")

                    number_active_device = 0
                    number_device_which_act_while = 0

                    for device, ch in self.get_active_ch_and_device():
                        if device.get_steps_number(ch) == False:
                            number_device_which_act_while += 1

                        if ch.am_i_active_in_experiment:
                            number_active_device += 1
                            if device.get_trigger(ch) == "Таймер":
                                if time.time() - ch.previous_step_time >= ch.pause_time:
                                    ch.previous_step_time = time.time()
                                    device.set_status_step(ch.get_name(), True)

                    if number_active_device == 0:
                        """остановка эксперимента, нет активных приборов"""
                        logger.debug("остановка эксперимента, нет активных приборов")
                        self.set_state_text("Остановка эксперимента...")
                        self.stop_experiment = True
                    if (
                        number_device_which_act_while == number_active_device
                        and number_active_device == 1
                    ):
                        """если активный прибор один и он работает, пока работают другие, то стоп"""
                        self.stop_experiment = True

                    target_execute = self.get_execute_part()

                    if target_execute is not False:
                        device = target_execute[0]
                        ch = target_execute[1]
                        device.set_status_step(ch_name=ch.get_name(), status=False)
                        t = time.time()
                        ans_device = device.on_next_step(ch, repeat=3)

                        if ans_device == ch_response_to_step.Step_done:
                            t = (
                                time.time() - t
                            )  # вычисляем время, необходимое на выставление шага
                            ch.number_meas += 1
                            if ch.get_type() == "act":
                                self.set_state_text(
                                    "Выполняется действие "
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
                                        "шаг "
                                        + device.get_name()
                                        + " "
                                        + str(ch.get_name())
                                        + " сделан за "
                                        + str(round(step_time))
                                        + " сек"
                                    )
                                    self.calc_last_exp_time()
                                elif ans == ch_response_to_step.Step_fail:
                                    ch.am_i_active_in_experiment = False
                                    self.add_text_to_log(
                                        "Ошибка опроса "
                                        + device.get_name()
                                        + str(ch.get_name()),
                                        "err",
                                    )
                                    if self.is_exp_run_anywhere == False:
                                        error = True  # ошибка при выполнении шага прибора, заканчиваем с ошибкой
                                else:
                                    pass

                            elif ch.get_type() == "meas":
                                self.set_state_text(
                                    "Выполняется измерение "
                                    + device.get_name()
                                    + str(ch.get_name())
                                )
                                logger.info(
                                    "Выполняется измерение "
                                    + device.get_name()
                                    + str(ch.get_name())
                                )
                                repeat_counter = 0
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
                                                "шаг "
                                                + device.get_name()
                                                + " "
                                                + str(ch.get_name())
                                                + " сделан за "
                                                + str(round(step_time))
                                                + " сек"
                                            )
                                            self.calc_last_exp_time()
                                        if ans == ch_response_to_step.Step_fail:
                                            self.add_text_to_log(
                                                "Ошибка опроса "
                                                + device.get_name()
                                                + " "
                                                + str(ch.get_name()),
                                                "err",
                                            )
                                            if self.is_exp_run_anywhere == False:
                                                ch.am_i_active_in_experiment = False
                                                error = True  # ошибка при выполнении шага прибора, заканчиваем с ошибкой
                                            break
                        elif ans_device == ch_response_to_step.End_list_of_steps:
                            self.add_text_to_log(
                                text=device.get_name()
                                + " "
                                + str(ch.get_name())
                                + " завершил "
                                + "работу",
                                status="ok",
                            )
                            ch.am_i_active_in_experiment = False
                        else:
                            ch.am_i_active_in_experiment = False

                        if device.get_steps_number(ch) is not False:
                            if (ch.number_meas >= device.get_steps_number(ch) 
                            or "end_work" in str(device.get_trigger_value(ch)) ):
                                
                                self.add_text_to_log(
                                    text=device.get_name()
                                    + " "
                                    + str(ch.get_name())
                                    + " завершил "
                                    + "работу",
                                    status="ok",
                                )
                                
                                ch.am_i_active_in_experiment = False
                        subscribers = self.message_broker.get_subscribers(
                            publisher=ch, name_subscribe=ch.do_operation_trigger
                        )

                        if ch.am_i_active_in_experiment == False:
                            """останавливаем подписчиков, которые срабатывали по завершению операции"""
                            for subscriber in subscribers:
                                dev = subscriber.device_class
                                if "do_operation" in dev.get_trigger_value(subscriber):
                                    self.add_text_to_log(
                                        text=dev.get_name()
                                        + " "
                                        + str(subscriber.get_name())
                                        + " завершил "
                                        + "работу",
                                        status="ok",
                                    )
                                    subscriber.am_i_active_in_experiment = False
                            # испускаем сигнал о том, что работа закончена
                            self.message_broker.push_publish(
                                name_subscribe=ch.end_operation_trigger, publisher=ch
                            )

                        else:
                            """передаем сигнал всем подписчикам о том, что операция произведена"""
                            self.message_broker.push_publish(
                                name_subscribe=ch.do_operation_trigger, publisher=ch
                            )

                        for dev in self.dict_active_device_class.values():
                            for channel in dev.channels:
                                if channel.is_ch_active():
                                    if (
                                        dev == device
                                        and ch.get_name() == channel.get_name()
                                    ):
                                        continue
                                    else:
                                        if channel.get_priority() > ch.get_priority():
                                            channel.increment_priority()
                        ch.set_priority(priority=self.min_priority)
        self.finalize_experiment(error=error, error_start_exp=error_start_exp)
        self.prepare_for_reexperiment()

    def finalize_experiment(self, error=False, error_start_exp=False):
        for dev, ch in self.get_active_ch_and_device():
            ans = dev.action_end_experiment(ch)
            if ans == False:
                pass
                print("ошибка при действии " + dev.get_name() + " после эксперимента")
        self.pbar_percent = 0  # сбрасываем прогресс бар

        if error:
            self.add_text_to_log("Эксперимент прерван из-за ошибки", "err")
            logger.debug("Эксперимент прерван из-за ошибки")
            # вывод окна с сообщением в другом потоке
            if error_start_exp == True:
                self.exp_th_connect.message = (
                    "Эксперимент прерван из-за ошибки при настройке прибора"
                )
            else:
                self.exp_th_connect.message = (
                    "Эксперимент прерван из-за ошибки при опросе прибора"
                )
            self.exp_th_connect.message_status = message_status.critical

        else:
            self.add_text_to_log("Эксперимент завершен")
            logger.debug("Эксперимент завершен")
            self.exp_th_connect.message = "Эксперимент завершен"
            self.exp_th_connect.message_status = message_status.info
        # ждем, пока ббудет показано сообщение в основном потоке
        self.exp_th_connect.is_message_show = False
        self.exp_th_connect.flag_show_message = True
        while self.exp_th_connect.is_message_show == False:
            pass
        self.set_state_text("Сохранение результатов")
        if error_start_exp == False:
            try:
                self.save_results()
            except:
                logger.debug("не удалось сохранить результаты", self.buf_file)

    def prepare_for_reexperiment(self):
        # ------------------подготовка к повторному началу эксперимента---------------------
        self.set_state_text("Подготовка к эксперименту")
        self.message_broker.clear_all_subscribers()
        self.is_experiment_endless = False
        self.stop_experiment = False
        self.installation_window.start_button.setText("Старт")
        self.pause_flag = True
        self.pause_exp()
        self.installation_window.pause_button.setStyleSheet(not_ready_style_background)
        for device in self.dict_active_device_class.values():
            device.am_i_active_in_experiment = True
        self.exp_th_connect.is_update_pbar = False
        # self.installation_window.open_graph_button.setEnabled(False)
        self.set_state_text("Ожидание старта")
        self.is_search_resources = True#разрешение на сканирование ресурсов


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


if __name__ == "__main__":
    # 11:09:02 DS1104Z_1 ch-1_meas	['VMAX1=3,0']	['VMAX2=3,08']	['VMAX3=3,16']	['VMAX4=0,08']	['VMIN1=-0,08']	['VMIN2=0,0']	['VMIN3=-0,2']	['VMIN4=-0,04']	['VPP1=3,08']	['VPP2=3,08']	['VPP3=3,36']	['VPP4=0,12']	['VTOP1=2,944615']	['VTOP2=2,975514']	['VTOP3=2,992146']	['VTOP4=9,9e+37']	['VBASE1=-0,04293274']	['VBASE2=0,05339111']	['VBASE3=-0,008302002']	['VBASE4=9,9e+37']	['VAMP1=2,9829']	['VAMP2=2,9166']	['VAMP3=2,9983']	['VAMP4=9,9e+37']	['VAVG1=1,412107']	['VAVG2=1,477559']	['VAVG3=1,440669']	['VAVG4=0,01140472']	['VRMS1=2,051022']	['VRMS2=2,071482']	['VRMS3=2,080493']	['VRMS4=0,05324268']	['OVERshoot1=0,01853845']	['OVERshoot2=0,0357567']	['OVERshoot3=0,05594298']	['OVERshoot4=9,9e+37']	['MPAREA1=0,00145112']	['MPAREA2=0,00151344']	['MPAREA3=0,00148976']	['MPAREA4=0,0']	['PERIOD1=0,001']	['PERIOD2=0,001']	['PERIOD3=0,001']	['PERIOD4=9,9e+37']	['FREQUENCY1=999,9999']	['FREQUENCY2=999,9999']	['FREQUENCY3=999,9999']	['FREQUENCY4=9,9e+37']	['PWIDth1=0,0005']	['PWIDth2=0,0005']	['PWIDth3=0,0005']	['PWIDth4=9,9e+37']	['NWIDth1=0,0005']	['NWIDth2=0,0005']	['NWIDth3=0,0005']	['NWIDth4=9,9e+37']	['NDUTy1=0,5']	['NDUTy2=0,5']	['NDUTy3=0,5']	['NDUTy4=9,9e+37']	['TVMAX1=-0,000558']	['TVMAX2=0,000118']	['TVMAX3=1,4e-05']	['TVMAX4=-0,00058']	['TVMIN1=-0,000494']	['TVMIN2=-0,000466']	['TVMIN3=-0,00048']	['TVMIN4=-0,000582']	['PSLEWrate1=478007,7']	['PSLEWrate2=467539,7']	['PSLEWrate3=480071,7']	['PSLEWrate4=9,9e+37']	['VMID1=1,450841']	['VMID2=1,514453']	['VMID3=1,491922']	['VMID4=9,9e+37']
    names = "DS1104Z_1 ch-1_meas"

    my_list = [3.2] * 5 + [0.15] * 5
    val = [f"wavech{1}=" + "|".join(map(str, my_list))]

    parameters = [names, ["VMAX1=3.0"], ["VMAX2=3.08"], ["VMAX3=3.16"], val]
    data = {}
    print_data(data)
