"""
SIH26002 — Checkpost Serializers.
"""
from rest_framework import serializers
from apps.checkposts.models import Checkpost, CheckpostVerification


class CheckpostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Checkpost
        fields = ["id", "name", "code", "authority", "node", "is_active"]
        read_only_fields = fields


class CheckpostVerificationSerializer(serializers.ModelSerializer):
    checkpost_name = serializers.ReadOnlyField(source="checkpost.name")
    checkpost_code = serializers.ReadOnlyField(source="checkpost.code")
    shipment_number = serializers.ReadOnlyField(source="document.shipment_number")

    class Meta:
        model = CheckpostVerification
        fields = [
            "id",
            "checkpost",
            "checkpost_name",
            "checkpost_code",
            "document",
            "shipment_number",
            "verified_by",
            "verification_result",
            "vehicle_matched",
            "driver_matched",
            "cargo_matched",
            "route_matched",
            "reason",
            "is_offline_verification",
            "sync_status",
            "raw_qr_token",
            "verified_at",
            "audit_metadata",
        ]
        read_only_fields = fields
