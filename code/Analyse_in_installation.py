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
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logger = logging.getLogger(__name__)
from PyQt5.QtWidgets import QApplication

from Adapter import Adapter
from base_installation import baseInstallation
from Devices.Classes import (not_ready_style_border, ready_style_border,
                             warning_style_border)

from functions import get_active_ch_and_device


class analyse(baseInstallation):
    def __init__(self) -> None:
        super().__init__()

    def get_time_line_devices(self):
        """возвращает массивы веток приборов, каждая ветка работает по своему таймеру. Веткой называется прибор, работающий по таймеру и все подписчики"""
        time_lines = []
        for device, ch in get_active_ch_and_device( self.dict_active_device_class):
            if device.get_trigger(ch) == "Таймер":
                time_line = [[device.get_name(), ch.number]]
                subscribers = self.get_subscribers(
                    [[device.get_name(), ch.number]], [device.get_name(), ch.number]
                )

                for sub in subscribers:
                    time_line.append([sub[0], sub[1]])

                time_lines.append(time_line)
                
        for line in time_lines:
            buf = []
            for lin in line:
                buf.append(lin[0] + " ch-" + str(lin[1]))

        return time_lines

    def analyse_endless_exp(self, matrix) -> bool:
        """определяет зацикливания по сигналам и выдает предупреждение о бесконечном эксперименте"""

        '''эксперимент будет бесконечен:
        - в случае, если есть минимум 2 канала с тригером таймером и количеством шагов, равном "пока активны другие приборы"
        - в случае, если в зацикленной линии ни один прибор не имеет конечное количество шагов"'''
        sourses = self.cycle_analyse( matrix )
        if sourses:
            logger.warning(f"зацикливание обнаружено {sourses}")

        first_array = copy.deepcopy(list(self.dict_active_device_class.keys()))

        name = []
        sourse = []
        for dev in first_array:
            name.append(dev)
        i = 0

        # ----------анализ по таймерам-----------------------
        experiment_endless = False
        mark_device_number = []
        for device, ch in get_active_ch_and_device( self.dict_active_device_class):
            trigger = device.get_trigger(ch)
            steps_number = device.get_steps_number(ch)

            if trigger == QApplication.translate('analyse',"Таймер") and not steps_number:
                mark_device_number.append(device.get_name() + str(ch.get_name()))

                if len(mark_device_number) >= 2:
                    message = QApplication.translate('analyse', "каналы ") + " ".join(mark_device_number) + " " + QApplication.translate('analyse', "будут работать бесконечно")
                    self.add_text_to_log(message, status="err")
                    experiment_endless = True
                    break
        # --------------------------------------------------

        # -----------------анализ других случаев------------
        #sourses = self.cycle_analyse()
        if sourses:
            for sourse in sourses:
                dev, ch_name = sourse.split()[0], sourse.split()[1]
                first_dev = self.name_to_class(name_device=dev)
                first_ch = first_dev.get_object_ch(ch_name=ch_name)
                branch = [sourse]

                subscriber_dev = first_dev
                subscriber_ch = first_ch
                while True:

                    ans = subscriber_dev.get_trigger_value(subscriber_ch)
                    if ans is not False:
                        dev, ch_name = ans.split()[0], ans.split()[1]
                        subscriber_dev = self.name_to_class(name_device=dev)
                        subscriber_ch = subscriber_dev.get_object_ch(ch_name=ch_name)
                        branch.append(ans)
                    else:
                        break

                    if subscriber_dev.get_steps_number(subscriber_ch) != False:
                        break

                    elif subscriber_dev == first_dev and subscriber_ch == first_ch:
                        experiment_endless = True
                        message = QApplication.translate('analyse',"зацикливание по ветке")
                        message+=" "
                        for n in branch:
                            message = message + n + " "
                        message += QApplication.translate('analyse',"эксперимент будет продолжаться бесконечно")
                        self.add_text_to_log(message, status="war")
                        logger.debug(
                            "бесконечный эксперимент, зацикливание с бесконечным количеством шагов"
                        )
                        break  # прошли круг

        return experiment_endless

    def get_sourse_line(self, line) -> list:
        out = []
        for c in line:
            if c != False:
                try:
                    dev_name, ch_name, trg = c.split()[0], c.split()[1], c.split()[2]
                except Exception as e:
                    logger.warning(f"ошибка расшифровки линии источника сигнала: {str(e)} {c=}")
                    out.append(False)
                    continue
                #TODO:подробнее разобрать случаи возникновения исключений и что делать в случае возникновения исключенийф

                dev = self.name_to_class(name_device=dev_name)
                if dev is not False:
                    ch = dev.get_object_ch(ch_name=ch_name)
                    if (dev.get_trigger(ch) == "Внешний сигнал") and (trg == "do_operation" or trg == "end_work"):
                        s = dev.get_trigger_value(ch)
                    else:
                        s = False
                else:
                    s = False

                out.append(s)
            else:
                out.append(False)
        return out
    
    def get_call_matrix(self) -> list:
        "вернет матрицу вызовов триггеров приборов, где по строкам расположены вызовы прибора один за другим"
        sourse = []
        i = 0

        # формируем первую линию сигналов
        for dev, ch in get_active_ch_and_device( self.dict_active_device_class ):
            if dev.get_trigger(ch) == "Внешний сигнал":
                s = dev.get_trigger_value(ch)
            else:
                s = False
            sourse.append(s)
        matrix_sourse = [copy.deepcopy(sourse)]
        while i < len(sourse):  
            # получаем матрицу источников сигналов с количеством столбцом равным количеству каналов в установке и количеством строк на 1 больше, чем столбцом
            matrix_sourse.append(self.get_sourse_line(matrix_sourse[i]))
            i += 1

        # ищем зацикливания, запоминаем первый элемент в столбце и идем по столбцу, если встретим такоц же элемент, то зацикливание обнаружено(кроме false)
        transposed_matrix = []

        for i in range(len(matrix_sourse[0])):
            transposed_row = []
            for row in matrix_sourse:
                transposed_row.append(row[i])
            transposed_matrix.append(transposed_row)

        return transposed_matrix

    def cycle_analyse(self, matrix):
        """проводит анализ зациливаний в матрице вызовов и возвращает корни всех обнаруженных зацикливаний в случае отсутствия корней вернет пстой список"""

        setted_dev = []  # массмив для хранения источников, которые уже были обнаружены в зацикливании и для которых установлена готовность шага
        for row in matrix:
            for i in range(1, len(row), 1):
                if row[0] == False or row[i] in setted_dev:
                    break
                if row[0] == row[i]:
                    setted_dev.append(row[0])
                    dev, ch_name = row[0].split()[0], row[0].split()[1]
                    dev = self.name_to_class(name_device=dev)

                    dev.set_status_step(ch_name=ch_name, status=True)
                    logger.warning(f"установка готовности шага {dev.get_name()} {ch_name}")
                    break

        return setted_dev
    
    def is_correct_call_stack(self, matrix) -> bool:

        ans = True
        checked = []
        for row in matrix:
            has_end_work = False
            for i in range(1, len(row), 1):
                if isinstance(row[i], str) and "end_work" in row[i]:
                    has_end_work = True
                if row[i] == False or row[i] in checked:
                    break
                if row[0] == row[i]:
                    if has_end_work:
                        for dev in row:
                            checked.append(dev)

                        logger.warning(f"в зацикливании есть прибор с триггером окончания работы другого прибора, запрещаем запуск")
                        ans = False
                        self.add_text_to_log(f"в цикле:" , status="war")
                        for dev in row:
                            self.add_text_to_log(f" {dev} ->", status="war", is_add_time=False)
                        self.add_text_to_log(f"обнаружен прибор с триггером окончания работы другого прибора, эксперимент остановится навсегда. Измените процедуру эксперимента",
                                             status="war",
                                             is_add_time=False)

        return ans
    def get_subscribers(self, signals, trig) -> list[list[str, str]]:
        """возвращает массив пар [имя прибора, имя канала] подписчиков данного сигнала-триггера и всех последующих подписчиков, рекурсивная функция"""

        subscribers = signals
        for device, ch in get_active_ch_and_device( self.dict_active_device_class):
            if device.get_trigger(ch).lower() == "внешний сигнал":
                stroka = device.get_trigger_value(ch)
                sourse = [stroka.split()[0], stroka.split()[1]]
                if [device.get_name(), ch.get_name()] in signals:
                    continue
                for sig in signals:
                    if sourse == sig:
                        subscribers.append([device.get_name(), ch.get_name()])
                        self.get_subscribers(subscribers, sourse)
        ret_sub = []
        for dev in subscribers:
            if trig == dev:
                continue
            ret_sub.append(dev)

        return ret_sub

    def analyse_com_ports(self) -> bool:
        """анализ конфликтов COM-портов и их доступности"""
        logger.info(f"анализируем ком порты и их доступность")
        self.is_search_resources = False#запрет на сканирование ресурсов
        time.sleep(0.5)
        status = True

        if not self.is_all_device_settable():
            return False

        list_COMs = []
        checked_connect_coms = {}
        list_device_name = []

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

            if com not in checked_connect_coms.keys():
                is_connect = False
                try:
                    buf_client = Adapter(com, int(baud))
                    buf_client.close()
                    del buf_client
                    is_connect = True

                except Exception as e:
                    logger.warning(f"Не удалось открыть порт {com}\n {str(e)}")
                    text = QApplication.translate('analyse',"Не удалось открыть порт {com} {exc}")
                    text = text.format(com = com, exc = str(e))
                    self.add_text_to_log( text, "war" )
                    status = False

                checked_connect_coms[com] = is_connect

            if not checked_connect_coms[com]:
                self.set_border_color_device(
                        device_name=device.get_name(), status_color=not_ready_style_border
                    )


        marked_com_incorrect = []
        marked_baud_incorrect = []
        for i in range(len(list_COMs)):
            for j in range(len(list_COMs)):
                if i == j:
                    continue

                if list_COMs[i] == list_COMs[j]:

                    if (
                        self.dict_active_device_class[
                            list_device_name[i]
                        ].get_type_connection()
                        == "serial"
                    ):

                        for device_name in [list_device_name[i], list_device_name[j]]:
                            self.set_border_color_device(
                                device_name=device_name,
                                status_color=warning_style_border,
                            )

                        is_show = True
                        for mark in marked_com_incorrect:
                            if (
                                list_device_name[i] in mark
                                and list_device_name[j] in mark
                            ):
                                is_show = False
                        if is_show:
                            marked_com_incorrect.append(
                                [list_device_name[i], list_device_name[j]]
                            )
                            text = QApplication.translate('analyse',"{device1} и {device2} не могут иметь один COM порт")
                            text = text.format(device1 = list_device_name[i], device2 = list_device_name[j])
                            self.add_text_to_log(
                                text = text,
                                status="war",
                            )
                        status = False
                    elif (
                        self.dict_active_device_class[
                            list_device_name[i]
                        ].get_type_connection()
                        == "modbus"
                        and self.dict_active_device_class[
                            list_device_name[j]
                        ].get_type_connection()
                        == "modbus"
                        and self.dict_active_device_class[
                            list_device_name[i]
                        ].get_baud()
                        != self.dict_active_device_class[list_device_name[j]].get_baud()
                    ):

                        for device_name in [list_device_name[i], list_device_name[j]]:
                            self.set_border_color_device(
                                device_name=device_name,
                                status_color=warning_style_border,
                            )

                        is_show = True
                        for mark in marked_baud_incorrect:
                            if (
                                list_device_name[i] in mark
                                and list_device_name[j] in mark
                            ):
                                is_show = False
                        if is_show:
                            marked_baud_incorrect.append(list_device_name[i])
                            marked_baud_incorrect.append(list_device_name[j])
                            
                            text = QApplication.translate('analyse',"{device1} и {device2} не могут иметь разную скорость подключения")
                            text = text.format(device1 = list_device_name[i], device2 = list_device_name[j])
                            self.add_text_to_log(
                                text = text,
                                status="war",
                            )
                        status = False

        for client in self.clients:
            try:
                client.close()
            except:
                pass
        self.clients.clear()

        self.is_search_resources = True#разрешение на сканирование ресурсов
        logger.info(f"ВЫход из функции analyse_com_port status={status}\n")
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
                        self.set_border_color_device(
                            device_name=dev.get_name(),
                            status_color=ready_style_border,
                            num_ch=ch.number,
                        )
                else:
                    self.set_border_color_device(
                        device_name=dev.get_name(),
                        status_color=not_ready_style_border,
                        num_ch=ch.number,
                    )

            if channels_count == 0:  # прибор активен, но нет включенных каналов
                status_dev = False

            if status_dev:
                self.set_border_color_device(
                    device_name=dev.get_name(),
                    status_color=ready_style_border,
                    is_only_device_lay=True,
                )
            else:
                self.set_border_color_device(
                    device_name=dev.get_name(),
                    status_color=not_ready_style_border,
                    is_only_device_lay=True,
                )

        if active_channels == 0:
            status = False

        return status
