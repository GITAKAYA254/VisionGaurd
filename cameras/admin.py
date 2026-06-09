from django.contrib import admin
from .models import Camera

@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ('name', 'location_name', 'status', 'is_active')
    list_filter = ('status', 'is_active')
    search_fields = ('name', 'location_name')
