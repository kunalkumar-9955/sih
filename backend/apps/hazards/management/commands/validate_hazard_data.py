"""
SIH26002 — Validate Hazard Data Management Command.

Executes data quality inspection across all weather, terrain, and edge records.
"""
from django.core.management.base import BaseCommand

from apps.hazards.models import TerrainFeature, WeatherObservation
from apps.hazards.services.data_quality import DataQualityValidator


class Command(BaseCommand):
    help = "Validates data quality across weather, terrain, and feature data"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Auditing hazard meteorological & terrain data quality..."))

        weather_records = list(
            WeatherObservation.objects.values(
                "rainfall_24h_mm", "rainfall_1h_mm", "temperature_c", "humidity_pct", "observation_time"
            )
        )
        terrain_records = list(
            TerrainFeature.objects.values(
                "slope_deg", "elevation_m", "soil_saturation", "fault_line_distance_km"
            )
        )

        report = DataQualityValidator.audit_records(
            weather_records=weather_records,
            terrain_records=terrain_records,
        )

        self.stdout.write(f"Audited Records: {report.total_records}")
        self.stdout.write(f"Errors Found:    {report.error_count}")
        self.stdout.write(f"Warnings Found:  {report.warning_count}")

        if report.is_clean:
            self.stdout.write(self.style.SUCCESS("Data Quality Check PASSED: No integrity violations detected."))
        else:
            self.stdout.write(self.style.ERROR("Data Quality Issues Found:"))
            for err in report.errors[:10]:
                self.stdout.write(f"  - {err}")
