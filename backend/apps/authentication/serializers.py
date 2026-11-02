"""
SIH26002 — Authentication serializers.
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import Language, User, UserRole


class RegisterSerializer(serializers.Serializer):
    """
    User registration serializer.
    Creates the user and returns JWT tokens.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=UserRole.choices, default=UserRole.DRIVER)
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    preferred_language = serializers.ChoiceField(
        choices=Language.choices, default=Language.ENGLISH, required=False
    )

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate(self, data: dict) -> dict:
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data: dict) -> dict:
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        # SUPER_ADMIN cannot be self-registered
        if validated_data.get("role") == UserRole.SUPER_ADMIN:
            raise serializers.ValidationError(
                {"role": "SUPER_ADMIN accounts cannot be self-registered."}
            )
        user = User.objects.create_user(password=password, **validated_data)
        tokens = RefreshToken.for_user(user)
        return {
            "user": user,
            "access": str(tokens.access_token),
            "refresh": str(tokens),
        }


class LoginSerializer(serializers.Serializer):
    """
    Email + password login. Returns JWT tokens.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data: dict) -> dict:
        user = authenticate(
            request=self.context.get("request"),
            email=data["email"].lower(),
            password=data["password"],
        )
        if not user:
            raise serializers.ValidationError(
                {"non_field_errors": ["Invalid email or password."]}
            )
        if not user.is_active:
            raise serializers.ValidationError(
                {"non_field_errors": ["This account is inactive."]}
            )
        data["user"] = user
        return data


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Response for token refresh."""

    access = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    """Accepts refresh token for blacklisting."""

    refresh = serializers.CharField()
