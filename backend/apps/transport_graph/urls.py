"""
SIH26002 — Transport graph URLs.
"""
from django.urls import path

from . import views

urlpatterns = [
    path("nodes/", views.TransportNodeListView.as_view(), name="transport-node-list"),
    path("nodes/<uuid:pk>/", views.TransportNodeDetailView.as_view(), name="transport-node-detail"),
    path("edges/", views.TransportEdgeListView.as_view(), name="transport-edge-list"),
    path("edges/<uuid:pk>/", views.TransportEdgeDetailView.as_view(), name="transport-edge-detail"),
    path("edges/<uuid:pk>/status/", views.TransportEdgeStatusUpdateView.as_view(), name="transport-edge-status"),
    path("graph/", views.TransportGraphDumpView.as_view(), name="transport-graph-dump"),
    path("accessibility/", views.AccessibilityIntelligenceView.as_view(), name="corridor-accessibility"),
]

