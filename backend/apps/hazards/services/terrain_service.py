"""
SIH26002 — Terrain Feature Abstraction & Providers.

Provides topographic, geological, elevation, and soil saturation data per corridor edge.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from apps.transport_graph.models import TransportEdge


@dataclass
class TerrainData:
    """
    Standard terrain attributes for an edge.
    """
    slope_deg: float
    elevation_m: float
    elevation_change_m: float
    soil_type: str
    soil_saturation: float
    drainage_density: float
    fault_line_distance_km: float
    source: str = "SYNTHETIC_DEMO"

    def to_dict(self) -> dict:
        return {
            "slope_deg": self.slope_deg,
            "elevation_m": self.elevation_m,
            "elevation_change_m": self.elevation_change_m,
            "soil_type": self.soil_type,
            "soil_saturation": self.soil_saturation,
            "drainage_density": self.drainage_density,
            "fault_line_distance_km": self.fault_line_distance_km,
            "source": self.source,
        }


class TerrainProvider(ABC):
    """
    Abstract interface for terrain characterization.
    """
    @abstractmethod
    def get_terrain_for_edge(self, edge: TransportEdge) -> TerrainData:
        pass


class MockTerrainProvider(TerrainProvider):
    """
    Deterministic terrain provider for the North Eastern Region corridor.
    Infers realistic elevation and slope characteristics from connecting nodes.
    """
    def __init__(self, terrain_overrides: Optional[dict] = None):
        self.terrain_overrides = terrain_overrides or {}

    def get_terrain_for_edge(self, edge: TransportEdge) -> TerrainData:
        if str(edge.id) in self.terrain_overrides:
            return self.terrain_overrides[str(edge.id)]

        # Infer approximate slope from endpoints if elevations are present
        src_elev = getattr(edge.source_node, "elevation_m", 100.0) or 100.0
        tgt_elev = getattr(edge.target_node, "elevation_m", 100.0) or 100.0
        elev_delta = abs(tgt_elev - src_elev)
        mean_elev = (src_elev + tgt_elev) / 2.0

        dist = max(100.0, float(edge.distance_m or 1000.0))
        gradient_ratio = min(1.0, elev_delta / dist)
        import math
        slope_deg = round(math.degrees(math.atan(gradient_ratio)), 1)
        # Cap slope to realistic road limits unless high-relief mountain pass
        if mean_elev > 800.0:
            slope_deg = max(12.0, slope_deg)

        # Higher elevation / mountain slopes have rocky/clay soils with varying saturation
        is_mountain = mean_elev > 500.0 or slope_deg > 15.0
        soil_type = "clay_loam" if is_mountain else "alluvial_silt"
        soil_sat = 0.45 if is_mountain else 0.25
        fault_dist = 6.0 if is_mountain else 25.0

        return TerrainData(
            slope_deg=slope_deg,
            elevation_m=round(mean_elev, 1),
            elevation_change_m=round(elev_delta, 1),
            soil_type=soil_type,
            soil_saturation=soil_sat,
            drainage_density=1.8 if is_mountain else 0.9,
            fault_line_distance_km=fault_dist,
            source="SYNTHETIC_DEMO",
        )
