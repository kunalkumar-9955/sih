"""
SIH26002 — Cold-Chain IoT Telemetry, Alert Hysteresis & Sensor Simulator.

Provides:
- Ingestion of temperature, humidity, and battery IoT telemetry
- Multi-reading hysteresis filtering to suppress transient sensor noise
- Automated thermal variance warning and critical excursion alert generation
- Scenario simulator (NORMAL, TEMPERATURE_RISE, CRITICAL_BREACH, SENSOR_OFFLINE, RECOVERY)
"""
import logging
from typing import Dict, Any, Optional
from django.utils import timezone

from apps.shipments.models import (
    ColdChainSensor,
    ColdChainReading,
    ColdChainAlert,
    ColdChainStatus,
)

logger = logging.getLogger(__name__)


class ColdChainTrackingService:
    """
    Ingests IoT telemetry and detects temperature breaches with hysteresis logic.
    """

    @classmethod
    def record_reading(
        cls,
        sensor: ColdChainSensor,
        temperature: float,
        humidity: float = 60.0,
        battery: float = 90.0,
        is_simulation: bool = True,
    ) -> Dict[str, Any]:
        """
        Records a telemetry packet and applies threshold evaluation.
        """
        now = timezone.now()
        reading = ColdChainReading.objects.create(
            sensor=sensor,
            document=sensor.document,
            temperature=temperature,
            humidity=humidity,
            battery_percentage=battery,
            is_simulation=is_simulation,
            recorded_at=now,
        )

        sensor.current_temperature = temperature
        sensor.current_humidity = humidity
        sensor.battery_percentage = battery
        sensor.last_reading_at = now

        # Thresholds
        min_t = sensor.min_threshold
        max_t = sensor.max_threshold

        alert_created = False
        new_status = ColdChainStatus.NORMAL

        if temperature > max_t or temperature < min_t:
            # Check previous reading to apply hysteresis filter
            prev_readings = list(
                ColdChainReading.objects.filter(sensor=sensor)
                .exclude(id=reading.id)
                .order_by("-recorded_at")[:2]
            )

            # Severe breach threshold (> 4.0°C deviation)
            is_severe = (temperature > max_t + 4.0) or (temperature < min_t - 4.0)

            if is_severe:
                new_status = ColdChainStatus.CRITICAL
                severity = "CRITICAL"
                msg = f"Severe thermal excursion: {temperature:.1f}°C breaches safe limit [{min_t}°C - {max_t}°C]."
                ColdChainAlert.objects.create(
                    sensor=sensor,
                    document=sensor.document,
                    severity=severity,
                    reading_value=temperature,
                    threshold_value=max_t if temperature > max_t else min_t,
                    message=msg,
                )
                alert_created = True
            else:
                # Moderate breach: check persistence
                has_consecutive_breach = False
                if prev_readings and (prev_readings[0].temperature > max_t or prev_readings[0].temperature < min_t):
                    has_consecutive_breach = True

                if has_consecutive_breach:
                    new_status = ColdChainStatus.CRITICAL
                    severity = "CRITICAL"
                    msg = f"Persistent thermal variance confirmed: {temperature:.1f}°C over multiple readings."
                    ColdChainAlert.objects.create(
                        sensor=sensor,
                        document=sensor.document,
                        severity=severity,
                        reading_value=temperature,
                        threshold_value=max_t if temperature > max_t else min_t,
                        message=msg,
                    )
                    alert_created = True
                else:
                    new_status = ColdChainStatus.WARNING
        else:
            # Within safe range: auto-resolve open alerts
            new_status = ColdChainStatus.NORMAL
            open_alerts = ColdChainAlert.objects.filter(sensor=sensor, is_resolved=False)
            if open_alerts.exists():
                open_alerts.update(is_resolved=True, resolved_at=now)

        sensor.status = new_status
        sensor.save(update_fields=["current_temperature", "current_humidity", "battery_percentage", "status", "last_reading_at"])

        return {
            "reading_id": str(reading.id),
            "sensor_code": sensor.sensor_code,
            "status": sensor.status,
            "temperature": temperature,
            "humidity": humidity,
            "battery_percentage": battery,
            "alert_created": alert_created,
            "is_simulation": is_simulation,
            "recorded_at": now.isoformat(),
        }


class ColdChainSimulator:
    """
    Generates deterministic simulated IoT sensor streams for demonstration.
    """

    @classmethod
    def run_scenario(cls, sensor: ColdChainSensor, scenario: str) -> Dict[str, Any]:
        scenario = scenario.upper().strip()

        if scenario == "NORMAL":
            return ColdChainTrackingService.record_reading(
                sensor=sensor,
                temperature=4.1,
                humidity=62.0,
                battery=94.0,
                is_simulation=True,
            )

        elif scenario == "TEMPERATURE_RISE":
            # Exceeds max 8.0°C by slight margin
            return ColdChainTrackingService.record_reading(
                sensor=sensor,
                temperature=9.4,
                humidity=68.0,
                battery=91.0,
                is_simulation=True,
            )

        elif scenario == "CRITICAL_BREACH":
            # Exceeds 8.0°C severely (14.2°C)
            return ColdChainTrackingService.record_reading(
                sensor=sensor,
                temperature=14.2,
                humidity=75.0,
                battery=88.0,
                is_simulation=True,
            )

        elif scenario == "SENSOR_OFFLINE":
            sensor.status = ColdChainStatus.SENSOR_OFFLINE
            sensor.save(update_fields=["status"])
            return {
                "sensor_code": sensor.sensor_code,
                "status": ColdChainStatus.SENSOR_OFFLINE,
                "temperature": sensor.current_temperature,
                "alert_created": False,
                "is_simulation": True,
                "message": "Sensor signal dropped (simulated battery/telemetry failure).",
            }

        elif scenario == "RECOVERY":
            # Back to safe range
            return ColdChainTrackingService.record_reading(
                sensor=sensor,
                temperature=3.8,
                humidity=60.0,
                battery=87.0,
                is_simulation=True,
            )

        else:
            return ColdChainTrackingService.record_reading(
                sensor=sensor,
                temperature=4.0,
                humidity=60.0,
                battery=90.0,
                is_simulation=True,
            )
