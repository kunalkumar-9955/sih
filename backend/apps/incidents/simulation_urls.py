"""
SIH26002 — Disruption Simulation URLs.
"""
from django.urls import path

from apps.incidents.simulation_views import (
    SimulationComparisonView,
    SimulationDetailView,
    SimulationQuickEvaluateView,
    SimulationRunView,
)

urlpatterns = [
    path("", SimulationRunView.as_view(), name="simulation-list-create"),
    path("quick-evaluate/", SimulationQuickEvaluateView.as_view(), name="simulation-quick-evaluate"),
    path("<uuid:pk>/", SimulationDetailView.as_view(), name="simulation-detail"),
    path("<uuid:pk>/comparison/", SimulationComparisonView.as_view(), name="simulation-comparison"),
]
