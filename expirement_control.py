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

class expirementControl(analyse):
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
        buf_time = []
        for device, ch in self.get_active_ch_and_device():
            if ch.am_i_active_in_experiment == True:
                trig = device.get_trigger(ch.number)
                if trig == "Таймер":
                    steps = device.get_steps_number(ch.number) - ch.number_meas 
                    if steps is not False:
                        t = steps * (device.get_trigger_value(ch.number) + ch.last_step_time)*float(self.installation_window.repeat_measurement_enter.currentText())                                                                                      
                        buf_time.append(t)
        self.max_exp_time = max(buf_time)+(time.time() - self.start_exp_time)
        
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
                    trig = device.get_trigger(ch.number)
                    if trig == "Таймер":
                        steps = device.get_steps_number(ch.number)
                        if steps is not False:
                            buf_time = (steps * \
                                (device.get_trigger_value(
                                    ch.number) + ch.base_duration_step))*float(self.installation_window.repeat_measurement_enter.currentText())

                    elif trig == "Внешний сигнал":
                        # TODO: рассчитать время в случае срабатывания цепочек приборов. Найти корень цепочки и смотреть на его параметры, значение таймера и количество повторов, затем рассчитать длительность срабатывания цепочки и сравнить со значением таймера, вернуть наибольшее
                        continue
                    else:
                        continue

                if buf_time is not False:

                    if buf_time > max_exp_time:
                        max_exp_time = copy.deepcopy(buf_time)

        return max_exp_time
    
        if self.analyse_com_ports():

            # если оказались в этой точке, значит приборы настроены корректно и нет проблем с конфликтами ком портов, если подключение не будет установлено, то ключ снова будет сброшен
            self.key_to_start_installation = True
            self.set_state_text("Ожидание старта эксперимента")

            self.create_clients()
            self.set_clients_for_device()
            self.confirm_devices_parameters()
        else:
            self.key_to_start_installation = False

        if self.key_to_start_installation == True:
            self.installation_window.start_button.setStyleSheet(
                ready_style_background)
        else:
            self.installation_window.start_button.setStyleSheet(
                not_ready_style_background)
            
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
        self.max_exp_time = 10000
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
                        #print("ошибка при настройке " + dev.get_name() + " перед экспериментом")

                        if not self.is_debug:
                            status = False
                            self.set_state_text("Остановка, ошибка")
                            break

                        # --------------------------------------------------------

                    self.add_text_to_log(
                        dev.get_name() + " ch-" + str(ch.number) + " настроен")

        error = not status  # флаг ошибки, будет поднят при ошибке во время эксперимента
        # error = False
        # print(status, "статус")
        logger.debug(status, "статус")

        if error is False and self.stop_experiment == False:


            self.max_exp_time = self.calculate_exp_time()
            if self.max_exp_time == True:
                # эксперимент бесконечен
                pass
            elif self.max_exp_time == False:
                self.max_exp_time = 100000
                # не определено время

            #print("общее время эксперимента", self.max_exp_time)
            logger.debug("общее время эксперимента = "+ str(self.max_exp_time))

            self.start_exp_time = time.time()
            self.installation_window.pbar.setMinimum(0)
            self.installation_window.pbar.setMaximum(100)

            min_priority = 0
            priority = 1

            for device in self.dict_active_device_class.values():
                for ch in device.channels:
                    if ch.is_ch_active():
                        ch.am_i_active_in_experiment = True
                        ch.number_meas = 0
                        ch.previous_step_time = time.time()
                        ch.pause_time = device.get_trigger_value(ch.number)
                        priority += 1
                        min_priority+=1

        number_active_device = 0
        target_execute = False
        sr = time.time()
        self.exp_th_connect.is_update_pbar = True
        while not self.stop_experiment and error == False:

            if self.pause_flag:
                pass
                # TODO: пауза эксперимента. остановка таймеров
            else:
                self.set_state_text("Продолжение эксперимента")
                # ----------------------------
                if time.time() - sr > 2:
                    sr = time.time()
                    #print("активных приборов - ", number_active_device)
                # -----------------------------------
                
                number_active_device = 0
                number_device_which_act_while = 0

                for device, ch in self.get_active_ch_and_device():
                    if device.get_steps_number(ch.number) == False:
                        number_device_which_act_while += 1

                    if ch.am_i_active_in_experiment:
                        number_active_device += 1
                        if device.get_trigger(ch.number) == "Таймер":
                            if time.time() - ch.previous_step_time >= ch.pause_time:
                                ch.previous_step_time = time.time()
                                device.set_status_step(ch.number, True)

                if number_active_device == 0:
                    '''остановка эксперимента, нет активных приборов'''
                    logger.debug('остановка эксперимента, нет активных приборов')
                    self.set_state_text("Остановка эксперимента...")
                    self.stop_experiment = True
                    #print("не осталось активных приборов, эксперимент остановлен")
                if number_device_which_act_while == number_active_device and number_active_device == 1:
                    '''если активный прибор один и он работает, пока работают другие, то стоп'''
                    self.stop_experiment = True

                target_execute = False
                target_priority = min_priority+1
                for device in self.dict_active_device_class.values():
                    for ch in device.channels:
                        if ch.is_ch_active():
                            if device.get_status_step(ch.number) == True:
                                if ch.get_priority() < target_priority:
                                    target_execute = [device, ch]
                                    target_priority = ch.get_priority()

                if target_execute is not False:
                    device = target_execute[0]
                    ch = target_execute[1]
                    self.set_state_text(
                        "Выполняется действие " + device.get_name() + " ch-" + str(ch.number))
                    logger.debug("Выполняется действие " + device.get_name() + " ch-" + str(ch.number))
                    device.set_status_step(ch.number, False)
                    t = time.time()
                    ans, param, step_time = device.do_meas(ch.number)

                    status, buffer_meas = update_parameters(data=self.measurement_parameters, entry=param, time=time.time() - self.start_exp_time)
                    if status:
                        self.measurement_parameters = buffer_meas
                        self.exp_th_connect.is_measurement_data_updated = True

                    if device.on_next_step(ch.number, repeat = 3) == ch_response_to_step.Step_done:
                        ch.number_meas += 1
                        repeat_counter = 0
                        t = time.time() - t#вычисляем время, необходимое на выставление шага
                        while repeat_counter < self.repeat_meas:
                            repeat_counter += 1
                            ans, param, step_time = device.do_meas(ch.number)
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
                            

                            ch.last_step_time = step_time + t

                            self.write_data_to_buf_file("", addTime=True)
                            for param in param:
                                self.write_data_to_buf_file(
                                    message=str(param) + "\t")
                            self.write_data_to_buf_file(message="\n")

                            if ans == ch_response_to_step.Step_done:
                                self.add_text_to_log("шаг " + device.get_name() + " ch-" + str(ch.number) + " сделан за " + str(round(step_time)) + " сек" )
                                self.calc_last_exp_time()
                            if ans == ch_response_to_step.Step_fail:
                                ch.am_i_active_in_experiment = False
                                error = True  # ошибка при выполнении шага прибора, заканчиваем с ошибкой
                                break
                    
                    else:
                        ch.am_i_active_in_experiment = False

                    if device.get_steps_number(ch.number) is not False:
                        if ch.number_meas >= device.get_steps_number(ch.number):
                            ch.am_i_active_in_experiment = False

                    subscribers = self.get_subscribers([[device.get_name(), ch.number]], [
                                                       device.get_name(), ch.number])

                    #print(device.get_name(), "подписчики", subscribers)

                    if ch.am_i_active_in_experiment == False:
                        '''останавливаем всех подписчиков'''
                        for subscriber in subscribers:
                            dev = self.name_to_class(subscriber[0])
                            for chann in dev.channels:
                                if chann.number == subscriber[1]:
                                    chann.am_i_active_in_experiment = False

                    else:
                        for subscriber in subscribers:
                            '''передаем сигнал всем подписчикам'''
                            self.name_to_class(
                                subscriber[0]).set_status_step(subscriber[1], True)

                    for dev in self.dict_active_device_class.values():
                        for channel in dev.channels:
                            if channel.is_ch_active():
                                #print(dev, channel.number, "приоритет = "+ str(channel.get_priority()))
                                if dev == device and ch.number == channel.number:
                                    continue
                                else:
                                    if channel.get_priority() > ch.get_priority():
                                        channel.increment_priority()
                    ch.set_priority(priority = min_priority)

   # -----------------------------------------------------------
        for dev, ch in self.get_active_ch_and_device():
            ans = dev.action_end_experiment(ch.number)
            if ans == False:
                pass
                #print("ошибка при действии " + dev.get_name() + " после эксперимента")
        self.pbar_percent = 0  # сбрасываем прогресс бар

        if error:
            self.add_text_to_log("Эксперимент прерван из-за ошибки", "err")
            logger.debug("Эксперимент прерван из-за ошибки")
            # вывод окна с сообщением в другом потоке
            self.exp_th_connect.is_message_show = False
            self.exp_th_connect.message = "Эксперимент прерван из-за ошибки. Знаем, бесят такие расплывчатые формулировки, прям ЪУЪ!!!. Мы пока не успели допилить анализ ошибок, простите"
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

        try:
            self.save_results()
        except:
            #print("не удалось сохранить результаты")
            logger.debug("не удалось сохранить результаты", self.buf_file)
        self.set_state_text("Подготовка к эксперименту")

        # ------------------подготовка к повторному началу эксперимента---------------------
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

        # -----------------------------------------------------------------------
