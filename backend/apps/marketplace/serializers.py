"""
SIH26002 — Marketplace Serializers.
"""
from rest_framework import serializers
from apps.marketplace.models import (
    MarketplaceListing,
    FreightBid,
    SmsCommand,
    IvrSession,
    ListingStatus,
    BidStatus,
    TransportModeOption,
)


class FreightBidSerializer(serializers.ModelSerializer):
    carrier_email = serializers.ReadOnlyField(source="carrier.email")
    vehicle_registration = serializers.ReadOnlyField(source="proposed_vehicle.registration_number")

    class Meta:
        model = FreightBid
        fields = [
            "id",
            "listing",
            "carrier",
            "carrier_email",
            "proposed_vehicle",
            "vehicle_registration",
            "proposed_mode",
            "price_inr",
            "estimated_transit_hours",
            "eta",
            "validity_period",
            "capacity_offered_kg",
            "terms",
            "operator_rating",
            "status",
            "ai_recommendation_score",
            "ai_recommendation_factors",
            "recommendation_explanation",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "carrier",
            "status",
            "ai_recommendation_score",
            "ai_recommendation_factors",
            "recommendation_explanation",
            "created_at",
        ]


class MarketplaceListingSerializer(serializers.ModelSerializer):
    shipper_email = serializers.ReadOnlyField(source="shipper.email")
    bids = FreightBidSerializer(many=True, read_only=True)
    bids_count = serializers.SerializerMethodField()

    class Meta:
        model = MarketplaceListing
        fields = [
            "id",
            "listing_code",
            "shipper",
            "shipper_email",
            "load",
            "title",
            "origin_name",
            "destination_name",
            "weight_kg",
            "volume_cbm",
            "cargo_type",
            "pickup_window_start",
            "pickup_window_end",
            "delivery_deadline",
            "preferred_modes",
            "max_budget_inr",
            "special_requirements",
            "is_cold_chain",
            "target_temp_min",
            "target_temp_max",
            "status",
            "published_at",
            "expires_at",
            "created_at",
            "bids_count",
            "bids",
        ]
        read_only_fields = ["id", "listing_code", "shipper", "status", "published_at", "expires_at", "created_at"]

    def get_bids_count(self, obj: MarketplaceListing) -> int:
        return obj.bids.count()


class SmsCommandSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsCommand
        fields = ["id", "phone_number", "raw_command", "parsed_action", "shipment_id", "response_message", "is_simulation", "created_at"]
        read_only_fields = fields


class IvrSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = IvrSession
        fields = ["id", "session_id", "phone_number", "language", "current_step", "selected_option", "transcript_log", "is_simulation", "created_at"]
        read_only_fields = fields
