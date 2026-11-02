"""
SIH26002 — Seed Hazard Demo Data Management Command.

Generates realistic terrain, weather, and incident histories for the 38 edges
in the Guwahati–Shillong–Silchar multimodal network.
Clearly labeled: DATASET_TYPE = SYNTHETIC_DEMO.
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.hazards.models import (
    HazardIncident,
    HazardSeverity,
    TerrainFeature,
    WeatherObservation,
)
from apps.hazards.services.prediction_service import HazardPredictionService
from apps.transport_graph.models import TransportEdge, TransportMode


class Command(BaseCommand):
    help = "Seeds synthetic terrain, weather observations, and incident records for the corridor"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Hazard Demo Data for Guwahati–Shillong–Silchar Corridor..."))

        edges = TransportEdge.objects.select_related("source_node", "target_node").all()
        if not edges.exists():
            self.stdout.write(self.style.WARNING("No transport edges found. Run 'python manage.py seed_corridor' first."))
            return

        now = timezone.now()
        created_terrain = 0
        created_weather = 0
        created_incidents = 0

        for e in edges:
            src_name = e.source_node.name.lower()
            tgt_name = e.target_node.name.lower()
            mode = e.mode

            # Determine geological archetype
            is_high_risk_pass = "sonapur" in src_name or "sonapur" in tgt_name or "ladrymbai" in src_name or "ladrymbai" in tgt_name
            is_mountain_shillong = "shillong" in src_name or "shillong" in tgt_name or "jowai" in src_name or "jowai" in tgt_name
            is_water = mode in (TransportMode.WATER, TransportMode.WATERWAY)
            is_rail = mode == TransportMode.RAIL

            if is_high_risk_pass:
                # Sonapur / NH-6 steep landslide & mudflow choke point
                slope = 32.5
                elev = 1150.0
                elev_delta = 320.0
                soil_type = "shale_clay"
                soil_sat = 0.88
                fault_dist = 4.5
                rain_24h = 135.0
                rain_6h = 65.0
                rain_1h = 24.0
                incidents = [
                    (HazardIncident.IncidentType.LANDSLIDE, HazardSeverity.CRITICAL, "Major slope mudflow blocking single-lane NH-6 corridor"),
                    (HazardIncident.IncidentType.ROCKFALL, HazardSeverity.HIGH, "Boulders dislodged onto roadway following heavy rain"),
                ]
            elif is_mountain_shillong:
                # Meghalaya plateau mountain climb (NH-6 / NH-40)
                slope = 18.0
                elev = 1450.0
                elev_delta = 450.0
                soil_type = "clay_loam"
                soil_sat = 0.65
                fault_dist = 12.0
                rain_24h = 68.0
                rain_6h = 28.0
                rain_1h = 9.0
                incidents = [
                    (HazardIncident.IncidentType.LANDSLIDE, HazardSeverity.MODERATE, "Minor soil slip on cut-slope shoulder"),
                ]
            elif is_water:
                # Waterway (Brahmaputra / Barak rivers)
                slope = 0.5
                elev = 45.0
                elev_delta = 5.0
                soil_type = "riverine_alluvium"
                soil_sat = 0.95
                fault_dist = 30.0
                rain_24h = 42.0
                rain_6h = 14.0
                rain_1h = 4.0
                incidents = []
            elif is_rail:
                # Lumding-Badarpur Railway alignment
                slope = 8.5
                elev = 420.0
                elev_delta = 180.0
                soil_type = "stabilized_ballast"
                soil_sat = 0.40
                fault_dist = 18.0
                rain_24h = 35.0
                rain_6h = 12.0
                rain_1h = 3.0
                incidents = []
            else:
                # Valley / plains road
                slope = 3.5
                elev = 95.0
                elev_delta = 15.0
                soil_type = "sandy_loam"
                soil_sat = 0.35
                fault_dist = 35.0
                rain_24h = 22.0
                rain_6h = 8.0
                rain_1h = 2.0
                incidents = []

            # 1. TerrainFeature (OneToOne)
            tf, _ = TerrainFeature.objects.update_or_create(
                edge=e,
                defaults={
                    "slope_deg": slope,
                    "elevation_m": elev,
                    "elevation_change_m": elev_delta,
                    "soil_type": soil_type,
                    "soil_saturation": soil_sat,
                    "drainage_density": 1.5 if slope > 15.0 else 0.8,
                    "fault_line_distance_km": fault_dist,
                    "source": "SYNTHETIC_DEMO",
                },
            )
            created_terrain += 1

            # 2. WeatherObservation
            WeatherObservation.objects.create(
                edge=e,
                rainfall_mm=round(rain_1h * 0.7, 1),
                rainfall_1h_mm=rain_1h,
                rainfall_6h_mm=rain_6h,
                rainfall_24h_mm=rain_24h,
                temperature_c=22.0 if elev < 500 else 17.5,
                humidity_pct=88.0 if rain_24h > 40.0 else 68.0,
                precipitation_probability=min(1.0, round(rain_24h / 100.0, 2)),
                observation_time=now,
                source="SYNTHETIC_DEMO",
                is_forecast=False,
            )
            created_weather += 1

            # 3. Incidents
            for inc_type, inc_sev, inc_desc in incidents:
                HazardIncident.objects.create(
                    edge=e,
                    incident_type=inc_type,
                    severity=inc_sev,
                    description=inc_desc,
                    occurred_at=now - timedelta(days=2),
                    rainfall_context_mm=rain_24h,
                    source=HazardIncident.IncidentSource.SYNTHETIC_DEMO,
                    status=HazardIncident.IncidentStatus.VERIFIED,
                )
                created_incidents += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded demo data: {created_terrain} terrain features, "
                f"{created_weather} weather observations, {created_incidents} incidents."
            )
        )
