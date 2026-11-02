"""
SIH26002 — Core base models.

All domain models inherit from TimestampedModel (created_at, updated_at)
and UUIDModel (UUID primary key) to enforce consistency.
"""
import uuid

from django.db import models


class UUIDModel(models.Model):
    """Abstract model providing a UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """Abstract model providing created_at and updated_at timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class BaseModel(UUIDModel, TimestampedModel):
    """
    Base model combining UUID PK and timestamps.
    All SIH26002 domain models should inherit from this.
    """

    class Meta:
        abstract = True
        ordering = ["-created_at"]
