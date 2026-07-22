from django.test import TestCase
from residents.models import Resident
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
