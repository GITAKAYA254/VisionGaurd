from django.db import models

class Camera(models.Model):
    STATUS_CHOICES = (
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline'),
        ('MAINTENANCE', 'Maintenance'),
    )
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    stream_url = models.CharField(max_length=500, help_text="RTSP or HTTP stream URL")
    location_name = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OFFLINE')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.location_name}"
