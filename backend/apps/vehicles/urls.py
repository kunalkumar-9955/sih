"""SIH26002 — Vehicles URLs."""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.VehicleListCreateView.as_view(), name="vehicle-list"),
    path("<uuid:pk>/", views.VehicleDetailView.as_view(), name="vehicle-detail"),
]
