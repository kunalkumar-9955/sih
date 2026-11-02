"""
SIH26002 — Authentication views.

POST /api/v1/auth/register/   → Create user + return JWT
POST /api/v1/auth/login/      → Validate credentials + return JWT
POST /api/v1/auth/refresh/    → Rotate access token
POST /api/v1/auth/logout/     → Blacklist refresh token
GET  /api/v1/auth/me/         → Return current user info
"""
import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.decorators import audit_action
from apps.users.serializers import UserProfileSerializer

from .serializers import LoginSerializer, LogoutSerializer, RegisterSerializer

logger = logging.getLogger("sih.authentication")


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    Public endpoint. Creates user account and returns tokens.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        user = result["user"]

        logger.info("New user registered: %s (%s)", user.email, user.role)

        return Response(
            {
                "success": True,
                "message": "Account created successfully.",
                "data": {
                    "user": UserProfileSerializer(user).data,
                    "tokens": {
                        "access": result["access"],
                        "refresh": result["refresh"],
                    },
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Validates credentials, returns JWT access + refresh tokens.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        tokens = RefreshToken.for_user(user)

        logger.info("User logged in: %s", user.email)

        return Response(
            {
                "success": True,
                "data": {
                    "user": UserProfileSerializer(user).data,
                    "tokens": {
                        "access": str(tokens.access_token),
                        "refresh": str(tokens),
                    },
                },
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    """
    POST /api/v1/auth/refresh/
    Accepts a refresh token and returns a new access token.
    Uses simplejwt's rotation (refresh is also rotated if ROTATE_REFRESH_TOKENS=True).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"success": False, "error": {"code": "missing_token", "message": "Refresh token is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            return Response(
                {
                    "success": True,
                    "data": {
                        "access": str(token.access_token),
                        "refresh": str(token) if token else None,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except TokenError as e:
            return Response(
                {"success": False, "error": {"code": "invalid_token", "message": str(e)}},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklists the provided refresh token. Requires authentication.
    """

    permission_classes = [IsAuthenticated]

    @audit_action("auth.logout")
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
            logger.info("User logged out: %s", request.user.email)
            return Response(
                {"success": True, "message": "Logged out successfully."},
                status=status.HTTP_200_OK,
            )
        except TokenError as e:
            return Response(
                {"success": False, "error": {"code": "invalid_token", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeView(APIView):
    """
    GET /api/v1/auth/me/
    Returns the currently authenticated user's profile.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {"success": True, "data": UserProfileSerializer(request.user).data},
            status=status.HTTP_200_OK,
        )
