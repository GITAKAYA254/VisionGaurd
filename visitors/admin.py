from django.contrib import admin
from .models import Visitor


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ("visitor_uuid", "visit_count", "is_known", "first_seen", "last_seen")
    list_filter = ("is_known",)
