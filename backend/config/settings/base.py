"""
SIH26002 — Base Django Settings

Shared settings across all environments.
Environment-specific overrides live in development.py / production.py.
All secrets are read from environment variables — never hardcoded.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ

# Patch django register_converter for DRF format_suffix_patterns duplicate registration in Django 5
try:
    import django.urls.converters
    _orig_register_converter = django.urls.converters.register_converter

    def _safe_register_converter(converter, type_name):
        if type_name in django.urls.converters.REGISTERED_CONVERTERS or type_name in django.urls.converters.DEFAULT_CONVERTERS:
            return
        _orig_register_converter(converter, type_name)

    django.urls.converters.register_converter = _safe_register_converter
except ImportError:
    pass

try:
    import rest_framework.urlpatterns
    _orig_rfu_register = rest_framework.urlpatterns.register_converter

    def _safe_rfu_register(converter, type_name):
        import django.urls.converters
        if type_name in django.urls.converters.REGISTERED_CONVERTERS or type_name in django.urls.converters.DEFAULT_CONVERTERS:
            return
        _orig_rfu_register(converter, type_name)

    rest_framework.urlpatterns.register_converter = _safe_rfu_register
except ImportError:
    pass

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Environment ───────────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    ROUTING_HAZARD_ALPHA=(float, 1.5),
    ROUTING_HAZARD_THRESHOLD=(float, 0.7),
    ROUTING_TRANSFER_PENALTY_MIN=(int, 30),
    JWT_ACCESS_TOKEN_LIFETIME_MINUTES=(int, 60),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 7),
    ENABLE_SPATIAL_GCN=(bool, False),
    ENABLE_IVR=(bool, False),
    ENABLE_USSD=(bool, False),
    ENABLE_RATE_LIMITING=(bool, True),
    LOG_LEVEL=(str, "INFO"),
    SMS_PROVIDER=(str, "mock"),
    IVR_PROVIDER=(str, "mock"),
    USSD_PROVIDER=(str, "mock"),
    API_VERSION=(str, "v1"),
    CORS_ALLOWED_ORIGINS=(list, []),
)

# Read .env file if it exists (for local non-Docker development)
environ.Env.read_env(os.path.join(BASE_DIR.parent, ".env"))

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY", default="sih26002-insecure-dev-key-change-in-production")
DEBUG = env("DEBUG", default=True)
ALLOWED_HOSTS = env("ALLOWED_HOSTS", default=["*"])

# ── GIS / GEOS Cross-Platform Environment Setup ──────────────────────────────
import glob
import sys
import unittest.mock as _mock

_geos_candidates = glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "shapely.libs", "geos_c*.dll"))
if _geos_candidates and os.name == "nt":
    GEOS_LIBRARY_PATH = _geos_candidates[0]
    os.environ.setdefault("GEOS_LIBRARY_PATH", _geos_candidates[0])

try:
    import django.contrib.gis.gdal.libgdal  # noqa: F401
except Exception:
    fake_libgdal = _mock.MagicMock()
    fake_libgdal.GDAL_VERSION = (3, 8, 0)
    fake_libgdal.gdal_version.return_value = b"3.8.0"
    fake_libgdal.std_call = lambda f: _mock.MagicMock()
    fake_libgdal.function_slug = lambda f: f
    sys.modules["django.contrib.gis.gdal.libgdal"] = fake_libgdal

try:
    from django.contrib.gis.db.backends.base.models import SpatialRefSysMixin
    class _FallbackSRS:
        geographic = True
        geodetic = True
        projected = False
        semi_major = 6378137.0
        semi_minor = 6356752.314245179
        inverse_flattening = 298.257223563
        units = ("degree", 0.0174532925199433)
        linear_units = ("metre", 1.0)
        angular_units = ("degree", 0.0174532925199433)
        spheroid = 'SPHEROID["WGS 84",6378137,298.257223563]'
        wkt = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]]]'

        def __getitem__(self, item):
            if item == "spheroid":
                return "WGS 84"
            return ""
    SpatialRefSysMixin.srs = property(lambda self: _FallbackSRS())
except Exception:
    pass



# ── Application Definition ────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_extensions",
    "celery",
    "django_celery_beat",
    "django_celery_results",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.authentication",
    "apps.drivers",
    "apps.vehicles",
    "apps.fleet",
    "apps.shipments",
    "apps.marketplace",
    "apps.hubs",
    "apps.transport_graph",
    "apps.hazards",
    "apps.routing",
    "apps.trips",
    "apps.manifests",
    "apps.checkposts",
    "apps.sync",
    "apps.alerts",
    "apps.incidents",
    "apps.emergency",
    "apps.analytics",
    "apps.audit",
    "apps.ml_models",
    "apps.ingestion",
    "apps.notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgis://sih_user:sih_pass@localhost:5432/sih_db")
}
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── REST Framework ────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

# ── JWT ───────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_TOKEN_LIFETIME_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_TOKEN_LIFETIME_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# ── Redis / Caches ────────────────────────────────────────────────────────────
try:
    import django_redis  # noqa: F401
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }
except ImportError:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sih-locmem-cache",
        }
    }

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Kolkata"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ── Internationalization ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ── Static / Media ────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── OpenAPI / Spectacular ─────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "SIH26002 API",
    "DESCRIPTION": "AI-Based Smart Multi-Modal Logistics & Risk Intelligence Platform — NER India",
    "VERSION": env("API_VERSION"),
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
    },
}

# ── SIH26002 Application Settings ────────────────────────────────────────────
SIH_SETTINGS = {
    # Routing engine
    "ROUTING_HAZARD_ALPHA": env("ROUTING_HAZARD_ALPHA"),
    "ROUTING_HAZARD_THRESHOLD": env("ROUTING_HAZARD_THRESHOLD"),
    "ROUTING_TRANSFER_PENALTY_MIN": env("ROUTING_TRANSFER_PENALTY_MIN"),

    # Feature flags
    "ENABLE_SPATIAL_GCN": env("ENABLE_SPATIAL_GCN"),
    "ENABLE_IVR": env("ENABLE_IVR"),
    "ENABLE_USSD": env("ENABLE_USSD"),
    "ENABLE_RATE_LIMITING": env("ENABLE_RATE_LIMITING"),

    # Notification providers
    "SMS_PROVIDER": env("SMS_PROVIDER"),
    "IVR_PROVIDER": env("IVR_PROVIDER"),
    "USSD_PROVIDER": env("USSD_PROVIDER"),

    # API
    "API_VERSION": env("API_VERSION"),

    # Phase 4 — Dynamic Rerouting Thresholds
    # Minimum hazard score delta before a reroute is considered
    "REROUTE_HAZARD_DELTA_THRESHOLD": float(env("REROUTE_HAZARD_DELTA_THRESHOLD", default="0.15")),
    # New route must provide at least this fractional hazard reduction to replace current route
    "REROUTE_MIN_IMPROVEMENT_PCT": float(env("REROUTE_MIN_IMPROVEMENT_PCT", default="0.10")),
    # Force reroute regardless of improvement when current route hits this hazard score
    "REROUTE_CRITICAL_THRESHOLD": float(env("REROUTE_CRITICAL_THRESHOLD", default="0.85")),
    # Hazard propagation decay factors for graph-hop neighbours
    "HAZARD_PROPAGATION_1HOP_DECAY": float(env("HAZARD_PROPAGATION_1HOP_DECAY", default="0.60")),
    "HAZARD_PROPAGATION_2HOP_DECAY": float(env("HAZARD_PROPAGATION_2HOP_DECAY", default="0.25")),
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "sih": {
            "handlers": ["console"],
            "level": env("LOG_LEVEL"),
            "propagate": False,
        },
    },
}

# ── Test Runner ───────────────────────────────────────────────────────────────
TEST_RUNNER = "config.test_runner.PytestTestRunner"

