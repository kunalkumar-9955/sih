"""
SIH26002 — Main URL Configuration

API versioning: /api/v1/
OpenAPI docs:   /api/schema/
               /api/docs/
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

api_version = settings.SIH_SETTINGS.get("API_VERSION", "v1")

urlpatterns = [
    # Django admin (super admin only — localhost restricted in production)
    path("admin/", admin.site.urls),

    # API v1
    path(
        f"api/{api_version}/",
        include([
            path("auth/", include("apps.authentication.urls")),
            path("users/", include("apps.users.urls")),
            path("drivers/", include("apps.drivers.urls")),
            path("driver/", include("apps.drivers.urls")),
            path("vehicles/", include("apps.vehicles.urls")),
            path("fleet/", include("apps.fleet.urls")),
            path("marketplace/", include("apps.marketplace.urls")),
            path("shipments/", include("apps.shipments.urls")),
            path("cold-chain/", include("apps.shipments.cold_chain_urls")),
            path("fallback/", include("apps.marketplace.fallback_urls")),
            path("hubs/", include("apps.hubs.urls")),
            path("transport/", include("apps.transport_graph.urls")),
            path("hazards/", include("apps.hazards.urls")),
            path("routes/", include("apps.routing.urls")),
            path("trips/", include("apps.trips.urls")),
            path("manifests/", include("apps.manifests.urls")),
            path("checkposts/", include("apps.checkposts.urls")),
            path("sync/", include("apps.sync.urls")),
            path("ingestion/", include("apps.ingestion.urls")),
            path("alerts/", include("apps.alerts.urls")),
            path("incidents/", include("apps.incidents.urls")),
            path("admin-api/", include("apps.emergency.urls")),
            path("analytics/", include("apps.analytics.urls")),
            path("intelligence/", include("apps.analytics.intelligence_urls")),
            path("optimization/", include("apps.fleet.optimization_urls")),
            path("simulations/", include("apps.incidents.simulation_urls")),
            path("health/", include("apps.core.health_urls")),
            path("demo/", include("apps.core.demo_urls")),
        ]),
    ),

    # OpenAPI schema and documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Development extras
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
