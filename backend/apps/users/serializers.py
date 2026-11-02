"""
SIH26002 — User serializers.
"""
from rest_framework import serializers

from .models import Language, User, UserRole


class UserProfileSerializer(serializers.ModelSerializer):
    """Read/update own profile. Password excluded."""

    full_name = serializers.ReadOnlyField()
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "role_display",
            "preferred_language",
            "is_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "email", "role", "is_verified", "created_at", "updated_at"]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Allows user to update their own mutable profile fields."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "preferred_language"]

    def validate_preferred_language(self, value):
        valid = [lang[0] for lang in Language.choices]
        if value not in valid:
            raise serializers.ValidationError(
                f"Invalid language. Choose from: {', '.join(valid)}"
            )
        return value


class AdminUserListSerializer(serializers.ModelSerializer):
    """Minimal user listing for admin views."""

    class Meta:
        model = User
        fields = ["id", "email", "phone", "first_name", "last_name", "role", "is_active", "is_verified", "created_at"]
        read_only_fields = fields
