from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.conf import settings
from cameras.models import Camera
from residents.models import Resident, ResidentEmbedding
from visitors.models import Visitor
from recognition.models import RecognitionEvent
from recognition.services.embedding_utils import cosine_similarity
from recognition.services.cooldown import CooldownService
from recognition.services.embedding_cache import EmbeddingCache

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


class EmbeddingCacheMultiEmbeddingTests(TestCase):
    """Tests for EmbeddingCache with multiple embeddings per resident (Sprint 1)."""
    
    def test_embedding_cache_loads_multiple_embeddings(self):
        """Test that EmbeddingCache loads multiple embeddings per resident."""
        resident = Resident.objects.create(
            full_name="Multi-Embedding Resident",
            house_number="H3",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
            is_active=True,
        )
        
        # Create multiple embeddings
        emb1 = ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[1.0] + [0.0] * 511,
            quality_score=0.95,
            is_active=True,
        )
        emb2 = ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[0.9] + [0.1] * 511,
            quality_score=0.88,
            is_active=True,
        )
        
        # Get cache
        cache = EmbeddingCache.get_residents()
        
        # Should have 2 entries for this one resident
        resident_entries = [e for e in cache if e["id"] == str(resident.id)]
        self.assertEqual(len(resident_entries), 2)
        
        # Verify embeddings are different
        embeddings = [e["embedding"] for e in resident_entries]
        self.assertNotEqual(embeddings[0], embeddings[1])
    
    def test_embedding_cache_backward_compatible_single_embedding(self):
        """Test that single legacy embeddings still work."""
        resident = Resident.objects.create(
            full_name="Legacy Single Embedding",
            house_number="H4",
            face_embedding=[0.5] * 512,
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
            is_active=True,
        )
        
        cache = EmbeddingCache.get_residents()
        
        # Should load the legacy embedding
        resident_entries = [e for e in cache if e["id"] == str(resident.id)]
        self.assertEqual(len(resident_entries), 1)
        self.assertEqual(resident_entries[0]["embedding"], [0.5] * 512)
    
    def test_embedding_cache_ignores_inactive_embeddings(self):
        """Test that inactive embeddings are not returned."""
        resident = Resident.objects.create(
            full_name="Inactive Embedding Test",
            house_number="H5",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
            is_active=True,
        )
        
        # Create active embedding
        active = ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[1.0] + [0.0] * 511,
            is_active=True,
        )
        
        # Create inactive embedding
        inactive = ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[0.0] * 512,
            is_active=False,
        )
        
        cache = EmbeddingCache.get_residents()
        resident_entries = [e for e in cache if e["id"] == str(resident.id)]
        
        # Should only have 1 (the active one)
        self.assertEqual(len(resident_entries), 1)
        self.assertEqual(resident_entries[0]["embedding"], [1.0] + [0.0] * 511)
    
    def test_embedding_cache_includes_quality_score(self):
        """Test that quality scores are included in cache."""
        resident = Resident.objects.create(
            full_name="Quality Score Test",
            house_number="H6",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
            is_active=True,
        )
        
        ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[0.5] * 512,
            quality_score=0.93,
            is_active=True,
        )
        
        cache = EmbeddingCache.get_residents()
        resident_entries = [e for e in cache if e["id"] == str(resident.id)]
        
        self.assertEqual(resident_entries[0]["quality_score"], 0.93)
    
    def test_api_payload_includes_multiple_embeddings(self):
        """Test that API payload correctly serializes multiple embeddings."""
        resident = Resident.objects.create(
            full_name="API Payload Test",
            house_number="H7",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
            is_active=True,
        )
        
        ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[1.0] + [0.0] * 511,
            is_active=True,
        )
        ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[0.9] + [0.1] * 511,
            is_active=True,
        )
        
        payload = EmbeddingCache.as_api_payload()
        
        # Verify payload structure
        self.assertIn("residents", payload)
        self.assertIn("visitors", payload)
        
        # Verify resident embeddings
        resident_entries = [e for e in payload["residents"] if e["id"] == str(resident.id)]
        self.assertEqual(len(resident_entries), 2)
    
    def test_embedding_cache_excludes_inactive_residents(self):
        """Test that inactive residents are not included."""
        inactive_resident = Resident.objects.create(
            full_name="Inactive Resident",
            house_number="H8",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
            is_active=False,
        )
        
        ResidentEmbedding.objects.create(
            resident=inactive_resident,
            embedding=[0.5] * 512,
            is_active=True,
        )
        
        cache = EmbeddingCache.get_residents()
        
        # Should not include inactive resident
        resident_ids = [e["id"] for e in cache]
        self.assertNotIn(str(inactive_resident.id), resident_ids)
    
    def test_embedding_cache_excludes_non_enrolled_residents(self):
        """Test that non-enrolled residents are not included."""
        pending_resident = Resident.objects.create(
            full_name="Pending Resident",
            house_number="H9",
            enrollment_status=Resident.ENROLLMENT_PENDING,
            is_active=True,
        )
        
        ResidentEmbedding.objects.create(
            resident=pending_resident,
            embedding=[0.5] * 512,
            is_active=True,
        )
        
        cache = EmbeddingCache.get_residents()
        
        # Should not include non-enrolled resident
        resident_ids = [e["id"] for e in cache]
        self.assertNotIn(str(pending_resident.id), resident_ids)


class MatchEmbeddingPrioritizationTests(TestCase):
    def test_resident_prioritized_over_higher_scoring_visitor(self):
        """
        Verify that if a resident score meets threshold (e.g. 0.85 >= 0.65),
        RESIDENT is immediately returned without checking visitors, even if a visitor
        has a higher score (e.g. 0.95).
        """
        from vision_engine.recognition import match_embedding

        target_emb = [1.0, 0.0, 0.0]
        residents = [
            {"id": "1", "name": "John", "embedding": [0.70, 0.714, 0.0], "type": "RESIDENT"}, # score 0.70
            {"id": "1", "name": "John", "embedding": [0.85, 0.5267, 0.0], "type": "RESIDENT"}, # score 0.85
        ]
        visitors = [
            {"id": "22", "name": "Visitor 22", "embedding": [0.98, 0.199, 0.0], "type": "VISITOR"} # score 0.98
        ]

        person_type, match_dict, score = match_embedding(target_emb, residents, visitors, threshold=0.65)
        self.assertEqual(person_type, "RESIDENT")
        self.assertEqual(match_dict["id"], "1")
        self.assertAlmostEqual(score, 0.85, places=2)

    def test_multi_embedding_resident_grouping(self):
        """
        Verify that multiple embeddings for the same resident are grouped by resident ID
        and that the highest score for each resident is selected.
        """
        from vision_engine.recognition import match_embedding

        target = [1.0, 0.0, 0.0]
        residents = [
            {"id": "1", "name": "John", "embedding": [0.80, 0.60, 0.0], "type": "RESIDENT"}, # score 0.80
            {"id": "1", "name": "John", "embedding": [0.95, 0.3122, 0.0], "type": "RESIDENT"}, # score 0.95
            {"id": "2", "name": "Mary", "embedding": [0.88, 0.475, 0.0], "type": "RESIDENT"}, # score 0.88
        ]
        visitors = []

        person_type, match_dict, score = match_embedding(target, residents, visitors, threshold=0.65)
        self.assertEqual(person_type, "RESIDENT")
        self.assertEqual(match_dict["id"], "1")
        self.assertAlmostEqual(score, 0.95, places=2)

    def test_fallback_to_visitor_when_no_resident_satisfies_threshold(self):
        from vision_engine.recognition import match_embedding

        target = [1.0, 0.0, 0.0]
        residents = [
            {"id": "1", "name": "John", "embedding": [0.50, 0.866, 0.0], "type": "RESIDENT"} # score 0.50
        ]
        visitors = [
            {"id": "22", "name": "Visitor 22", "embedding": [0.82, 0.5724, 0.0], "type": "VISITOR"} # score 0.82
        ]

        person_type, match_dict, score = match_embedding(target, residents, visitors, threshold=0.65)
        self.assertEqual(person_type, "VISITOR")
        self.assertEqual(match_dict["id"], "22")
        self.assertAlmostEqual(score, 0.82, places=2)


