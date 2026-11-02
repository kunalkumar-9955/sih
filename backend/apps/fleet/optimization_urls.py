"""
SIH26002 — Optimization URLs.
"""
from django.urls import path

from apps.fleet.optimization_views import (
    ConsolidationBundleListView,
    ConsolidationOptimizationView,
    FleetOptimizationView,
    OptimizationRunDetailView,
    OptimizationRunListView,
)
from apps.routing.views import MultimodalRouteOptimizationView

urlpatterns = [
    path("fleet/", FleetOptimizationView.as_view(), name="optimization-fleet"),
    path("consolidation/", ConsolidationOptimizationView.as_view(), name="optimization-consolidation"),
    path("routes/", MultimodalRouteOptimizationView.as_view(), name="optimization-routes"),
    path("runs/", OptimizationRunListView.as_view(), name="optimization-runs-list"),
    path("runs/<uuid:pk>/", OptimizationRunDetailView.as_view(), name="optimization-run-detail"),
    path("bundles/", ConsolidationBundleListView.as_view(), name="optimization-bundles-list"),
]
