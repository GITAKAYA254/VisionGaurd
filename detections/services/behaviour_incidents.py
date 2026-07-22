"""Persist behaviour incidents while retaining the existing Incident model."""
from django.db import transaction
from django.utils import timezone

from cameras.models import Camera
from detections.models import Incident
from .threat_scoring import ThreatScoringService


BEHAVIOUR_LABELS = {
    "LOITERING": "Loitering",
    "RESTRICTED_ZONE": "Restricted-zone entry",
}


def incident_summary(behaviour_type, track_id, zone_name=""):
    label = BEHAVIOUR_LABELS[behaviour_type]
    if zone_name:
        return f"{label} detected in {zone_name} (track #{track_id})"
    return f"{label} detected (track #{track_id})"


def create_behaviour_incident(camera, behaviour_type, track_id, cooldown_seconds, zone_name=""):
    """Create one open incident per behaviour signature during its cooldown."""
    summary = incident_summary(behaviour_type, track_id, zone_name)
    cutoff = timezone.now() - timezone.timedelta(seconds=int(cooldown_seconds))
    with transaction.atomic():
        camera = Camera.objects.select_for_update().get(pk=camera.pk)
        existing = Incident.objects.select_for_update().filter(
            camera=camera,
            status="OPEN",
            summary=summary,
            start_time__gte=cutoff,
        ).first()
        if existing:
            return existing, False

        assessment = ThreatScoringService.assess(behaviour_type)
        incident = Incident.objects.create(
            camera=camera,
            start_time=timezone.now(),
            risk_score=assessment.risk_score,
            severity=assessment.severity,
            summary=summary,
        )
    return incident, True
