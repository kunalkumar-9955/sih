"""
SIH26002 — User views.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.decorators import audit_action

from .models import User
from .permissions import IsAdminLevel
from .serializers import AdminUserListSerializer, UserProfileSerializer, UserProfileUpdateSerializer


class UserProfileView(APIView):
    """
    GET  /api/v1/users/profile/  — Return own profile.
    PUT  /api/v1/users/profile/  — Update own mutable fields.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response({"success": True, "data": serializer.data})

    @audit_action("user.profile.update")
    def put(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"success": True, "data": UserProfileSerializer(request.user).data}
        )


class AdminUserListView(APIView):
    """
    GET /api/v1/users/  — List all users (MINISTRY_ADMIN, SUPER_ADMIN only).
    """

    permission_classes = [IsAuthenticated, IsAdminLevel]

    def get(self, request):
        users = User.objects.all().order_by("-created_at")
        serializer = AdminUserListSerializer(users, many=True)
        return Response(
            {
                "success": True,
                "count": users.count(),
                "data": serializer.data,
            }
        )
