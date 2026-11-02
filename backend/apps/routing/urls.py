"""
SIH26002 — Routing URLs.
"""
from django.urls import path

from . import views

urlpatterns = [
    path("plan/", views.RoutePlanView.as_view(), name="route-plan"),
    path("compute/", views.RouteComputeView.as_view(), name="route-compute"),
    path("multimodal-optimize/", views.MultimodalRouteOptimizationView.as_view(), name="route-multimodal-optimize"),
    path("<uuid:pk>/", views.RouteDetailView.as_view(), name="route-detail"),
    path("", views.RouteListView.as_view(), name="route-list"),
]

