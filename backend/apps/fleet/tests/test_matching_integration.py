"""
Integration tests for Fleet Intelligence, Automated Load Matching,
Operator Overrides, Emergency SOS Triage, and Disaster Mode Operations.
"""
from datetime import timedelta
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.utils import timezone

from apps.drivers.models import Driver
from apps.fleet.models import (
    CargoPriority,
    CargoStatus,
    CargoType,
    FreightLoad,
    LoadAssignment,
    MatchingRecommendation,
)
from apps.fleet.services.emergency_service import EmergencyOperationsService
from apps.fleet.services.matching_engine import AutomatedLoadMatchingEngine
from apps.sync.models import EmergencySOS, EmergencySOSStatus
from apps.transport_graph.models import NodeType, TransportNode
from apps.vehicles.models import Vehicle, VehicleStatus, VehicleType

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def dispatcher_user(db):
    return User.objects.create_user(
        email="dispatcher@sih26002.local",
        password="DispatcherPassword123!",
        role="DISPATCHER",
        first_name="Control",
        last_name="Room",
    )


@pytest.fixture
def driver_user(db):
    user = User.objects.create_user(
        email="driver1@sih26002.local",
        password="DriverPassword123!",
        role="DRIVER",
        first_name="Ramesh",
        last_name="Boro",
    )
    Driver.objects.create(user=user, license_number="AS-01-2024-998811")
    return user


@pytest.fixture
def network_nodes(db):
    hub_ghy = TransportNode.objects.create(
        name="Guwahati Multimodal Hub",
        short_code="GHY-HUB",
        state="Assam",
        geometry=Point(91.7362, 26.1445, srid=4326),
        node_type=NodeType.MULTIMODAL_HUB,
    )
    depot_shl = TransportNode.objects.create(
        name="Shillong Logistics Depot",
        short_code="SHL-DEPOT",
        state="Meghalaya",
        geometry=Point(91.8933, 25.5788, srid=4326),
        node_type=NodeType.LOGISTICS_HUB,
    )
    nongpoh_relay = TransportNode.objects.create(
        name="Nongpoh Transit Node",
        short_code="NGP-RELAY",
        state="Meghalaya",
        geometry=Point(91.8804, 25.9034, srid=4326),
        node_type=NodeType.ROAD_INTERSECTION,
    )
    return {
        "guwahati": hub_ghy,
        "shillong": depot_shl,
        "nongpoh": nongpoh_relay,
    }


@pytest.fixture
def fleet_vehicles(db, dispatcher_user, driver_user):
    # Vehicle A: Heavy Truck, stationed at Guwahati (close to pickup)
    veh_a = Vehicle.objects.create(
        owner=dispatcher_user,
        assigned_driver=driver_user.driver_profile,
        registration_number="AS-01-HV-1001",
        vehicle_type=VehicleType.HEAVY_TRUCK,
        capacity_kg=16000.0,
        fuel_efficiency_kmpl=4.2,
        status=VehicleStatus.AVAILABLE,
        maintenance_status="HEALTHY",
        current_location=Point(91.7360, 26.1440, srid=4326),
        last_gps_update=timezone.now(),
    )
    # Vehicle B: Light Truck, stationed at Guwahati (insufficient for heavy loads)
    veh_b = Vehicle.objects.create(
        owner=dispatcher_user,
        registration_number="AS-01-LT-2002",
        vehicle_type=VehicleType.LIGHT_TRUCK,
        capacity_kg=3000.0,
        fuel_efficiency_kmpl=6.5,
        status=VehicleStatus.AVAILABLE,
        maintenance_status="HEALTHY",
        current_location=Point(91.7350, 26.1430, srid=4326),
        last_gps_update=timezone.now(),
    )
    # Vehicle C: Medium Truck, stationed far away in Shillong
    veh_c = Vehicle.objects.create(
        owner=dispatcher_user,
        registration_number="ML-05-MD-3003",
        vehicle_type=VehicleType.MEDIUM_TRUCK,
        capacity_kg=8000.0,
        fuel_efficiency_kmpl=5.0,
        status=VehicleStatus.AVAILABLE,
        maintenance_status="HEALTHY",
        current_location=Point(91.8900, 25.5800, srid=4326),
        last_gps_update=timezone.now(),
    )
    return [veh_a, veh_b, veh_c]


@pytest.mark.django_db
class TestLoadMatchingWorkflow:
    def test_automated_matching_and_ranking(self, dispatcher_user, network_nodes, fleet_vehicles):
        veh_a, veh_b, veh_c = fleet_vehicles
        ghy = network_nodes["guwahati"]
        shl = network_nodes["shillong"]

        # Heavy emergency relief load (12,000 kg)
        heavy_load = FreightLoad.objects.create(
            shipper=dispatcher_user,
            title="Emergency Medical & Tents Relief",
            origin_node=ghy,
            destination_node=shl,
            cargo_type=CargoType.EMERGENCY_AID,
            weight_kg=12000.0,
            priority=CargoPriority.EMERGENCY,
        )

        candidates = AutomatedLoadMatchingEngine.find_and_rank_candidates(heavy_load)

        # Only Veh A has capacity (16,000 kg >= 12,000 kg)
        assert len(candidates) == 1
        assert candidates[0]["registration_number"] == veh_a.registration_number
        assert candidates[0]["rank"] == 1
        assert "Optimal payload fit" in candidates[0]["explanation"] or "payload utilization" in candidates[0]["explanation"]

    def test_execute_match_api_and_manual_override(self, api_client, dispatcher_user, network_nodes, fleet_vehicles):
        api_client.force_authenticate(user=dispatcher_user)
        veh_a, veh_b, veh_c = fleet_vehicles
        ghy = network_nodes["guwahati"]
        shl = network_nodes["shillong"]

        load = FreightLoad.objects.create(
            shipper=dispatcher_user,
            title="Commercial Agricultural Tea",
            origin_node=ghy,
            destination_node=shl,
            cargo_type=CargoType.GENERAL,
            weight_kg=6000.0,
            priority=CargoPriority.NORMAL,
        )

        # 1. Fetch Candidates via API
        cand_resp = api_client.get(f"/api/v1/fleet/loads/{load.id}/candidates/")
        assert cand_resp.status_code == 200
        assert cand_resp.data["candidate_count"] >= 1

        # 2. Execute Automated Match
        match_resp = api_client.post(
            f"/api/v1/fleet/loads/{load.id}/match/",
            {"vehicle_id": str(veh_a.id), "is_manual_override": False},
            format="json",
        )
        assert match_resp.status_code == 200
        assert match_resp.data["load_status"] == CargoStatus.MATCHED
        assert match_resp.data["vehicle_status"] == VehicleStatus.ASSIGNED

        # Verify DB Assignment
        assignment = LoadAssignment.objects.get(load=load, is_active=True)
        assert assignment.vehicle == veh_a
        assert assignment.is_manual_override is False

        # 3. Test Manual Override to Vehicle C with Reason
        override_resp = api_client.post(
            f"/api/v1/fleet/loads/{load.id}/match/",
            {
                "vehicle_id": str(veh_c.id),
                "is_manual_override": True,
                "override_reason": "Pre-positioning fleet back to Shillong depot for return cargo",
            },
            format="json",
        )
        assert override_resp.status_code == 200
        assignment.refresh_from_db()
        assert assignment.is_active is False  # previous assignment deactivated

        new_assignment = LoadAssignment.objects.get(load=load, is_active=True)
        assert new_assignment.vehicle == veh_c
        assert new_assignment.is_manual_override is True
        assert "Pre-positioning" in new_assignment.override_reason


@pytest.mark.django_db
class TestEmergencyOperationsAndDisasterMode:
    def test_emergency_sos_lifecycle_and_operator_actions(
        self, api_client, dispatcher_user, driver_user, network_nodes
    ):
        api_client.force_authenticate(user=dispatcher_user)
        nongpoh = network_nodes["nongpoh"]

        # Create SOS distress signal from driver
        sos = EmergencySOS.objects.create(
            driver=driver_user.driver_profile,
            location=Point(91.8800, 25.9030, srid=4326),  # Near Nongpoh
            status=EmergencySOSStatus.TRIGGERED,
            message="Vehicle stuck near mudslide edge. Need recovery winch.",
        )

        # 1. System Triage
        triage_res = EmergencyOperationsService.triage_and_enrich_sos(sos)
        assert triage_res["nearest_hub"] is not None
        assert triage_res["distance_km"] < 10.0
        assert len(sos.audit_log) >= 1

        # 2. Operator Acknowledges Distress via API
        ack_resp = api_client.post(
            f"/api/v1/fleet/emergencies/{sos.id}/action/",
            {"action": "ACKNOWLEDGE", "notes": "Disaster control room acknowledged beacon"},
            format="json",
        )
        assert ack_resp.status_code == 200
        assert ack_resp.data["status"] == EmergencySOSStatus.ACKNOWLEDGED

        # 3. Operator Dispatches Rescue Unit via API
        disp_resp = api_client.post(
            f"/api/v1/fleet/emergencies/{sos.id}/action/",
            {"action": "DISPATCH", "notes": "Dispatched emergency crane from Nongpoh depot"},
            format="json",
        )
        assert disp_resp.status_code == 200
        assert disp_resp.data["status"] == EmergencySOSStatus.DISPATCHED

        # 4. Operator Resolves Incident
        res_resp = api_client.post(
            f"/api/v1/fleet/emergencies/{sos.id}/action/",
            {"action": "RESOLVE", "notes": "Vehicle recovered and cleared to safe siding"},
            format="json",
        )
        assert res_resp.status_code == 200
        assert res_resp.data["status"] == EmergencySOSStatus.RESOLVED

        sos.refresh_from_db()
        assert sos.status == EmergencySOSStatus.RESOLVED
        assert len(sos.audit_log) == 4  # Triage + Acknowledge + Dispatch + Resolve

    def test_disaster_mode_activation_and_reset_apis(self, api_client, dispatcher_user):
        api_client.force_authenticate(user=dispatcher_user)

        # Activate
        act_resp = api_client.post(
            "/api/v1/fleet/disaster-mode/",
            {
                "affected_corridors": ["NH-6_MEGHALAYA", "NW-2_BRAHMAPUTRA"],
                "notes": "Flood stage 3 alert activated",
            },
            format="json",
        )
        assert act_resp.status_code == 200
        assert act_resp.data["mode"] == "DISASTER_RESPONSE"

        # Overview endpoint reflects disaster mode
        ov_resp = api_client.get("/api/v1/fleet/overview/")
        assert ov_resp.status_code == 200
        assert ov_resp.data["operational_mode"]["is_disaster_mode"] is True

        # Reset
        reset_resp = api_client.post("/api/v1/fleet/disaster-mode/reset/")
        assert reset_resp.status_code == 200
        assert reset_resp.data["mode"] == "NORMAL_OPERATIONS"

        ov_resp_after = api_client.get("/api/v1/fleet/overview/")
        assert ov_resp_after.data["operational_mode"]["is_disaster_mode"] is False
