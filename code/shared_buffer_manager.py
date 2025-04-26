import time
from collections import deque
from multiprocessing import Process, Pipe, Lock
from multiprocessing.shared_memory import SharedMemory
import numpy as np

class SharedBufferManager:
    def __init__(self, conn):
        self.conn = conn
        self.buffer = []
        
        self.send_times = deque(maxlen=10)
        self.last_send_time = None
        
        self.put_intervals = deque(maxlen=10)
        self.last_put_time = None

    def put(self, key, data):
        current_time = time.perf_counter()
        if self.last_put_time is not None:
            self.put_intervals.append(current_time - self.last_put_time)
        self.last_put_time = current_time

        shm = SharedMemory(create=True, size=data.nbytes)
        shared_array = np.ndarray(data.shape, dtype=data.dtype, buffer=shm.buf)
        np.copyto(shared_array, data)
        self.buffer.append((key, shm, data.shape, data.dtype))

    def send_next_chunk(self):
        if not self.buffer:
            return False

        key, shm, shape, dtype = self.buffer[0]
        try:
            start_time = time.perf_counter()
            self.conn.send((key, shm.name, shape, dtype))
            response = self.conn.recv()
            duration = time.perf_counter() - start_time
            
            self.send_times.append(duration)
            self.buffer.pop(0)
            
            if response == "Готово":
                shm.close()
                shm.unlink()
                return True
        except Exception as e:
            print(f"Ошибка: {e}")
            shm.close()
            shm.unlink()
            return False

    def get_recent_avg_put_interval(self, n=5):
        current_time = time.perf_counter()
        intervals = list(self.put_intervals)
        if self.last_put_time is not None:
            intervals.append(current_time - self.last_put_time)
        recent = intervals[-n:] if len(intervals) >= n else intervals
        return sum(recent)/len(recent) if recent else 0

    def get_recent_avg_send_time(self, n=5):
        items = list(self.send_times)[-n:]
        return sum(items)/len(items) if items else 0

def child_process(conn, lock):
    try:
        while True:
            key, shm_name, shape, dtype = conn.recv()
            shm = SharedMemory(name=shm_name)
            array = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
            
            # 3. Копируем данные в локальную память
            local_copy = np.empty_like(array)
               
            shm.close()
            conn.send("Готово")
    except EOFError:
        print("Соединение закрыто")

# Пример использования
if __name__ == "__main__":
    parent_conn, child_conn = Pipe()
    lock = Lock()
    
    p = Process(target=child_process, args=(child_conn, lock))
    p.start()
    
    manager = SharedBufferManager(parent_conn)
    
    # Тестовая нагрузка
    for i in range(5):
        data = np.random.rand(1000000)
        manager.put(f"array_{i}", data)
    
    while manager.send_next_chunk():
        print(f"Среднее время отправки: {manager.get_recent_avg_send_time():.4f} сек")
        print(f"Средний интервал добавления: {manager.get_recent_avg_put_interval():.4f} сек")
    
    parent_conn.close()
    p.join()