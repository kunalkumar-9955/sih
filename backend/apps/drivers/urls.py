"""NorthLink / SIH26002 — Drivers URLs."""
from django.urls import path
from . import views
from . import dashboard_views

urlpatterns = [
    path("profile/", views.DriverProfileView.as_view(), name="driver-profile"),
    path("dashboard/", dashboard_views.DriverDashboardView.as_view(), name="driver-dashboard"),
    path("trip/", dashboard_views.DriverTripView.as_view(), name="driver-trip"),
    path("shipments/", dashboard_views.DriverShipmentsView.as_view(), name="driver-shipments"),
    path("alerts/", dashboard_views.DriverAlertsView.as_view(), name="driver-alerts"),
    path("sos/", dashboard_views.DriverSOSView.as_view(), name="driver-sos"),
]
