"""
SIH26002 — SMS & IVR Low-Connectivity Fallback Gateways (Mock Providers).

Provides:
- Feature phone SMS command interface (STATUS, ROUTE, SYNC, SOS)
- Deterministic IVR voice tree simulation for remote hill drivers
- Explicit mock/demo labeling: is_simulation = True
"""
import uuid
import logging
from typing import Dict, Any, Optional

from apps.marketplace.models import SmsCommand, IvrSession
from apps.shipments.models import DigitalShipmentDocument

logger = logging.getLogger(__name__)


class SmsFallbackGateway:
    """
    Mock SMS gateway abstraction enabling drivers with basic 2G feature phones
    to query status, get route advisories, or trigger emergency distress.
    """

    @classmethod
    def process_incoming_sms(cls, phone_number: str, raw_text: str) -> Dict[str, Any]:
        cleaned = raw_text.strip()
        tokens = cleaned.split()
        cmd = tokens[0].upper() if tokens else "HELP"
        shipment_ref = tokens[1].upper() if len(tokens) > 1 else ""

        response_text = ""
        action = "UNKNOWN"

        if cmd == "STATUS":
            action = "STATUS"
            if shipment_ref:
                doc = DigitalShipmentDocument.objects.filter(shipment_number__iexact=shipment_ref).first()
                if doc:
                    sensor = doc.cold_chain_sensors.first()
                    temp_info = f", Temp {sensor.current_temperature}°C ({sensor.status})" if sensor else ""
                    response_text = (
                        f"[SIH26002 DEMO SMS] {doc.shipment_number}: Status {doc.document_status}, "
                        f"Cargo: {doc.cargo_summary[:30]}{temp_info}. Destination: {doc.destination_name}. Reply ROUTE for path."
                    )
                else:
                    response_text = f"[SIH26002 DEMO SMS] Shipment '{shipment_ref}' not found in registry."
            else:
                response_text = "[SIH26002 DEMO SMS] Usage: STATUS <SHIPMENT_NUM>, e.g. STATUS SHIP-1A2B3C4D"

        elif cmd == "ROUTE":
            action = "ROUTE"
            if shipment_ref:
                doc = DigitalShipmentDocument.objects.filter(shipment_number__iexact=shipment_ref).first()
                if doc:
                    response_text = (
                        f"[SIH26002 DEMO SMS] {doc.shipment_number} Route: {doc.origin_name} -> {doc.destination_name} "
                        f"(Corridor Active). Route Risk: LOW. NH-6 Bypass clear."
                    )
                else:
                    response_text = f"[SIH26002 DEMO SMS] Shipment '{shipment_ref}' not found in registry."
            else:
                response_text = "[SIH26002 DEMO SMS] Usage: ROUTE <SHIPMENT_NUM>"

        elif cmd == "SYNC":
            action = "SYNC"
            response_text = f"[SIH26002 DEMO SMS] Offline Sync ACK: Registry cache current for phone {phone_number}."

        elif cmd == "SOS":
            action = "SOS"
            response_text = (
                f"[SIH26002 DEMO SMS] EMERGENCY DISTRESS RECORDED: Control Room alerted for {phone_number}. "
                f"Nearest logistics node: Nongpoh Hub. Stay inside vehicle. Rescue dispatched."
            )

        else:
            action = "HELP"
            response_text = (
                "[SIH26002 DEMO SMS] Valid commands: STATUS <SHIPMENT_ID>, ROUTE <SHIPMENT_ID>, "
                "SYNC <SHIPMENT_ID>, SOS. Powered by MDoNER Logistics Platform."
            )

        record = SmsCommand.objects.create(
            phone_number=phone_number,
            raw_command=cleaned,
            parsed_action=action,
            shipment_id=shipment_ref,
            response_message=response_text,
            is_simulation=True,
        )

        return {
            "id": str(record.id),
            "phone_number": phone_number,
            "command": cleaned,
            "action": action,
            "response": response_text,
            "is_simulation": True,
        }


class IvrFallbackGateway:
    """
    Deterministic IVR interactive voice simulation for feature phone accessibility.
    """

    PROMPTS = {
        "MAIN_MENU": (
            "Welcome to MDoNER Logistics Voice Assistance. "
            "Press 1 for Shipment Status. Press 2 for Route Advisory. "
            "Press 3 to Report Geohazard. Press 4 for Emergency SOS. Press 5 to Confirm Delivery."
        ),
        "1": "Shipment status advisory: Your active cargo shipment is in transit along NH-6. Moving on schedule.",
        "2": "Route advisory: NH-6 and NH-27 corridors are currently operating under Normal status. No active landslide blocks.",
        "3": "Geohazard report accepted: Your voice report has been logged for validation by the nearest checkpost. Thank you for driver safety.",
        "4": "EMERGENCY SOS CONFIRMED: Your coordinates have been forwarded to Meghalaya State Disaster Management Authority and nearest police outpost.",
        "5": "Delivery confirmation: Please enter your 8-digit shipment code or scan QR manifest at the destination depot.",
    }

    @classmethod
    def interact(
        cls,
        session_id: Optional[str] = None,
        phone_number: str = "+919876543210",
        dtmf_digit: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        if not session_id:
            session_id = f"IVR-{uuid.uuid4().hex[:8].upper()}"
            session = IvrSession.objects.create(
                session_id=session_id,
                phone_number=phone_number,
                language=language,
                current_step="MAIN_MENU",
                transcript_log=[{"speaker": "SYSTEM", "text": cls.PROMPTS["MAIN_MENU"]}],
                is_simulation=True,
            )
            return {
                "session_id": session.session_id,
                "prompt": cls.PROMPTS["MAIN_MENU"],
                "step": "MAIN_MENU",
                "options": ["1: Status", "2: Route", "3: Hazard", "4: SOS", "5: Delivery"],
                "is_simulation": True,
            }

        session = IvrSession.objects.filter(session_id=session_id).first()
        if not session:
            return cls.interact(phone_number=phone_number, language=language)

        digit = str(dtmf_digit).strip() if dtmf_digit else "1"
        response_prompt = cls.PROMPTS.get(digit, cls.PROMPTS["MAIN_MENU"])
        next_step = f"OPTION_{digit}" if digit in cls.PROMPTS else "MAIN_MENU"

        transcript = list(session.transcript_log)
        transcript.append({"speaker": "USER", "dtmf": digit})
        transcript.append({"speaker": "SYSTEM", "text": response_prompt})

        session.current_step = next_step
        session.selected_option = digit
        session.transcript_log = transcript
        session.save(update_fields=["current_step", "selected_option", "transcript_log"])

        return {
            "session_id": session.session_id,
            "prompt": response_prompt,
            "step": next_step,
            "selected_option": digit,
            "is_simulation": True,
        }
