from django.contrib import admin
from .models import Resident


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "house_number", "enrollment_status", "is_active", "date_registered")
    list_filter = ("enrollment_status", "is_active")
    search_fields = ("full_name", "house_number", "phone_number")
