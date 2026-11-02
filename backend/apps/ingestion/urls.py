"""
SIH26002 — Ingestion & Scenario URLs.
"""
from django.urls import path

from apps.ingestion.views import (
    DataProviderListView,
    DemoScenarioActivateView,
    DemoScenarioListView,
    DemoScenarioResetView,
    FreshnessSummaryView,
    SyncAllProvidersView,
)

app_name = "ingestion"

urlpatterns = [
    path("providers/", DataProviderListView.as_view(), name="provider-list"),
    path("freshness/", FreshnessSummaryView.as_view(), name="freshness-summary"),
    path("sync-all/", SyncAllProvidersView.as_view(), name="sync-all-providers"),
    path("scenarios/", DemoScenarioListView.as_view(), name="scenario-list"),
    path("scenarios/activate/", DemoScenarioActivateView.as_view(), name="scenario-activate"),
    path("scenarios/reset/", DemoScenarioResetView.as_view(), name="scenario-reset"),
]
