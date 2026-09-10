import base64
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from cameras.models import Camera
from residents.models import Resident
from visitors.models import Visitor
from visitors.services.visitor_tracking import VisitorTrackingService
from .models import RecognitionEvent
from .services.embedding_cache import EmbeddingCache
from .services.cooldown import CooldownService
from notifications.services import NotificationService


def _save_snapshot(event, snapshot_b64):
    if not snapshot_b64:
        return
    from django.core.files.base import ContentFile
    data = base64.b64decode(snapshot_b64)
    event.snapshot.save(f"event_{event.id}.jpg", ContentFile(data), save=True)


class RecognitionEventAPI(APIView):
    def get_authenticators(self):
        if self.request.method == "POST":
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if self.request.method == "POST":
            return []
        return [IsAuthenticated()]

    def get(self, request):
        limit = int(request.query_params.get("limit", 50))
        events = RecognitionEvent.objects.select_related(
            "camera", "resident", "visitor"
        ).order_by("-timestamp")[:limit]
        data = [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "person": e.person_name,
                "person_type": e.person_type,
                "confidence": e.confidence,
                "camera": e.camera.name,
            }
            for e in events
        ]
        return Response({"events": data})

    def post(self, request):
        token = request.headers.get("X-Engine-Token", "")
        if token != settings.VISION_GUARD_ENGINE_TOKEN:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        camera_id = request.data.get("camera_id")
        person_type = request.data.get("person_type")
        confidence = float(request.data.get("confidence", 0))
        cooldown_key = request.data.get("cooldown_key", "")
        snapshot_b64 = request.data.get("snapshot_b64")

        cooldown = CooldownService()
        if cooldown.is_active(cooldown_key):
            return Response({"status": "skipped", "reason": "cooldown"})

        try:
            camera = Camera.objects.get(id=camera_id)
        except Camera.DoesNotExist:
            return Response({"error": "Camera not found"}, status=status.HTTP_404_NOT_FOUND)

        resident = None
        visitor = None

        if person_type == "RESIDENT":
            rid = request.data.get("resident_id")
            resident = Resident.objects.filter(pk=rid).first()
            person_type = RecognitionEvent.PERSON_RESIDENT
        elif person_type == "VISITOR":
            vid = request.data.get("visitor_id")
            visitor = Visitor.objects.filter(pk=vid).first()
            person_type = RecognitionEvent.PERSON_VISITOR
        elif person_type == "UNKNOWN":
            embedding = request.data.get("embedding")
            if embedding:
                tracker = VisitorTrackingService()
                visitor, created, score = tracker.find_or_create(embedding, snapshot_b64)
                confidence = max(confidence, score)
                person_type = RecognitionEvent.PERSON_VISITOR if visitor else RecognitionEvent.PERSON_UNKNOWN
            else:
                person_type = RecognitionEvent.PERSON_UNKNOWN
        else:
            return Response({"error": "invalid person_type"}, status=status.HTTP_400_BAD_REQUEST)

        event = RecognitionEvent.objects.create(
            camera=camera,
            person_type=person_type,
            resident=resident,
            visitor=visitor,
            confidence=confidence,
            cooldown_key=cooldown_key,
        )
        if snapshot_b64 and not (visitor and visitor.snapshot):
            _save_snapshot(event, snapshot_b64)

        if event.person_type == RecognitionEvent.PERSON_RESIDENT and resident:
            NotificationService.notify_resident(
                resident_name=resident.full_name,
                camera=camera,
                metadata={"resident_id": resident.id, "event_id": event.id},
                snapshot_b64=snapshot_b64,
            )
        elif event.person_type == RecognitionEvent.PERSON_UNKNOWN:
            track_id = request.data.get("track_id")
            if not track_id and ":" in cooldown_key:
                track_id = cooldown_key.split(":")[-1]
            NotificationService.notify_unknown(
                track_id=track_id,
                camera=camera,
                metadata={"cooldown_key": cooldown_key, "event_id": event.id},
                snapshot_b64=snapshot_b64,
            )

        return Response({"status": "success", "event_id": event.id})


class EmbeddingsAPI(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        token = request.headers.get("X-Engine-Token", "")
        if token != settings.VISION_GUARD_ENGINE_TOKEN:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(EmbeddingCache.as_api_payload())


class RecognitionStatsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        return Response(
            {
                "residents_registered": Resident.objects.filter(is_active=True).count(),
                "residents_enrolled": Resident.objects.filter(
                    enrollment_status=Resident.ENROLLMENT_ENROLLED
                ).count(),
                "known_visitors": Visitor.objects.filter(is_known=True).count(),
                "unknown_visitors_today": Visitor.objects.filter(
                    is_known=False, first_seen__date=today
                ).count(),
                "returning_visitors": Visitor.objects.filter(is_known=True, visit_count__gt=1).count(),
            }
        )


@login_required
def recognition_feed(request):
    events = RecognitionEvent.objects.select_related("camera", "resident", "visitor")[:50]
    return render(request, "recognition/recognition_feed.html", {"events": events})
