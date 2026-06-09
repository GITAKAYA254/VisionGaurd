from django.contrib import admin
from .models import Detection, Incident, Visitor, CameraLiveStats

@admin.register(Detection)
class DetectionAdmin(admin.ModelAdmin):
    list_display = ('label', 'class_name', 'camera', 'confidence', 'timestamp')
    list_filter = ('label', 'camera')

@admin.register(CameraLiveStats)
class CameraLiveStatsAdmin(admin.ModelAdmin):
    list_display = ('camera', 'people_count', 'vehicle_count', 'updated_at')

@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'camera', 'risk_score', 'status', 'start_time')
    list_filter = ('status', 'camera')

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('visitor_uuid', 'visit_count', 'first_seen', 'last_seen')
