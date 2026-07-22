from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.conf import settings
from cameras.models import Camera
from residents.models import Resident
from visitors.models import Visitor
from recognition.models import RecognitionEvent
from recognition.services.embedding_utils import cosine_similarity
from recognition.services.cooldown import CooldownService

User = get_user_model()


class RecognitionScenarioTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="guard", password="pass123", role="GUARD")
        self.camera = Camera.objects.create(
            name="Gate",
            stream_url="0",
            location_name="Main Gate",
            is_active=True,
        )
        self.headers = {"HTTP_X_ENGINE_TOKEN": settings.VISION_GUARD_ENGINE_TOKEN}

    def test_scenario_resident_identified(self):
        resident = Resident.objects.create(
            full_name="John Resident",
            house_number="H1",
            face_embedding=[1.0] + [0.0] * 511,
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )
        response = self.client.post(
            "/recognition/api/events/",
            {
                "camera_id": self.camera.id,
                "person_type": "RESIDENT",
                "resident_id": resident.id,
                "confidence": 0.92,
                "cooldown_key": f"resident:{resident.id}",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        event = RecognitionEvent.objects.get()
        self.assertEqual(event.person_type, "RESIDENT")
        self.assertEqual(event.resident, resident)

    def test_scenario_unknown_creates_visitor(self):
        embedding = [0.5] * 512
        response = self.client.post(
            "/recognition/api/events/",
            {
                "camera_id": self.camera.id,
                "person_type": "UNKNOWN",
                "confidence": 0.4,
                "embedding": embedding,
                "cooldown_key": "unknown:abc",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Visitor.objects.count(), 1)

    def test_scenario_cooldown_blocks_duplicate(self):
        Resident.objects.create(
            full_name="Jane",
            house_number="H2",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )
        self.client.post(
            "/recognition/api/events/",
            {
                "camera_id": self.camera.id,
                "person_type": "RESIDENT",
                "resident_id": 1,
                "confidence": 0.9,
                "cooldown_key": "resident:1",
            },
            content_type="application/json",
            **self.headers,
        )
        response = self.client.post(
            "/recognition/api/events/",
            {
                "camera_id": self.camera.id,
                "person_type": "RESIDENT",
                "resident_id": 1,
                "confidence": 0.9,
                "cooldown_key": "resident:1",
            },
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(response.json().get("status"), "skipped")
        self.assertEqual(RecognitionEvent.objects.count(), 1)

    def test_scenario_cosine_similarity(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(a, b), 1.0)

    def test_stats_api_requires_login(self):
        response = self.client.get("/recognition/api/stats/")
        self.assertEqual(response.status_code, 403)
        self.client.login(username="guard", password="pass123")
        response = self.client.get("/recognition/api/stats/")
        self.assertEqual(response.status_code, 200)
