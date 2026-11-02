"""
SIH26002 — RBAC Permission classes for DRF.

Provides clean, reusable permission guards based on the User.role field.
Usage:
    class MyView(APIView):
        permission_classes = [IsAuthenticated, IsDriver]
"""
from rest_framework.permissions import BasePermission

from .models import UserRole


class IsDriver(BasePermission):
    """Allow access only to users with DRIVER role."""
    message = "Access restricted to drivers."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.DRIVER
        )


class IsFleetOperator(BasePermission):
    """Allow access only to FLEET_OPERATOR role."""
    message = "Access restricted to fleet operators."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.FLEET_OPERATOR
        )


class IsShipper(BasePermission):
    """Allow access only to SHIPPER role."""
    message = "Access restricted to shippers."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.SHIPPER
        )


class IsCheckpostOperator(BasePermission):
    """Allow access only to CHECKPOST_OPERATOR role."""
    message = "Access restricted to checkpost operators."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.CHECKPOST_OPERATOR
        )


class IsCommunityNodeManager(BasePermission):
    """Allow access only to COMMUNITY_NODE_MANAGER role."""
    message = "Access restricted to community node managers."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.COMMUNITY_NODE_MANAGER
        )


class IsMinistryAdmin(BasePermission):
    """Allow access only to MINISTRY_ADMIN role."""
    message = "Access restricted to ministry administrators."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.MINISTRY_ADMIN
        )


class IsSuperAdmin(BasePermission):
    """Allow access only to SUPER_ADMIN role."""
    message = "Access restricted to super administrators."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.SUPER_ADMIN
        )


class IsAdminLevel(BasePermission):
    """Allow access to MINISTRY_ADMIN and SUPER_ADMIN."""
    message = "Access restricted to administrators."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_admin_level
        )


class IsDriverOrFleetOperator(BasePermission):
    """Allow access to DRIVER or FLEET_OPERATOR."""
    message = "Access restricted to drivers and fleet operators."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.DRIVER, UserRole.FLEET_OPERATOR)
        )


class CanComputeRoute(BasePermission):
    """
    Any authenticated user except CHECKPOST_OPERATOR can compute routes.
    Per RBAC matrix in implementation plan.
    """
    message = "You do not have permission to compute routes."
    _ALLOWED_ROLES = {
        UserRole.DRIVER,
        UserRole.FLEET_OPERATOR,
        UserRole.SHIPPER,
        UserRole.COMMUNITY_NODE_MANAGER,
        UserRole.MINISTRY_ADMIN,
        UserRole.SUPER_ADMIN,
    }

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self._ALLOWED_ROLES
        )


class CanManageVehicles(BasePermission):
    """FLEET_OPERATOR and SUPER_ADMIN can manage vehicles."""
    message = "Only fleet operators and super admins can manage vehicles."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.FLEET_OPERATOR, UserRole.SUPER_ADMIN)
        )


class CanManageFleet(BasePermission):
    """FLEET_OPERATOR, MINISTRY_ADMIN, and SUPER_ADMIN can manage fleet optimization."""
    message = "Only fleet operators and administrators can manage fleet operations."
    _ALLOWED_ROLES = {UserRole.FLEET_OPERATOR, UserRole.MINISTRY_ADMIN, UserRole.SUPER_ADMIN}

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role in self._ALLOWED_ROLES or request.user.is_admin_level)
        )


class CanCreateTrip(BasePermission):
    """DRIVER, FLEET_OPERATOR, and SUPER_ADMIN can create trips."""
    message = "You do not have permission to create trips."
    _ALLOWED_ROLES = {UserRole.DRIVER, UserRole.FLEET_OPERATOR, UserRole.SUPER_ADMIN}

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self._ALLOWED_ROLES
        )


class CanManageTransportGraph(BasePermission):
    """
    MINISTRY_ADMIN and SUPER_ADMIN can modify the transport graph (nodes/edges).
    Read access is granted to all authenticated users via their view's permission_classes.
    """
    message = "Only ministry or super administrators can modify the transport graph."
    _ALLOWED_ROLES = {UserRole.MINISTRY_ADMIN, UserRole.SUPER_ADMIN}

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self._ALLOWED_ROLES
        )


class IsAuthenticatedAndVerified(BasePermission):
    """
    Any user that is authenticated and whose account is active.
    Acts as a combined guard replacing the common pattern of
    ``IsAuthenticated`` + manual ``is_active`` check in views.
    """
    message = "Authentication required. Ensure your account is active."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )
