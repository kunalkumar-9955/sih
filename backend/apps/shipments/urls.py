"""
SIH26002 — Shipments URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.shipments.views import (
    DigitalShipmentDocumentViewSet,
    ColdChainReadingView,
    ColdChainShipmentView,
    ColdChainAlertsListView,
    ColdChainSimulateView,
)

router = DefaultRouter()
router.register(r"documents", DigitalShipmentDocumentViewSet, basename="shipments-documents")

urlpatterns = [
    path("", include(router.urls)),
    path("<str:pk>/document/", DigitalShipmentDocumentViewSet.as_view({"get": "retrieve"}), name="shipment-document-detail"),
    path("<str:pk>/qr/", DigitalShipmentDocumentViewSet.as_view({"get": "qr"}), name="shipment-qr"),
    path("<str:pk>/tracking/", DigitalShipmentDocumentViewSet.as_view({"get": "tracking"}), name="shipment-tracking"),
    path("cold-chain/readings/", ColdChainReadingView.as_view(), name="cold-chain-readings"),
    path("cold-chain/shipments/<str:pk>/", ColdChainShipmentView.as_view(), name="cold-chain-shipment"),
    path("cold-chain/alerts/", ColdChainAlertsListView.as_view(), name="cold-chain-alerts"),
    path("cold-chain/simulate/", ColdChainSimulateView.as_view(), name="cold-chain-simulate"),
]
