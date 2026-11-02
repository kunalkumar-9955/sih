"""
SIH26002 — Fleet & Automated Matching URLs.
Wired under: /api/v1/fleet/
"""
from django.urls import path

from apps.fleet.views import (
    BatchMatchingRecommendView,
    DisasterModeActivateView,
    DisasterModeResetView,
    FleetEmergenciesListView,
    FleetEmergencyActionView,
    FleetOverviewView,
    FreightLoadDetailView,
    FreightLoadListCreateView,
    LoadCandidatesView,
    LoadConsolidationListView,
    LoadMatchExecuteView,
    VehicleAvailabilityListView,
)

app_name = "fleet"

urlpatterns = [
    # Freight Demands & Loads
    path("loads/", FreightLoadListCreateView.as_view(), name="load-list-create"),
    path("loads/<uuid:pk>/", FreightLoadDetailView.as_view(), name="load-detail"),
    path("loads/<uuid:pk>/candidates/", LoadCandidatesView.as_view(), name="load-candidates"),
    path("loads/<uuid:pk>/match/", LoadMatchExecuteView.as_view(), name="load-match"),

    # Automated Matching & Consolidation
    path("matching/recommend/", BatchMatchingRecommendView.as_view(), name="matching-recommend"),
    path("consolidations/", LoadConsolidationListView.as_view(), name="load-consolidations"),

    # Fleet & Vehicle Observability
    path("vehicles/availability/", VehicleAvailabilityListView.as_view(), name="vehicle-availability"),
    path("overview/", FleetOverviewView.as_view(), name="fleet-overview"),

    # Emergency Operations & Distress Rescue Triage
    path("emergencies/", FleetEmergenciesListView.as_view(), name="fleet-emergencies"),
    path("emergencies/<uuid:pk>/action/", FleetEmergencyActionView.as_view(), name="fleet-emergency-action"),

    # Disaster Fleet Mode Escalation
    path("disaster-mode/", DisasterModeActivateView.as_view(), name="disaster-mode-activate"),
    path("disaster-mode/reset/", DisasterModeResetView.as_view(), name="disaster-mode-reset"),
]
