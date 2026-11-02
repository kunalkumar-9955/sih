"""
SIH26002 — Marketplace URLs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.marketplace.views import (
    MarketplaceListingViewSet,
    FreightBidViewSet,
    MultimodalOptionsView,
    SmsFallbackView,
    IvrFallbackView,
)

router = DefaultRouter()
router.register(r"listings", MarketplaceListingViewSet, basename="marketplace-listings")
router.register(r"bids", FreightBidViewSet, basename="marketplace-bids")

urlpatterns = [
    path("", include(router.urls)),
    path("multimodal-options/", MultimodalOptionsView.as_view(), name="marketplace-multimodal-options"),
    path("fallback/sms/", SmsFallbackView.as_view(), name="marketplace-fallback-sms"),
    path("fallback/ivr/", IvrFallbackView.as_view(), name="marketplace-fallback-ivr"),
]
