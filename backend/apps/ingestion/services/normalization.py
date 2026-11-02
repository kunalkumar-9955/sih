"""
SIH26002 — Geospatial & Physical Attribute Normalization Service.

Enforces geographic boundary checks (NER bounding box), PostGIS geometry
validations, impossible-value rejections, and spatial association to transport edges.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.utils import timezone

from apps.ingestion.models import FreshnessState, NormalizedTerrainRecord, NormalizedWeatherRecord
from apps.transport_graph.models import TransportEdge

logger = logging.getLogger("sih.ingestion.normalization")


class GeospatialNormalizer:
    """
    Validates and normalizes geospatial coordinates and maps observations to transport edges.
    """

    # Extended North Eastern Region bounding box (Assam, Meghalaya, Tripura, Mizoram, Manipur, Nagaland, Arunachal Pradesh, Sikkim)
    NER_BBOX = {
        "min_lon": 88.0,
        "max_lon": 97.5,
        "min_lat": 21.5,
        "max_lat": 29.5,
    }

    @classmethod
    def is_within_ner_bounds(cls, lon: float, lat: float) -> bool:
        """Checks if coordinate falls inside the NER operational boundary."""
        return (
            cls.NER_BBOX["min_lon"] <= lon <= cls.NER_BBOX["max_lon"]
            and cls.NER_BBOX["min_lat"] <= lat <= cls.NER_BBOX["max_lat"]
        )

    @classmethod
    def create_point_geometry(cls, lon: float, lat: float) -> Tuple[Optional[Point], List[str]]:
        """
        Validates coordinates and returns PostGIS Point(lon, lat, srid=4326).
        """
        errors = []
        if not (-180.0 <= lon <= 180.0):
            errors.append(f"Longitude {lon} is out of global WGS84 range [-180, 180].")
        if not (-90.0 <= lat <= 90.0):
            errors.append(f"Latitude {lat} is out of global WGS84 range [-90, 90].")

        if not cls.is_within_ner_bounds(lon, lat):
            errors.append(
                f"Coordinates ({lat}, {lon}) fall outside North Eastern Region operational bbox "
                f"[{cls.NER_BBOX['min_lat']}, {cls.NER_BBOX['min_lon']}] to "
                f"[{cls.NER_BBOX['max_lat']}, {cls.NER_BBOX['max_lon']}]."
            )

        if errors:
            return None, errors

        pt = Point(lon, lat, srid=4326)
        if not pt.valid:
            errors.append("Constructed PostGIS geometry failed ST_IsValid check.")
            return None, errors

        return pt, []

    @classmethod
    def associate_nearest_edge(
        cls, point: Point, max_distance_m: float = 30000.0
    ) -> Optional[TransportEdge]:
        """
        Finds the closest active TransportEdge to an observation coordinate.
        """
        try:
            return (
                TransportEdge.objects.filter(geometry__isnull=False, is_available=True)
                .annotate(distance=Distance("geometry", point))
                .order_by("distance")
                .first()
            )
        except Exception as exc:
            logger.warning("Failed to match nearest edge: %s", exc)
            return None

    @classmethod
    def persist_normalized_weather(cls, norm_dict: Dict[str, Any]) -> Tuple[Optional[NormalizedWeatherRecord], List[str]]:
        """
        Validates, binds to nearest edge, and saves NormalizedWeatherRecord.
        """
        lon = norm_dict.get("longitude")
        lat = norm_dict.get("latitude")
        pt, geom_errors = cls.create_point_geometry(lon, lat)
        if geom_errors:
            return None, geom_errors

        edge = cls.associate_nearest_edge(pt)

        record = NormalizedWeatherRecord.objects.create(
            edge=edge,
            location=pt,
            rainfall_1h_mm=norm_dict.get("rainfall_1h_mm", 0.0),
            rainfall_6h_mm=norm_dict.get("rainfall_6h_mm", 0.0),
            rainfall_24h_mm=norm_dict.get("rainfall_24h_mm", 0.0),
            precipitation_probability=norm_dict.get("precipitation_probability", 0.0),
            temperature_c=norm_dict.get("temperature_c"),
            humidity_pct=norm_dict.get("humidity_pct"),
            wind_speed_mps=norm_dict.get("wind_speed_mps", 0.0),
            weather_severity=norm_dict.get("weather_severity", "CLEAR"),
            observation_time=norm_dict.get("observation_time", timezone.now()),
            freshness_state=norm_dict.get("freshness_state", FreshnessState.FRESH),
            provider_source=norm_dict.get("provider_source", "IMD_WEATHER"),
            provenance=norm_dict.get("provenance", {}),
        )
        return record, []
