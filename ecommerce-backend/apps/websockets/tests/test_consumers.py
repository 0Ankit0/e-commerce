from django.test import TestCase

from apps.websockets.consumers import NotificationConsumer


class WebsocketConsumerTests(TestCase):
    def test_consumer_import(self):
        # Basic sanity check that code imports
        self.assertTrue(NotificationConsumer)
