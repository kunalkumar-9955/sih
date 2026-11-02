"""
SIH26002 — Core exception handler.

Provides consistent JSON error responses across the entire API.
"""
import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("sih.core")


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that returns a consistent JSON envelope:

    {
        "success": false,
        "error": {
            "code": "error_code",
            "message": "Human-readable message",
            "details": {...}   # optional
        }
    }
    """
    # First call DRF's default handler
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            "success": False,
            "error": {
                "code": _get_error_code(exc),
                "message": _extract_message(response.data),
                "details": response.data if isinstance(response.data, dict) else None,
            },
        }
        response.data = error_data
        return response

    # Handle Django exceptions not caught by DRF
    if isinstance(exc, Http404):
        return Response(
            {
                "success": False,
                "error": {"code": "not_found", "message": "Resource not found."},
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, PermissionDenied):
        return Response(
            {
                "success": False,
                "error": {"code": "permission_denied", "message": "Permission denied."},
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, ValidationError):
        return Response(
            {
                "success": False,
                "error": {
                    "code": "validation_error",
                    "message": "Validation failed.",
                    "details": exc.message_dict if hasattr(exc, "message_dict") else str(exc),
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Unhandled — log and return 500
    logger.exception("Unhandled exception in API view: %s", exc)
    return Response(
        {
            "success": False,
            "error": {"code": "internal_error", "message": "An internal error occurred."},
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _get_error_code(exc) -> str:
    """Map exception type to a short error code string."""
    exc_type = type(exc).__name__
    code_map = {
        "AuthenticationFailed": "authentication_failed",
        "NotAuthenticated": "not_authenticated",
        "PermissionDenied": "permission_denied",
        "NotFound": "not_found",
        "MethodNotAllowed": "method_not_allowed",
        "ValidationError": "validation_error",
        "ParseError": "parse_error",
        "Throttled": "rate_limited",
        "TokenError": "token_error",
        "InvalidToken": "invalid_token",
    }
    return code_map.get(exc_type, "error")


def _extract_message(data) -> str:
    """Extract a human-readable message from DRF error data."""
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        # Flatten first field error
        for _key, value in data.items():
            if isinstance(value, list) and value:
                return str(value[0])
            return str(value)
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data)
