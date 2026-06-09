from django.urls import path
from . import views

urlpatterns = [
    path('', views.CameraListView.as_view(), name='camera_list'),
    path('add/', views.CameraCreateView.as_view(), name='camera_add'),
    path('<int:pk>/edit/', views.CameraUpdateView.as_view(), name='camera_edit'),
    path('<int:pk>/delete/', views.CameraDeleteView.as_view(), name='camera_delete'),
    path('<int:camera_id>/feed/', views.camera_feed, name='camera_feed'),
]
