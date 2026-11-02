"""
SIH26002 — Trips URLs.
"""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.TripListCreateView.as_view(), name="trip-list-create"),
    path("<uuid:pk>/", views.TripDetailView.as_view(), name="trip-detail"),
    path("<uuid:pk>/status/", views.TripStatusUpdateView.as_view(), name="trip-status-update"),
    path("<uuid:pk>/location/", views.TripLocationUpdateView.as_view(), name="trip-location-update"),
    # Phase 4: Dynamic Rerouting & Risk Intelligence
    path("<uuid:pk>/route-risk/", views.TripRouteRiskView.as_view(), name="trip-route-risk"),
    path("<uuid:pk>/recalculate-route/", views.TripRecalculateRouteView.as_view(), name="trip-recalculate-route"),
    path("<uuid:pk>/reroute-events/", views.TripRerouteEventListView.as_view(), name="trip-reroute-events"),
    path("<uuid:pk>/reroute-events/<uuid:event_id>/acknowledge/", views.TripRerouteAcknowledgeView.as_view(), name="trip-reroute-acknowledge"),
]
