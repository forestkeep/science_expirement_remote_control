import time
import struct
from collections import deque
from multiprocessing import Process, Pipe
from multiprocessing.shared_memory import SharedMemory
#from profilehooks import profile

import time
import struct
from collections import deque
from multiprocessing import Process, Pipe
from multiprocessing.shared_memory import SharedMemory
from typing import Deque, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SentItem:
    __slots__ = ('id', 'data', 'attempts', 'last_sent', 'shm')
    
    def __init__(
        self,
        id: int,
        data: bytes,
        attempts: int,
        last_sent: float,
        shm: SharedMemory
    ):
        self.id = id
        self.data = data
        self.attempts = attempts
        self.last_sent = last_sent
        self.shm = shm

class SharedBufferManager:
    """Управляет буфером данных и их отправкой через разделяемую память."""
    
    def __init__(self, conn):
        self.conn = conn
        self.buffer: List[bytes] = []
        self.sent_queue: List[SentItem] = []
        self.next_id = 0
        self.metrics = {
            'put_intervals': deque(maxlen=10),
            'last_put_time': None
        }

        self.state = 0
        
        self.timeout = 2    #Таймаут подтверждения в секундах
        self.max_attempts = 2 # Максимальноеколичество попыток отправки
        self.max_pending = 50  # Максимум активных сессий передачи
        self.max_single_pending = 5 # Максимальное количество передаваемых пакетов за один вход в функцию

    def _serialize_data(self, data_packet: list, float_value: float) -> bytes:
        """Упаковывает данные в бинарный формат."""
        key = data_packet[0].encode('utf-8')
        key_len = len(key)
        
        str_parts = [
            elem.encode('utf-8') 
            for sublist in data_packet[1:] 
            for elem in sublist
        ]
        str_data = b''.join(
            struct.pack('I', len(part)) + part 
            for part in str_parts
        )
        str_section_len = len(str_data)
        
        float_bytes = struct.pack('d', float_value)
        
        return (
            struct.pack('II', key_len, str_section_len) +
            key +
            str_data +
            float_bytes
        )

    def add_data(self, data_packet: list, float_value: float) -> None:
        """Добавляет новые данные в буфер для отправки."""
        current_time = time.perf_counter()
        
        if self.metrics['last_put_time']:
            self.metrics['put_intervals'].append(
                current_time - self.metrics['last_put_time']
            )
        self.metrics['last_put_time'] = current_time
        
        self.buffer.append(self._serialize_data(data_packet, float_value))

    def _send_data_bytes(self, data_bytes: bytes) -> Optional[SentItem]:
        """Отправляет данные через разделяемую память."""
        try:
            shm = SharedMemory(create=True, size=len(data_bytes))
            shm.buf[:] = data_bytes
            shm_name = shm.name
            
            current_id = self.next_id
            self.next_id += 1
            logger.debug(f"данные {id} отправлены в {time.perf_counter()}")
            self.conn.send((current_id, shm_name))

            return SentItem(
                id = current_id,
                data = data_bytes,
                attempts = 1,
                last_sent = time.perf_counter(),
                shm = shm
            )
        except Exception as e:
            logger.warning(f"Ошибка отправки данных в другой процесс: {e}")
            if 'shm' in locals():
                shm.close()
                shm.unlink()
            return None

    def _handle_acknowledgments(self) -> None:
        """Обрабатывает входящие подтверждения."""
        while self.conn.poll():
            try:
                ack = self.conn.recv()
                if isinstance(ack, tuple) and ack[1] == "K":
                    ack_id = ack[0]
                    for i, item in enumerate(self.sent_queue):
                        if item.id == ack_id:
                            sent_item = self.sent_queue.pop(i)
                            sent_item.shm.close()
                            sent_item.shm.unlink()
                            break
            except Exception as e:
                logger.warning(f"Ошибка подтверждения получения данных: {e}")

    def _retry_timeouts(self) -> None:
        """Повторяет отправку данных с истекшим таймаутом."""
        current_time = time.perf_counter()
        new_sent_queue = []
        
        for item in self.sent_queue:
            if current_time - item.last_sent > self.timeout:
                if item.attempts < self.max_attempts:
                    new_item = self._send_data_bytes(item.data)
                    if new_item:
                        new_item.id = item.id
                        new_item.attempts = item.attempts + 1
                        item.shm.close()
                        item.shm.unlink()
                        new_sent_queue.append(new_item)
                    else:
                        new_sent_queue.append(item)
                else:
                    logger.warning(f"Количество попыток отправки истекло для объекта {item.id}")
                    item.shm.close()
                    item.shm.unlink()
            else:
                new_sent_queue.append(item)
                
        self.sent_queue = new_sent_queue

    def _send_new_data(self) -> None:
        """Отправляет новые данные из буфера."""
        count_start_packet = 0
        while len(self.sent_queue) < self.max_pending and self.buffer and count_start_packet <= self.max_single_pending:
            data_bytes = self.buffer.pop(0)
            new_item = self._send_data_bytes(data_bytes)
            
            if new_item:
                self.sent_queue.append(new_item)
                count_start_packet+=1
            else:
                self.buffer.insert(0, data_bytes)
                break

    def send_data(self) -> bool:
        """Основной метод обработки отправки данных."""
        if self.state == 0:
            self._send_new_data()
        elif self.state == 1:
            self._handle_acknowledgments()
        elif self.state == 2:
            self._retry_timeouts()

        self.state+=1
        if self.state > 2:
            self.state = 0
        
        return len(self.buffer) > 0 or len(self.sent_queue) > 0

    def get_average_metric(self, metric_name: str, window: int = 5) -> float:
        """Возвращает среднее значение метрики за указанное окно."""
        values = list(self.metrics[metric_name])[-window:]
        return sum(values)/len(values) if values else 0.0

def child_process(conn) -> None:
    try:
        while True:
            if conn.poll():
                received = conn.recv()
                if isinstance(received, tuple) and len(received) == 2:
                    _process_received_data(conn, *received)
    except (EOFError, KeyboardInterrupt):
        print("Выход из процесса")
    except Exception as e:
        print(f"Ошибка: {e}")

def _process_received_data(conn , current_id: int, shm_name: str) -> None:
    try:
        shm = SharedMemory(shm_name)
        key_len, str_len = struct.unpack('II', shm.buf[:8])
        
        # Чтение ключа
        offset = 8
        key = shm.buf[offset:offset+key_len].tobytes().decode('utf-8')
        offset += key_len
        
        str_data = []
        while str_len > 0:
            part_len = struct.unpack('I', shm.buf[offset:offset+4])[0]
            offset += 4
            str_data.append(
                shm.buf[offset:offset+part_len].tobytes().decode('utf-8')
            )
            offset += part_len
            str_len -= 4 + part_len
        
        float_value = struct.unpack('d', shm.buf[offset:offset+8])[0]
        shm.close()
        conn.send((current_id, "K"))
        logger.debug(f"данные {current_id} приняты в {time.perf_counter()}")
        return key, str_data, float_value

    except Exception as e:
        logger.warning(f"Ошибка обработки входных данных: {e}")
        conn.send((current_id, "E"))

if __name__ == "__main__":
    parent_conn, child_conn = Pipe()
    processor = Process(target=child_process, args=(child_conn,))
    processor.start()
    
    manager = SharedBufferManager(parent_conn)

    # Тестовые данные
    base_test_data = [
        ["raw=b'-25 \\t -3 \\t -24 \\t 33.894 \\r\\n'"],
        ['0=-25.0'],
        ['1=-3.0'],
        ['2=-24.0'],
        ['3=33.894'],
        ['0=-25.0'],
        ['1=-3.0'],
        ['2=-24.0'],
        ['3=33.894']
    ]
    test_float = 8.2426285
    
    # Генерация тестовых данных
    for i in range(1000):
        test_data = [f'{i}pig_in_a_poke_1 ch-1_meas'] + base_test_data
        manager.add_data(test_data, test_float)
        time.sleep(0.001)
    
    # Основной цикл обработки
    while manager.send_data():
        pass
        #print(f"Средний интервал добавления: "f"{manager.get_average_metric('put_intervals'):.4f} сек")

    parent_conn.close()
    processor.join()