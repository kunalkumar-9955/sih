"""
SIH26002 — Checkposts & Digital QR E-Way Verification Models.
"""
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class VerificationResult(models.TextChoices):
    """Outcomes of a checkpost cargo and document inspection."""
    VALID = "VALID", "Valid & Cleared"
    INVALID = "INVALID", "Invalid Cryptographic Token"
    EXPIRED = "EXPIRED", "Expired E-Way Validity Window"
    MISMATCH = "MISMATCH", "Discrepancy (Vehicle / Driver / Cargo)"
    BLOCKED = "BLOCKED", "Blocked by Authority / Corridor Alert"


class Checkpost(BaseModel):
    """
    Physical inspection barrier, weighbridge, or state border terminal in the NER network.
    """
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=32, unique=True, db_index=True)
    authority = models.CharField(
        max_length=150,
        default="State Transport Authority",
        help_text="e.g. Meghalaya Transport Dept, Assam Motor Vehicle Dept",
    )
    node = models.ForeignKey(
        "transport_graph.TransportNode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checkposts",
    )
    location = gis_models.PointField(srid=4326, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "checkposts_checkpost"
        ordering = ["name"]
        verbose_name = "Checkpost"
        verbose_name_plural = "Checkposts"

    def __str__(self) -> str:
        return f"{self.name} [{self.code}]"


class CheckpostVerification(BaseModel):
    """
    Audit log of every QR document scan and physical inspection event at a checkpost.
    """
    checkpost = models.ForeignKey(
        Checkpost,
        on_delete=models.CASCADE,
        related_name="verifications",
        db_index=True,
    )
    document = models.ForeignKey(
        "shipments.DigitalShipmentDocument",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verifications",
        db_index=True,
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conducted_verifications",
    )
    verification_result = models.CharField(
        max_length=20,
        choices=VerificationResult.choices,
        default=VerificationResult.VALID,
        db_index=True,
    )
    vehicle_matched = models.BooleanField(default=True)
    driver_matched = models.BooleanField(default=True)
    cargo_matched = models.BooleanField(default=True)
    route_matched = models.BooleanField(default=True)
    reason = models.TextField(blank=True)

    is_offline_verification = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if scanned and verified locally during cellular dead-zone outage.",
    )
    sync_status = models.CharField(max_length=20, default="SYNCED")
    raw_qr_token = models.CharField(max_length=512, blank=True)
    verified_at = models.DateTimeField(default=timezone.now, db_index=True)
    audit_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "checkposts_verification"
        ordering = ["-verified_at"]
        indexes = [
            models.Index(fields=["checkpost", "verification_result"]),
            models.Index(fields=["verified_at"]),
        ]
        verbose_name = "Checkpost Verification"
        verbose_name_plural = "Checkpost Verifications"

    def __str__(self) -> str:
        doc_num = self.document.shipment_number if self.document else "UNKNOWN"
        return f"Scan at {self.checkpost.code} -> {doc_num}: {self.verification_result}"
