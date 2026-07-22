from django.db import models
from cameras.models import Camera

class Detection(models.Model):
    LABEL_CHOICES = (
        ('PERSON', 'Person'),
        ('VEHICLE', 'Vehicle'),
        ('BICYCLE', 'Bicycle'),
        ('MOTORCYCLE', 'Motorcycle'),
    )
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='detections')
    label = models.CharField(max_length=20, choices=LABEL_CHOICES)
    class_name = models.CharField(max_length=50, blank=True, help_text="YOLO class name, e.g. person, car")
    confidence = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    thumbnail = models.ImageField(upload_to='thumbnails/%Y/%m/%d/', blank=True, null=True)
    
    # Coordinates of the bounding box
    x_min = models.FloatField(blank=True, null=True)
    y_min = models.FloatField(blank=True, null=True)
    x_max = models.FloatField(blank=True, null=True)
    y_max = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"{self.label} at {self.camera.name} ({self.timestamp})"

class Incident(models.Model):
    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('INVESTIGATING', 'Investigating'),
        ('RESOLVED', 'Resolved'),
        ('FALSE_ALARM', 'False Alarm'),
    )
    camera = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    lead_detection = models.OneToOneField(Detection, on_delete=models.SET_NULL, null=True, related_name='incident_as_lead')
    risk_score = models.IntegerField(default=0) # 0-100
    summary = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    ai_analysis = models.TextField(blank=True, help_text="Guard Copilot generated summary")

    def __str__(self):
        return f"Incident {self.id} - {self.status} (Score: {self.risk_score})"

class CameraLiveStats(models.Model):
    camera = models.OneToOneField(Camera, on_delete=models.CASCADE, related_name="live_stats")
    people_count = models.PositiveIntegerField(default=0)
    vehicle_count = models.PositiveIntegerField(default=0)
    detected_names = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Live stats for {self.camera.name}: {self.people_count} people, {self.vehicle_count} vehicles"
