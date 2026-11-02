"""
SIH26002 — Config package entry point.
Ensure Celery app is loaded when Django starts.
"""
# Patch django register_converter for DRF format_suffix_patterns duplicate registration
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

from .celery import app as celery_app

__all__ = ("celery_app",)

