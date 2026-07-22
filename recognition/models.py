from django.db import models
from cameras.models import Camera
from residents.models import Resident
from visitors.models import Visitor


class RecognitionEvent(models.Model):
    PERSON_RESIDENT = "RESIDENT"
    PERSON_VISITOR = "VISITOR"
    PERSON_UNKNOWN = "UNKNOWN"
    PERSON_TYPES = (
        (PERSON_RESIDENT, "Resident"),
        (PERSON_VISITOR, "Visitor"),
        (PERSON_UNKNOWN, "Unknown"),
    )

    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name="recognition_events")
    person_type = models.CharField(max_length=20, choices=PERSON_TYPES)
    resident = models.ForeignKey(Resident, on_delete=models.SET_NULL, null=True, blank=True)
    visitor = models.ForeignKey(Visitor, on_delete=models.SET_NULL, null=True, blank=True)
    confidence = models.FloatField(default=0.0)
    snapshot = models.ImageField(upload_to="recognition/snapshots/%Y/%m/%d/", blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    cooldown_key = models.CharField(max_length=100, blank=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.person_type} @ {self.camera.name} ({self.timestamp})"

    @property
    def person_name(self):
        if self.resident:
            return self.resident.full_name
        if self.visitor:
            return f"Visitor {str(self.visitor.visitor_uuid)[:8]}"
        return "Unknown"
