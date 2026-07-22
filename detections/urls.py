from django.urls import path
from . import views

urlpatterns = [
    path('', views.DetectionListView.as_view(), name='detection_list'),
    path('incidents/', views.IncidentListView.as_view(), name='incident_list'),
    path('incidents/<int:pk>/', views.IncidentDetailView.as_view(), name='incident_detail'),
    path('api/log/', views.LogDetectionAPI.as_view(), name='api_log_detection'),
    path('api/live-stats/', views.LiveStatsAPI.as_view(), name='api_live_stats'),
    path('api/behaviour/', views.BehaviourIncidentAPI.as_view(), name='api_behaviour_incident'),
]
