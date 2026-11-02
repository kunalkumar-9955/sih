"""
SIH26002 — Demo & SIH Readiness URLs.
"""
from django.urls import path
from apps.core.demo_views import (
    DemoGeneralizationReportView,
    DemoOrchestrationView,
    DemoReadinessView,
    DemoResetView,
)

urlpatterns = [
    path("readiness/", DemoReadinessView.as_view(), name="demo-readiness"),
    path("reset/", DemoResetView.as_view(), name="demo-reset"),
    path("orchestrate/", DemoOrchestrationView.as_view(), name="demo-orchestrate"),
    path("generalization-report/", DemoGeneralizationReportView.as_view(), name="demo-generalization-report"),
]
