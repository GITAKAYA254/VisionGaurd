from django.urls import path
from . import views

urlpatterns = [
    path("", views.VisitorListView.as_view(), name="visitor_list"),
    path("<int:pk>/", views.VisitorDetailView.as_view(), name="visitor_detail"),
]
