"""
SIH26002 — Checkposts URLs.
"""
from django.urls import path
from apps.checkposts.views import CheckpostListView, CheckpostVerificationView

urlpatterns = [
    path("list/", CheckpostListView.as_view(), name="checkpost-list"),
    path("verify/", CheckpostVerificationView.as_view(), name="checkpost-verify"),
    path("events/", CheckpostVerificationView.as_view(), name="checkpost-events"),
]
