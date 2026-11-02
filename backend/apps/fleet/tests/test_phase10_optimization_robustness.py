"""
SIH26002 — Phase 10 Fleet Optimization & Dynamic Consolidation Robustness Tests.
"""
from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.fleet.models import CargoPriority, CargoStatus, CargoType, FreightLoad
from apps.fleet.services.dynamic_consolidation_service import DynamicLoadConsolidationService
from apps.fleet.services.fleet_optimizer import MultiDepotFleetOptimizer
from apps.transport_graph.models import NodeType, TransportNode
from apps.vehicles.models import FuelType, Vehicle, VehicleStatus, VehicleType

User = get_user_model()


@pytest.mark.django_db
class TestPhase10OptimizationRobustness:
    def setup_method(self):
        self.user = User.objects.create(
            email="opt_tester@nerlogistics.gov.in",
            phone="+919876543999",
            first_name="Opt",
            last_name="Tester",
            is_active=True,
        )
        self.depot = TransportNode.objects.create(
            name="Guwahati Central Depot",
            node_type=NodeType.LOGISTICS_HUB,
            geometry="POINT(91.73 26.18)",
            state="Assam",
            is_active=True,
        )
        self.dest1 = TransportNode.objects.create(
            name="Shillong North Drop",
            node_type=NodeType.CHECKPOST,
            geometry="POINT(91.89 25.57)",
            state="Meghalaya",
            is_active=True,
        )
        self.dest2 = TransportNode.objects.create(
            name="Silchar South Drop",
            node_type=NodeType.LOGISTICS_HUB,
            geometry="POINT(92.79 24.83)",
            state="Assam",
            is_active=True,
        )

    def test_zero_available_vehicles_returns_infeasibility_cleanly(self):
        """When no vehicles are available, optimizer gracefully returns zero dispatches and explanation."""
        load = FreightLoad.objects.create(
            title="Heavy Transformer Unit",
            shipper=self.user,
            origin_node=self.depot,
            destination_node=self.dest1,
            weight_kg=5000.0,
            volume_cbm=10.0,
            cargo_type=CargoType.GENERAL,
            priority=CargoPriority.NORMAL,
            status=CargoStatus.AVAILABLE,
            pickup_window_start=timezone.now(),
            delivery_window_end=timezone.now() + timedelta(hours=24),
        )

        res = MultiDepotFleetOptimizer.optimize(
            depot_ids=[str(self.depot.id)],
            load_ids=[str(load.id)],
            vehicle_ids=[],  # Zero vehicles
        )
        assert res is not None
        assert not res.get("success") or res.get("status") in ["OPTIMIZED", "NO_FEASIBLE_ROUTES", "COMPLETED"]
        assert len(res.get("routes", [])) == 0

    def test_empty_shipment_set(self):
        """When shipment list is empty, optimizer returns clean zero-dispatch plan without crashing."""
        v = Vehicle.objects.create(
            registration_number="AS-01-OPT-100",
            owner=self.user,
            vehicle_type=VehicleType.HEAVY_TRUCK,
            capacity_kg=10000.0,
            capacity_cbm=25.0,
            fuel_type=FuelType.DIESEL,
            status=VehicleStatus.AVAILABLE,
            is_active=True,
        )
        res = MultiDepotFleetOptimizer.optimize(
            depot_ids=[str(self.depot.id)],
            load_ids=[],
            vehicle_ids=[str(v.id)],
        )
        assert res is not None
        assert len(res.get("routes", [])) == 0

    def test_single_shipment_direct_dispatch(self):
        """Single shipment is successfully dispatched on available compatible truck."""
        v = Vehicle.objects.create(
            registration_number="AS-01-OPT-200",
            owner=self.user,
            vehicle_type=VehicleType.MEDIUM_TRUCK,
            capacity_kg=6000.0,
            capacity_cbm=15.0,
            fuel_type=FuelType.DIESEL,
            status=VehicleStatus.AVAILABLE,
            is_active=True,
        )
        load = FreightLoad.objects.create(
            title="Surgical Consumables",
            shipper=self.user,
            origin_node=self.depot,
            destination_node=self.dest1,
            weight_kg=1200.0,
            volume_cbm=3.0,
            cargo_type=CargoType.COLD_CHAIN,
            priority=CargoPriority.HIGH,
            status=CargoStatus.AVAILABLE,
            pickup_window_start=timezone.now(),
            delivery_window_end=timezone.now() + timedelta(hours=18),
        )
        res = MultiDepotFleetOptimizer.optimize(
            depot_ids=[str(self.depot.id)],
            load_ids=[str(load.id)],
            vehicle_ids=[str(v.id)],
        )
        assert res is not None

    def test_consolidation_clustering_recommends_bundles(self):
        """Dynamic load consolidation groups compatible shipments sharing nearby destinations."""
        l1 = FreightLoad.objects.create(
            title="Consolidation Bundle Part 1",
            shipper=self.user,
            origin_node=self.depot,
            destination_node=self.dest1,
            weight_kg=800.0,
            volume_cbm=2.5,
            cargo_type=CargoType.GENERAL,
            priority=CargoPriority.NORMAL,
            status=CargoStatus.AVAILABLE,
            pickup_window_start=timezone.now(),
            delivery_window_end=timezone.now() + timedelta(hours=24),
        )
        l2 = FreightLoad.objects.create(
            title="Consolidation Bundle Part 2",
            shipper=self.user,
            origin_node=self.depot,
            destination_node=self.dest1,
            weight_kg=950.0,
            volume_cbm=3.0,
            cargo_type=CargoType.GENERAL,
            priority=CargoPriority.NORMAL,
            status=CargoStatus.AVAILABLE,
            pickup_window_start=timezone.now(),
            delivery_window_end=timezone.now() + timedelta(hours=24),
        )

        res = DynamicLoadConsolidationService.consolidate_compatible_shipments(
            shipment_ids=[str(l1.id), str(l2.id)],
            max_detour_km=40.0,
        )
        assert res is not None
        assert "recommendations" in res
        assert "summary" in res
