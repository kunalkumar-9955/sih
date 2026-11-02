"""
SIH26002 — Spatial Query Helpers & PostGIS Utilities.

Provides high-performance spatial queries for finding nearest transport nodes,
edges, nearby multimodal hubs, and bounding-box subgraph filtering.
"""
from typing import List, Optional, Tuple

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point, Polygon
from django.db.models import QuerySet

from .models import NodeType, TransportEdge, TransportNode


def _norm_coords(lon: float, lat: float) -> Tuple[float, float]:
    """Detect and handle lat/lon ordering transparently."""
    if 10.0 <= lon <= 40.0 and 60.0 <= lat <= 105.0:
        return float(lat), float(lon)
    return float(lon), float(lat)


def create_point(longitude: float, latitude: float, srid: int = 4326) -> Point:
    """Helper to instantiate a WGS84 Point."""
    lon, lat = _norm_coords(longitude, latitude)
    return Point(lon, lat, srid=srid)


def find_nearest_node(
    longitude: float,
    latitude: float,
    node_types: Optional[List[str]] = None,
    max_distance_m: Optional[float] = None,
    active_only: bool = True,
) -> Optional[TransportNode]:
    """
    Finds the geographically closest transport node to the given coordinates.
    Utilizes PostGIS ST_Distance with spatial index.
    """
    ref_pt = create_point(longitude, latitude)
    qs = TransportNode.objects.all()

    if active_only:
        qs = qs.filter(is_active=True)

    if node_types:
        qs = qs.filter(node_type__in=node_types)

    qs = qs.annotate(distance=Distance("geometry", ref_pt)).order_by("distance")

    if max_distance_m is not None:
        # 1 degree lat is ~111,000 m
        deg_buffer = max_distance_m / 100000.0
        qs = qs.filter(
            geometry__dwithin=(ref_pt, deg_buffer)
        )

    return qs.first()


def find_nearest_edge(
    longitude: float,
    latitude: float,
    modes: Optional[List[str]] = None,
    active_only: bool = True,
) -> Optional[TransportEdge]:
    """
    Finds the geographically closest traversable edge to the given coordinates.
    """
    ref_pt = create_point(longitude, latitude)
    qs = TransportEdge.objects.filter(geometry__isnull=False).select_related("source_node", "target_node")

    if active_only:
        qs = qs.filter(is_available=True)

    if modes:
        qs = qs.filter(mode__in=modes)

    qs = qs.annotate(distance=Distance("geometry", ref_pt)).order_by("distance")
    return qs.first()


def find_nearby_hubs(
    longitude: float,
    latitude: float,
    radius_km: float = 50.0,
    limit: int = 10,
) -> List[TransportNode]:
    """
    Finds multimodal logistics hubs, rail yards, and river ports within radius.
    """
    ref_pt = create_point(longitude, latitude)
    hub_types = [
        NodeType.MULTIMODAL_HUB,
        NodeType.LOGISTICS_HUB,
        NodeType.RAIL_YARD,
        NodeType.WATERWAY_TERMINAL,
        NodeType.RIVER_JETTY,
        NodeType.PORT,
    ]

    deg_radius = radius_km / 111.0  # Approx degree conversion

    return list(
        TransportNode.objects.filter(
            is_active=True,
            node_type__in=hub_types,
            geometry__dwithin=(ref_pt, deg_radius),
        )
        .annotate(distance=Distance("geometry", ref_pt))
        .order_by("distance")[:limit]
    )


def get_corridor_bbox_polygon(
    origin: TransportNode,
    destination: TransportNode,
    buffer_deg: float = 0.6,
) -> Polygon:
    """
    Constructs a bounding box polygon encompassing origin and destination
    with safety margin buffer for regional subgraph extraction.
    """
    x1, y1 = origin.geometry.x, origin.geometry.y
    x2, y2 = destination.geometry.x, destination.geometry.y

    min_x = min(x1, x2) - buffer_deg
    max_x = max(x1, x2) + buffer_deg
    min_y = min(y1, y2) - buffer_deg
    max_y = max(y1, y2) + buffer_deg

    return Polygon.from_bbox((min_x, min_y, max_x, max_y))


def get_corridor_subgraph_edges(
    origin: Optional[TransportNode] = None,
    destination: Optional[TransportNode] = None,
    buffer_deg: float = 0.6,
    min_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lat: Optional[float] = None,
    max_lon: Optional[float] = None,
) -> QuerySet:
    """
    Extracts only the subset of transport edges within the corridor bounding box.
    Avoids loading full national networks into application memory for localized routing.
    """
    if min_lat is not None and min_lon is not None:
        min_x = min_lon
        max_x = max_lon if max_lon is not None else min_lon + buffer_deg
        min_y = min_lat
        max_y = max_lat if max_lat is not None else min_lat + buffer_deg
        bbox = Polygon.from_bbox((min_x, min_y, max_x, max_y))
    elif origin is not None and destination is not None:
        bbox = get_corridor_bbox_polygon(origin, destination, buffer_deg)
    else:
        raise ValueError("Either (origin, destination) or bbox bounds required.")

    return TransportEdge.objects.filter(
        is_available=True,
        source_node__geometry__within=bbox,
        target_node__geometry__within=bbox,
    ).select_related("source_node", "target_node")

