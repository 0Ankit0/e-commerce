from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.notifications.strategies import InAppNotificationStrategy
from apps.notifications.models import Notification

User = get_user_model()

class NotificationStrategyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='p')

    def test_in_app_notification_send(self):
        data = {"message": "Hello"}
        InAppNotificationStrategy.send_notification(
            user=self.user, 
            type="info", 
            data=data, 
            issuer="system"
        )
        
        self.assertEqual(Notification.objects.count(), 1)
        notif = Notification.objects.first()
        self.assertEqual(notif.user, self.user)
        self.assertEqual(notif.data, data)
