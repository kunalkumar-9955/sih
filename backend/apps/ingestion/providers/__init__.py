"""
SIH26002 — Data Ingestion Providers.
"""
from apps.ingestion.providers.base import BaseDataProvider, QualityReport
from apps.ingestion.providers.incident_provider import StateDisasterIncidentProvider
from apps.ingestion.providers.terrain_provider import BhuvanTerrainProvider, SentinelInSARProvider
from apps.ingestion.providers.transport_provider import (
    FOISRailwayProvider,
    GatiShaktiRoadProvider,
    IWAIWaterwayProvider,
)
from apps.ingestion.providers.weather_provider import IMDWeatherProvider

__all__ = [
    "BaseDataProvider",
    "QualityReport",
    "IMDWeatherProvider",
    "BhuvanTerrainProvider",
    "SentinelInSARProvider",
    "GatiShaktiRoadProvider",
    "FOISRailwayProvider",
    "IWAIWaterwayProvider",
    "StateDisasterIncidentProvider",
]
