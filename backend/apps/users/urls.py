"""
SIH26002 — Users URL configuration.
"""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.AdminUserListView.as_view(), name="user-list"),
    path("profile/", views.UserProfileView.as_view(), name="user-profile"),
]
