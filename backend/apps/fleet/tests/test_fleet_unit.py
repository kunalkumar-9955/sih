"""
Unit tests for Fleet Availability, Cost Optimization, Deadline Risk,
Priority Scoring, Load Consolidation, and Emergency Operations.
"""
from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.utils import timezone

from apps.fleet.models import (
    CargoPriority,
    CargoType,
    FreightLoad,
)
from apps.fleet.services.consolidation_service import LoadConsolidationEngine
from apps.fleet.services.cost_service import LogisticsCostOptimizer
from apps.fleet.services.deadline_service import DeadlineRiskStatus, DeliveryDeadlineIntelligence
from apps.fleet.services.disaster_mode_service import DisasterFleetModeService
from apps.fleet.services.eligibility_service import FleetAvailabilityEngine
from apps.fleet.services.emergency_service import EmergencyOperationsService
from apps.fleet.services.priority_engine import DeterministicPriorityEngine
from apps.sync.models import EmergencySOS, EmergencySOSStatus
from apps.transport_graph.models import TransportNode
from apps.vehicles.models import Vehicle, VehicleStatus, VehicleType

User = get_user_model()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        email="shipper@sih26002.local",
        password="ShipperPassword123!",
        role="SHIPPER",
    )


@pytest.fixture
def origin_node(db):
    return TransportNode.objects.create(
        name="Guwahati Dispatch Hub",
        short_code="GHY-HUB",
        state="Assam",
        geometry=Point(91.7362, 26.1445, srid=4326),
        node_type="MULTIMODAL_HUB",
    )


@pytest.fixture
def dest_node(db):
    return TransportNode.objects.create(
        name="Shillong Delivery Depot",
        short_code="SHL-DEPOT",
        state="Meghalaya",
        geometry=Point(91.8933, 25.5788, srid=4326),
        node_type="LOGISTICS_HUB",
    )


@pytest.fixture
def sample_vehicle(db, test_user):
    return Vehicle.objects.create(
        owner=test_user,
        registration_number="AS-01-FL-9988",
        vehicle_type=VehicleType.HEAVY_TRUCK,
        capacity_kg=16000.0,
        capacity_cbm=45.0,
        fuel_efficiency_kmpl=4.2,
        status=VehicleStatus.AVAILABLE,
        maintenance_status="HEALTHY",
        operating_region="NER_CORRIDOR",
    )


@pytest.mark.django_db
class TestFleetAvailabilityEngine:
    def test_eligible_vehicle_accepted(self, sample_vehicle, test_user, origin_node, dest_node):
        load = FreightLoad.objects.create(
            shipper=test_user,
            title="General Construction Freight",
            origin_node=origin_node,
            destination_node=dest_node,
            cargo_type=CargoType.GENERAL,
            weight_kg=12000.0,
            volume_cbm=30.0,
        )
        res = FleetAvailabilityEngine.evaluate_vehicle_eligibility(sample_vehicle, load)
        assert res["eligible"] is True
        assert "meets all payload" in res["reason"]

    def test_ineligible_on_weight_capacity_overflow(self, sample_vehicle, test_user, origin_node, dest_node):
        load = FreightLoad.objects.create(
            shipper=test_user,
            origin_node=origin_node,
            destination_node=dest_node,
            cargo_type=CargoType.GENERAL,
            weight_kg=22000.0,  # exceeds vehicle capacity 16000kg
        )
        res = FleetAvailabilityEngine.evaluate_vehicle_eligibility(sample_vehicle, load)
        assert res["eligible"] is False
        assert "INSUFFICIENT_WEIGHT_CAPACITY" in res["constraints"]

    def test_ineligible_on_critical_maintenance(self, sample_vehicle, test_user, origin_node, dest_node):
        sample_vehicle.maintenance_status = "CRITICAL"
        sample_vehicle.save()

        load = FreightLoad.objects.create(
            shipper=test_user,
            origin_node=origin_node,
            destination_node=dest_node,
            cargo_type=CargoType.GENERAL,
            weight_kg=5000.0,
        )
        res = FleetAvailabilityEngine.evaluate_vehicle_eligibility(sample_vehicle, load)
        assert res["eligible"] is False
        assert "MAINTENANCE_CRITICAL" in res["constraints"]

    def test_hazmat_restriction_on_light_truck(self, test_user, origin_node, dest_node):
        mini_truck = Vehicle.objects.create(
            owner=test_user,
            registration_number="AS-01-MN-1122",
            vehicle_type=VehicleType.MINI_TRUCK,
            capacity_kg=1200.0,
            status=VehicleStatus.AVAILABLE,
        )
        hazmat_load = FreightLoad.objects.create(
            shipper=test_user,
            origin_node=origin_node,
            destination_node=dest_node,
            cargo_type=CargoType.HAZMAT,
            weight_kg=800.0,
        )
        res = FleetAvailabilityEngine.evaluate_vehicle_eligibility(mini_truck, hazmat_load)
        assert res["eligible"] is False
        assert "HAZMAT_VEHICLE_RESTRICTION" in res["constraints"]


@pytest.mark.django_db
class TestLogisticsCostOptimizer:
    def test_cost_calculation_and_breakdown(self, sample_vehicle):
        cost_eval = LogisticsCostOptimizer.estimate_trip_cost(
            distance_km=100.0,
            vehicle=sample_vehicle,
            transfers_count=1,
            average_hazard_index=0.15,
        )
        assert cost_eval["is_estimate"] is True
        assert cost_eval["total_estimated_cost_inr"] > 0
        assert "fuel_cost_inr" in cost_eval["breakdown"]
        assert "toll_cost_inr" in cost_eval["breakdown"]
        assert "transfer_handling_inr" in cost_eval["breakdown"]

    def test_hazard_risk_surcharge_applied(self, sample_vehicle):
        low_hazard_cost = LogisticsCostOptimizer.estimate_trip_cost(
            distance_km=100.0,
            vehicle=sample_vehicle,
            average_hazard_index=0.10,
        )
        high_hazard_cost = LogisticsCostOptimizer.estimate_trip_cost(
            distance_km=100.0,
            vehicle=sample_vehicle,
            average_hazard_index=0.85,  # extreme monsoon hazard
        )
        assert high_hazard_cost["total_estimated_cost_inr"] > low_hazard_cost["total_estimated_cost_inr"]
        assert high_hazard_cost["breakdown"]["hazard_risk_surcharge_inr"] > 0


@pytest.mark.django_db
class TestDeliveryDeadlineIntelligence:
    def test_on_time_classification(self, test_user, origin_node, dest_node):
        now = timezone.now()
        load = FreightLoad.objects.create(
            shipper=test_user,
            origin_node=origin_node,
            destination_node=dest_node,
            weight_kg=5000.0,
            required_delivery_time=now + timedelta(hours=6),
        )
        # 2 hour transit with 6 hour deadline gives ~4 hours (240 min) slack
        eval_res = DeliveryDeadlineIntelligence.evaluate_deadline_risk(
            load=load,
            estimated_transit_time_min=120.0,
            departure_time=now,
        )
        assert eval_res["status"] == DeadlineRiskStatus.ON_TIME
        assert eval_res["slack_time_min"] > 60.0
        assert eval_res["compliance_score"] == 100.0

    def test_blocked_route_forces_critical(self, test_user, origin_node, dest_node):
        now = timezone.now()
        load = FreightLoad.objects.create(
            shipper=test_user,
            origin_node=origin_node,
            destination_node=dest_node,
            weight_kg=5000.0,
            required_delivery_time=now + timedelta(hours=8),
        )
        eval_res = DeliveryDeadlineIntelligence.evaluate_deadline_risk(
            load=load,
            estimated_transit_time_min=120.0,
            is_route_blocked=True,
        )
        assert eval_res["status"] == DeadlineRiskStatus.CRITICAL
        assert eval_res["compliance_score"] == 0.0


@pytest.mark.django_db
class TestDeterministicPriorityEngine:
    def test_emergency_aid_scores_higher_than_commercial(self, test_user, origin_node, dest_node):
        comm_load = FreightLoad.objects.create(
            shipper=test_user,
            origin_node=origin_node,
            destination_node=dest_node,
            cargo_type=CargoType.GENERAL,
            weight_kg=5000.0,
            priority=CargoPriority.NORMAL,
        )
        relief_load = FreightLoad.objects.create(
            shipper=test_user,
            origin_node=origin_node,
            destination_node=dest_node,
            cargo_type=CargoType.EMERGENCY_AID,
            weight_kg=5000.0,
            priority=CargoPriority.EMERGENCY,
            is_perishable=True,
        )
        p_comm = DeterministicPriorityEngine.calculate_load_priority(comm_load)
        p_relief = DeterministicPriorityEngine.calculate_load_priority(relief_load)

        assert p_relief["priority_score"] > p_comm["priority_score"]
        assert p_relief["priority_level"] == "CRITICAL_URGENT"


@pytest.mark.django_db
class TestLoadConsolidationEngine:
    def test_compatible_loads_can_consolidate(self, test_user, origin_node, dest_node):
        load_1 = FreightLoad.objects.create(
            shipper=test_user,
            origin_node=origin_node,
            destination_node=dest_node,
            cargo_type=CargoType.GENERAL,
            weight_kg=4000.0,
            volume_cbm=10.0,
        )
        load_2 = FreightLoad.objects.create(
            shipper=test_user,
            origin_node=origin_node,
            destination_node=dest_node,
            cargo_type=CargoType.GENERAL,
            weight_kg=5000.0,
            volume_cbm=12.0,
        )
        res = LoadConsolidationEngine.evaluate_consolidation_pair(
            load_1, load_2, vehicle_capacity_kg=15000.0
        )
        assert res["can_consolidate"] is True
        assert res["combined_weight_kg"] == 9000.0
        assert res["estimated_savings_inr"] > 0

    def test_incompatible_cargo_hazmat_food_rejected(self, test_user, origin_node, dest_node):
        load_food = FreightLoad.objects.create(
            shipper=test_user,
            origin_node=origin_node,
            destination_node=dest_node,
            cargo_type=CargoType.PERISHABLE,
            weight_kg=2000.0,
        )
        load_hazmat = FreightLoad.objects.create(
            shipper=test_user,
            origin_node=origin_node,
            destination_node=dest_node,
            cargo_type=CargoType.HAZMAT,
            weight_kg=2000.0,
        )
        res = LoadConsolidationEngine.evaluate_consolidation_pair(
            load_food, load_hazmat, vehicle_capacity_kg=15000.0
        )
        assert res["can_consolidate"] is False
        assert "CARGO_CLASS_CONFLICT" in res["constraints"]


@pytest.mark.django_db
class TestDisasterFleetMode:
    def test_toggle_and_reset_disaster_mode(self):
        act_res = DisasterFleetModeService.activate_disaster_mode(
            activated_by="CHIEF_DISASTER_OFFICER",
            notes="Active monsoon flood warning in Brahmaputra valley",
        )
        assert act_res["status"] == "ACTIVATED"
        assert act_res["mode"] == "DISASTER_RESPONSE"

        state = DisasterFleetModeService.get_current_state()
        assert state["is_disaster_mode"] is True

        # Reset
        reset_res = DisasterFleetModeService.reset_to_normal_operations(reset_by="ADMIN")
        assert reset_res["status"] == "RESET"
        assert reset_res["mode"] == "NORMAL_OPERATIONS"

        state_after = DisasterFleetModeService.get_current_state()
        assert state_after["is_disaster_mode"] is False
