"""
SIH26002 — Transport Graph app config.
"""
from django.apps import AppConfig


class TransportGraphConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.transport_graph"
    verbose_name = "Transport Graph"
