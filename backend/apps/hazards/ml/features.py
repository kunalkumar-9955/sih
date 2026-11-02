"""
SIH26002 — Hazard Feature Engineering Pipeline.

Extracts, imputes, and standardizes multi-source feature vectors for each transport edge:
- Topographic & Terrain indicators (slope, elevation, gradient delta)
- Meteorological context (instantaneous intensity, 1h/6h/24h accumulated rainfall)
- Historical disruption counts (total and recent incidents)
- Geological & network parameters (soil saturation, fault proximity, edge length)
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class FeatureDefinition:
    name: str
    dtype: str
    default_value: float
    description: str


FEATURE_DEFINITIONS: List[FeatureDefinition] = [
    FeatureDefinition("slope_deg", "float", 5.0, "Average terrain gradient slope in degrees"),
    FeatureDefinition("elevation_m", "float", 150.0, "Mean elevation above sea level (meters)"),
    FeatureDefinition("elevation_change_m", "float", 20.0, "Total elevation delta across edge (meters)"),
    FeatureDefinition("soil_saturation", "float", 0.30, "Soil pore-water saturation index [0.0 - 1.0]"),
    FeatureDefinition("drainage_density", "float", 1.0, "Drainage stream channel density index"),
    FeatureDefinition("fault_line_distance_km", "float", 20.0, "Proximity distance to geological fault line (km)"),
    FeatureDefinition("rainfall_1h_mm", "float", 0.0, "Immediate 1-hour rainfall accumulation (mm)"),
    FeatureDefinition("rainfall_6h_mm", "float", 0.0, "6-hour cumulative rainfall (mm)"),
    FeatureDefinition("rainfall_24h_mm", "float", 0.0, "24-hour cumulative antecedent rainfall (mm)"),
    FeatureDefinition("rainfall_intensity_ratio", "float", 0.0, "Ratio of 1h intensity to total 24h precipitation"),
    FeatureDefinition("precipitation_probability", "float", 0.1, "Precipitation probability [0.0 - 1.0]"),
    FeatureDefinition("historical_incident_count", "float", 0.0, "Total historical incidents recorded on this segment"),
    FeatureDefinition("recent_incident_count", "float", 0.0, "Incidents recorded within the past 30 days"),
    FeatureDefinition("edge_length_km", "float", 10.0, "Length of the transport segment (km)"),
    FeatureDefinition("is_mountain_corridor", "float", 0.0, "Binary indicator (1 if slope > 12 deg or elev > 500m)"),
]

FEATURE_NAMES: List[str] = [f.name for f in FEATURE_DEFINITIONS]


class HazardFeatureExtractor:
    """
    Constructs deterministic tabular feature vectors from raw entities.
    """

    @classmethod
    def extract_from_raw(
        cls,
        terrain: Optional[Dict[str, Any]] = None,
        weather: Optional[Dict[str, Any]] = None,
        incident_stats: Optional[Dict[str, Any]] = None,
        edge_stats: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Extracts named feature dictionary with safe defaults and missing-value imputation.
        """
        terrain = terrain or {}
        weather = weather or {}
        incident_stats = incident_stats or {}
        edge_stats = edge_stats or {}

        # Terrain
        slope = float(terrain.get("slope_deg", 5.0) or 5.0)
        elevation = float(terrain.get("elevation_m", 150.0) or 150.0)
        elev_change = float(terrain.get("elevation_change_m", 20.0) or 20.0)
        soil_sat = float(terrain.get("soil_saturation", 0.30) or 0.30)
        drainage = float(terrain.get("drainage_density", 1.0) or 1.0)
        fault_dist = float(terrain.get("fault_line_distance_km", 20.0) or 20.0)

        # Weather
        rain_1h = float(weather.get("rainfall_1h_mm", 0.0) or 0.0)
        rain_6h = float(weather.get("rainfall_6h_mm", 0.0) or 0.0)
        rain_24h = float(weather.get("rainfall_24h_mm", 0.0) or 0.0)
        precip_prob = float(weather.get("precipitation_probability", 0.0) or 0.0)

        # Derived intensity
        intensity_ratio = (rain_1h / max(1.0, rain_24h)) if rain_24h > 0.0 else 0.0

        # Incidents
        hist_incidents = float(incident_stats.get("total_count", 0.0) or 0.0)
        recent_incidents = float(incident_stats.get("recent_count", 0.0) or 0.0)

        # Edge stats
        length_km = float(edge_stats.get("distance_m", 10000.0) or 10000.0) / 1000.0
        is_mountain = 1.0 if (slope >= 12.0 or elevation >= 500.0) else 0.0

        return {
            "slope_deg": slope,
            "elevation_m": elevation,
            "elevation_change_m": elev_change,
            "soil_saturation": soil_sat,
            "drainage_density": drainage,
            "fault_line_distance_km": fault_dist,
            "rainfall_1h_mm": rain_1h,
            "rainfall_6h_mm": rain_6h,
            "rainfall_24h_mm": rain_24h,
            "rainfall_intensity_ratio": round(intensity_ratio, 3),
            "precipitation_probability": precip_prob,
            "historical_incident_count": hist_incidents,
            "recent_incident_count": recent_incidents,
            "edge_length_km": round(length_km, 2),
            "is_mountain_corridor": is_mountain,
        }

    @classmethod
    def to_array(cls, feature_dict: Dict[str, float]) -> np.ndarray:
        """Converts feature dictionary to ordered numpy vector."""
        return np.array([feature_dict.get(k, 0.0) for k in FEATURE_NAMES], dtype=np.float32)

    @classmethod
    def get_feature_names(cls) -> List[str]:
        return list(FEATURE_NAMES)
