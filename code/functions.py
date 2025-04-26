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
from multiprocessing import Queue
from queue import Empty

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