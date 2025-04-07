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

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
import logging
logger = logging.getLogger(__name__)

class tabPage(QWidget):
    def __init__(self, number, parent=None):
        super().__init__(parent)
        self.number = number
        self.callbacks = {Qt.Key_Delete:[]}

    def keyPressEvent(self, event):
        logger.info(f"нажата клавиша {event.key()}")
        for callback in self.callbacks.get(event.key(), []):
            callback()

    def subscribe_to_key_press(self, key, callback):

        if key not in self.callbacks.keys():
            self.callbacks[key] = []
        self.callbacks[key].append(callback)