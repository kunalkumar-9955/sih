"""
SIH26002 — Audit middleware.
Records all API requests (method, path, status, actor) for observability.
Heavy-volume endpoints can be excluded via AUDIT_EXCLUDE_PATHS setting.
"""
import logging
import time
import uuid

logger = logging.getLogger("sih.audit")

_EXCLUDE_PATHS = {
    "/api/v1/health/",
    "/api/v1/health/db/",
    "/api/v1/health/redis/",
}


class AuditMiddleware:
    """
    Lightweight request logging middleware with request correlation tracking.
    Propagates X-Correlation-ID for end-to-end distributed tracing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.correlation_id = correlation_id

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        # Attach correlation ID to response headers
        response["X-Correlation-ID"] = correlation_id

        if request.path not in _EXCLUDE_PATHS and request.path.startswith("/api/"):
            user_id = None
            if hasattr(request, "user") and request.user.is_authenticated:
                user_id = str(request.user.id)

            logger.info(
                "[cid=%s] API %s %s → %s  %.2fms  user=%s",
                correlation_id,
                request.method,
                request.path,
                response.status_code,
                duration_ms,
                user_id or "anon",
            )

        return response

