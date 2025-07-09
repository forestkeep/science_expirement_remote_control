# Copyright © 2025 Zakhidov Dmitry <zakhidov.dim@yandex.ru>
# 
# This file may be used under the terms of the GNU General Public License
# version 3.0 as published by the Free Software Foundation and appearing in
# the file LICENSE included in the packaging of this file. Please review the
# following information to ensure the GNU General Public License version 3.0
# requirements will be met: https://www.gnu.org/copyleft/gpl.html.
# 
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
# WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
import datetime
import os
from multiprocessing import Queue
from queue import Empty
from pymodbus.client import ModbusSerialClient

from Adapter import Adapter
import logging

logger = logging.getLogger(__name__)

from enum import Enum, auto
class ExperimentState(Enum):
    PREPARATION = auto()        # Подготовка к эксперименту
    READY = auto()              # Готовность к старту
    IN_PROGRESS = auto()        # Эксперимент идет
    PAUSED = auto()             # Эксперимент приостановлен
    FINALIZING = auto()         # Подготовка к окончанию
    COMPLETED = auto()          # Эксперимент окончен

def open_log_file(self):
        folder_path = os.path.abspath(os.path.join(os.getenv('USERPROFILE'), "AppData", "Local", "Installation_Controller"))
        os.startfile(folder_path)
        
def get_active_ch_and_device(device_classes: dict):
	for device in device_classes.values():
		for channel in device.channels:
			if channel.is_ch_active():
				yield device, channel

def write_data_to_buf_file(file: str,  message: str, addTime: bool=False, ):
        message = f"{datetime.now().strftime('%H:%M:%S.%f')[:-3] + ' ' if addTime else ''} {message.replace('.', ',')}"
        with open(file, "a") as file:
            file.write( str(message) )

def clear_queue(queue: Queue):
    try:
        while True:
            queue.get_nowait()
    except Empty:
        pass
    
def clear_pipe(pipe):
    """Очищает пайп от данных."""
    while pipe.poll():
        pipe.recv()

def create_clients(clients, dict_devices) -> tuple:
        """функция создает клиенты для приборов с учетом того, что несколько приборов могут быть подключены к одному порту. Возвращает список ресурсов, которые не удалось создать"""
        list_type_connection = []
        list_COMs = []
        list_baud = []
        dict_modbus_clients = {}
        dict_serial_clients = {}
        bad_resources = []
        for client in clients:
            try:
                client.close()
                del client
            except:
                pass
        clients.clear()
        for device in dict_devices.values():
            is_dev_active = False
            for ch in device.channels:
                if ch.is_ch_active():
                    is_dev_active = True
                    break
            if is_dev_active:
                list_type_connection.append(device.get_type_connection())
                list_COMs.append(device.get_COM())
                list_baud.append(device.get_baud())
            else:

                list_type_connection.append(False)
                list_COMs.append(False)
                list_baud.append(False)
        for i in range(len(list_baud)):

            if list_type_connection[i] == False:
                clients.append(False)

            elif list_type_connection[i] != "modbus":
                if list_COMs[i] in dict_serial_clients.keys():
                    clients.append(dict_serial_clients[list_COMs[i]])
                else:
                    try:
                        ser = Adapter(list_COMs[i], int(list_baud[i]))
                    except Exception as e:
                        logger.warning(f"Error create {list_COMs[i]} client: {str(e)}")
                        bad_resources.append(list_COMs[i])
                        ser = False

                    dict_serial_clients[list_COMs[i]] = ser
                    clients.append(ser)

            elif list_type_connection[i] == "modbus":
                if list_COMs[i] in dict_modbus_clients.keys():
                    # если клиент был создан ранее, то просто добавляем ссылку на него
                    clients.append(dict_modbus_clients[list_COMs[i]])
                else:  # иначе создаем новый клиент и добавляем в список клиентов и список модбас клиентов

                    try:
                        dict_modbus_clients[list_COMs[i]] = ModbusSerialClient(
                                port=list_COMs[i],
                                baudrate=int(list_baud[i]),
                                stopbits=1,
                                bytesize=8,
                                parity="E",
                                timeout=0.3,
                                retries=1,
                        )
                    except Exception as e:
                        bad_resources.append(list_COMs[i])
                        dict_modbus_clients[list_COMs[i]] = False
                        logger.warning(f"Error create {list_COMs[i]} modbus client: {str(e)}")

                    clients.append(dict_modbus_clients[list_COMs[i]])
        return clients, bad_resources