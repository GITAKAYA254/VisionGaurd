from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    path('monitor/', views.live_monitor, name='monitor'),
    path('map/', views.estate_map, name='map'),
]
