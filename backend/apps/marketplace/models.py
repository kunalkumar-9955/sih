"""
SIH26002 — Multimodal Freight Marketplace & Bidding Models.
"""
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class ListingStatus(models.TextChoices):
    """Lifecycle statuses for a marketplace listing."""
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published / Open"
    BIDDING = "BIDDING", "Active Bidding"
    MATCHED = "MATCHED", "Matched / Bid Accepted"
    IN_TRANSIT = "IN_TRANSIT", "In Transit"
    DELIVERED = "DELIVERED", "Delivered"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


class BidStatus(models.TextChoices):
    """Lifecycle statuses for a carrier freight bid."""
    SUBMITTED = "SUBMITTED", "Submitted"
    ACTIVE = "ACTIVE", "Active / Under Review"
    ACCEPTED = "ACCEPTED", "Accepted / Awarded"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"
    WITHDRAWN = "WITHDRAWN", "Withdrawn by Carrier"


class TransportModeOption(models.TextChoices):
    """Multimodal transport mode options for freight proposals."""
    ROAD = "ROAD", "Direct Road Transit"
    RAIL = "RAIL", "Indian Railways Freight (FOIS)"
    WATERWAY = "WATERWAY", "Inland Waterway (NW-2 Brahmaputra)"
    ROAD_RAIL = "ROAD_RAIL", "Intermodal Road + Rail"
    ROAD_WATERWAY = "ROAD_WATERWAY", "Intermodal Road + Inland Waterway"
    MULTIMODAL = "MULTIMODAL", "Multimodal Road + Rail + Waterway"


def generate_listing_code() -> str:
    return f"MKT-{uuid.uuid4().hex[:8].upper()}"


class MarketplaceListing(BaseModel):
    """
    Public or invite-only freight requirement created by verified Shippers
    for competitive multimodal carrier bidding.
    """
    listing_code = models.CharField(
        max_length=32,
        unique=True,
        default=generate_listing_code,
        db_index=True,
    )
    shipper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="marketplace_listings",
        db_index=True,
    )
    load = models.ForeignKey(
        "fleet.FreightLoad",
        on_delete=models.CASCADE,
        related_name="marketplace_listings",
        null=True,
        blank=True,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    origin_name = models.CharField(max_length=200)
    destination_name = models.CharField(max_length=200)
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    volume_cbm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    cargo_type = models.CharField(max_length=50, default="GENERAL")
    
    pickup_window_start = models.DateTimeField(null=True, blank=True)
    pickup_window_end = models.DateTimeField(null=True, blank=True)
    delivery_deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    
    preferred_modes = models.JSONField(
        default=list,
        blank=True,
        help_text="e.g. ['ROAD', 'RAIL', 'WATERWAY', 'MULTIMODAL']",
    )
    max_budget_inr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    special_requirements = models.JSONField(default=list, blank=True)
    
    # Cold-chain requirements
    is_cold_chain = models.BooleanField(default=False, db_index=True)
    target_temp_min = models.FloatField(null=True, blank=True, help_text="Min temp in Celsius")
    target_temp_max = models.FloatField(null=True, blank=True, help_text="Max temp in Celsius")

    status = models.CharField(
        max_length=20,
        choices=ListingStatus.choices,
        default=ListingStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "marketplace_listing"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "is_cold_chain"]),
            models.Index(fields=["shipper", "status"]),
        ]
        verbose_name = "Marketplace Listing"
        verbose_name_plural = "Marketplace Listings"

    def __str__(self) -> str:
        return f"{self.listing_code} ({self.title} - {self.status})"


class FreightBid(BaseModel):
    """
    Commercial & operational bid submitted by a licensed Logistics Operator / Carrier.
    """
    listing = models.ForeignKey(
        MarketplaceListing,
        on_delete=models.CASCADE,
        related_name="bids",
        db_index=True,
    )
    carrier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_bids",
        db_index=True,
    )
    proposed_vehicle = models.ForeignKey(
        "vehicles.Vehicle",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketplace_bids",
    )
    proposed_mode = models.CharField(
        max_length=30,
        choices=TransportModeOption.choices,
        default=TransportModeOption.ROAD,
        db_index=True,
    )
    price_inr = models.DecimalField(max_digits=12, decimal_places=2)
    estimated_transit_hours = models.FloatField(default=12.0)
    eta = models.DateTimeField(null=True, blank=True)
    validity_period = models.DateTimeField(null=True, blank=True)
    capacity_offered_kg = models.DecimalField(max_digits=10, decimal_places=2, default=5000.0)
    terms = models.TextField(blank=True)
    operator_rating = models.FloatField(default=4.5)

    status = models.CharField(
        max_length=20,
        choices=BidStatus.choices,
        default=BidStatus.SUBMITTED,
        db_index=True,
    )

    # Explainable AI Recommendation Scoring (0 - 100)
    ai_recommendation_score = models.FloatField(default=0.0)
    ai_recommendation_factors = models.JSONField(
        default=dict,
        blank=True,
        help_text="Itemized subscores for cost, eta, route risk, vehicle fit, operator reliability",
    )
    recommendation_explanation = models.TextField(blank=True)

    class Meta:
        db_table = "marketplace_freight_bid"
        ordering = ["-ai_recommendation_score", "price_inr"]
        indexes = [
            models.Index(fields=["listing", "status"]),
            models.Index(fields=["carrier", "status"]),
        ]
        verbose_name = "Freight Bid"
        verbose_name_plural = "Freight Bids"

    def __str__(self) -> str:
        return f"Bid #{str(self.id)[:8]} on {self.listing.listing_code} by {self.carrier.email} (INR {self.price_inr})"


class SmsCommand(BaseModel):
    """
    Audit record of inbound SMS commands received via SMS gateway abstraction.
    """
    phone_number = models.CharField(max_length=20, db_index=True)
    raw_command = models.CharField(max_length=255)
    parsed_action = models.CharField(max_length=32, db_index=True)
    shipment_id = models.CharField(max_length=64, blank=True)
    response_message = models.TextField()
    is_simulation = models.BooleanField(default=True)

    class Meta:
        db_table = "marketplace_sms_command"
        ordering = ["-created_at"]
        verbose_name = "SMS Command"
        verbose_name_plural = "SMS Commands"


class IvrSession(BaseModel):
    """
    Audit log of interactive voice response (IVR) phone calls for feature phones.
    """
    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    phone_number = models.CharField(max_length=20, db_index=True)
    language = models.CharField(max_length=10, default="en")
    current_step = models.CharField(max_length=32, default="MAIN_MENU")
    selected_option = models.CharField(max_length=32, blank=True)
    transcript_log = models.JSONField(default=list, blank=True)
    is_simulation = models.BooleanField(default=True)

    class Meta:
        db_table = "marketplace_ivr_session"
        ordering = ["-created_at"]
        verbose_name = "IVR Session"
        verbose_name_plural = "IVR Sessions"
