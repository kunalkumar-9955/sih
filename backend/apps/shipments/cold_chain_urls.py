"""
SIH26002 — Cold Chain IoT URLs.
"""
from django.urls import path
from apps.shipments.views import (
    ColdChainReadingView,
    ColdChainShipmentView,
    ColdChainAlertsListView,
    ColdChainSimulateView,
)

urlpatterns = [
    path("readings/", ColdChainReadingView.as_view(), name="cold-chain-readings-direct"),
    path("shipments/<str:pk>/", ColdChainShipmentView.as_view(), name="cold-chain-shipment-direct"),
    path("alerts/", ColdChainAlertsListView.as_view(), name="cold-chain-alerts-direct"),
    path("simulate/", ColdChainSimulateView.as_view(), name="cold-chain-simulate-direct"),
]
