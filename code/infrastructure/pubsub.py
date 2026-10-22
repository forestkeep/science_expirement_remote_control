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

import logging

logger = logging.getLogger(__name__)

class subscribe:
    def __init__(self, name, publiser, description) -> None:
        self.publisher = publiser
        self.name = name
        self.description = description
        self.subscribers = []

    def add_subscriber(self, sub):
        self.subscribers.append(sub)
        logger.debug(f"Добавлен подписчик {sub} в подписку {self.name}")

    def remove_all_subscribers(self):
        self.subscribers = []

    def remove_subscriber(self, sub) -> bool:
        index = 0
        for sb in self.subscribers:
            if sub == sb:
                self.subscribers.pop(index)
                return True
            index += 1
        return False

    def push_message(self):
        for sub in self.subscribers:
            try:
                sub.receive_message(self.name)
            except Exception as e:
                logger.warning(f"Ошибка при отправке сообщения от {self.name} подписчику {sub} ошибка {e}")

    def get_name(self):
        return self.name

class messageBroker:
    def __init__(self) -> None:
        self.subscribe_list = []

    def get_subscribe_list(self, object) -> list:
        send_list = []
        for sub in self.subscribe_list:
            if sub.publisher != object:
                if sub.publisher.is_active:
                    send_list.append(sub.get_name())
        return send_list
    
    def get_subscribe_description(self, subscribe_name) -> list:
        for sub in self.subscribe_list:
            if sub.get_name() == subscribe_name:
                return sub.description
        return ""

    def subscribe(self, object, name_subscribe):
        for subscribe in self.subscribe_list:
            if name_subscribe == subscribe.get_name():
                subscribe.add_subscriber(object)
                return True
        return False

    def remove_my_subscribe(self, object, name_subscribe=False):
        if name_subscribe == False:
            for subscribe in self.subscribe_list:
                subscribe.remove_subscriber(object)
        else:
            for subscribe in self.subscribe_list:
                if name_subscribe == subscribe.get_name():
                    subscribe.remove_subscriber(object)
                    break

    def clear_all_subscribers(self):
        """очистить все подписки от подписчиков"""
        for subscribe in self.subscribe_list:
            subscribe.remove_all_subscribers()

    def clear_all(self):
        """очистить все подписки"""
        self.subscribe_list = []

    def clear_my_topicks(self, publisher):
        buf_list = []
        for ind, subscribe in enumerate(self.subscribe_list):
                if publisher != subscribe.publisher:
                    buf_list.append(subscribe)
                else:
                    del subscribe

        self.subscribe_list = buf_list
                    
    def create_subscribe(self, name_subscribe, publisher, description=""):
        new_subscribe = subscribe(
            name=name_subscribe, publiser=publisher, description=description
        )
        self.subscribe_list.append(new_subscribe)

    def push_publish(self, name_subscribe, publisher):
        for sub in self.subscribe_list:
            if sub.get_name() == name_subscribe:
                if sub.publisher == publisher:
                    sub.push_message()
                    return True
                else:
                    return False
        return False

    def get_subscribers(self, publisher, name_subscribe):
        for sub in self.subscribe_list:
            if sub.get_name() == name_subscribe:
                if sub.publisher == publisher:
                    return sub.subscribers
                else:
                    return False
                
    def get_publisher(self, name_subscribe):
        """
        Возвращает издателя (publisher) подписки с указанным именем.
        Если подписка не найдена, возвращает None.
        """
        for sub in self.subscribe_list:
            if sub.get_name() == name_subscribe:
                return sub.publisher
        return None

class MockSubscriber:
    def __init__(self, name):
        self.name = name
        self.received_messages = []

    def receive_message(self, message):
        self.received_messages.append(message)
