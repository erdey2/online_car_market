from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Notification, NotificationPreference


User = get_user_model()


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="safe-pass-123",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="safe-pass-123",
        )
        self.client.force_authenticate(user=self.user)

    def test_list_returns_only_current_user_notifications(self):
        own = Notification.objects.create(recipient=self.user, message="Own notification")
        Notification.objects.create(recipient=self.other_user, message="Other notification")

        response = self.client.get("/api/notifications/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], own.id)

    def test_unread_filter_and_count(self):
        Notification.objects.create(recipient=self.user, message="Unread one", is_read=False)
        Notification.objects.create(recipient=self.user, message="Read one", is_read=True)

        list_response = self.client.get("/api/notifications/?unread=true")
        count_response = self.client.get("/api/notifications/unread_count/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(count_response.status_code, status.HTTP_200_OK)
        self.assertEqual(count_response.data["unread"], 1)

    def test_mark_read_single_and_all(self):
        first = Notification.objects.create(recipient=self.user, message="N1", is_read=False)
        second = Notification.objects.create(recipient=self.user, message="N2", is_read=False)

        single_response = self.client.post("/api/notifications/mark_read/", {"id": first.id}, format="json")
        self.assertEqual(single_response.status_code, status.HTTP_200_OK)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertTrue(first.is_read)
        self.assertFalse(second.is_read)

        all_response = self.client.post("/api/notifications/mark_read/", {}, format="json")
        self.assertEqual(all_response.status_code, status.HTTP_200_OK)
        second.refresh_from_db()
        self.assertTrue(second.is_read)

    def test_notification_preferences_get_or_create(self):
        self.assertFalse(NotificationPreference.objects.filter(user=self.user).exists())

        response = self.client.get("/api/notifications/notification-preferences/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(NotificationPreference.objects.filter(user=self.user).exists())
