from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Detection, Incident, CameraLiveStats
from cameras.models import Camera
from django.utils import timezone

PERSON_CLASS_NAMES = {"person"}
VEHICLE_CLASS_NAMES = {"car", "bus", "truck"}
CLASS_NAME_TO_LABEL = {
    "person": "PERSON",
    "car": "VEHICLE",
    "bus": "VEHICLE",
    "truck": "VEHICLE",
    "bicycle": "BICYCLE",
    "motorcycle": "MOTORCYCLE",
}


def label_from_class_name(class_name):
    return CLASS_NAME_TO_LABEL.get(class_name.lower(), "VEHICLE")


class DetectionListView(LoginRequiredMixin, ListView):
    model = Detection
    template_name = "detections/detection_list.html"
    context_object_name = "detections"
    paginate_by = 50
    ordering = ["-timestamp"]


class IncidentListView(LoginRequiredMixin, ListView):
    model = Incident
    template_name = "detections/incident_list.html"
    context_object_name = "incidents"
    ordering = ["-start_time"]


class IncidentDetailView(LoginRequiredMixin, DetailView):
    model = Incident
    template_name = "detections/incident_detail.html"


class LogDetectionAPI(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        token = request.headers.get("X-Engine-Token", "")
        if token != settings.VISION_GUARD_ENGINE_TOKEN:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        camera_id = request.data.get("camera_id")
        label = request.data.get("label")
        class_name = request.data.get("class_name", "")
        confidence = request.data.get("confidence")

        if camera_id is None or confidence is None:
            return Response(
                {"error": "camera_id and confidence are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if class_name:
            label = label_from_class_name(class_name)
        elif label is None:
            return Response(
                {"error": "label or class_name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            return Response({"error": "confidence must be a number"}, status=status.HTTP_400_BAD_REQUEST)

        if not (0.0 <= confidence <= 1.0):
            return Response({"error": "confidence must be between 0 and 1"}, status=status.HTTP_400_BAD_REQUEST)

        if label not in dict(Detection.LABEL_CHOICES):
            return Response({"error": "invalid label"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            camera = Camera.objects.get(id=camera_id)
        except Camera.DoesNotExist:
            return Response({"error": "Camera not found"}, status=status.HTTP_404_NOT_FOUND)

        detection = Detection.objects.create(
            camera=camera,
            label=label,
            class_name=class_name or label.lower(),
            confidence=confidence,
        )

        two_mins_ago = timezone.now() - timezone.timedelta(minutes=2)
        incident = Incident.objects.filter(
            camera=camera,
            status="OPEN",
            start_time__gte=two_mins_ago,
        ).first()

        if not incident:
            incident = Incident.objects.create(
                camera=camera,
                start_time=timezone.now(),
                lead_detection=detection,
                risk_score=50 if label == "PERSON" else 20,
            )
        else:
            incident.end_time = timezone.now()
            incident.save()

        return Response({"status": "success", "detection_id": detection.id, "incident_id": incident.id})


class LiveStatsAPI(APIView):
    def get_authenticators(self):
        if self.request.method == "POST":
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if self.request.method == "POST":
            return []
        return [IsAuthenticated()]

    def post(self, request):
        token = request.headers.get("X-Engine-Token", "")
        if token != settings.VISION_GUARD_ENGINE_TOKEN:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        camera_id = request.data.get("camera_id")
        people_count = request.data.get("people_count")
        vehicle_count = request.data.get("vehicle_count")
        detected_names = request.data.get("detected_names", [])

        if camera_id is None or people_count is None or vehicle_count is None:
            return Response(
                {"error": "camera_id, people_count, and vehicle_count are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            camera = Camera.objects.get(id=camera_id)
        except Camera.DoesNotExist:
            return Response({"error": "Camera not found"}, status=status.HTTP_404_NOT_FOUND)

        if not isinstance(detected_names, list):
            return Response({"error": "detected_names must be a list"}, status=status.HTTP_400_BAD_REQUEST)

        CameraLiveStats.objects.update_or_create(
            camera=camera,
            defaults={
                "people_count": int(people_count),
                "vehicle_count": int(vehicle_count),
                "detected_names": detected_names,
            },
        )

        return Response({"status": "success"})

    def get(self, request):
        camera_id = request.query_params.get("camera_id")
        stale_seconds = 10
        now = timezone.now()

        stats_qs = CameraLiveStats.objects.select_related("camera")
        if camera_id:
            stats_qs = stats_qs.filter(camera_id=camera_id)

        data = []
        for stats in stats_qs:
            age = (now - stats.updated_at).total_seconds()
            is_stale = age > stale_seconds
            data.append(
                {
                    "camera_id": stats.camera_id,
                    "camera_name": stats.camera.name,
                    "people_count": 0 if is_stale else stats.people_count,
                    "vehicle_count": 0 if is_stale else stats.vehicle_count,
                    "detected_names": [] if is_stale else stats.detected_names,
                    "updated_at": stats.updated_at.isoformat(),
                    "is_stale": is_stale,
                }
            )

        return Response({"cameras": data})
