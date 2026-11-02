"""
Global pytest configuration and early runtime patching.
"""
import pytest
import os
import sys

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

