"""
SIH26002 — Development Settings
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "backend", "testserver", "*"]

# Development: allow all origins
CORS_ALLOW_ALL_ORIGINS = True

# Show SQL queries in development
INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405

MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

# Simpler email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable rate limiting in development
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}
