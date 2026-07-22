from django.contrib import admin
from .models import Detection, Incident, CameraLiveStats

@admin.register(Detection)
class DetectionAdmin(admin.ModelAdmin):
    list_display = ('label', 'class_name', 'camera', 'confidence', 'timestamp')
    list_filter = ('label', 'camera')

@admin.register(CameraLiveStats)
class CameraLiveStatsAdmin(admin.ModelAdmin):
    list_display = ('camera', 'people_count', 'vehicle_count', 'updated_at')

@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'camera', 'risk_score', 'severity', 'status', 'start_time')
    list_filter = ('severity', 'status', 'camera')
