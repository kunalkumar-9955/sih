"""
SIH26002 — Low Connectivity Fallback URLs.
"""
from django.urls import path
from apps.marketplace.views import SmsFallbackView, IvrFallbackView

urlpatterns = [
    path("sms/", SmsFallbackView.as_view(), name="fallback-sms"),
    path("ivr/", IvrFallbackView.as_view(), name="fallback-ivr"),
]
