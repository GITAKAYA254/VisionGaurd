from django.contrib import admin
from .models import RecognitionEvent


@admin.register(RecognitionEvent)
class RecognitionEventAdmin(admin.ModelAdmin):
    list_display = ("person_type", "camera", "confidence", "timestamp")
    list_filter = ("person_type", "camera")
