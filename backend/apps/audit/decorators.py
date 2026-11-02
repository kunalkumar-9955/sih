"""
SIH26002 — Audit decorator & helper.

Usage (decorator):
    @audit_action("resource.action")
    def my_view_method(self, request, ...):
        ...

Usage (direct call):
    audit_log(actor=user, action="trip.create", resource_type="Trip",
              resource_id=str(trip.id), payload={"key": "value"})

The decorator records the action to AuditLog after the view executes.
On exception, it records outcome=FAILURE.
``audit_log`` is an alias for the direct-write helper so both the
decorator-based and imperative usages can import from this module.
"""
import functools
import logging

logger = logging.getLogger("sih.audit")


def audit_log(
    actor=None,
    action: str = "",
    resource_type: str = "",
    resource_id: str = "",
    payload: dict = None,
    ip_address: str = "",
    user_agent: str = "",
    outcome: str = None,
):
    """
    Standalone helper to write an AuditLog entry imperatively.

    Never raises — audit failures are swallowed and logged at ERROR level
    so that a failing audit write never crashes the calling code path.
    """
    from .models import AuditLog

    try:
        AuditLog.objects.create(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else "",
            payload=payload or {},
            outcome=outcome or AuditLog.SUCCESS,
        )
    except Exception as exc:
        logger.error("Failed to write audit log for action '%s': %s", action, exc)


def audit_action(action: str, resource_type: str = None):
    """
    Decorator for DRF view methods that automatically creates an AuditLog entry.

    Args:
        action: dot-notation action name, e.g. 'auth.logout', 'trip.create'
        resource_type: optional resource type string, e.g. 'Trip'
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, request, *args, **kwargs):
            from .models import AuditLog

            actor = request.user if request.user.is_authenticated else None
            ip_address = _get_client_ip(request)
            resource_id = str(kwargs.get("pk", ""))

            outcome = AuditLog.SUCCESS
            try:
                response = func(self, request, *args, **kwargs)
                return response
            except Exception as exc:
                outcome = AuditLog.FAILURE
                raise exc
            finally:
                try:
                    AuditLog.objects.create(
                        actor=actor,
                        action=action,
                        resource_type=resource_type or "",
                        resource_id=resource_id,
                        ip_address=ip_address,
                        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                        payload={
                            "method": request.method,
                            "path": request.path,
                        },
                        outcome=outcome,
                    )
                except Exception as audit_exc:
                    # Never let audit failure crash the main request
                    logger.error("Failed to write audit log for action '%s': %s", action, audit_exc)

        return wrapper

    return decorator


def _get_client_ip(request) -> str:
    """Extract real client IP, handling proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
