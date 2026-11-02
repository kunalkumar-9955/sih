"""
SIH26002 — Weather Ingestion Abstraction & Providers.

Provides an extensible meteorological data provider interface for real-time
observations, cumulative rainfall calculations, and forecasting.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.utils import timezone

from apps.transport_graph.models import TransportEdge


@dataclass
class WeatherData:
    """
    Standard meteorological reading.
    """
    rainfall_mm: float
    rainfall_1h_mm: float
    rainfall_6h_mm: float
    rainfall_24h_mm: float
    precipitation_probability: float
    observation_time: datetime
    source: str
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    is_forecast: bool = False

    def to_dict(self) -> dict:
        return {
            "rainfall_mm": self.rainfall_mm,
            "rainfall_1h_mm": self.rainfall_1h_mm,
            "rainfall_6h_mm": self.rainfall_6h_mm,
            "rainfall_24h_mm": self.rainfall_24h_mm,
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "precipitation_probability": self.precipitation_probability,
            "observation_time": self.observation_time.isoformat(),
            "source": self.source,
            "is_forecast": self.is_forecast,
        }


class WeatherProvider(ABC):
    """
    Abstract meteorological provider.
    """
    @abstractmethod
    def get_weather_for_edge(self, edge: TransportEdge) -> WeatherData:
        """Retrieves weather context for a specific transport edge."""
        pass

    @abstractmethod
    def get_weather_for_location(self, lat: float, lon: float) -> WeatherData:
        """Retrieves weather readings for arbitrary coordinate."""
        pass


class MockWeatherProvider(WeatherProvider):
    """
    Deterministic mock provider for development and scenario simulation.
    Allows specifying rain intensity by corridor sector or edge ID.
    """
    def __init__(self, default_rain_24h: float = 15.0, rain_overrides: Optional[dict] = None):
        self.default_rain_24h = default_rain_24h
        self.rain_overrides = rain_overrides or {}

    def get_weather_for_edge(self, edge: TransportEdge) -> WeatherData:
        rain_24h = self.rain_overrides.get(str(edge.id), self.default_rain_24h)
        rain_6h = round(rain_24h * 0.40, 1)
        rain_1h = round(rain_24h * 0.15, 1)
        precip_prob = min(1.0, round(rain_24h / 100.0, 2))

        return WeatherData(
            rainfall_mm=round(rain_1h * 0.8, 1),
            rainfall_1h_mm=rain_1h,
            rainfall_6h_mm=rain_6h,
            rainfall_24h_mm=rain_24h,
            temperature_c=22.5,
            humidity_pct=85.0 if rain_24h > 20.0 else 65.0,
            precipitation_probability=precip_prob,
            observation_time=timezone.now(),
            source="SYNTHETIC_DEMO",
            is_forecast=False,
        )

    def get_weather_for_location(self, lat: float, lon: float) -> WeatherData:
        return WeatherData(
            rainfall_mm=2.0,
            rainfall_1h_mm=2.5,
            rainfall_6h_mm=10.0,
            rainfall_24h_mm=self.default_rain_24h,
            temperature_c=22.0,
            humidity_pct=75.0,
            precipitation_probability=0.35,
            observation_time=timezone.now(),
            source="SYNTHETIC_DEMO",
            is_forecast=False,
        )
