import logging, time, enum, copy
from Analyse_in_installation import *

logger = logging.getLogger(__name__)


class exp_th_connection():
    def __init__(self) -> None:
        self.flag_show_message = False
        self.message = ""
        self.message_status = message_status.info
        self.is_message_show = False
        self.ask_save_the_results = False
        self.is_update_pbar = False
        self.is_measurement_data_updated = False

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
        
    def is_experiment_running(self) -> bool:
        return self.experiment_thread is not None and self.experiment_thread.is_alive()
    
    def connection_two_thread(self):
        '''функция для связи основного потока и потока эксперимента, поток эксперимента выставляет значения/флаги/сообщения, а основной поток их обрабатывает'''
        if self.is_experiment_running():
            #self.installation_window.open_graph_button.setEnabled(True)
            self.timer_for_connection_main_exp_thread.start(1000)
            self.installation_window.label_time.setText("")

            if not self.pause_flag:
                if self.is_experiment_endless:
                    self.pbar_percent = 50
                    self.installation_window.label_time.setText("Бесконечный эксперимент")
                    self.update_pbar()
                else:

                    if self.exp_th_connect.is_update_pbar == True:
                        self.pbar_percent = (((time.time() - self.start_exp_time)/self.max_exp_time))*100
                    else:
                        self.pbar_percent = 0
                    if self.max_exp_time - (time.time() - self.start_exp_time) > 0:
                        min = int( (self.max_exp_time - (time.time() - self.start_exp_time))/60 )
                        sec = int( (self.max_exp_time - (time.time() - self.start_exp_time))%60 )
                    else:
                        min = 0
                        sec = 0
                    self.installation_window.label_time.setText(f"Осталось {min}:{sec} мин")
                    self.update_pbar()
            else:
                self.installation_window.label_time.setText("Осталось -- мин")
            self.show_th_window()

            if self.exp_th_connect.is_measurement_data_updated and self.graph_window is not None:
                self.exp_th_connect.is_measurement_data_updated = False
                self.graph_window.update_dict_param(self.measurement_parameters)
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
                    ready_style_background)
                try:
                    self.start_exp_time += time.time() - self.pause_start_time
                except:
                    pass

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
                        t = steps * (device.get_trigger_value(ch) + ch.last_step_time)*float(self.installation_window.repeat_measurement_enter.currentText())                                                                                      
                        buf_time.append(t)
        self.max_exp_time = max(buf_time)+(time.time() - self.start_exp_time)

    def update_pbar(self) -> None:
        self.installation_window.pbar.setValue(int(self.pbar_percent))
        
    def calculate_exp_time(self):
        '''оценивает продолжительность эксперимента, возвращает результат в секундах, если эксперимент бесконечно долго длится, то вернется ответ True. В случае ошибки при расчете количества секунд вернется False'''
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
                            buf_time = (steps * \
                                (device.get_trigger_value(
                                    ch) + ch.base_duration_step))*float(self.installation_window.repeat_measurement_enter.currentText())

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
        '''функция срабатывает по таймеру во время паузы эксперимента'''

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

        style = "background-color: rgb(" + str(self.bright) + \
            "," + "255" + "," + str(self.bright) + ");"

        self.installation_window.pause_button.setStyleSheet(
            style)

    def get_execute_part(self):
        '''Возващает спсок из устройства и канала, которые должны сделать действие, отбор выполняется с учетом приоритета'''

        target_execute = False
        target_priority = self.min_priority+1
        for device in self.dict_active_device_class.values():
                        for ch in device.channels:
                            if ch.is_ch_active():
                                if ch.am_i_active_in_experiment:
                                    if device.get_status_step(ch_name = ch.get_name()) == True:
                                        if ch.get_priority() < target_priority:
                                            target_execute = [device, ch]
                                            target_priority = ch.get_priority()
        if target_execute is not False:
            print(f"{target_execute=}")
        return target_execute
    
    def exp_th(self):
        def update_parameters(data, entry, time):
            device, channel = entry[0].split()
            parameter_pairs = entry[1:]
            status = True

            for parameter_pair in parameter_pairs:
                name, value = parameter_pair[0].split('=')
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
                    name, value = parameter_pair[0].split('=')
                    value = float(value)
                    
                    if name not in data[device][channel]:
                        data[device][channel][name] = []
                    data[device][channel][name].append(value)

                if 'time' not in data[device][channel]:
                    data[device][channel]['time'] = []
                data[device][channel]['time'].append(time)
            return status, data

        status = True
        self.start_exp_time = time.time()
        self.max_exp_time = 100
        self.installation_window.pbar.setMinimum(0)
        self.installation_window.pbar.setMaximum(100)
        self.add_text_to_log("настройка приборов.. ")
        logger.debug("запущен поток эксперимента")
        #print("запущен поток эксперимента")

        for dev, ch in self.get_active_ch_and_device():
                    #print(ch.number, "канал состояние")
                    ans = dev.action_before_experiment(ch.number)
                    if ans == False:
                        logger.debug("ошибка при настройке " + dev.get_name() + " перед экспериментом")
                        self.add_text_to_log("Ошибка настройки " + dev.get_name() + " ch-" + str(ch.number) + " перед экспериментом", "err" )
                        if not self.is_debug:
                            status = False
                            self.set_state_text("Остановка, ошибка")
                            break
                        # --------------------------------------------------------
                    else:
                        self.add_text_to_log(
                            dev.get_name() + " ch-" + str(ch.number) + " настроен")

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

            print("общее время эксперимента", self.max_exp_time)
            logger.debug("общее время эксперимента = "+ str(self.max_exp_time))

            self.start_exp_time = time.time()
            self.installation_window.pbar.setMinimum(0)
            self.installation_window.pbar.setMaximum(100)

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
                        self.min_priority+=1

        target_execute = False
        sr = time.time()
        self.exp_th_connect.is_update_pbar = True
        if not error_start_exp:
            while not self.stop_experiment and error == False:

                if self.pause_flag:
                    pass
                    # TODO: пауза эксперимента. остановка таймеров
                else:
                    self.set_state_text("Продолжение эксперимента")

                    if time.time() - sr > 3:
                        sr = time.time()
                        print(f"{number_active_device=}")
                    
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
                        '''остановка эксперимента, нет активных приборов'''
                        logger.debug('остановка эксперимента, нет активных приборов')
                        self.set_state_text("Остановка эксперимента...")
                        self.stop_experiment = True
                        #print("не осталось активных приборов, эксперимент остановлен")
                    if number_device_which_act_while == number_active_device and number_active_device == 1:
                        '''если активный прибор один и он работает, пока работают другие, то стоп'''
                        self.stop_experiment = True

                    target_execute = self.get_execute_part()

                    if target_execute is not False:
                        device = target_execute[0]
                        ch = target_execute[1]
                        device.set_status_step(ch_name = ch.get_name(), status = False)
                        t = time.time()
                        ans_device = device.on_next_step(ch, repeat = 3)
                        if ans_device == ch_response_to_step.Step_done:
                            t = time.time() - t#вычисляем время, необходимое на выставление шага
                            ch.number_meas += 1
                            if ch.get_type() == "act":
                                self.set_state_text("Выполняется действие " + device.get_name() +  str(ch.get_name()))
                                logger.debug("Выполняется действие " + device.get_name() +  str(ch.get_name()))
                                ans, param, step_time = device.do_action(ch)
                                if ans == ch_response_to_step.Incorrect_ch:
                                    pass
                                elif ans == ch_response_to_step.Step_done:
                                    self.add_text_to_log("шаг " + device.get_name() + " " +  str(ch.get_name()) + " сделан за " + str(round(step_time)) + " сек" )
                                    self.calc_last_exp_time()
                                elif ans == ch_response_to_step.Step_fail:
                                    ch.am_i_active_in_experiment = False
                                    self.add_text_to_log("Ошибка опроса " + device.get_name()  + str(ch.get_name()), "err" )
                                    if self.is_exp_run_anywhere == False:
                                        error = True  # ошибка при выполнении шага прибора, заканчиваем с ошибкой
                                else:
                                    pass

                            elif ch.get_type() == "meas":
                                self.set_state_text("Выполняется измерение " + device.get_name() +  str(ch.get_name()))
                                logger.debug("Выполняется измерение " + device.get_name() +  str(ch.get_name()))
                                repeat_counter = 0
                                while repeat_counter < self.repeat_meas:
                                    repeat_counter += 1
                                    ans, param, step_time = device.do_meas(ch)
                                    if ans == ch_response_to_step.Incorrect_ch:
                                        break
                                    status, buffer_meas = update_parameters(data=self.measurement_parameters, entry=param, time=time.time() - self.start_exp_time)
                                    if status:
                                        self.measurement_parameters = buffer_meas
                                        self.exp_th_connect.is_measurement_data_updated = True
                                    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                                    def print_data(data):
                                        for device, channels in data.items():
                                            print(f"Device: {device}")
                                            for channel, parameters in channels.items():
                                                print(f"Channel: {channel}")
                                                for parameter, values in parameters.items():
                                                    if parameter == 'time':
                                                        print(f"  {parameter}: {values}")
                                                    else:
                                                        print(f"  {parameter}: {', '.join([str(value) for value in values])}")
                                    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                                    #print_data(self.measurement_parameters)
                                    
                                    ch.last_step_time = step_time

                                    self.write_data_to_buf_file("", addTime=True)
                                    for param in param:
                                        self.write_data_to_buf_file(message=str(param) + "\t")
                                    self.write_data_to_buf_file(message="\n")

                                    if ans == ch_response_to_step.Step_done:
                                        self.add_text_to_log("шаг " + device.get_name() + " " + str(ch.get_name()) + " сделан за " + str(round(step_time)) + " сек" )
                                        self.calc_last_exp_time()
                                    if ans == ch_response_to_step.Step_fail:
                                        ch.am_i_active_in_experiment = False
                                        self.add_text_to_log("Ошибка опроса " + device.get_name() + " " + str(ch.get_name()), "err" )
                                        if self.is_exp_run_anywhere == False:
                                            error = True  # ошибка при выполнении шага прибора, заканчиваем с ошибкой
                                        break
                        elif ans_device == ch_response_to_step.End_list_of_steps:
                            self.add_text_to_log(text = device.get_name() + " " + str(ch.get_name()) + " завершил " + "работу", status = "ok" )
                            ch.am_i_active_in_experiment = False
                        else:
                            ch.am_i_active_in_experiment = False

                        if device.get_steps_number(ch) is not False:
                            if ch.number_meas >= device.get_steps_number(ch) or "end_work" in str(device.get_trigger_value(ch)):
                                self.add_text_to_log(text = device.get_name() + " " + str(ch.get_name()) + " завершил " + "работу", status = "ok" )
                                ch.am_i_active_in_experiment = False
 
                        subscribers = self.message_broker.get_subscribers(publisher = ch, name_subscribe = ch.do_operation_trigger)

                        print(device.get_name(), "подписчики", subscribers)

                        if ch.am_i_active_in_experiment == False:
                            '''останавливаем подписчиков, которые срабатывали по завершению операции'''
                            for subscriber in subscribers:
                                dev = subscriber.device_class
                                if "do_operation" in dev.get_trigger_value(subscriber):
                                    self.add_text_to_log(text = dev.get_name() + " " + str(subscriber.get_name()) + " завершил " + "работу", status = "ok" )
                                    subscriber.am_i_active_in_experiment = False
                            #испускаем сигнал о том, что работа закончена
                            self.message_broker.push_publish(name_subscribe = ch.end_operation_trigger, publisher = ch)

                        else:
                            '''передаем сигнал всем подписчикам о том, что операция произведена'''
                            self.message_broker.push_publish(name_subscribe = ch.do_operation_trigger, publisher = ch)


                        for dev in self.dict_active_device_class.values():
                            for channel in dev.channels:
                                if channel.is_ch_active():
                                    print(f"{dev.get_name()} {channel.get_name()} {channel.get_priority()=} {channel.am_i_should_do_step=}")
                                    if dev == device and ch.get_name() == channel.get_name():
                                        continue
                                    else:
                                        if channel.get_priority() > ch.get_priority():
                                            channel.increment_priority()
                        ch.set_priority(priority = self.min_priority)

   # -----------------------------------------------------------
        for dev, ch in self.get_active_ch_and_device():
            ans = dev.action_end_experiment(ch)
            if ans == False:
                pass
                #print("ошибка при действии " + dev.get_name() + " после эксперимента")
        self.pbar_percent = 0  # сбрасываем прогресс бар

        if error:
            self.add_text_to_log("Эксперимент прерван из-за ошибки", "err")
            logger.debug("Эксперимент прерван из-за ошибки")
            # вывод окна с сообщением в другом потоке
            self.exp_th_connect.is_message_show = False
            if error_start_exp == True:
                self.exp_th_connect.message = "Эксперимент прерван из-за ошибки при настройке прибора"
            else:
                self.exp_th_connect.message = "Эксперимент прерван из-за ошибки при опросе прибора"
            self.exp_th_connect.message_status = message_status.critical
            self.exp_th_connect.flag_show_message = True

            # TODO: из-за какой ошибки прерван эксперимент, вывести в сообщение
        else:
            self.add_text_to_log("Эксперимент завершен")
            logger.debug("Эксперимент завершен")
            self.exp_th_connect.is_message_show = False
            self.exp_th_connect.message = "Эксперимент завершен"
            self.exp_th_connect.message_status = message_status.info
            self.exp_th_connect.flag_show_message = True

        # ждем, пока ббудет показано сообщение в основном потоке
        while self.exp_th_connect.is_message_show == False:
            pass
        self.set_state_text("Сохранение результатов")
        if error_start_exp == False:
            try:
                self.save_results()
            except:
                #print("не удалось сохранить результаты")
                logger.debug("не удалось сохранить результаты", self.buf_file)
        self.set_state_text("Подготовка к эксперименту")

        # ------------------подготовка к повторному началу эксперимента---------------------
        self.message_broker.clear_all_subscribers()
        self.is_experiment_endless = False
        self.stop_experiment = False
        self.installation_window.start_button.setText("Старт")
        self.pause_flag = True
        self.pause_exp()
        self.installation_window.pause_button.setStyleSheet(
            not_ready_style_background)
        for device in self.dict_active_device_class.values():
            device.am_i_active_in_experiment = True
        self.exp_th_connect.is_update_pbar = False
        #self.installation_window.open_graph_button.setEnabled(False)
        self.set_state_text("Ожидание старта")

        # -----------------------------------------------------------------------
