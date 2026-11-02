"""
SIH26002 — Driver views.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsDriver

from .models import Driver
from .serializers import DriverProfileSerializer, DriverProfileUpdateSerializer


class DriverProfileView(APIView):
    """
    GET  /api/v1/drivers/profile/   — Own driver profile (DRIVER role)
    PUT  /api/v1/drivers/profile/   — Update own driver profile
    """

    permission_classes = [IsAuthenticated, IsDriver]

    def _get_or_create_profile(self, user):
        driver, _ = Driver.objects.get_or_create(user=user)
        return driver

    def get(self, request):
        driver = self._get_or_create_profile(request.user)
        return Response(
            {"success": True, "data": DriverProfileSerializer(driver).data}
        )

    def put(self, request):
        driver = self._get_or_create_profile(request.user)
        serializer = DriverProfileUpdateSerializer(driver, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"success": True, "data": DriverProfileSerializer(driver).data}
        )
