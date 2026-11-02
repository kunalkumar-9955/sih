"""
SIH26002 — Checkpost Verification Views.
"""
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.checkposts.models import Checkpost, CheckpostVerification
from apps.checkposts.serializers import CheckpostSerializer, CheckpostVerificationSerializer
from apps.checkposts.services.verification_service import CheckpostVerificationService


class CheckpostListView(APIView):
    """
    List all registered border checkposts and weighbridge terminals.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        checkposts = Checkpost.objects.filter(is_active=True).order_by("name")
        if not checkposts.exists():
            # Seed default checkposts for demonstration
            Checkpost.objects.get_or_create(code="CHK-JORABAT", defaults={"name": "Jorabat Inter-State Checkpost", "authority": "Assam-Meghalaya Joint Border Authority"})
            Checkpost.objects.get_or_create(code="CHK-BYRN", defaults={"name": "Byrnihat Commercial Toll Gate", "authority": "Meghalaya Transport Dept"})
            Checkpost.objects.get_or_create(code="CHK-UMROI", defaults={"name": "Umroi Highway Checkpoint", "authority": "Ri-Bhoi District Checkpost"})
            checkposts = Checkpost.objects.filter(is_active=True).order_by("name")

        return Response(CheckpostSerializer(checkposts, many=True).data)


class CheckpostVerificationView(APIView):
    """
    Execute QR token scan verification and retrieve audit history.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        chk_code = request.data.get("checkpost_code", "CHK-JORABAT")
        token = request.data.get("token", "")
        veh_reg = request.data.get("vehicle_reg")
        driver_id = request.data.get("driver_id")
        is_offline = request.data.get("is_offline", False)

        verifier = request.user if request.user.is_authenticated else None

        result = CheckpostVerificationService.verify_qr_scan(
            checkpost_code=chk_code,
            token=token,
            vehicle_reg=veh_reg,
            driver_id=driver_id,
            verifier_user=verifier,
            is_offline=is_offline,
        )

        return Response(result, status=status.HTTP_200_OK if result["is_valid"] else status.HTTP_200_OK)

    def get(self, request):
        events = CheckpostVerification.objects.all().select_related("checkpost", "document")[:50]
        return Response(CheckpostVerificationSerializer(events, many=True).data)
