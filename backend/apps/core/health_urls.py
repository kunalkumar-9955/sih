"""
SIH26002 — Health check URL configuration.
Mounted at /api/v1/health/
"""
from django.urls import path

from . import health_views

urlpatterns = [
    path("", health_views.HealthView.as_view(), name="health"),
    path("db/", health_views.DatabaseHealthView.as_view(), name="health-db"),
    path("redis/", health_views.RedisHealthView.as_view(), name="health-redis"),
    path("detailed/", health_views.DetailedHealthView.as_view(), name="health-detailed"),
]

