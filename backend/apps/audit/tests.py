"""
SIH26002 — Audit logging tests.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.audit.decorators import audit_log
from apps.audit.models import AuditLog
from apps.users.models import UserRole

User = get_user_model()


@pytest.mark.django_db
class TestAuditLog:

    def test_audit_log_creation(self):
        user = User.objects.create_user(
            email="admin@ner.in", password="Password123!", role=UserRole.SUPER_ADMIN
        )
        audit_log(
            actor=user,
            action="TEST_ACTION",
            resource_type="TestResource",
            resource_id="12345",
            payload={"key": "value"},
        )
        assert AuditLog.objects.filter(actor=user, action="TEST_ACTION").exists()
        log = AuditLog.objects.get(actor=user, action="TEST_ACTION")
        assert log.resource_type == "TestResource"
        assert log.payload == {"key": "value"}
