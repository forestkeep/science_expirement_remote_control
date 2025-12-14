import time
import struct
from collections import deque
from multiprocessing import Process, Pipe
from multiprocessing.shared_memory import SharedMemory

from typing import List, Optional
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
    
    def __init__(self, conn, logger_level = logging.WARNING):
        self.conn = conn
        self.buffer: List[bytes] = []
        self.sent_queue: List[SentItem] = []
        self.next_id = 0
        logger.setLevel(logger_level)

        # Метрики
        self.metrics = {
            'put_intervals': deque(maxlen=10),  # Интервалы добавления данных
            'last_put_time': None,               # Время последнего добавления
            
            # Метрики отправки
            'send_intervals': deque(maxlen=10),  # Интервалы между отправками
            'last_send_time': None,              # Время последней отправки
            'total_sent': 0,                     # Всего отправлено пакетов
            'total_bytes_sent': 0,               # Всего отправлено байт
            'send_errors': 0,                    # Ошибок отправки
            
            # Метрики получения подтверждений
            'ack_intervals': deque(maxlen=10),   # Интервалы между подтверждениями
            'last_ack_time': None,               # Время последнего подтверждения
            'total_acked': 0,                    # Всего подтверждено пакетов
            
            # Статистика успешных отправок и ошибок
            'successful_sends': 0,               # Успешно отправлено
            'failed_sends': 0,                   # Неудачных отправок
            'timeout_errors': 0,                 # Ошибок по таймауту
            
            # Временные метки для расчета средних скоростей
            'first_send_time': None,
            'first_ack_time': None
        }

        self.state = 0
        
        self.timeout = 180    # Таймаут подтверждения в секундах
        self.max_attempts = 3 # Максимальное количество попыток отправки
        self.max_pending = 250  # Максимум активных сессий передачи
        self.max_single_pending = 7 # Максимальное количество передаваемых пакетов за один вход в функцию
        
        # Для отладочного вывода
        self.last_debug_output_time = time.perf_counter()
        self.debug_interval = 300

        #TODO: необходимо динамически менять эти параметра в зависимости от параметров конкретного эксперимента, его длительности, частоты опроса, количества приборов и др.

    def _update_send_metrics(self, data_size: int) -> None:
        """Обновляет метрики отправки."""
        current_time = time.perf_counter()
        
        if self.metrics['last_send_time']:
            interval = current_time - self.metrics['last_send_time']
            self.metrics['send_intervals'].append(interval)
        
        self.metrics['last_send_time'] = current_time
        self.metrics['total_sent'] += 1
        self.metrics['total_bytes_sent'] += data_size
        
        if self.metrics['first_send_time'] is None:
            self.metrics['first_send_time'] = current_time

    def _update_ack_metrics(self) -> None:
        """Обновляет метрики получения подтверждений."""
        current_time = time.perf_counter()
        
        if self.metrics['last_ack_time']:
            interval = current_time - self.metrics['last_ack_time']
            self.metrics['ack_intervals'].append(interval)
        
        self.metrics['last_ack_time'] = current_time
        self.metrics['total_acked'] += 1
        self.metrics['successful_sends'] += 1
        
        if self.metrics['first_ack_time'] is None:
            self.metrics['first_ack_time'] = current_time

    def _get_instant_send_rate(self) -> float:
        """Возвращает мгновенную скорость отправки (пакетов/сек)."""
        if len(self.metrics['send_intervals']) == 0:
            return 0.0
        last_interval = self.metrics['send_intervals'][-1]
        return 1.0 / last_interval if last_interval > 0 else 0.0

    def _get_average_send_rate(self) -> float:
        """Возвращает среднюю скорость отправки за все время (пакетов/сек)."""
        if self.metrics['first_send_time'] is None:
            return 0.0
        elapsed = time.perf_counter() - self.metrics['first_send_time']
        if elapsed <= 0:
            return 0.0
        return self.metrics['total_sent'] / elapsed

    def _get_instant_receive_rate(self) -> float:
        """Возвращает мгновенную скорость получения подтверждений (подтверждений/сек)."""
        if len(self.metrics['ack_intervals']) == 0:
            return 0.0
        last_interval = self.metrics['ack_intervals'][-1]
        return 1.0 / last_interval if last_interval > 0 else 0.0

    def _get_average_receive_rate(self) -> float:
        """Возвращает среднюю скорость получения подтверждений за все время (подтверждений/сек)."""
        if self.metrics['first_ack_time'] is None:
            return 0.0
        elapsed = time.perf_counter() - self.metrics['first_ack_time']
        if elapsed <= 0:
            return 0.0
        return self.metrics['total_acked'] / elapsed

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
        
    def print_statistics(self) -> None:
        """Выводит отладочную информацию о состоянии системы."""
        instant_send_rate = self._get_instant_send_rate()
        average_send_rate = self._get_average_send_rate()
        instant_receive_rate = self._get_instant_receive_rate()
        average_receive_rate = self._get_average_receive_rate()
        
        debug_info = [
            f"Ожидающие отправки: {len(self.buffer)} пакетов",
            f"Активные сессии: {len(self.sent_queue)} пакетов",
            f"Скорость отправки: мгновенная={instant_send_rate:.2f} пак/сек, средняя={average_send_rate:.2f} пак/сек",
            f"Скорость получения: мгновенная={instant_receive_rate:.2f} подтв/сек, средняя={average_receive_rate:.2f} подтв/сек",
            f"Статистика отправки: успешно={self.metrics['successful_sends']}, "
            f"ошибки={self.metrics['failed_sends']}, "
            f"таймауты={self.metrics['timeout_errors']}",
            f"Всего отправлено: {self.metrics['total_sent']} пакетов, "
            f"{self.metrics['total_bytes_sent']} байт",
            f"Всего подтверждено: {self.metrics['total_acked']} пакетов",
            f"Ошибки отправки: {self.metrics['send_errors']}",
            f"Среднее время добавления данных: {self.get_average_metric('put_intervals', 5):.4f} сек",
            "=" * 50
        ]
        
        for line in debug_info:
            logger.warning(line)

    def _send_data_bytes(self, data_bytes: bytes) -> Optional[SentItem]:
        """Отправляет данные через разделяемую память."""
        try:
            shm = SharedMemory(create=True, size=len(data_bytes))
            shm.buf[:] = data_bytes
            shm_name = shm.name
            
            current_id = self.next_id
            self.next_id += 1
            logger.debug(f"данные {current_id} отправлены в {time.perf_counter()}")
            
            # Обновляем метрики отправки
            self._update_send_metrics(len(data_bytes))
            
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
            self.metrics['send_errors'] += 1
            self.metrics['failed_sends'] += 1
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
                            
                            # Обновляем метрики получения
                            self._update_ack_metrics()
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
                    logger.warning(f"Количество попыток отправки истекло для объекта {item.id=} {item.shm=}")
                    self.metrics['timeout_errors'] += 1
                    self.metrics['failed_sends'] += 1
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
                count_start_packet += 1
            else:
                self.buffer.insert(0, data_bytes)
                break

    def send_data(self) -> bool:
        """Основной метод обработки отправки данных."""
        if self.get_average_metric('put_intervals', 5) > 3:
            self._send_new_data()
            self._handle_acknowledgments()
            self._retry_timeouts()
        else:
            if self.state == 0:
                self._send_new_data()
            elif self.state == 1:
                self._handle_acknowledgments()
            elif self.state == 2:
                self._retry_timeouts()

            self.state += 1
            if self.state > 2:
                self.state = 0

        current_real_time = time.perf_counter()
        if current_real_time - self.last_debug_output_time >= self.debug_interval:
            self.print_statistics()
            self.last_debug_output_time = current_real_time
        
        return len(self.buffer) > 0 or len(self.sent_queue) > 0

    def get_average_metric(self, metric_name: str, window: int = 5) -> float:
        """Возвращает среднее значение метрики за указанное окно."""
        values = list(self.metrics[metric_name])[-window:]
        return sum(values)/len(values) if values else 0.0

def child_process(conn, delay) -> None:
    try:
        while True:
            if conn.poll():
                received = conn.recv()
                if isinstance(received, tuple) and len(received) == 2:
                    _process_received_data(conn, *received)
                    time.sleep(delay)
    except Exception as e:
        print(f"end {e}")

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
        logger.warning(f"Ошибка обработки входных данных {current_id=}: {e}")
        conn.send((current_id, "E"))

if __name__ == "__main__":

    delay_child_process = 0.04
    delay_main_process = 0.02

    #======================================================================

    parent_conn, child_conn = Pipe()
    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"

    log_level_consol = logging.INFO


    console = logging.StreamHandler()
    console.setLevel(log_level_consol)
    console.setFormatter(logging.Formatter(FORMAT))
    logging.basicConfig(handlers=[console], level=logging.DEBUG)

    processor = Process(target=child_process, args=(child_conn,delay_child_process))
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
    
    for i in range(100000000000):
        test_data = [f'{i}pig_in_a_poke_1 ch-1_meas'] + base_test_data
        manager.add_data(test_data, test_float)
        time.sleep(delay_main_process)
        manager.send_data()
    
    parent_conn.close()
    processor.join()