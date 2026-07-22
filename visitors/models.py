import uuid
from django.db import models
from residents.models import Resident


class Visitor(models.Model):
    visitor_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    face_embedding = models.JSONField(default=list, blank=True)
    snapshot = models.ImageField(upload_to="visitors/snapshots/%Y/%m/%d/", blank=True, null=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    visit_count = models.PositiveIntegerField(default=1)
    associated_resident = models.ForeignKey(
        Resident, on_delete=models.SET_NULL, null=True, blank=True, related_name="visitors"
    )
    notes = models.TextField(blank=True)
    is_known = models.BooleanField(default=False)

    class Meta:
        ordering = ["-last_seen"]

    def __str__(self):
        return f"Visitor {self.visitor_uuid} ({self.visit_count} visits)"
