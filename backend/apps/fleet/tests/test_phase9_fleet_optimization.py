"""
SIH26002 — Phase 9 Multi-Depot Fleet Optimization & Dynamic Consolidation Tests.
"""
from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.fleet.models import (
    CargoPriority,
    CargoStatus,
    CargoType,
    ConsolidationBundle,
    FreightLoad,
    OptimizationAssignment,
    OptimizationRun,
)
from apps.fleet.services.dynamic_consolidation_service import DynamicLoadConsolidationService
from apps.fleet.services.fleet_optimizer import MultiDepotFleetOptimizer
from apps.transport_graph.models import EdgeStatus, NodeType, TransportEdge, TransportMode, TransportNode
from apps.vehicles.models import FuelType, Vehicle, VehicleStatus, VehicleType

User = get_user_model()


@pytest.mark.django_db
class TestPhase9FleetOptimization:
    @pytest.fixture(autouse=True)
    def setup_fleet_and_demands(self):
        self.user = User.objects.create(
            email="fleet_tester@nerlogistics.gov.in",
            phone="+919876543001",
            first_name="Fleet",
            last_name="Tester",
        )

        self.depot_1 = TransportNode.objects.create(
            name="Guwahati Central Depot",
            node_type=NodeType.MULTIMODAL_HUB,
            geometry="POINT(91.73 26.18)",
            is_active=True,
        )
        self.depot_2 = TransportNode.objects.create(
            name="Tezpur Logistics Base",
            node_type=NodeType.LOCAL_HUB,
            geometry="POINT(92.79 26.63)",
            is_active=True,
        )
        self.dest_shillong = TransportNode.objects.create(
            name="Shillong Distribution Depot",
            node_type=NodeType.LOGISTICS_HUB,
            geometry="POINT(91.89 25.57)",
            is_active=True,
        )
        self.dest_silchar = TransportNode.objects.create(
            name="Silchar Forward Hub",
            node_type=NodeType.LOGISTICS_HUB,
            geometry="POINT(92.79 24.83)",
            is_active=True,
        )

        # Vehicles
        self.v1 = Vehicle.objects.create(
            owner=self.user,
            registration_number="AS-01-PH9-001",
            vehicle_type=VehicleType.HEAVY_TRUCK,
            capacity_kg=12000.0,
            capacity_cbm=35.0,
            fuel_type=FuelType.DIESEL,
            status=VehicleStatus.AVAILABLE,
            is_active=True,
        )
        self.v2 = Vehicle.objects.create(
            owner=self.user,
            registration_number="AS-01-PH9-002",
            vehicle_type=VehicleType.MEDIUM_TRUCK,
            capacity_kg=6000.0,
            capacity_cbm=18.0,
            fuel_type=FuelType.DIESEL,
            status=VehicleStatus.AVAILABLE,
            is_active=True,
        )

        # Freight demands
        self.load_1 = FreightLoad.objects.create(
            shipper=self.user,
            title="Consignment A - Cold Chain Medical",
            origin_node=self.depot_1,
            destination_node=self.dest_shillong,
            weight_kg=1200.0,
            volume_cbm=4.0,
            cargo_type=CargoType.COLD_CHAIN,
            priority=CargoPriority.URGENT,
            status=CargoStatus.AVAILABLE,
            pickup_window_start=timezone.now(),
            delivery_window_end=timezone.now() + timedelta(hours=12),
        )
        self.load_2 = FreightLoad.objects.create(
            shipper=self.user,
            title="Consignment B - General Provisions",
            origin_node=self.depot_1,
            destination_node=self.dest_silchar,
            weight_kg=2500.0,
            volume_cbm=8.0,
            cargo_type=CargoType.GENERAL,
            priority=CargoPriority.NORMAL,
            status=CargoStatus.AVAILABLE,
            pickup_window_start=timezone.now(),
            delivery_window_end=timezone.now() + timedelta(hours=24),
        )

    def test_multi_depot_fleet_optimizer_execution(self):
        res = MultiDepotFleetOptimizer.optimize(
            depot_ids=[str(self.depot_1.id)],
            load_ids=[str(self.load_1.id), str(self.load_2.id)],
            vehicle_ids=[str(self.v1.id), str(self.v2.id)],
            enable_consolidation=True,
            is_simulation=True,
        )

        assert res["success"] is True
        assert "run_id" in res
        assert "plan_comparison" in res
        comparison = res["plan_comparison"]
        assert "baseline_total_distance_km" in comparison
        assert "optimized_total_distance_km" in comparison
        assert "distance_improvement_pct" in comparison
        assert "cost_improvement_pct" in comparison

        # Ensure database records were created
        run = OptimizationRun.objects.get(id=res["run_id"])
        assert run.status == OptimizationRun.RunStatus.COMPLETED
        assert run.is_simulation is True

    def test_dynamic_load_consolidation_service(self):
        # Create a 3rd load compatible with load_1 (same origin & dest)
        load_3 = FreightLoad.objects.create(
            shipper=self.user,
            title="Consignment C - Pharma Vaccines",
            origin_node=self.depot_1,
            destination_node=self.dest_shillong,
            weight_kg=800.0,
            volume_cbm=2.5,
            cargo_type=CargoType.COLD_CHAIN,
            priority=CargoPriority.URGENT,
            status=CargoStatus.AVAILABLE,
            pickup_window_start=timezone.now(),
            delivery_window_end=timezone.now() + timedelta(hours=14),
        )

        res = DynamicLoadConsolidationService.consolidate_compatible_shipments(
            shipment_ids=[str(self.load_1.id), str(load_3.id)],
            max_detour_km=30.0,
            is_simulation=True,
        )

        assert res["success"] is True
        assert res["bundles_count"] >= 1
        bundle = res["bundles"][0]
        assert bundle["loads_count"] >= 2
        assert bundle["expected_utilization_pct"] > 0
        assert bundle["estimated_cost_savings_inr"] > 0
        assert bundle["is_estimate"] is True
        assert "reasons" in bundle
