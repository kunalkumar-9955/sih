"""
SIH26002 — PM Gati Shakti, FOIS Rail, & IWAI Waterway Transport Providers.

Ingests multimodal infrastructure statuses:
- PM Gati Shakti NMP road maintenance & weight restrictions
- FOIS Indian Railways freight yard availability & transshipment turnarounds
- IWAI NW-2 Brahmaputra navigable draft depths & river terminal operational windows
"""
from typing import Any, Dict, List, Tuple
from django.utils import timezone

from apps.ingestion.models import ProviderSourceType
from apps.ingestion.providers.base import BaseDataProvider


class GatiShaktiRoadProvider(BaseDataProvider):
    """
    PM Gati Shakti National Master Plan (NMP) Road Infrastructure Provider.
    """

    def __init__(self, is_mock_fallback: bool = False):
        super().__init__(
            source_code="GATI_SHAKTI_ROAD",
            source_name="PM Gati Shakti National Master Plan (MoRTH / PWD)",
            source_type=ProviderSourceType.ROAD,
            source_version="v2.4",
            base_url="https://gatishakti.gov.in/api/corridors/",
            is_mock_fallback=is_mock_fallback,
        )

    def fetch_raw_data(self, **kwargs) -> List[Dict[str, Any]]:
        return [
            {
                "corridor_code": "NH6_MEGHALAYA_BARAK",
                "road_name": "NH-6 National Highway",
                "status": "OPEN",
                "max_weight_tonnes": 40.0,
                "lane_count": 2,
                "is_monsoon_restricted": False,
                "active_maintenance_zones": 1,
            },
            {
                "corridor_code": "NH106_SHILLONG_BYPASS",
                "road_name": "Shillong Western Bypass",
                "status": "OPEN",
                "max_weight_tonnes": 45.0,
                "lane_count": 4,
                "is_monsoon_restricted": False,
                "active_maintenance_zones": 0,
            },
        ]

    def validate_schema(self, raw_record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        for k in ["corridor_code", "status", "max_weight_tonnes"]:
            if k not in raw_record:
                errors.append(f"Missing required road field '{k}'.")
        return len(errors) == 0, errors

    def normalize_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "corridor_code": raw_record["corridor_code"],
            "road_name": raw_record.get("road_name", ""),
            "status": raw_record["status"],
            "max_weight_tonnes": float(raw_record["max_weight_tonnes"]),
            "lane_count": int(raw_record.get("lane_count", 2)),
            "is_monsoon_restricted": bool(raw_record.get("is_monsoon_restricted", False)),
            "observation_time": timezone.now(),
            "provenance": {"provider": self.source_name, "version": self.source_version},
        }


class FOISRailwayProvider(BaseDataProvider):
    """
    Indian Railways FOIS (Freight Operations Information System) Provider.
    """

    def __init__(self, is_mock_fallback: bool = False):
        super().__init__(
            source_code="FOIS_RAIL",
            source_name="Indian Railways Freight Operations Information System (FOIS)",
            source_type=ProviderSourceType.RAIL,
            source_version="v4.2",
            base_url="https://fois.indianrail.gov.in/api/freight/",
            is_mock_fallback=is_mock_fallback,
        )

    def fetch_raw_data(self, **kwargs) -> List[Dict[str, Any]]:
        return [
            {
                "terminal_code": "GAU_RAIL_YARD",
                "terminal_name": "Guwahati Freight Yard",
                "operating_status": "OPERATIONAL",
                "rake_capacity_tonnes": 2400.0,
                "avg_transshipment_turnaround_hours": 2.5,
                "available_lines": 4,
            },
            {
                "terminal_code": "SILCHAR_GOODS",
                "terminal_name": "Silchar Goods Terminal",
                "operating_status": "OPERATIONAL",
                "rake_capacity_tonnes": 1800.0,
                "avg_transshipment_turnaround_hours": 3.0,
                "available_lines": 3,
            },
        ]

    def validate_schema(self, raw_record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        for k in ["terminal_code", "operating_status", "rake_capacity_tonnes"]:
            if k not in raw_record:
                errors.append(f"Missing required FOIS rail field '{k}'.")
        return len(errors) == 0, errors

    def normalize_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "terminal_code": raw_record["terminal_code"],
            "terminal_name": raw_record.get("terminal_name", ""),
            "operating_status": raw_record["operating_status"],
            "rake_capacity_tonnes": float(raw_record["rake_capacity_tonnes"]),
            "avg_transshipment_turnaround_hours": float(raw_record.get("avg_transshipment_turnaround_hours", 2.0)),
            "observation_time": timezone.now(),
            "provenance": {"provider": self.source_name, "version": self.source_version},
        }


class IWAIWaterwayProvider(BaseDataProvider):
    """
    Inland Waterways Authority of India (IWAI) National Waterway 2 (Brahmaputra) Provider.
    """

    def __init__(self, is_mock_fallback: bool = False):
        super().__init__(
            source_code="IWAI_WATERWAY",
            source_name="Inland Waterways Authority of India (NW-2 Brahmaputra)",
            source_type=ProviderSourceType.WATERWAY,
            source_version="v1.8",
            base_url="https://iwai.nic.in/api/nw2/",
            is_mock_fallback=is_mock_fallback,
        )

    def fetch_raw_data(self, **kwargs) -> List[Dict[str, Any]]:
        return [
            {
                "port_code": "PANDU_PORT_NW2",
                "port_name": "Pandu Port (Guwahati)",
                "water_level_stage_m": 48.2,
                "navigable_depth_m": 2.8,  # Minimum 2.0m required for standard cargo barge
                "operating_hours": "06:00-20:00",
                "is_navigable": True,
                "vessel_draft_limit_m": 2.2,
            },
            {
                "port_code": "DHUBRI_JETTY_NW2",
                "port_name": "Dhubri River Terminal",
                "water_level_stage_m": 28.5,
                "navigable_depth_m": 2.5,
                "operating_hours": "06:00-19:00",
                "is_navigable": True,
                "vessel_draft_limit_m": 2.0,
            },
        ]

    def validate_schema(self, raw_record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        for k in ["port_code", "navigable_depth_m", "is_navigable"]:
            if k not in raw_record:
                errors.append(f"Missing required IWAI field '{k}'.")

        depth = raw_record.get("navigable_depth_m")
        if depth is not None and depth < 0.0:
            errors.append(f"Invalid negative water depth: {depth}m")

        return len(errors) == 0, errors

    def normalize_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "port_code": raw_record["port_code"],
            "port_name": raw_record.get("port_name", ""),
            "water_level_stage_m": float(raw_record.get("water_level_stage_m", 0.0)),
            "navigable_depth_m": round(float(raw_record["navigable_depth_m"]), 2),
            "operating_hours": raw_record.get("operating_hours", "06:00-18:00"),
            "is_navigable": bool(raw_record["is_navigable"]),
            "vessel_draft_limit_m": float(raw_record.get("vessel_draft_limit_m", 1.8)),
            "observation_time": timezone.now(),
            "provenance": {"provider": self.source_name, "version": self.source_version},
        }
