"""
SIH26002 — ASGI config (for WebSocket support in Phase 5+)
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

application = get_asgi_application()
