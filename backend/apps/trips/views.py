"""
SIH26002 — Trip views.
"""
from django.contrib.gis.geos import Point
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.decorators import audit_action, audit_log  # noqa: F401
from apps.drivers.models import Driver
from apps.routing.services import RerouteDecisionService, RouteRiskEvaluator
from apps.users.models import UserRole
from .models import RerouteEvent, RerouteEventStatus, Trip, TripStatus
from .serializers import (
    RerouteAcknowledgeSerializer,
    RerouteEventSerializer,
    TripCreateSerializer,
    TripLocationUpdateSerializer,
    TripSerializer,
    TripStatusUpdateSerializer,
)


class TripListCreateView(generics.ListCreateAPIView):
    """
    List and create trips.
    Queryset is strictly scoped to the caller's role.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TripCreateSerializer
        return TripSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Trip.objects.select_related(
            "driver", "driver__user", "vehicle", "origin_node", "destination_node", "route"
        )

        # Scoped access by role
        if user.role == UserRole.DRIVER:
            qs = qs.filter(driver__user=user)
        elif user.role == UserRole.FLEET_OPERATOR:
            qs = qs.filter(vehicle__owner=user)
        elif user.role in [UserRole.SUPER_ADMIN, UserRole.MINISTRY_ADMIN]:
            pass  # Full visibility for administrators
        else:
            qs = qs.filter(driver__user=user)

        # Optional query filters
        trip_status = self.request.query_params.get("status")
        if trip_status:
            qs = qs.filter(status=trip_status)

        return qs

    def perform_create(self, serializer):
        user = self.request.user
        driver = serializer.validated_data.get("driver")

        # Auto-assign driver profile if caller is a driver
        if not driver and user.role == UserRole.DRIVER:
            driver_profile, _ = Driver.objects.get_or_create(user=user)
            trip = serializer.save(driver=driver_profile)
        else:
            trip = serializer.save()

        audit_log(
            actor=user,
            action="CREATE_TRIP",
            resource_type="Trip",
            resource_id=trip.id,
            payload={
                "origin": trip.origin_node.name,
                "destination": trip.destination_node.name,
                "status": trip.status,
            },
        )


class TripDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or partially update trip info. Strictly scoped by caller role.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TripSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Trip.objects.select_related(
            "driver", "driver__user", "vehicle", "origin_node", "destination_node", "route"
        )
        if user.role == UserRole.DRIVER:
            return qs.filter(driver__user=user)
        elif user.role == UserRole.FLEET_OPERATOR:
            return qs.filter(vehicle__owner=user)
        return qs


class TripStatusUpdateView(APIView):
    """
    POST /api/v1/trips/{id}/status/
    Transition trip state (e.g. PLANNED -> ACTIVE -> COMPLETED).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            trip = Trip.objects.get(pk=pk)
        except Trip.DoesNotExist:
            return Response({"detail": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = TripStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data["status"]
        notes = serializer.validated_data.get("notes")

        if notes:
            trip.notes = f"{trip.notes}\n[{timezone.now().isoformat()}] {notes}".strip()

        old_status = trip.status
        trip.transition_status(new_status)

        audit_log(
            actor=request.user,
            action="UPDATE_TRIP_STATUS",
            resource_type="Trip",
            resource_id=trip.id,
            payload={"old_status": old_status, "new_status": new_status},
        )

        return Response(TripSerializer(trip).data, status=status.HTTP_200_OK)


class TripLocationUpdateView(APIView):
    """
    POST /api/v1/trips/{id}/location/
    Update driver & vehicle GPS position during an active trip.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            trip = Trip.objects.get(pk=pk)
        except Trip.DoesNotExist:
            return Response({"detail": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = TripLocationUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        lat = serializer.validated_data["latitude"]
        lon = serializer.validated_data["longitude"]
        pt = Point(lon, lat, srid=4326)
        now = timezone.now()

        trip.current_location = pt
        trip.last_location_update = now
        trip.save(update_fields=["current_location", "last_location_update", "updated_at"])

        if trip.vehicle:
            trip.vehicle.current_location = pt
            trip.vehicle.location_updated_at = now
            trip.vehicle.save(update_fields=["current_location", "location_updated_at", "updated_at"])

        return Response(
            {"status": "Location updated successfully", "latitude": lat, "longitude": lon},
            status=status.HTTP_200_OK,
        )


class TripRouteRiskView(APIView):
    """
    GET /api/v1/trips/{id}/route-risk/
    Returns real-time risk assessment for the trip's assigned route.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        if not trip.route:
            return Response(
                {"detail": "No route assigned to this trip."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        evaluation = RouteRiskEvaluator.evaluate_route(trip.route)
        evaluation["trip_id"] = str(trip.id)
        evaluation["trip_status"] = trip.status
        evaluation["route_version"] = trip.route_version
        evaluation["route_assigned_at"] = trip.route_assigned_at.isoformat() if trip.route_assigned_at else None

        return Response(evaluation, status=status.HTTP_200_OK)


class TripRecalculateRouteView(APIView):
    """
    POST /api/v1/trips/{id}/recalculate-route/
    Manually or automatically triggers dynamic reroute evaluation for an active trip.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        force = request.data.get("force", False)
        auto_apply = request.data.get("auto_apply", False)

        service = RerouteDecisionService()
        result = service.evaluate_and_reroute_trip(
            trip=trip,
            auto_apply=auto_apply,
            force=force,
        )

        audit_log(
            actor=request.user,
            action="RECALCULATE_TRIP_ROUTE",
            resource_type="Trip",
            resource_id=trip.id,
            payload={
                "rerouted": result.get("rerouted", False),
                "reason": result.get("reason") or result.get("trigger_reason"),
                "event_id": result.get("event_id"),
            },
        )

        resp_status = status.HTTP_201_CREATED if result.get("rerouted") and not result.get("is_existing") else status.HTTP_200_OK
        return Response(result, status=resp_status)


class TripRerouteEventListView(generics.ListAPIView):
    """
    GET /api/v1/trips/{id}/reroute-events/
    List all historical and pending reroute audit events for this trip.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RerouteEventSerializer

    def get_queryset(self):
        pk = self.kwargs["pk"]
        return RerouteEvent.objects.filter(trip_id=pk).select_related(
            "old_route", "new_route"
        ).order_by("-created_at")


class TripRerouteAcknowledgeView(APIView):
    """
    POST /api/v1/trips/{id}/reroute-events/{event_id}/acknowledge/
    Driver acknowledges a proposed reroute event (ACCEPT / DECLINE).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, event_id):
        trip = get_object_or_404(Trip, pk=pk)
        event = get_object_or_404(RerouteEvent, pk=event_id, trip=trip)

        serializer = RerouteAcknowledgeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        action = serializer.validated_data["action"]
        notes = serializer.validated_data.get("notes", "")

        now = timezone.now()
        event.driver_acknowledged_at = now

        if action == "ACCEPT":
            if event.new_route:
                trip.route = event.new_route
                trip.route_version = (trip.route_version or 1) + 1
                trip.route_assigned_at = now
                trip.route_hazard_snapshot_at = now
                trip.route_snapshot = {
                    "route_id": str(event.new_route.id),
                    "policy": event.new_route.route_type,
                    "total_distance_m": event.new_route.total_distance_m,
                    "total_time_min": event.new_route.total_time_min,
                    "max_hazard_score": getattr(event.new_route, "max_hazard_score", 0.0),
                    "assigned_at": now.isoformat(),
                    "acknowledged_by_driver": True,
                }
                trip.save(
                    update_fields=[
                        "route",
                        "route_version",
                        "route_assigned_at",
                        "route_hazard_snapshot_at",
                        "route_snapshot",
                        "updated_at",
                    ]
                )
            event.status = RerouteEventStatus.APPLIED

        elif action == "DECLINE":
            # Check if this reroute was mandatory (e.g. physical road closure)
            payload = event.notification_payload or {}
            if payload.get("is_mandatory", False):
                return Response(
                    {"detail": "Cannot decline mandatory safety reroute due to road blockage or critical hazard."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            event.status = RerouteEventStatus.DISMISSED

        event.save()

        audit_log(
            actor=request.user,
            action=f"REROUTE_{action}",
            resource_type="RerouteEvent",
            resource_id=event.id,
            payload={
                "trip_id": str(trip.id),
                "action": action,
                "notes": notes,
                "status": event.status,
            },
        )

        return Response(RerouteEventSerializer(event).data, status=status.HTTP_200_OK)
