"""
SIH26002 — Script to create initial super admin user.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

def create_admin():
    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from apps.users.models import UserRole

    User = get_user_model()
    email = os.environ.get("ADMIN_EMAIL", "admin@sih26002.gov.in")
    password = os.environ.get("ADMIN_PASSWORD", "Admin@SIH26002!")

    if not User.objects.filter(email=email).exists():
        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name="Ministry",
            last_name="Admin",
            role=UserRole.SUPER_ADMIN,
            is_verified=True,
        )
        print(f"Superadmin created: {email}")
    else:
        print(f"Superadmin already exists: {email}")

    # Ensure demo driver exists
    driver_email = os.environ.get("DRIVER_EMAIL", "driver1@ner.gov.in")
    driver_password = os.environ.get("DRIVER_PASSWORD", "SecurePassword123!")
    driver_user = User.objects.filter(email=driver_email).first()
    if not driver_user:
        driver_user = User.objects.create_user(
            email=driver_email,
            password=driver_password,
            first_name="Tenzing",
            last_name="Norbu",
            role=UserRole.DRIVER,
            is_verified=True,
        )
        print(f"Demo driver created: {driver_email}")
    else:
        driver_user.set_password(driver_password)
        driver_user.is_active = True
        driver_user.save()
        print(f"Demo driver password synchronized: {driver_email}")

    from apps.drivers.models import Driver
    Driver.objects.get_or_create(
        user=driver_user,
        defaults={
            "license_number": "AS-01-2024-0099",
            "license_state": "Assam",
            "is_verified": True,
            "years_of_experience": 8,
        },
    )

if __name__ == "__main__":
    create_admin()
