import os
import sys

OSGEO4W = r"C:\Users\Kunal Kumar\AppData\Local\Programs\OSGeo4W"
GDAL_BIN = os.path.join(OSGEO4W, "bin")

if os.path.isdir(GDAL_BIN):
    os.add_dll_directory(GDAL_BIN)

os.environ.setdefault("GDAL_LIBRARY_PATH", os.path.join(GDAL_BIN, "gdal311.dll"))
os.environ.setdefault("GDAL_DATA", os.path.join(OSGEO4W, "apps", "gdal", "share", "gdal"))
os.environ.setdefault("GDAL_DRIVER_PATH", os.path.join(OSGEO4W, "apps", "gdal", "lib", "gdalplugins"))

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
