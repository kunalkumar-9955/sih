"""
SIH26002 — Audit log model.

Every sensitive action in the system is recorded here.
Audit records are append-only — never updated or deleted.
"""
import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Immutable audit record for every tracked system action.

    Design:
    - id is a UUID for global uniqueness.
    - actor is nullable (system actions may have no user).
    - payload stores request/response snapshot as JSONB.
    - Records must never be deleted or updated.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        db_index=True,
    )

    # What happened
    action = models.CharField(max_length=200, db_index=True)

    # What resource was affected
    resource_type = models.CharField(max_length=100, blank=True, null=True)
    resource_id = models.CharField(max_length=100, blank=True, null=True)

    # Context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)

    # Structured payload (request body snapshot, outcome, etc.)
    payload = models.JSONField(default=dict, blank=True)

    # Outcome
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    OUTCOME_CHOICES = [(SUCCESS, "Success"), (FAILURE, "Failure")]
    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES, default=SUCCESS)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_auditlog"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "action"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["action", "created_at"]),
        ]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self) -> str:
        actor_email = self.actor.email if self.actor else "system"
        return f"[{self.created_at}] {actor_email} → {self.action}"

    def save(self, *args, **kwargs):
        """Prevent updates to audit records (append-only)."""
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("Audit log records are immutable and cannot be updated.")
        super().save(*args, **kwargs)
