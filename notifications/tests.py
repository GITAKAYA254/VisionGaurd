from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.conf import settings
from cameras.models import Camera
from residents.models import Resident
from notifications.models import Notification
from notifications.services import NotificationService
from recognition.models import RecognitionEvent

User = get_user_model()


class NotificationModelTests(TestCase):
    def setUp(self):
        self.camera = Camera.objects.create(
            name="Front Gate",
            stream_url="0",
            location_name="Front Gate",
            is_active=True,
        )

    def test_notification_creation_ordering_and_live_url(self):
        n1 = Notification.objects.create(
            title="First",
            message="First message",
            severity=Notification.SEVERITY_INFO,
            camera=self.camera,
        )
        n2 = Notification.objects.create(
            title="Second",
            message="Second message",
            severity=Notification.SEVERITY_WARNING,
            camera=self.camera,
        )

        notifications = list(Notification.objects.all())
        self.assertEqual(notifications, [n2, n1])
        self.assertFalse(n1.is_read)
        self.assertIn("INFO", str(n1))
        self.assertEqual(n1.live_url, f"/monitor/?camera_id={self.camera.id}")


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.camera = Camera.objects.create(
            name="Front Door",
            stream_url="0",
            location_name="Main Entry",
            is_active=True,
        )

    def test_notify_resident(self):
        n = NotificationService.notify_resident("David Gitakaya", camera=self.camera)
        self.assertIsNotNone(n)
        self.assertEqual(n.title, "Resident Detected")
        self.assertIn("David Gitakaya arrived", n.message)
        self.assertEqual(n.severity, Notification.SEVERITY_INFO)
        self.assertEqual(n.camera, self.camera)

    def test_notify_unknown_and_deduplication(self):
        n1 = NotificationService.notify_unknown(track_id=12, camera=self.camera)
        self.assertIsNotNone(n1)
        self.assertEqual(n1.title, "Unknown Person Detected")
        self.assertEqual(n1.severity, Notification.SEVERITY_WARNING)

        # Second unknown detection for same track_id while unread is skipped
        n2 = NotificationService.notify_unknown(track_id=12, camera=self.camera)
        self.assertIsNone(n2)
        self.assertEqual(Notification.objects.count(), 1)

        # Once marked read, a new track event creates a notification
        n1.is_read = True
        n1.save()

        n3 = NotificationService.notify_unknown(track_id=12, camera=self.camera)
        self.assertIsNotNone(n3)
        self.assertEqual(Notification.objects.count(), 2)

    def test_notify_loitering_and_deduplication(self):
        n1 = NotificationService.notify_loitering(track_id=45, camera=self.camera)
        self.assertIsNotNone(n1)
        self.assertEqual(n1.title, "Suspicious Activity")
        self.assertEqual(n1.severity, Notification.SEVERITY_HIGH)

        # Duplicate loitering notification for same track is skipped
        n2 = NotificationService.notify_loitering(track_id=45, camera=self.camera)
        self.assertIsNone(n2)
        self.assertEqual(Notification.objects.count(), 1)

    def test_resident_never_triggers_loitering(self):
        """EXPLICIT BUSINESS RULE: Residents standing outside never generate loitering notifications."""
        n = NotificationService.notify_loitering(
            track_id=10,
            camera=self.camera,
            person_type="RESIDENT",
            metadata={"person_type": "RESIDENT"},
        )
        self.assertIsNone(n)
        self.assertEqual(Notification.objects.count(), 0)


class NotificationViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="guard", password="pass123")
        self.camera = Camera.objects.create(name="Cam 1", stream_url="0")
        self.n1 = Notification.objects.create(
            title="Alert 1", message="Msg 1", severity=Notification.SEVERITY_INFO, camera=self.camera
        )
        self.n2 = Notification.objects.create(
            title="Alert 2", message="Msg 2", severity=Notification.SEVERITY_WARNING, camera=self.camera
        )

    def test_notification_list_requires_login(self):
        response = self.client.get("/notifications/")
        self.assertEqual(response.status_code, 302)

        self.client.login(username="guard", password="pass123")
        response = self.client.get("/notifications/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alert 1")
        self.assertContains(response, "Alert 2")

    def test_view_live_marks_read_and_redirects(self):
        self.client.login(username="guard", password="pass123")
        response = self.client.get(f"/notifications/{self.n1.pk}/live/")
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/monitor/?camera_id={self.camera.id}", response.url)

        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

    def test_notification_detail_auto_marks_read(self):
        self.client.login(username="guard", password="pass123")
        response = self.client.get(f"/notifications/{self.n1.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View Live")

        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

    def test_live_notifications_api(self):
        self.client.login(username="guard", password="pass123")
        response = self.client.get("/notifications/api/live/?since_id=0")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["notifications"]), 2)
        self.assertIn("live_url", data["notifications"][0])


class EngineEventNotificationIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.camera = Camera.objects.create(name="Gate Cam", stream_url="0")
        self.headers = {"HTTP_X_ENGINE_TOKEN": settings.VISION_GUARD_ENGINE_TOKEN}

    def test_recognition_event_api_creates_resident_notification(self):
        resident = Resident.objects.create(
            full_name="Alice Smith",
            house_number="H10",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )

        response = self.client.post(
            "/recognition/api/events/",
            {
                "camera_id": self.camera.id,
                "person_type": "RESIDENT",
                "resident_id": resident.id,
                "confidence": 0.95,
                "cooldown_key": f"resident:{resident.id}",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)

        notif = Notification.objects.get()
        self.assertEqual(notif.severity, Notification.SEVERITY_INFO)
        self.assertIn("Alice Smith arrived", notif.message)

    def test_behaviour_api_creates_loitering_notification_for_unknown(self):
        response = self.client.post(
            "/detections/api/behaviour/",
            {
                "camera_id": self.camera.id,
                "behaviour_type": "LOITERING",
                "person_type": "UNKNOWN",
                "track_id": 99,
                "zone_name": "Main Entrance",
                "cooldown_seconds": 120,
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)

        notif = Notification.objects.get()
        self.assertEqual(notif.severity, Notification.SEVERITY_HIGH)
        self.assertEqual(notif.title, "Suspicious Activity")

    def test_behaviour_api_ignores_loitering_for_resident(self):
        response = self.client.post(
            "/detections/api/behaviour/",
            {
                "camera_id": self.camera.id,
                "behaviour_type": "LOITERING",
                "person_type": "RESIDENT",
                "track_id": 100,
                "zone_name": "Main Entrance",
                "cooldown_seconds": 120,
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Notification.objects.count(), 0)
