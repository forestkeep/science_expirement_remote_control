
import logging, copy
logger = logging.getLogger(__name__)
from base_installation import *
from Adapter import Adapter, instrument

class analyse(baseInstallation):
    def __init__(self) -> None:
        super().__init__()
        
    def get_time_line_devices(self):
        '''возвращает массивы веток приборов, каждая ветка работает по своему таймеру. Веткой называется прибор, работающий по таймеру и все подписчики'''
        time_lines = []
        for device, ch in self.get_active_ch_and_device():
                    if device.get_trigger(ch.number) == "Таймер":
                        time_line = [[device.get_name(), ch.number]]
                        subscribers = self.get_subscribers([[device.get_name(), ch.number]], [device.get_name(), ch.number])
                        print(f"{subscribers=}")
                        for sub in subscribers:
                              time_line.append([sub[0], sub[1]])

                        time_lines.append(time_line)


        print(time_lines)
        for line in time_lines:
            buf = []
            for lin in line:
                  buf.append(lin[0] + " ch-" + str(lin[1]))
            print(buf)

        return time_lines
                    
    def analyse_endless_exp(self) -> bool:
        '''определяет зацикливания по сигналам и выдает предупреждение о бесконечном эксперименте'''

        '''эксперимент будет бесконечен:
        - в случае, если есть минимум 2 канала с тригером таймером и количеством шагов, равном "пока активны другие приборы"
        - в случае, если в зацикленной линии ни один прибор не имеет конечное количество шагов"'''
        sourses = self.cycle_analyse()
        if sourses:
            for sourse in sourses:
                first = sourse

        first_array = copy.deepcopy(self.current_installation_list)
        name = []
        sourse = []
        for dev in first_array:
            name.append(dev)
        i = 0
        sourse_lines = []
        array = name
        cycle_device = []

        # ----------анализ по таймерам-----------------------
        experiment_endless = False
        mark_device_number = []
        for device, ch in self.get_active_ch_and_device():
                    if device.get_trigger(ch.number) == "Таймер" and device.get_steps_number(ch.number) == False:
                        mark_device_number.append(device.get_name() + str(ch.number))
                        
                        if len(mark_device_number) >= 2:
                            message = "каналы "
                            for n in mark_device_number:
                                message = message + n + " "
                            message = message + "будут работать бесконечно"
                            self.add_text_to_log(
                                message, status="err")
                            experiment_endless = True
                            break
        # --------------------------------------------------

        # -----------------анализ других случаев------------
        sourses = self.cycle_analyse()
        if sourses:
            for sourse in sourses:
                dev, ch = sourse.split()[0], sourse.split()[1]
                first_ch = ch[3:4:1]
                first_dev = self.name_to_class(name=dev)
                branch = [sourse]

                subscriber_dev = first_dev
                subscriber_ch = first_ch
                while True:
                    ans = subscriber_dev.get_trigger_value(subscriber_ch)
                    if ans is not False:
                        dev, ch = ans.split()[0], ans.split()[1]
                        subscriber_ch = ch[3:4:1]
                        subscriber_dev = self.name_to_class(name=dev)
                        branch.append(ans)
                    else:
                        break

                    if subscriber_dev.get_steps_number(subscriber_ch) != False:
                        break

                    elif subscriber_dev == first_dev and subscriber_ch == first_ch:
                        experiment_endless = True
                        message = "зацикливание по ветке "
                        for n in branch:
                            message = message + n + " "
                        message += "эксперимент будет продолжаться бесконечно"
                        self.add_text_to_log(
                            message, status="err")
                        logger.debug("бесконечный эксперимент, зацикливание с бесконечным количеством шагов")
                        break  # прошли круг

        return experiment_endless

    def get_sourse_line(self, line) -> list:
        out = []
        for c in line:
            if c != False:
                dev, ch = c.split()[0], c.split()[1]
                ch_num = ch[3:4:1]
                dev = self.name_to_class(name=dev)
                if dev.get_trigger(ch_num) == "Внешний сигнал":
                    s = dev.get_trigger_value(ch_num)
                else:
                    s = False
                out.append(s)
            else:
                out.append(False)
        return out

    def cycle_analyse(self):
        '''проводим анализ на предмет зацикливания, если оно обнаружено, то необходимо установить флаг готовности одного прибора из цикла, чтобы цикл начался.'''
        names = copy.deepcopy(self.current_installation_list)
        sourse = []
        i = 0
        sourse_lines = []
        array = names

        for dev, ch in self.get_active_ch_and_device():
                    if dev.get_trigger(ch.number) == "Внешний сигнал":
                        s = dev.get_trigger_value(ch.number)
                    else:
                        s = False
                    sourse.append(s)
        matrix_sourse = [copy.deepcopy(sourse)]
        while i < len(sourse):  # получаем матрицу источников сигналов с количеством столбцом равным количеству каналов в установке и количеством строк на 1 больше, чем столбцом
            matrix_sourse.append(self.get_sourse_line(matrix_sourse[i]))
            i += 1
        #for m in matrix_sourse:
        #    print(m)

        # ищем зацикливания, запоминаем первый элемент в столбце и идем по столбцу, если встретим такоц же элемент, то зацикливание обнаружено(кроме false)
        transposed_matrix = []

        for i in range(len(matrix_sourse[0])):
            transposed_row = []
            for row in matrix_sourse:
                transposed_row.append(row[i])
            transposed_matrix.append(transposed_row)

        setted_dev = []  # массмив для хранения источников, которые уже были обнаружены в зацикливании и для которых установлена готовность шага
        for row in (transposed_matrix):
            for i in range(1, len(row), 1):
                if row[0] == False or row[i] in setted_dev:
                    break
                if row[0] == row[i]:
                    #print("зацикливание по строке ", row)
                    setted_dev.append(row[0])
                    dev, ch = row[0].split()[0], row[0].split()[1]
                    ch_num = ch[3:4:1]
                    dev = self.name_to_class(name=dev)

                    dev.set_status_step(ch_num, True)
                    break
        return setted_dev

    def get_subscribers(self, signals, trig) -> list[list[str,str]]:
        '''возвращает массив пар [имя прибора, номер канала] подписчиков данного сигнала-триггера и всех последующих подписчиков, рекурсивная функция'''

        subscribers = signals
        for device, ch in self.get_active_ch_and_device():
                    if device.get_trigger(ch.number).lower() == "внешний сигнал":
                        stroka = device.get_trigger_value(ch.number)
                        sourse = [stroka.split()[0], int(
                            stroka.split()[1][-1])]
                        if [device.get_name(), ch.number] in signals:
                            continue
                        for sig in signals:
                            if sourse == sig:
                                subscribers.append(
                                    [device.get_name(), ch.number])
                                self.get_subscribers(subscribers, sourse)
        ret_sub = []
        for dev in subscribers:
            if trig == dev:
                continue
            ret_sub.append(dev)

        return ret_sub

    def analyse_com_ports(self) -> bool:
        '''анализ конфликтов COM-портов и их доступности'''
        status = True
        
        if not self.is_all_device_settable():
            return False

        list_COMs = []
        list_device_name = []
        fail_ports_list = []

        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients.clear()

        for device in self.dict_active_device_class.values():
            is_dev_active = any(ch.is_ch_active() for ch in device.channels)
            
            if not is_dev_active:
                continue
            
            com = device.get_COM()
            baud = device.get_baud()
            list_COMs.append(com)
            list_device_name.append(device.get_name())

            try:
                #buf_client = serial.Serial(com, int(baud))
                buf_client = Adapter(com, int(baud))
                buf_client.close()

            except:
                self.set_border_color_device(device_name=device.get_name(), status_color = not_ready_style_border)
                self.add_text_to_log(f"Не удалось открыть порт {com}\n", "war")
                logger.debug(f"Не удалось открыть порт {com}\n")
                if com not in fail_ports_list:
                    fail_ports_list.append(com)
                status = False

        marked_com_incorrect = []
        marked_baud_incorrect = []
        for i in range(len(list_COMs)):
            for j in range(len(list_COMs)):
                if i == j:
                    continue

                if list_COMs[i] == list_COMs[j]:
                    
                    if self.dict_active_device_class[list_device_name[i]].get_type_connection() == "serial":

                        for device_name in [list_device_name[i], list_device_name[j]]:
                            self.set_border_color_device(device_name=device_name, status_color = warning_style_border)

                        is_show = True
                        for mark in marked_com_incorrect:
                            if list_device_name[i] in mark and list_device_name[j] in mark:
                                is_show = False
                        if is_show:
                                marked_com_incorrect.append([list_device_name[i],list_device_name[j]])
                                self.add_text_to_log(f"{list_device_name[i]} и {list_device_name[j]} не могут иметь один COM порт", status="war")
                        status = False
                    elif self.dict_active_device_class[list_device_name[i]].get_type_connection() == "modbus" and \
                         self.dict_active_device_class[list_device_name[j]].get_type_connection() == "modbus" and \
                         self.dict_active_device_class[list_device_name[i]].get_baud() != self.dict_active_device_class[list_device_name[j]].get_baud():
                        
                        for device_name in [list_device_name[i], list_device_name[j]]:
                            self.set_border_color_device(device_name=device_name, status_color = warning_style_border)
                        
                        is_show = True
                        for mark in marked_baud_incorrect:
                            if list_device_name[i] in mark and list_device_name[j] in mark:
                                is_show = False
                        if is_show:  
                            marked_baud_incorrect.append(list_device_name[i])
                            marked_baud_incorrect.append(list_device_name[j])
                            self.add_text_to_log(f"{list_device_name[i]} и {list_device_name[j]} не могут иметь разную скорость подключения", status="war")
                        status = False

        if self.is_debug:
            status = True
        return status
    
    def is_all_device_settable(self) -> bool:
        status = True
        if len(self.dict_active_device_class.values()) == 0:
            status = False

        active_channels = 0

        for dev in self.dict_active_device_class.values():
            channels_count = 0
            status_dev = True
            for ch in dev.channels:
                if ch.is_ch_active():
                    active_channels += 1
                    if not ch.is_ch_seted():
                        status_dev = False
                        status = False
                        break
                    else:
                        channels_count += 1
                        self.set_border_color_device(device_name=dev.get_name(), status_color=ready_style_border, num_ch=ch.number)
                else:
                    self.set_border_color_device(device_name=dev.get_name(
                    ), status_color=not_ready_style_border, num_ch=ch.number)

            if channels_count == 0:  # прибор активен, но нет включенных каналов
                status_dev = False

            if status_dev:
                # print("красим слой в зеленый")
                self.set_border_color_device(device_name=dev.get_name(
                ), status_color=ready_style_border, is_only_device_lay=True)
            else:
                # print("красим слой в красный")
                self.set_border_color_device(device_name=dev.get_name(
                ), status_color=not_ready_style_border, is_only_device_lay=True)
            # установить для устройства зеленый лейбл
        if active_channels == 0:
            status = False

        return status

if __name__ == "__main__":
    pass