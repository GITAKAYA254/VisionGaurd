from django.db import models
from cameras.models import Camera


class Notification(models.Model):
    SEVERITY_INFO = "INFO"
    SEVERITY_WARNING = "WARNING"
    SEVERITY_HIGH = "HIGH"

    SEVERITY_CHOICES = [
        (SEVERITY_INFO, "Info"),
        (SEVERITY_WARNING, "Warning"),
        (SEVERITY_HIGH, "High"),
    ]

    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default=SEVERITY_INFO)
    camera = models.ForeignKey(
        Camera,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    snapshot = models.ImageField(
        upload_to="notification_snapshots/",
        null=True,
        blank=True,
    )
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def live_url(self):
        if self.camera_id:
            return f"/monitor/?camera_id={self.camera_id}"
        return "/monitor/"

    def __str__(self):
        return f"[{self.severity}] {self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
