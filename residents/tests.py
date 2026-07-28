import base64
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from residents.models import Resident, ResidentEmbedding
from residents.services.face_enrollment import FaceEnrollmentService
from residents.services.face_enhancement import FaceEnhancementService


User = get_user_model()


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


class FaceEnhancementServiceTests(TestCase):
    """Tests for Sprint 2 face enhancement feature."""
    
    def test_get_embedding_count(self):
        """Test getting count of active embeddings."""
        resident = Resident.objects.create(
            full_name="Embedding Count Test",
            house_number="A5",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )
        
        # Create 3 active embeddings
        for i in range(3):
            ResidentEmbedding.objects.create(
                resident=resident,
                embedding=[float(i)] * 512,
                is_active=True,
            )
        
        # Create 1 inactive embedding
        ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[0.5] * 512,
            is_active=False,
        )
        
        count = FaceEnhancementService.get_embedding_count(resident)
        self.assertEqual(count, 3)
    
    def test_get_resident_embeddings(self):
        """Test getting all active embeddings for a resident."""
        resident = Resident.objects.create(
            full_name="Get Embeddings Test",
            house_number="A6",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )
        
        # Create embeddings
        emb1 = ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[1.0] * 512,
            is_active=True,
        )
        emb2 = ResidentEmbedding.objects.create(
            resident=resident,
            embedding=[0.9] * 512,
            is_active=True,
        )
        
        embeddings = FaceEnhancementService.get_resident_embeddings(resident)
        
        self.assertEqual(len(embeddings), 2)
        # Check that both embeddings are returned (order might vary if same timestamp)
        embedding_ids = {e.id for e in embeddings}
        self.assertEqual(embedding_ids, {emb1.id, emb2.id})
    
    def test_reject_too_many_images(self):
        """Test that requests with too many images are rejected before processing."""
        resident = Resident.objects.create(
            full_name="Too Many Images Test",
            house_number="A7",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )
        
        # Create more images than the limit
        images = ['fake_base64_image_' + str(i) for i in range(FaceEnhancementService.MAX_IMAGES + 1)]
        
        result = FaceEnhancementService.process_webcam_captures(resident, images)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['embeddings_created'], 0)
        self.assertIn('exceeded image limit', result['message'])
        self.assertTrue(any('exceeds maximum' in e for e in result['errors']))
    
    def test_reject_high_pixel_image(self):
        """Test that images exceeding pixel dimension limits are rejected."""
        from PIL import Image
        import io
        
        resident = Resident.objects.create(
            full_name="High Pixel Image Test",
            house_number="A9",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )
        
        # Create image that exceeds MAX_IMAGE_PIXELS
        # Use dimensions that exceed the limit (e.g., 5000x5000 = 25M pixels vs 16M max)
        img = Image.new('RGB', (5000, 5000), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=50)  # Lower quality to keep file size reasonable
        img_bytes.seek(0)
        img_base64 = base64.b64encode(img_bytes.read()).decode('ascii')
        images = [img_base64]
        
        result = FaceEnhancementService.process_webcam_captures(resident, images)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['embeddings_created'], 0)
        self.assertIn('dimension limit', result['message'])
        self.assertTrue(any('exceeds pixel limit' in e for e in result['errors']))


class EnhanceFaceViewTests(TestCase):
    """Tests for Sprint 2 enhance face view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="guard", password="testpass", role="GUARD")
        self.resident = Resident.objects.create(
            full_name="Test Resident",
            house_number="H1",
            enrollment_status=Resident.ENROLLMENT_ENROLLED,
        )
    
    def test_enhance_face_page_requires_login(self):
        """Test that enhance face page requires authentication."""
        response = self.client.get(f'/residents/{self.resident.pk}/enhance-face/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_enhance_face_page_loads(self):
        """Test that enhance face page loads for authenticated user."""
        self.client.login(username="guard", password="testpass")
        response = self.client.get(f'/residents/{self.resident.pk}/enhance-face/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enhance Face Recognition')
        self.assertContains(response, self.resident.full_name)
    
    def test_enhance_face_api_requires_authentication(self):
        """Test that enhance face API requires authentication."""
        response = self.client.post(
            f'/residents/api/{self.resident.pk}/enhance-face/',
            {'images': []},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
    
    def test_enhance_face_api_requires_images(self):
        """Test that enhance face API requires images."""
        self.client.login(username="guard", password="testpass")
        response = self.client.post(
            f'/residents/api/{self.resident.pk}/enhance-face/',
            {'images': []},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

