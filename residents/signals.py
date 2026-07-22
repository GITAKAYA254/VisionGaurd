from django.db.models.signals import post_save
from django.dispatch import receiver

from residents.models import Resident
from residents.services.face_enrollment import FaceEnrollmentService


@receiver(post_save, sender=Resident)
def enroll_resident_face(sender, instance, created, **kwargs):
    if instance.photo and instance.enrollment_status == Resident.ENROLLMENT_PENDING:
        FaceEnrollmentService.enroll(instance)
