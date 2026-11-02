"""
SIH26002 — Driver model.
"""
import uuid

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Driver(BaseModel):
    """
    Driver profile linked 1:1 to a User with DRIVER role.

    Stores license details and operational metadata.
    Created automatically after user registration via signal or
    explicitly via the driver profile API.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile",
        db_index=True,
    )

    # License
    license_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    license_expiry = models.DateField(null=True, blank=True)
    license_state = models.CharField(max_length=50, blank=True)

    # Location / home base
    home_state = models.CharField(max_length=100, blank=True)
    home_district = models.CharField(max_length=100, blank=True)

    # Verification status
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    # Experience
    years_of_experience = models.PositiveSmallIntegerField(default=0)

    # Emergency contact
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "drivers_driver"
        verbose_name = "Driver"
        verbose_name_plural = "Drivers"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Driver: {self.user.email} ({self.license_number or 'no license'})"

    @property
    def is_license_valid(self) -> bool:
        """Returns True if license is set and not expired."""
        import datetime
        if not self.license_expiry:
            return False
        return self.license_expiry >= datetime.date.today()
