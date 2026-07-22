from django.test import TestCase
from residents.models import Resident, ResidentEmbedding
from residents.services.face_enrollment import FaceEnrollmentService


class FaceEnrollmentTests(TestCase):
    def test_enrollment_fails_without_photo(self):
        resident = Resident.objects.create(
            full_name="Jane Doe",
            house_number="A12",
            enrollment_status=Resident.ENROLLMENT_PENDING,
        )
        FaceEnrollmentService.enroll(resident)
        resident.refresh_from_db()
        self.assertEqual(resident.enrollment_status, Resident.ENROLLMENT_FAILED)
        self.assertIn("No photo", resident.enrollment_error)


class ResidentEmbeddingTests(TestCase):
    """Tests for multi-embedding support (Sprint 1)."""
    
    def test_resident_can_have_multiple_embeddings(self):
        """Test that a resident can store multiple embeddings."""
        resident = Resident.objects.create(
            full_name="Test Resident",
            house_number="A1",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )
        
        # Create multiple embeddings for the same resident
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
        
        # Verify both embeddings exist
        embeddings = ResidentEmbedding.objects.filter(resident=resident, is_active=True)
        self.assertEqual(embeddings.count(), 2)
    
    def test_embedding_quality_score_stored(self):
        """Test that quality scores are stored and retrievable."""
        resident = Resident.objects.create(
            full_name="Quality Test",
            house_number="A2",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )
        
        embedding = ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[0.5] * 512,
            quality_score=0.92,
            is_active=True,
        )
        
        retrieved = ResidentEmbedding.objects.get(id=embedding.id)
        self.assertEqual(retrieved.quality_score, 0.92)
    
    def test_embedding_deactivation(self):
        """Test that embeddings can be deactivated."""
        resident = Resident.objects.create(
            full_name="Deactivation Test",
            house_number="A3",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )
        
        embedding = ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[0.5] * 512,
            is_active=True,
        )
        
        embedding.is_active = False
        embedding.save()
        
        # Verify only active embeddings are returned
        active_count = ResidentEmbedding.objects.filter(
            resident=resident,
            is_active=True
        ).count()
        self.assertEqual(active_count, 0)
    
    def test_migration_preserves_backward_compatibility(self):
        """
        Test that residents with legacy face_embedding still work.
        This simulates the state after migration 0003.
        """
        # Create resident with legacy embedding
        resident = Resident.objects.create(
            full_name="Legacy Resident",
            house_number="A4",
            face_embedding=[1.0] + [0.0] * 511,
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )
        
        # Also create a ResidentEmbedding (migration should do this)
        ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[1.0] + [0.0] * 511,
            is_active=True,
        )
        
        # Verify both exist
        self.assertIsNotNone(resident.face_embedding)
        embeddings = ResidentEmbedding.objects.filter(resident=resident, is_active=True)
        self.assertEqual(embeddings.count(), 1)
