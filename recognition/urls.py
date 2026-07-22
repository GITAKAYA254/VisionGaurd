from django.urls import path
from . import views

urlpatterns = [
    path("feed/", views.recognition_feed, name="recognition_feed"),
    path("api/events/", views.RecognitionEventAPI.as_view(), name="recognition_events_api"),
    path("api/embeddings/", views.EmbeddingsAPI.as_view(), name="recognition_embeddings_api"),
    path("api/stats/", views.RecognitionStatsAPI.as_view(), name="recognition_stats_api"),
]
