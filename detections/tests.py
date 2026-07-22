from django.conf import settings
from django.test import TestCase

from cameras.models import Camera
from detections.models import Incident
from detections.services.threat_scoring import ThreatScoringService


class BehaviourIncidentAPITests(TestCase):
    def setUp(self):
        self.camera = Camera.objects.create(
            name="Gate",
            stream_url="0",
            location_name="Main Gate",
        )
        self.headers = {"HTTP_X_ENGINE_TOKEN": settings.VISION_GUARD_ENGINE_TOKEN}

    def test_loitering_creates_medium_risk_incident_once_per_cooldown(self):
        payload = {
            "camera_id": self.camera.id,
            "behaviour_type": "LOITERING",
            "track_id": 12,
            "cooldown_seconds": 120,
        }
        first = self.client.post("/detections/api/behaviour/", payload, content_type="application/json", **self.headers)
        second = self.client.post("/detections/api/behaviour/", payload, content_type="application/json", **self.headers)

        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["created"])
        self.assertFalse(second.json()["created"])
        incident = Incident.objects.get()
        self.assertEqual(incident.risk_score, 50)
        self.assertEqual(incident.severity, "MEDIUM")
        self.assertIn("Loitering", incident.summary)

    def test_restricted_zone_creates_high_risk_incident(self):
        response = self.client.post(
            "/detections/api/behaviour/",
            {
                "camera_id": self.camera.id,
                "behaviour_type": "RESTRICTED_ZONE",
                "track_id": 12,
                "zone_name": "Server room",
                "cooldown_seconds": 120,
            },
            content_type="application/json",
            **self.headers,
        )

        self.assertEqual(response.status_code, 200)
        incident = Incident.objects.get()
        self.assertEqual(incident.risk_score, 75)
        self.assertEqual(incident.severity, "HIGH")
        self.assertIn("Server room", incident.summary)


class ThreatScoringTests(TestCase):
    def test_scores_and_severity_boundaries(self):
        self.assertEqual(ThreatScoringService.assess("LOITERING").risk_score, 50)
        self.assertEqual(ThreatScoringService.assess("RESTRICTED_ZONE").severity, "HIGH")
        self.assertEqual(ThreatScoringService.severity_for_score(30), "LOW")
        self.assertEqual(ThreatScoringService.severity_for_score(31), "MEDIUM")
        self.assertEqual(ThreatScoringService.severity_for_score(61), "HIGH")
        self.assertEqual(ThreatScoringService.severity_for_score(81), "CRITICAL")
