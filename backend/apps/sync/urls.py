"""
SIH26002 — Sync URLs.
"""
from django.urls import path

from apps.sync.views import (
    EmergencySOSView,
    OfflineGraphDownloadView,
    OfflineGraphVersionView,
    SyncBatchEventView,
    SyncStatusView,
)

app_name = "sync"

urlpatterns = [
    path("graph/version/", OfflineGraphVersionView.as_view(), name="graph-version"),
    path("graph/download/", OfflineGraphDownloadView.as_view(), name="graph-download"),
    path("events/batch/", SyncBatchEventView.as_view(), name="sync-batch-events"),
    path("status/", SyncStatusView.as_view(), name="sync-status"),
    path("sos/", EmergencySOSView.as_view(), name="emergency-sos"),
]
