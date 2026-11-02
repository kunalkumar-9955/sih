"""
SIH26002 — Batch Sync Processor.

Processes offline event batches uploaded by drivers upon network reconnection.
Provides atomic per-event idempotency, conflict detection, and transactional dispatch
to domain entities (Trips, Hazards, SOS, Vehicles).
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import dateparse, timezone

from apps.drivers.models import Driver
from apps.hazards.models import HazardIncident, HazardSeverity
from apps.sync.models import (
    EmergencySOS,
    EmergencySOSStatus,
    SyncEventStatus,
    SyncEventType,
    SyncQueueRecord,
)
from apps.sync.services.conflict_resolver import SyncConflictResolver
from apps.trips.models import Trip, TripStatus

logger = logging.getLogger(__name__)


class BatchSyncProcessor:
    """
    Processes a list of queued offline events synchronously or in worker.
    """

    def __init__(self, driver: Optional[Driver] = None):
        self.driver = driver

    def process_batch(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Processes each event in the batch, returning individual results and summary counts.
        """
        results = []
        applied_count = 0
        conflict_count = 0
        duplicate_count = 0
        rejected_count = 0

        for raw_event in events:
            event_result = self._process_single_event(raw_event)
            status = event_result["status"]

            if status == SyncEventStatus.APPLIED:
                applied_count += 1
            elif status == SyncEventStatus.CONFLICT:
                conflict_count += 1
            elif status == SyncEventStatus.DUPLICATE:
                duplicate_count += 1
            elif status == SyncEventStatus.REJECTED:
                rejected_count += 1

            results.append(event_result)

        return {
            "total_events": len(events),
            "applied_count": applied_count,
            "conflict_count": conflict_count,
            "duplicate_count": duplicate_count,
            "rejected_count": rejected_count,
            "results": results,
        }

    def _process_single_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes an individual sync event with idempotency and domain handling.
        """
        idempotency_key = str(event_data.get("idempotency_key", "")).strip()
        event_type = event_data.get("event_type", "").upper()
        raw_ts = event_data.get("client_timestamp")
        payload = event_data.get("payload", {})

        if not idempotency_key:
            return {
                "idempotency_key": "",
                "status": SyncEventStatus.REJECTED,
                "message": "Missing required 'idempotency_key'.",
            }

        # Check existing record for strict deduplication
        existing = SyncQueueRecord.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return {
                "idempotency_key": idempotency_key,
                "event_type": existing.event_type,
                "status": SyncEventStatus.DUPLICATE,
                "message": f"Event was previously processed with status '{existing.status}'.",
                "details": existing.conflict_details,
            }

        # Parse timestamp
        client_ts = None
        if raw_ts:
            if isinstance(raw_ts, str):
                client_ts = dateparse.parse_datetime(raw_ts)
            elif isinstance(raw_ts, (int, float)):
                client_ts = datetime.fromtimestamp(raw_ts, tz=timezone.utc)
            elif isinstance(raw_ts, datetime):
                client_ts = raw_ts

        if not client_ts:
            client_ts = timezone.now()

        # Sanity check on timestamp
        is_sane, sanity_err = SyncConflictResolver.validate_timestamp_sanity(client_ts)
        if not is_sane:
            rec = SyncQueueRecord.objects.create(
                idempotency_key=idempotency_key,
                event_type=event_type or SyncEventType.LOCATION_UPDATE,
                driver=self.driver,
                client_timestamp=client_ts,
                payload=payload,
                status=SyncEventStatus.REJECTED,
                error_message=sanity_err,
            )
            return {
                "idempotency_key": idempotency_key,
                "status": SyncEventStatus.REJECTED,
                "message": sanity_err,
            }

        # Dispatch based on event_type
        try:
            with transaction.atomic():
                if event_type == SyncEventType.LOCATION_UPDATE:
                    return self._handle_location_update(idempotency_key, client_ts, payload)
                elif event_type == SyncEventType.TRIP_STATUS:
                    return self._handle_trip_status(idempotency_key, client_ts, payload)
                elif event_type == SyncEventType.HAZARD_REPORT:
                    return self._handle_hazard_report(idempotency_key, client_ts, payload)
                elif event_type == SyncEventType.ROUTE_ACK:
                    return self._handle_route_ack(idempotency_key, client_ts, payload)
                elif event_type == SyncEventType.SOS_EMERGENCY:
                    return self._handle_sos_emergency(idempotency_key, client_ts, payload)
                elif event_type == SyncEventType.LOAD_STATUS:
                    return self._handle_load_status(idempotency_key, client_ts, payload)
                elif event_type == SyncEventType.CHECKPOST_EVENT:
                    return self._handle_checkpost_event(idempotency_key, client_ts, payload)
                elif event_type == SyncEventType.COLD_CHAIN_READING:
                    return self._handle_cold_chain_reading(idempotency_key, client_ts, payload)
                elif event_type == SyncEventType.SMS_COMMAND:
                    return self._handle_sms_command(idempotency_key, client_ts, payload)
                else:
                    rec = SyncQueueRecord.objects.create(
                        idempotency_key=idempotency_key,
                        event_type=SyncEventType.LOCATION_UPDATE,
                        driver=self.driver,
                        client_timestamp=client_ts,
                        payload=payload,
                        status=SyncEventStatus.REJECTED,
                        error_message=f"Unsupported event_type '{event_type}'.",
                    )
                    return {
                        "idempotency_key": idempotency_key,
                        "status": SyncEventStatus.REJECTED,
                        "message": f"Unsupported event_type '{event_type}'.",
                    }
        except Exception as exc:
            logger.exception("Error processing event %s: %s", idempotency_key, exc)
            return {
                "idempotency_key": idempotency_key,
                "status": SyncEventStatus.REJECTED,
                "message": f"Processing error: {str(exc)}",
            }

    def _handle_location_update(
        self, idempotency_key: str, client_ts: datetime, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        lat = payload.get("latitude")
        lon = payload.get("longitude")
        trip_id = payload.get("trip_id")

        trip = None
        if trip_id:
            trip = Trip.objects.filter(id=trip_id).first()

        # Update vehicle location if driver has assigned vehicle
        if self.driver and getattr(self.driver, "current_vehicle", None) and lat and lon:
            vehicle = self.driver.current_vehicle
            vehicle.last_location = Point(float(lon), float(lat), srid=4326)
            vehicle.last_seen = client_ts
            vehicle.save(update_fields=["last_location", "last_seen"])

        rec = SyncQueueRecord.objects.create(
            idempotency_key=idempotency_key,
            event_type=SyncEventType.LOCATION_UPDATE,
            driver=self.driver,
            trip=trip,
            client_timestamp=client_ts,
            payload=payload,
            status=SyncEventStatus.APPLIED,
        )

        return {
            "idempotency_key": idempotency_key,
            "event_type": SyncEventType.LOCATION_UPDATE,
            "status": SyncEventStatus.APPLIED,
            "message": "Location telemetry recorded.",
        }

    def _handle_trip_status(
        self, idempotency_key: str, client_ts: datetime, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        trip_id = payload.get("trip_id")
        requested_status = payload.get("status", "").upper()
        client_route_version = payload.get("route_version")

        if not trip_id:
            rec = SyncQueueRecord.objects.create(
                idempotency_key=idempotency_key,
                event_type=SyncEventType.TRIP_STATUS,
                driver=self.driver,
                client_timestamp=client_ts,
                payload=payload,
                status=SyncEventStatus.REJECTED,
                error_message="Missing trip_id in TRIP_STATUS payload.",
            )
            return {
                "idempotency_key": idempotency_key,
                "status": SyncEventStatus.REJECTED,
                "message": "Missing trip_id in TRIP_STATUS payload.",
            }

        trip = Trip.objects.filter(id=trip_id).first()
        if not trip:
            rec = SyncQueueRecord.objects.create(
                idempotency_key=idempotency_key,
                event_type=SyncEventType.TRIP_STATUS,
                driver=self.driver,
                client_timestamp=client_ts,
                payload=payload,
                status=SyncEventStatus.REJECTED,
                error_message=f"Trip '{trip_id}' does not exist.",
            )
            return {
                "idempotency_key": idempotency_key,
                "status": SyncEventStatus.REJECTED,
                "message": f"Trip '{trip_id}' not found.",
            }

        # Validate monotonic transition
        allowed, msg = SyncConflictResolver.resolve_trip_state_transition(trip.status, requested_status)
        if not allowed:
            conflict_details = {
                "server_status": trip.status,
                "requested_status": requested_status,
                "reason": msg,
            }
            rec = SyncQueueRecord.objects.create(
                idempotency_key=idempotency_key,
                event_type=SyncEventType.TRIP_STATUS,
                driver=self.driver,
                trip=trip,
                client_timestamp=client_ts,
                payload=payload,
                status=SyncEventStatus.CONFLICT,
                conflict_details=conflict_details,
            )
            return {
                "idempotency_key": idempotency_key,
                "event_type": SyncEventType.TRIP_STATUS,
                "status": SyncEventStatus.CONFLICT,
                "message": msg,
                "server_state": {"trip_id": str(trip.id), "status": trip.status},
            }

        # Validate route version if specified
        if client_route_version is not None:
            rv_ok, rv_msg = SyncConflictResolver.validate_route_version(trip, client_route_version)
            if not rv_ok:
                conflict_details = {
                    "server_route_version": trip.route_version,
                    "client_route_version": client_route_version,
                    "reason": rv_msg,
                }
                rec = SyncQueueRecord.objects.create(
                    idempotency_key=idempotency_key,
                    event_type=SyncEventType.TRIP_STATUS,
                    driver=self.driver,
                    trip=trip,
                    client_timestamp=client_ts,
                    payload=payload,
                    status=SyncEventStatus.CONFLICT,
                    conflict_details=conflict_details,
                )
                return {
                    "idempotency_key": idempotency_key,
                    "event_type": SyncEventType.TRIP_STATUS,
                    "status": SyncEventStatus.CONFLICT,
                    "message": rv_msg,
                    "server_state": {
                        "trip_id": str(trip.id),
                        "status": trip.status,
                        "route_version": trip.route_version,
                    },
                }

        # Apply state transition
        trip.status = requested_status
        if requested_status == TripStatus.ACTIVE and not trip.actual_departure:
            trip.actual_departure = client_ts
        elif requested_status == TripStatus.COMPLETED and not trip.actual_arrival:
            trip.actual_arrival = client_ts

        trip.save(update_fields=["status", "actual_departure", "actual_arrival"])

        rec = SyncQueueRecord.objects.create(
            idempotency_key=idempotency_key,
            event_type=SyncEventType.TRIP_STATUS,
            driver=self.driver,
            trip=trip,
            client_timestamp=client_ts,
            payload=payload,
            status=SyncEventStatus.APPLIED,
        )

        return {
            "idempotency_key": idempotency_key,
            "event_type": SyncEventType.TRIP_STATUS,
            "status": SyncEventStatus.APPLIED,
            "message": f"Trip {str(trip.id)} transitioned to '{requested_status}'.",
        }

    def _handle_hazard_report(
        self, idempotency_key: str, client_ts: datetime, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        inc_type = payload.get("incident_type", HazardIncident.IncidentType.LANDSLIDE).upper()
        severity = payload.get("severity", HazardSeverity.MODERATE).upper()
        lat = payload.get("latitude")
        lon = payload.get("longitude")
        desc = payload.get("description", "Driver offline incident report.")
        edge_id = payload.get("edge_id")

        pt = None
        if lat is not None and lon is not None:
            pt = Point(float(lon), float(lat), srid=4326)

        incident = HazardIncident.objects.create(
            edge_id=edge_id,
            incident_type=inc_type,
            severity=severity,
            location=pt,
            description=desc,
            occurred_at=client_ts,
            source=HazardIncident.IncidentSource.DRIVER,
            status=HazardIncident.IncidentStatus.REPORTED,
        )

        rec = SyncQueueRecord.objects.create(
            idempotency_key=idempotency_key,
            event_type=SyncEventType.HAZARD_REPORT,
            driver=self.driver,
            client_timestamp=client_ts,
            payload=payload,
            status=SyncEventStatus.APPLIED,
            conflict_details={"incident_id": str(incident.id)},
        )

        return {
            "idempotency_key": idempotency_key,
            "event_type": SyncEventType.HAZARD_REPORT,
            "status": SyncEventStatus.APPLIED,
            "message": f"Hazard incident {str(incident.id)} logged.",
            "incident_id": str(incident.id),
        }

    def _handle_route_ack(
        self, idempotency_key: str, client_ts: datetime, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        trip_id = payload.get("trip_id")
        client_version = payload.get("route_version")

        trip = Trip.objects.filter(id=trip_id).first() if trip_id else None
        if not trip:
            rec = SyncQueueRecord.objects.create(
                idempotency_key=idempotency_key,
                event_type=SyncEventType.ROUTE_ACK,
                driver=self.driver,
                client_timestamp=client_ts,
                payload=payload,
                status=SyncEventStatus.REJECTED,
                error_message=f"Trip '{trip_id}' not found.",
            )
            return {
                "idempotency_key": idempotency_key,
                "status": SyncEventStatus.REJECTED,
                "message": f"Trip '{trip_id}' not found.",
            }

        if client_version is not None and client_version < trip.route_version:
            msg = f"Stale route ack: client version v{client_version} is behind server v{trip.route_version}."
            rec = SyncQueueRecord.objects.create(
                idempotency_key=idempotency_key,
                event_type=SyncEventType.ROUTE_ACK,
                driver=self.driver,
                trip=trip,
                client_timestamp=client_ts,
                payload=payload,
                status=SyncEventStatus.CONFLICT,
                conflict_details={"server_route_version": trip.route_version},
                error_message=msg,
            )
            return {
                "idempotency_key": idempotency_key,
                "status": SyncEventStatus.CONFLICT,
                "message": msg,
                "server_route_version": trip.route_version,
            }

        rec = SyncQueueRecord.objects.create(
            idempotency_key=idempotency_key,
            event_type=SyncEventType.ROUTE_ACK,
            driver=self.driver,
            trip=trip,
            client_timestamp=client_ts,
            payload=payload,
            status=SyncEventStatus.APPLIED,
        )

        return {
            "idempotency_key": idempotency_key,
            "event_type": SyncEventType.ROUTE_ACK,
            "status": SyncEventStatus.APPLIED,
            "message": f"Route version {client_version} acknowledged.",
        }

    def _handle_sos_emergency(
        self, idempotency_key: str, client_ts: datetime, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.driver:
            # Fall back to finding driver from payload if provided
            driver_id = payload.get("driver_id")
            if driver_id:
                self.driver = Driver.objects.filter(id=driver_id).first()

        if not self.driver:
            rec = SyncQueueRecord.objects.create(
                idempotency_key=idempotency_key,
                event_type=SyncEventType.SOS_EMERGENCY,
                client_timestamp=client_ts,
                payload=payload,
                status=SyncEventStatus.REJECTED,
                error_message="Emergency SOS requires an authenticated driver.",
            )
            return {
                "idempotency_key": idempotency_key,
                "status": SyncEventStatus.REJECTED,
                "message": "Emergency SOS requires an authenticated driver.",
            }

        trip_id = payload.get("trip_id")
        trip = Trip.objects.filter(id=trip_id).first() if trip_id else None

        lat = payload.get("latitude")
        lon = payload.get("longitude")
        pt = None
        if lat is not None and lon is not None:
            pt = Point(float(lon), float(lat), srid=4326)

        msg = payload.get("message", "Emergency SOS beacon triggered offline.")

        sos = EmergencySOS.objects.create(
            driver=self.driver,
            trip=trip,
            location=pt,
            status=EmergencySOSStatus.TRIGGERED,
            message=msg,
            triggered_at=client_ts,
            metadata=payload,
        )

        rec = SyncQueueRecord.objects.create(
            idempotency_key=idempotency_key,
            event_type=SyncEventType.SOS_EMERGENCY,
            driver=self.driver,
            trip=trip,
            client_timestamp=client_ts,
            payload=payload,
            status=SyncEventStatus.APPLIED,
            conflict_details={"sos_id": str(sos.id)},
        )

        logger.warning(
            "EMERGENCY SOS DISTRESS TRIGGERED: id=%s driver=%s loc=(%s, %s)",
            str(sos.id),
            self.driver.name if self.driver else "Unknown",
            lat,
            lon,
        )

        return {
            "idempotency_key": idempotency_key,
            "event_type": SyncEventType.SOS_EMERGENCY,
            "status": SyncEventStatus.APPLIED,
            "message": "Emergency SOS beacon registered with control center.",
            "sos_id": str(sos.id),
        }

    def _handle_load_status(
        self, idempotency_key: str, client_ts: datetime, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        from apps.fleet.models import FreightLoad, CargoStatus
        load_id = payload.get("load_id")
        target_status = payload.get("status", "").upper()

        load = None
        if load_id:
            load = FreightLoad.objects.filter(id=load_id).first()

        if not load:
            rec = SyncQueueRecord.objects.create(
                idempotency_key=idempotency_key,
                event_type=SyncEventType.LOAD_STATUS,
                driver=self.driver,
                client_timestamp=client_ts,
                payload=payload,
                status=SyncEventStatus.REJECTED,
                error_message=f"FreightLoad '{load_id}' not found.",
            )
            return {
                "idempotency_key": idempotency_key,
                "status": SyncEventStatus.REJECTED,
                "message": f"FreightLoad '{load_id}' not found.",
            }

        if target_status in CargoStatus.values:
            load.status = target_status
            load.save(update_fields=["status"])

        rec = SyncQueueRecord.objects.create(
            idempotency_key=idempotency_key,
            event_type=SyncEventType.LOAD_STATUS,
            driver=self.driver,
            client_timestamp=client_ts,
            payload=payload,
            status=SyncEventStatus.APPLIED,
            conflict_details={"load_id": str(load.id), "new_status": target_status},
        )

        return {
            "idempotency_key": idempotency_key,
            "event_type": SyncEventType.LOAD_STATUS,
            "status": SyncEventStatus.APPLIED,
            "message": f"FreightLoad status transitioned to {target_status}.",
            "load_id": str(load.id),
        }

    def _handle_checkpost_event(
        self, idempotency_key: str, client_ts: datetime, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        from apps.checkposts.services.verification_service import CheckpostVerificationService
        chk_code = payload.get("checkpost_code", "CHK-OFFLINE")
        token = payload.get("token", "")
        veh_reg = payload.get("vehicle_reg")

        result = CheckpostVerificationService.verify_qr_scan(
            checkpost_code=chk_code,
            token=token,
            vehicle_reg=veh_reg,
            verifier_user=None,
            is_offline=True,
        )

        rec = SyncQueueRecord.objects.create(
            idempotency_key=idempotency_key,
            event_type=SyncEventType.CHECKPOST_EVENT,
            driver=self.driver,
            client_timestamp=client_ts,
            payload=payload,
            status=SyncEventStatus.APPLIED,
            conflict_details=result,
        )

        return {
            "idempotency_key": idempotency_key,
            "event_type": SyncEventType.CHECKPOST_EVENT,
            "status": SyncEventStatus.APPLIED,
            "message": "Offline checkpost verification event synchronized.",
            "verification": result,
        }

    def _handle_cold_chain_reading(
        self, idempotency_key: str, client_ts: datetime, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        from apps.shipments.models import ColdChainSensor
        from apps.shipments.services.cold_chain_service import ColdChainTrackingService

        sensor_code = payload.get("sensor_code")
        temp = float(payload.get("temperature", 4.0))
        hum = float(payload.get("humidity", 60.0))
        bat = float(payload.get("battery", 90.0))

        sensor = ColdChainSensor.objects.filter(sensor_code=sensor_code).first()
        if not sensor:
            rec = SyncQueueRecord.objects.create(
                idempotency_key=idempotency_key,
                event_type=SyncEventType.COLD_CHAIN_READING,
                driver=self.driver,
                client_timestamp=client_ts,
                payload=payload,
                status=SyncEventStatus.REJECTED,
                error_message=f"Sensor '{sensor_code}' not found.",
            )
            return {
                "idempotency_key": idempotency_key,
                "status": SyncEventStatus.REJECTED,
                "message": f"Sensor '{sensor_code}' not found.",
            }

        telemetry_result = ColdChainTrackingService.record_reading(
            sensor=sensor,
            temperature=temp,
            humidity=hum,
            battery=bat,
            is_simulation=True,
        )

        rec = SyncQueueRecord.objects.create(
            idempotency_key=idempotency_key,
            event_type=SyncEventType.COLD_CHAIN_READING,
            driver=self.driver,
            client_timestamp=client_ts,
            payload=payload,
            status=SyncEventStatus.APPLIED,
            conflict_details=telemetry_result,
        )

        return {
            "idempotency_key": idempotency_key,
            "event_type": SyncEventType.COLD_CHAIN_READING,
            "status": SyncEventStatus.APPLIED,
            "message": "Offline cold chain reading recorded.",
            "telemetry": telemetry_result,
        }

    def _handle_sms_command(
        self, idempotency_key: str, client_ts: datetime, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        from apps.marketplace.services.fallback_service import SmsFallbackGateway
        phone = payload.get("phone_number", "+919876543210")
        cmd_text = payload.get("command", "STATUS")

        sms_result = SmsFallbackGateway.process_incoming_sms(phone_number=phone, raw_text=cmd_text)

        rec = SyncQueueRecord.objects.create(
            idempotency_key=idempotency_key,
            event_type=SyncEventType.SMS_COMMAND,
            driver=self.driver,
            client_timestamp=client_ts,
            payload=payload,
            status=SyncEventStatus.APPLIED,
            conflict_details=sms_result,
        )

        return {
            "idempotency_key": idempotency_key,
            "event_type": SyncEventType.SMS_COMMAND,
            "status": SyncEventStatus.APPLIED,
            "message": "Offline SMS command processed.",
            "sms": sms_result,
        }

