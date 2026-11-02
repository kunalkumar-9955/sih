"""
SIH26002 — Vehicle views.
"""
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.decorators import audit_action
from apps.users.permissions import CanManageVehicles

from .models import Vehicle
from .serializers import VehicleCreateSerializer, VehicleSerializer, VehicleUpdateSerializer


class VehicleListCreateView(APIView):
    """
    GET  /api/v1/vehicles/   — List vehicles (scoped by role)
    POST /api/v1/vehicles/   — Create vehicle (FLEET_OPERATOR, SUPER_ADMIN)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_admin_level:
            vehicles = Vehicle.objects.select_related("owner").all()
        elif user.is_fleet_operator:
            vehicles = Vehicle.objects.select_related("owner").filter(owner=user)
        elif user.is_driver:
            vehicles = Vehicle.objects.select_related("owner").filter(owner=user)
        else:
            vehicles = Vehicle.objects.none()

        serializer = VehicleSerializer(vehicles, many=True)
        return Response({"success": True, "count": vehicles.count(), "data": serializer.data})

    @audit_action("vehicle.create", resource_type="Vehicle")
    def post(self, request):
        # Enforce permission: only FLEET_OPERATOR and SUPER_ADMIN
        perm = CanManageVehicles()
        if not perm.has_permission(request, self):
            return Response(
                {"success": False, "error": {"code": "permission_denied", "message": perm.message}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = VehicleCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        vehicle = serializer.save()
        return Response(
            {"success": True, "data": VehicleSerializer(vehicle).data},
            status=status.HTTP_201_CREATED,
        )


class VehicleDetailView(APIView):
    """
    GET  /api/v1/vehicles/{id}/   — Vehicle detail
    PUT  /api/v1/vehicles/{id}/   — Update vehicle
    DELETE /api/v1/vehicles/{id}/ — Soft-delete (is_active=False)
    """

    permission_classes = [IsAuthenticated]

    def _get_vehicle(self, pk, user):
        vehicle = get_object_or_404(Vehicle, pk=pk)
        if not user.is_admin_level and vehicle.owner != user:
            return None
        return vehicle

    def get(self, request, pk):
        vehicle = self._get_vehicle(pk, request.user)
        if not vehicle:
            return Response(
                {"success": False, "error": {"code": "permission_denied", "message": "Not found or access denied."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"success": True, "data": VehicleSerializer(vehicle).data})

    @audit_action("vehicle.update", resource_type="Vehicle")
    def put(self, request, pk):
        vehicle = self._get_vehicle(pk, request.user)
        if not vehicle:
            return Response(
                {"success": False, "error": {"code": "permission_denied", "message": "Not found or access denied."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = VehicleUpdateSerializer(vehicle, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": VehicleSerializer(vehicle).data})

    @audit_action("vehicle.delete", resource_type="Vehicle")
    def delete(self, request, pk):
        vehicle = self._get_vehicle(pk, request.user)
        if not vehicle:
            return Response(
                {"success": False, "error": {"code": "permission_denied", "message": "Not found or access denied."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        vehicle.is_active = False
        vehicle.save(update_fields=["is_active", "updated_at"])
        return Response({"success": True, "message": "Vehicle deactivated."}, status=status.HTTP_200_OK)
