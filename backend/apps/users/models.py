"""
SIH26002 — User model with RBAC role system.

Design decisions:
- Custom AbstractBaseUser for full control over auth fields.
- Role stored as a single CharField with choices (not Django groups)
  to keep the RBAC model simple and explicit for Milestone 1.
- Preferred language stored on user for multilingual UX.
- Phone number stored for SMS/IVR channels.
- UUID primary key throughout.
"""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserRole(models.TextChoices):
    """
    RBAC roles for SIH26002.
    Every user has exactly one role.
    """
    DRIVER = "DRIVER", "Driver"
    FLEET_OPERATOR = "FLEET_OPERATOR", "Fleet Operator"
    SHIPPER = "SHIPPER", "Shipper"
    CHECKPOST_OPERATOR = "CHECKPOST_OPERATOR", "Checkpost Operator"
    COMMUNITY_NODE_MANAGER = "COMMUNITY_NODE_MANAGER", "Community Node Manager"
    MINISTRY_ADMIN = "MINISTRY_ADMIN", "Ministry Admin"
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"


class Language(models.TextChoices):
    """
    Supported UI languages for the NER region.
    Maps to l10n keys in the Flutter app.
    """
    ENGLISH = "en", "English"
    HINDI = "hi", "Hindi"
    ASSAMESE = "as", "Assamese"
    MANIPURI = "mni", "Manipuri"
    BENGALI = "bn", "Bengali"
    KHASI = "kha", "Khasi"


class UserManager(BaseUserManager):
    """Custom manager for the SIH26002 User model."""

    def create_user(self, email: str, password: str = None, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", UserRole.DRIVER)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)
        extra_fields.setdefault("is_verified", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    SIH26002 custom user model.

    Uses email as the primary identifier instead of username.
    Role-based access is controlled via the `role` field.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identity
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True, null=True, unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    # RBAC
    role = models.CharField(
        max_length=30,
        choices=UserRole.choices,
        default=UserRole.DRIVER,
        db_index=True,
    )

    # Localisation
    preferred_language = models.CharField(
        max_length=10,
        choices=Language.choices,
        default=Language.ENGLISH,
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    objects = UserManager()

    class Meta:
        db_table = "users_user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["email", "is_active"]),
        ]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return f"{self.email} ({self.get_role_display()})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    # ── Role helpers ──────────────────────────────────────────────────────────
    @property
    def is_driver(self) -> bool:
        return self.role == UserRole.DRIVER

    @property
    def is_fleet_operator(self) -> bool:
        return self.role == UserRole.FLEET_OPERATOR

    @property
    def is_shipper(self) -> bool:
        return self.role == UserRole.SHIPPER

    @property
    def is_checkpost_operator(self) -> bool:
        return self.role == UserRole.CHECKPOST_OPERATOR

    @property
    def is_community_node_manager(self) -> bool:
        return self.role == UserRole.COMMUNITY_NODE_MANAGER

    @property
    def is_ministry_admin(self) -> bool:
        return self.role == UserRole.MINISTRY_ADMIN

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_admin_level(self) -> bool:
        """True for MINISTRY_ADMIN and SUPER_ADMIN."""
        return self.role in (UserRole.MINISTRY_ADMIN, UserRole.SUPER_ADMIN)
