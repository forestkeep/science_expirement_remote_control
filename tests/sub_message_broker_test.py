
import unittest
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
