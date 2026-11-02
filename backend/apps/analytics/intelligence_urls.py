"""
SIH26002 — Operational Intelligence URLs.
"""
from django.urls import path

from apps.analytics.intelligence_views import (
    AccessibilityIntelligenceAPIView,
    CorridorHealthView,
    DemoScenarioOrchestrationView,
    ETAIntelligenceView,
    ExplainableRecommendationsView,
    NetworkOperationalSummaryView,
)

urlpatterns = [
    path("network/", NetworkOperationalSummaryView.as_view(), name="intelligence-network"),
    path("corridors/", CorridorHealthView.as_view(), name="intelligence-corridors"),
    path("recommendations/", ExplainableRecommendationsView.as_view(), name="intelligence-recommendations"),
    path("eta/", ETAIntelligenceView.as_view(), name="intelligence-eta-list"),
    path("eta/predict/", ETAIntelligenceView.as_view(), name="intelligence-eta-predict"),
    path("accessibility/", AccessibilityIntelligenceAPIView.as_view(), name="intelligence-accessibility"),
    path("demo-scenario/", DemoScenarioOrchestrationView.as_view(), name="intelligence-demo-scenario"),
]
