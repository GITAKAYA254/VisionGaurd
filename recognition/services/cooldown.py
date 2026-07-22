import time
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from recognition.models import RecognitionEvent


class CooldownService:
    def __init__(self, seconds=None):
        self.seconds = seconds or int(getattr(settings, "RECOGNITION_COOLDOWN_SECONDS", 30))

    def is_active(self, cooldown_key):
        if not cooldown_key:
            return False
        cutoff = timezone.now() - timedelta(seconds=self.seconds)
        return RecognitionEvent.objects.filter(
            cooldown_key=cooldown_key,
            timestamp__gte=cutoff,
        ).exists()

    def mark(self, cooldown_key):
        return cooldown_key
