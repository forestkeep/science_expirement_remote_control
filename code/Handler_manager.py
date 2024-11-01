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

import unittest


class subscribe:
    def __init__(self, name, publiser, description) -> None:
        self.publisher = publiser
        self.name = name
        self.description = description
        self.subscribers = []

    def add_subscriber(self, sub):
        self.subscribers.append(sub)

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
            except:
                print(f"Ошибка при отправке сообщения от {self.name} подписчику {sub}")

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
                    print(
                        f"Ошибка, отправить публикацию может только создатель {sub.publisher=} {publisher=}"
                    )
                    return False
        return False

    def get_subscribers(self, publisher, name_subscribe):
        for sub in self.subscribe_list:
            if sub.get_name() == name_subscribe:
                if sub.publisher == publisher:
                    return sub.subscribers
                else:
                    print("Ошибка, отправить публикацию может только создатель")
                    return False


class MockSubscriber:
    def __init__(self, name):
        self.name = name
        self.received_messages = []

    def receive_message(self, message):
        self.received_messages.append(message)


class TestSubscribeAndMessageBroker(unittest.TestCase):

    def setUp(self):
        self.publisher_name = "Publisher1"
        self.subscriber_name = "Subscriber1"
        self.subscriber = MockSubscriber(self.subscriber_name)
        self.subscribe_service = subscribe(
            "Subscription1", self.publisher_name, "Description1"
        )
        self.message_broker = messageBroker()

    def test_add_subscriber(self):
        self.subscribe_service.add_subscriber(self.subscriber)
        self.assertIn(self.subscriber, self.subscribe_service.subscribers)

    def test_remove_subscriber(self):
        self.subscribe_service.add_subscriber(self.subscriber)
        self.assertTrue(self.subscribe_service.remove_subscriber(self.subscriber))
        self.assertNotIn(self.subscriber, self.subscribe_service.subscribers)

    def test_push_message(self):
        self.subscribe_service.add_subscriber(self.subscriber)
        self.subscribe_service.push_message()
        self.assertEqual(self.subscriber.received_messages, ["Subscription1"])

    def test_create_subscribe(self):
        self.message_broker.create_subscribe("Subscription2", "Publisher2")
        self.assertEqual(len(self.message_broker.subscribe_list), 1)
        self.assertEqual(
            self.message_broker.subscribe_list[0].get_name(), "Subscription2"
        )

    def test_subscribe_to_existing(self):
        self.message_broker.create_subscribe("Subscription2", "Publisher2")
        result = self.message_broker.subscribe(self.subscriber, "Subscription2")
        self.assertTrue(result)
        self.assertIn(
            self.subscriber, self.message_broker.subscribe_list[0].subscribers
        )

    def test_push_publish(self):
        self.message_broker.create_subscribe("Subscription2", self.publisher_name)
        self.message_broker.subscribe(self.subscriber, "Subscription2")
        result = self.message_broker.push_publish("Subscription2", self.publisher_name)
        self.assertTrue(result)
        self.assertEqual(self.subscriber.received_messages, ["Subscription2"])

    def test_push_publish_wrong_publisher(self):
        self.message_broker.create_subscribe("Subscription2", self.publisher_name)
        result = self.message_broker.push_publish("Subscription2", "WrongPublisher")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
