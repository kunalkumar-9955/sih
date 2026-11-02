"""
SIH26002 — Hazard Data Quality & Validation Utilities.

Performs deterministic integrity audits on weather observations, terrain attributes,
historical incidents, and feature vectors before training and inference.
Rule: Never silently fix bad data — log and flag issues.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.utils import timezone

logger = logging.getLogger("sih.hazards.data_quality")


@dataclass
class DataQualityReport:
    """
    Summary outcome of data quality inspection.
    """
    is_clean: bool
    total_records: int
    error_count: int
    warning_count: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    inspected_at: datetime = field(default_factory=timezone.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_clean": self.is_clean,
            "total_records": self.total_records,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "inspected_at": self.inspected_at.isoformat(),
        }


class DataQualityValidator:
    """
    Validates weather, terrain, and ML feature representations.
    """

    @staticmethod
    def validate_weather(data: Dict[str, Any]) -> List[str]:
        """Validates single weather measurement."""
        issues = []
        # Rainfall bounds
        rain_24h = data.get("rainfall_24h_mm")
        if rain_24h is not None:
            if rain_24h < 0.0:
                issues.append(f"Negative 24h rainfall: {rain_24h}mm")
            elif rain_24h > 1500.0:
                issues.append(f"Unphysically high 24h rainfall: {rain_24h}mm (exceeds global records)")

        rain_1h = data.get("rainfall_1h_mm")
        if rain_1h is not None:
            if rain_1h < 0.0:
                issues.append(f"Negative 1h rainfall: {rain_1h}mm")
            elif rain_24h is not None and rain_1h > rain_24h:
                issues.append(f"1h rainfall ({rain_1h}mm) exceeds 24h accumulated rainfall ({rain_24h}mm)")

        # Temperature
        temp = data.get("temperature_c")
        if temp is not None and (temp < -40.0 or temp > 60.0):
            issues.append(f"Physically implausible surface temperature: {temp}°C")

        # Humidity
        humidity = data.get("humidity_pct")
        if humidity is not None and (humidity < 0.0 or humidity > 100.0):
            issues.append(f"Relative humidity out of bounds [0, 100]: {humidity}%")

        # Timestamp check
        obs_time = data.get("observation_time")
        if obs_time and isinstance(obs_time, datetime):
            if obs_time > timezone.now() + timedelta(hours=1):
                issues.append(f"Observation timestamp is in future: {obs_time}")

        return issues

    @staticmethod
    def validate_terrain(data: Dict[str, Any]) -> List[str]:
        """Validates single terrain feature set."""
        issues = []
        slope = data.get("slope_deg")
        if slope is not None:
            if not (0.0 <= slope <= 90.0):
                issues.append(f"Slope angle {slope}° out of bounds [0.0, 90.0]")

        elev = data.get("elevation_m")
        if elev is not None and (elev < -100.0 or elev > 8848.0):
            issues.append(f"Elevation {elev}m is physically implausible")

        soil_sat = data.get("soil_saturation")
        if soil_sat is not None and not (0.0 <= soil_sat <= 1.0):
            issues.append(f"Soil saturation index {soil_sat} out of bounds [0.0, 1.0]")

        fault_dist = data.get("fault_line_distance_km")
        if fault_dist is not None and fault_dist < 0.0:
            issues.append(f"Negative fault line distance: {fault_dist} km")

        return issues

    @classmethod
    def audit_records(
        cls,
        weather_records: Optional[List[Dict[str, Any]]] = None,
        terrain_records: Optional[List[Dict[str, Any]]] = None,
    ) -> DataQualityReport:
        """Audits sets of weather and terrain observations."""
        errors: List[str] = []
        warnings: List[str] = []
        total = 0

        if weather_records:
            total += len(weather_records)
            for w in weather_records:
                w_issues = cls.validate_weather(w)
                errors.extend(w_issues)

        if terrain_records:
            total += len(terrain_records)
            for t in terrain_records:
                t_issues = cls.validate_terrain(t)
                errors.extend(t_issues)

        is_clean = len(errors) == 0
        if not is_clean:
            logger.warning(f"Data quality audit found {len(errors)} issues across {total} records.")

        return DataQualityReport(
            is_clean=is_clean,
            total_records=total,
            error_count=len(errors),
            warning_count=len(warnings),
            errors=errors,
            warnings=warnings,
        )
