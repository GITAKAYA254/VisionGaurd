from django.urls import path
from . import views

urlpatterns = [
    path("", views.notification_list, name="notification_list"),
    path("<int:pk>/", views.notification_detail, name="notification_detail"),
    path("<int:pk>/live/", views.notification_view_live, name="notification_view_live"),
    path("<int:pk>/read/", views.mark_as_read, name="notification_mark_read"),
    path("read-all/", views.mark_all_read, name="notification_mark_all_read"),
    path("api/live/", views.live_notifications_api, name="live_notifications_api"),
]
