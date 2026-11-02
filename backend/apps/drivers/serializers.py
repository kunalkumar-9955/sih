"""
SIH26002 — Driver serializers.
"""
from rest_framework import serializers

from .models import Driver


class DriverProfileSerializer(serializers.ModelSerializer):
    """Full driver profile read."""

    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    is_license_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Driver
        fields = [
            "id",
            "email",
            "full_name",
            "license_number",
            "license_expiry",
            "license_state",
            "home_state",
            "home_district",
            "is_verified",
            "verified_at",
            "years_of_experience",
            "emergency_contact_name",
            "emergency_contact_phone",
            "is_license_valid",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_verified", "verified_at", "created_at", "updated_at"]


class DriverProfileUpdateSerializer(serializers.ModelSerializer):
    """Driver updating their own profile."""

    class Meta:
        model = Driver
        fields = [
            "license_number",
            "license_expiry",
            "license_state",
            "home_state",
            "home_district",
            "years_of_experience",
            "emergency_contact_name",
            "emergency_contact_phone",
        ]
