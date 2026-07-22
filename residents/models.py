from django.db import models


class Resident(models.Model):
    ENROLLMENT_PENDING = "PENDING"
    ENROLLMENT_ENROLLED = "ENROLLED"
    ENROLLMENT_FAILED = "FAILED"
    ENROLLMENT_CHOICES = (
        (ENROLLMENT_PENDING, "Pending"),
        (ENROLLMENT_ENROLLED, "Enrolled"),
        (ENROLLMENT_FAILED, "Failed"),
    )

    full_name = models.CharField(max_length=200)
    house_number = models.CharField(max_length=50, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to="residents/photos/%Y/%m/%d/", blank=True, null=True)
    face_embedding = models.JSONField(default=list, blank=True)
    enrollment_status = models.CharField(
        max_length=20, choices=ENROLLMENT_CHOICES, default=ENROLLMENT_PENDING
    )
    enrollment_error = models.TextField(blank=True)
    date_registered = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.house_number})"


class ResidentEmbedding(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name="embeddings")
    embedding = models.JSONField(default=list, blank=True)
    quality_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["resident", "is_active"])]

    def __str__(self):
        return f"Embedding for {self.resident.full_name} ({self.created_at})"
