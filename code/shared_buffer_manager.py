import time
import struct
from collections import deque
from multiprocessing import Process, Pipe
from multiprocessing.shared_memory import SharedMemory

class SharedBufferManager:
    def __init__(self, conn):
        self.conn = conn
        self.buffer = []
        self.metrics = {
            'send_times': deque(maxlen=10),
            'put_intervals': deque(maxlen=10),
            'last_put_time': None
        }

    def _serialize_data(self, data_packet, float_value):
        # Сериализация ключа
        key = data_packet[0].encode('utf-8')
        key_len = len(key)
        
        # Сериализация строковых данных
        str_parts = [elem[0].encode('utf-8') for sublist in data_packet[1:] for elem in sublist]
        str_data = b''.join([struct.pack('I', len(p)) + p for p in str_parts])
        str_section_len = len(str_data)
        
        # Упаковка float
        float_bytes = struct.pack('d', float_value)
        
        # Создание единого буфера
        buffer = (
            struct.pack('II', key_len, str_section_len) +
            key +
            str_data +
            float_bytes
        )
        
        return buffer

    def add_data(self, data_packet, float_value):
        # Расчет интервалов добавления
        current_time = time.perf_counter()
        if self.metrics['last_put_time']:
            self.metrics['put_intervals'].append(current_time - self.metrics['last_put_time'])
        self.metrics['last_put_time'] = current_time

        # Создание shared memory
        buffer = self._serialize_data(data_packet, float_value)
        shm = SharedMemory(create=True, size=len(buffer))
        shm.buf[:] = buffer
        self.buffer.append(shm)

    def send_data(self):
        if not self.buffer:
            return False

        shm = self.buffer[0]
        try:
            start_time = time.perf_counter()
            
            # Отправка только имени shared memory
            print("time send: ", time.perf_counter())
            self.conn.send(shm.name)
            print(time.perf_counter() - start_time)
            
            # Ожидание подтверждения
            if self.conn.recv() == "K":
                print("time ans2: ", time.perf_counter())
                duration = time.perf_counter() - start_time
                self.metrics['send_times'].append(duration)
                self.buffer.pop(0).close()
                return True
                
        except Exception as e:
            print(f"Ошибка передачи: {e}")
            shm.close()
            shm.unlink()
        
        return False

    def get_average_metric(self, metric_name, window=5):
        values = list(self.metrics[metric_name])[-window:]
        return sum(values)/len(values) if values else 0.0

def child_process(conn):
    try:
        while True:
            shm_name = conn.recv()
            print("time send2: ", time.perf_counter())
            start = time.perf_counter()
            shm = SharedMemory(shm_name)
            
            # Чтение метаданных
            key_len, str_len = struct.unpack('II', shm.buf[:8])
            offset = 8
            
            # Извлечение ключа
            key = shm.buf[offset:offset+key_len].tobytes().decode('utf-8')
            offset += key_len
            
            # Извлечение строк
            str_data = []
            while str_len > 0:
                part_len = struct.unpack('I', shm.buf[offset:offset+4])[0]
                offset +=4
                str_data.append(shm.buf[offset:offset+part_len].tobytes().decode('utf-8'))
                offset += part_len
                str_len -= 4 + part_len
            
            # Извлечение float
            float_value = struct.unpack('d', shm.buf[offset:offset+8])[0]
            
            print(f"Received key: {key}")
            print("String parts:", str_data)
            print("Float value:", float_value)
            print(f"Time: {time.perf_counter() - start} sec")
            
            shm.close()
            #shm.unlink()
            print("time ans: ", time.perf_counter())
            conn.send("K")
            
    except EOFError:
        print("Соединение закрыто")

if __name__ == "__main__":
    parent_conn, child_conn = Pipe()
    
    processor = Process(target=child_process, args=(child_conn,))
    processor.start()
    
    manager = SharedBufferManager(parent_conn)
    
    # Пример данных
    test_data = [
        'pig_in_a_poke_1 ch-1_meas',
        ["raw=b'-25 \\t -3 \\t -24 \\t 33.894 \\r\\n'"],
        ['0=-25.0'],
        ['1=-3.0'],
        ['2=-24.0'],
        ['3=33.894']
    ]
    test_float = 8.2426285
    
    manager.add_data(test_data, test_float)
    
    while manager.send_data():
        print(f"Среднее время отправки: {manager.get_average_metric('send_times'):.4f} сек")
        print(f"Средний интервал добавления: {manager.get_average_metric('put_intervals'):.4f} сек")
    
    parent_conn.close()
    processor.join()