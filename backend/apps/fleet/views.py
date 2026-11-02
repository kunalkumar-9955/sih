"""
SIH26002 — Fleet Intelligence, Load Matching & Emergency Operations API Views.
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.fleet.models import (
    CargoPriority,
    CargoStatus,
    DisasterFleetModeState,
    FreightLoad,
    LoadAssignment,
    MatchingRecommendation,
)
from apps.fleet.serializers import (
    CreateFreightLoadSerializer,
    DisasterModeActivateSerializer,
    EmergencyActionRequestSerializer,
    EmergencySOSDetailSerializer,
    ExecuteMatchRequestSerializer,
    FreightLoadSerializer,
    LoadAssignmentSerializer,
    MatchingRecommendationSerializer,
)
from apps.fleet.services.consolidation_service import LoadConsolidationEngine
from apps.fleet.services.depot_optimizer import MultiDepotOptimizationEngine
from apps.fleet.services.disaster_mode_service import DisasterFleetModeService
from apps.fleet.services.eligibility_service import FleetAvailabilityEngine
from apps.fleet.services.emergency_service import EmergencyOperationsService
from apps.fleet.services.matching_engine import AutomatedLoadMatchingEngine
from apps.sync.models import EmergencySOS, EmergencySOSStatus
from apps.vehicles.models import Vehicle, VehicleStatus


class FreightLoadListCreateView(APIView):
    """
    GET /api/v1/fleet/loads/
    POST /api/v1/fleet/loads/
    Lists active freight loads or creates a new freight demand.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        role = getattr(user, "role", "SHIPPER")

        # Drivers see loads assigned to their vehicle/trips
        if role == "DRIVER" and hasattr(user, "driver_profile"):
            assigned_vehicles = user.driver_profile.assigned_vehicles.all()
            loads = FreightLoad.objects.filter(assigned_vehicle__in=assigned_vehicles)
        else:
            loads = FreightLoad.objects.all().select_related("origin_node", "destination_node", "assigned_vehicle")

        status_filter = request.query_params.get("status")
        if status_filter:
            loads = loads.filter(status=status_filter.upper())

        priority_filter = request.query_params.get("priority")
        if priority_filter:
            loads = loads.filter(priority=priority_filter.upper())

        serializer = FreightLoadSerializer(loads, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CreateFreightLoadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        load = serializer.save(
            shipper=request.user,
            status=CargoStatus.AVAILABLE,
        )
        return Response(FreightLoadSerializer(load).data, status=status.HTTP_201_CREATED)


class FreightLoadDetailView(APIView):
    """
    GET /api/v1/fleet/loads/{id}/
    Returns detailed load state, route suggestions, and depot options.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        load = get_object_or_404(
            FreightLoad.objects.select_related("origin_node", "destination_node", "assigned_vehicle"),
            pk=pk,
        )
        serializer = FreightLoadSerializer(load)
        depot_opts = MultiDepotOptimizationEngine.recommend_optimal_depot_and_transfer(load)

        return Response({
            "load": serializer.data,
            "depot_optimization": depot_opts,
        }, status=status.HTTP_200_OK)


class LoadCandidatesView(APIView):
    """
    GET /api/v1/fleet/loads/{id}/candidates/
    Runs the multi-factor matching engine and returns ranked candidate vehicles with explainable factors.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        load = get_object_or_404(FreightLoad, pk=pk)
        candidates = AutomatedLoadMatchingEngine.find_and_rank_candidates(load, persist_recommendations=True)

        # Drop vehicle_obj reference from JSON payload
        serializable_candidates = []
        for c in candidates:
            item = {k: v for k, v in c.items() if k != "vehicle_obj"}
            serializable_candidates.append(item)

        return Response({
            "load_id": str(load.id),
            "cargo_type": load.cargo_type,
            "weight_kg": float(load.weight_kg),
            "candidate_count": len(serializable_candidates),
            "ranked_candidates": serializable_candidates,
        }, status=status.HTTP_200_OK)


class LoadMatchExecuteView(APIView):
    """
    POST /api/v1/fleet/loads/{id}/match/
    Binds a vehicle to a freight load. Supports operator manual overrides.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        load = get_object_or_404(FreightLoad, pk=pk)
        serializer = ExecuteMatchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        vehicle_id = serializer.validated_data["vehicle_id"]
        is_override = serializer.validated_data["is_manual_override"]
        override_reason = serializer.validated_data["override_reason"]

        vehicle = get_object_or_404(Vehicle, pk=vehicle_id)

        # Validate physical eligibility if not a strict emergency override
        if not is_override:
            eligibility = FleetAvailabilityEngine.evaluate_vehicle_eligibility(vehicle, load)
            if not eligibility["eligible"]:
                return Response({
                    "error": "INELIGIBLE_VEHICLE",
                    "reason": eligibility["reason"],
                    "constraints": eligibility["constraints"],
                }, status=status.HTTP_400_BAD_REQUEST)

        # Fetch score from recommendations if exists
        rec = MatchingRecommendation.objects.filter(load=load, vehicle=vehicle).first()
        matched_score = rec.final_score if rec else 75.0
        matching_factors = {
            "capacity_score": rec.capacity_score if rec else 75.0,
            "safety_score": rec.safety_score if rec else 80.0,
            "distance_score": rec.distance_score if rec else 70.0,
        }

        # Deactivate any prior assignment
        LoadAssignment.objects.filter(load=load, is_active=True).update(is_active=False)

        # Create LoadAssignment record
        assignment = LoadAssignment.objects.create(
            load=load,
            vehicle=vehicle,
            driver=vehicle.assigned_driver,
            matched_score=matched_score,
            matching_factors=matching_factors,
            is_manual_override=is_override,
            override_reason=override_reason,
            assigned_by=request.user,
            is_active=True,
        )

        # Update load state
        load.status = CargoStatus.MATCHED
        load.assigned_vehicle = vehicle
        load.save(update_fields=["status", "assigned_vehicle"])

        # Update vehicle status to ASSIGNED
        vehicle.status = VehicleStatus.ASSIGNED
        vehicle.save(update_fields=["status"])

        return Response({
            "message": f"Load successfully matched to vehicle {vehicle.registration_number}.",
            "assignment": LoadAssignmentSerializer(assignment).data,
            "load_status": load.status,
            "vehicle_status": vehicle.status,
        }, status=status.HTTP_200_OK)


class BatchMatchingRecommendView(APIView):
    """
    POST /api/v1/fleet/matching/recommend/
    Runs automated matching for all unassigned AVAILABLE loads.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        unassigned_loads = FreightLoad.objects.filter(status=CargoStatus.AVAILABLE)[:10]
        results = []

        for load in unassigned_loads:
            candidates = AutomatedLoadMatchingEngine.find_and_rank_candidates(load, persist_recommendations=True)
            top_candidate = candidates[0] if candidates else None
            results.append({
                "load_id": str(load.id),
                "title": load.title or f"Load #{str(load.id)[:6]}",
                "priority": load.priority,
                "weight_kg": float(load.weight_kg),
                "best_candidate": {
                    "vehicle_id": top_candidate["vehicle_id"],
                    "registration_number": top_candidate["registration_number"],
                    "score": top_candidate["final_score"],
                    "explanation": top_candidate["explanation"],
                } if top_candidate else None,
            })

        return Response({
            "evaluated_loads_count": len(results),
            "recommendations": results,
            "timestamp": timezone.now().isoformat(),
        }, status=status.HTTP_200_OK)


class VehicleAvailabilityListView(APIView):
    """
    GET /api/v1/fleet/vehicles/availability/
    Returns list of vehicles categorized by operational and maintenance states.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        vehicles = Vehicle.objects.filter(is_active=True).select_related("assigned_driver")
        data = []
        for v in vehicles:
            data.append({
                "id": str(v.id),
                "registration_number": v.registration_number,
                "vehicle_type": v.vehicle_type,
                "capacity_kg": float(v.capacity_kg),
                "fuel_efficiency_kmpl": v.fuel_efficiency_kmpl,
                "status": v.status,
                "maintenance_status": v.maintenance_status,
                "operating_region": v.operating_region,
                "driver": str(v.assigned_driver) if v.assigned_driver else None,
                "has_gps": v.current_location is not None,
                "last_gps_update": v.last_gps_update.isoformat() if v.last_gps_update else None,
            })
        return Response(data, status=status.HTTP_200_OK)


class FleetOverviewView(APIView):
    """
    GET /api/v1/fleet/overview/
    Returns high-level control room metrics across vehicles, loads, and emergency alerts.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        total_vehicles = Vehicle.objects.filter(is_active=True).count()
        available_vehicles = Vehicle.objects.filter(is_active=True, status=VehicleStatus.AVAILABLE).count()
        assigned_vehicles = Vehicle.objects.filter(is_active=True, status=VehicleStatus.ASSIGNED).count()
        on_trip_vehicles = Vehicle.objects.filter(is_active=True, status=VehicleStatus.ON_TRIP).count()
        maintenance_vehicles = Vehicle.objects.filter(is_active=True, status=VehicleStatus.MAINTENANCE).count()
        emergency_vehicles = Vehicle.objects.filter(is_active=True, status=VehicleStatus.EMERGENCY).count()

        total_loads = FreightLoad.objects.count()
        available_loads = FreightLoad.objects.filter(status=CargoStatus.AVAILABLE).count()
        matched_loads = FreightLoad.objects.filter(status=CargoStatus.MATCHED).count()
        in_transit_loads = FreightLoad.objects.filter(status=CargoStatus.IN_TRANSIT).count()
        urgent_loads = FreightLoad.objects.filter(priority__in=[CargoPriority.URGENT, CargoPriority.EMERGENCY]).count()

        active_sos_count = EmergencySOS.objects.filter(
            status__in=[EmergencySOSStatus.TRIGGERED, EmergencySOSStatus.ACKNOWLEDGED, EmergencySOSStatus.DISPATCHED]
        ).count()

        disaster_mode = DisasterFleetModeService.get_current_state()

        return Response({
            "fleet": {
                "total_vehicles": total_vehicles,
                "available": available_vehicles,
                "assigned": assigned_vehicles,
                "on_trip": on_trip_vehicles,
                "maintenance": maintenance_vehicles,
                "emergency": emergency_vehicles,
            },
            "loads": {
                "total_loads": total_loads,
                "available": available_loads,
                "matched": matched_loads,
                "in_transit": in_transit_loads,
                "urgent_emergency": urgent_loads,
            },
            "emergencies": {
                "active_sos_count": active_sos_count,
            },
            "operational_mode": disaster_mode,
            "evaluated_at": timezone.now().isoformat(),
        }, status=status.HTTP_200_OK)


class FleetEmergenciesListView(APIView):
    """
    GET /api/v1/fleet/emergencies/
    Lists all SOS distress beacons, triage advice, and active rescue dispatches.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sos_list = EmergencySOS.objects.all().select_related("driver", "trip", "nearest_hub").order_by("-triggered_at")
        serializer = EmergencySOSDetailSerializer(sos_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FleetEmergencyActionView(APIView):
    """
    POST /api/v1/fleet/emergencies/{id}/action/
    Executes ACKNOWLEDGE, DISPATCH, RESOLVE, or FALSE_ALARM for an active distress beacon.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        sos = get_object_or_404(EmergencySOS, pk=pk)
        serializer = EmergencyActionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        action = serializer.validated_data["action"]
        notes = serializer.validated_data.get("notes", "")

        try:
            result = EmergencyOperationsService.execute_operator_action(
                sos=sos,
                action=action,
                operator_email=request.user.email,
                notes=notes,
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class DisasterModeActivateView(APIView):
    """
    POST /api/v1/fleet/disaster-mode/
    Activates system-wide DISASTER_RESPONSE mode.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DisasterModeActivateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        corridors = serializer.validated_data.get("affected_corridors")
        notes = serializer.validated_data.get("notes")

        res = DisasterFleetModeService.activate_disaster_mode(
            activated_by=request.user.email,
            affected_corridors=corridors,
            notes=notes,
        )
        return Response(res, status=status.HTTP_200_OK)


class DisasterModeResetView(APIView):
    """
    POST /api/v1/fleet/disaster-mode/reset/
    Restores NORMAL_OPERATIONS mode.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        res = DisasterFleetModeService.reset_to_normal_operations(reset_by=request.user.email)
        return Response(res, status=status.HTTP_200_OK)


class LoadConsolidationListView(APIView):
    """
    GET /api/v1/fleet/consolidations/
    Returns identified load bundling opportunities.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        opportunities = LoadConsolidationEngine.find_all_consolidations()
        return Response({
            "consolidation_opportunities_count": len(opportunities),
            "opportunities": opportunities,
        }, status=status.HTTP_200_OK)
