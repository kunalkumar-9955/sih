"""
SIH26002 — Hazard Intelligence URL Routing.
"""
from django.urls import path

from .views import (
    DataQualityAuditView,
    HazardIncidentListView,
    HazardIncidentReportView,
    HazardModelRecordListView,
    HazardSegmentDetailView,
    HazardSegmentListView,
    HazardSummaryView,
)

app_name = "hazards"

urlpatterns = [
    path("", HazardSummaryView.as_view(), name="hazard-index"),
    path("summary/", HazardSummaryView.as_view(), name="hazard-summary"),
    path("segments/", HazardSegmentListView.as_view(), name="hazard-segments-list"),
    path("segments/<uuid:edge_id>/", HazardSegmentDetailView.as_view(), name="hazard-segment-detail"),
    path("report/", HazardIncidentReportView.as_view(), name="hazard-report"),
    path("incidents/", HazardIncidentListView.as_view(), name="hazard-incidents-list"),
    path("models/", HazardModelRecordListView.as_view(), name="hazard-models-list"),
    path("data-quality/", DataQualityAuditView.as_view(), name="hazard-data-quality"),
]
