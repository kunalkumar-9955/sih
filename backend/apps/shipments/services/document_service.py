"""
SIH26002 — Cryptographic Digital Shipment Document & QR Service.

Provides:
- Opaque, HMAC-SHA256 signed digital e-way references (no plain PII in QR)
- Anti-tamper token verification
- Dynamic SVG / Base64 QR code payload generation
- Automated sensor attachment for cold-chain shipments
"""
import hmac
import hashlib
import json
import uuid
import logging
from typing import Dict, Any, Tuple
from django.conf import settings
from django.utils import timezone

from apps.shipments.models import (
    DigitalShipmentDocument,
    ShipmentTrackingEvent,
    ColdChainSensor,
    DocumentStatus,
    TrackingEventType,
    ColdChainStatus,
)

logger = logging.getLogger(__name__)


class DigitalShipmentDocumentService:
    """
    Cryptographically secure generation and validation for digital freight documents.
    """

    @classmethod
    def get_signing_secret(cls) -> str:
        return getattr(settings, "SECRET_KEY", "sih26002-freight-signing-secret")

    @classmethod
    def generate_hmac_token(cls, shipment_number: str, valid_until: Any) -> str:
        """
        Creates an opaque HMAC-SHA256 signature token.
        Format: SIG1.<shipment_number>.<hmac_hex[:32]>
        Contains NO personally identifiable information.
        """
        secret = cls.get_signing_secret().encode("utf-8")
        payload = f"{shipment_number}:{valid_until.isoformat()}".encode("utf-8")
        sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()[:32]
        return f"SIG1.{shipment_number}.{sig}"

    @classmethod
    def verify_token(cls, token: str) -> Tuple[bool, str, Optional[DigitalShipmentDocument]]:
        """
        Validates token format, cryptographic signature, and document validity window.
        """
        if not token or not token.startswith("SIG1."):
            return False, "Malformed token format. Must start with SIG1 prefix.", None

        parts = token.split(".")
        if len(parts) != 3:
            return False, "Invalid token structure.", None

        _, shipment_num, signature = parts
        document = DigitalShipmentDocument.objects.filter(shipment_number=shipment_num).first()
        if not document:
            return False, f"Shipment document '{shipment_num}' not found.", None

        # Check signature with constant-time compare
        secret = cls.get_signing_secret().encode("utf-8")
        payload = f"{document.shipment_number}:{document.valid_until.isoformat()}".encode("utf-8")
        expected_sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()[:32]

        if not hmac.compare_digest(signature, expected_sig):
            return False, "Cryptographic signature verification failed (tampering detected).", document

        # Check expiration
        if document.valid_until < timezone.now():
            return False, f"Document expired at {document.valid_until.isoformat()}.", document

        if document.document_status == DocumentStatus.REVOKED:
            return False, "Document has been revoked by authority.", document

        return True, "Valid and authentic.", document

    @classmethod
    def generate_qr_payload(cls, document: DigitalShipmentDocument) -> str:
        """
        Generates clean JSON payload embedded inside the QR code.
        """
        payload = {
            "token": document.secure_qr_token,
            "shipment_number": document.shipment_number,
            "origin": document.origin_name,
            "destination": document.destination_name,
            "valid_until": document.valid_until.isoformat(),
            "authority": "MDoNER / State Transport Authority",
        }
        return json.dumps(payload)

    @classmethod
    def generate_document_for_bid(cls, bid: Any, user: Any) -> DigitalShipmentDocument:
        """
        Issues an official DigitalShipmentDocument upon carrier bid acceptance.
        """
        listing = bid.listing
        load = listing.load

        now = timezone.now()
        valid_until = now + timezone.timedelta(days=7)
        shipment_num = f"SHIP-{uuid.uuid4().hex[:8].upper()}"
        qr_token = cls.generate_hmac_token(shipment_num, valid_until)

        driver = None
        if bid.proposed_vehicle and getattr(bid.proposed_vehicle, "assigned_driver", None):
            driver = bid.proposed_vehicle.assigned_driver

        origin = listing.origin_name
        dest = listing.destination_name
        weight = listing.weight_kg
        cargo_summary = f"{listing.cargo_type} ({weight} kg via {bid.proposed_mode})"

        document = DigitalShipmentDocument.objects.create(
            shipment_number=shipment_num,
            load=load,
            listing=listing,
            shipper=listing.shipper,
            carrier=bid.carrier,
            vehicle=bid.proposed_vehicle,
            driver=driver,
            origin_name=origin,
            destination_name=dest,
            cargo_summary=cargo_summary,
            weight_kg=weight,
            route_version="1.0.0",
            secure_qr_token=qr_token,
            document_status=DocumentStatus.ACTIVE,
            generated_at=now,
            valid_until=valid_until,
        )

        # Attach cold-chain IoT sensor if refrigerated cargo
        if listing.is_cold_chain:
            sensor_code = f"CC-IOT-{uuid.uuid4().hex[:6].upper()}"
            min_t = listing.target_temp_min if listing.target_temp_min is not None else 2.0
            max_t = listing.target_temp_max if listing.target_temp_max is not None else 8.0
            ColdChainSensor.objects.create(
                sensor_code=sensor_code,
                document=document,
                current_temperature=4.2,
                current_humidity=65.0,
                battery_percentage=98.0,
                status=ColdChainStatus.NORMAL,
                min_threshold=min_t,
                max_threshold=max_t,
                last_reading_at=now,
                is_simulation=True,
            )

        # Record tracking milestone
        ShipmentTrackingEvent.objects.create(
            document=document,
            event_type=TrackingEventType.BID_ACCEPTED,
            location_name=origin,
            notes=f"Carrier bid INR {bid.price_inr} accepted. E-Way document generated.",
            recorded_at=now,
        )

        return document
