"""
SIH26002 — Shipment Document, QR Code & Cold-Chain IoT Views.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.shipments.models import (
    DigitalShipmentDocument,
    ShipmentTrackingEvent,
    ColdChainSensor,
    ColdChainReading,
    ColdChainAlert,
)
from apps.shipments.serializers import (
    DigitalShipmentDocumentSerializer,
    ShipmentTrackingEventSerializer,
    ColdChainSensorSerializer,
    ColdChainReadingSerializer,
    ColdChainAlertSerializer,
)
from apps.shipments.services.document_service import DigitalShipmentDocumentService
from apps.shipments.services.risk_service import ShipmentRiskEngine
from apps.shipments.services.cold_chain_service import ColdChainTrackingService, ColdChainSimulator


class DigitalShipmentDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Querying and viewing digital freight e-way documents and cryptographic QR credentials.
    """
    queryset = DigitalShipmentDocument.objects.all().select_related("shipper", "carrier", "vehicle", "driver").prefetch_related("tracking_events", "cold_chain_sensors")
    serializer_class = DigitalShipmentDocumentSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        pk = self.kwargs.get("pk")
        # Support lookup by UUID or by shipment_number
        obj = DigitalShipmentDocument.objects.filter(id=pk).first()
        if not obj:
            obj = DigitalShipmentDocument.objects.filter(shipment_number__iexact=pk).first()
        if not obj:
            from rest_framework.exceptions import NotFound
            raise NotFound(f"Shipment document '{pk}' not found.")
        return obj

    @action(detail=True, methods=["get"])
    def qr(self, request, pk=None):
        doc = self.get_object()
        qr_payload = DigitalShipmentDocumentService.generate_qr_payload(doc)
        return Response({
            "shipment_number": doc.shipment_number,
            "secure_token": doc.secure_qr_token,
            "qr_payload": qr_payload,
            "valid_until": doc.valid_until.isoformat(),
            "status": doc.document_status,
        })

    @action(detail=True, methods=["get"])
    def tracking(self, request, pk=None):
        doc = self.get_object()
        events = doc.tracking_events.order_by("recorded_at")
        risk_evaluation = ShipmentRiskEngine.evaluate_shipment_risk(doc)
        return Response({
            "shipment_number": doc.shipment_number,
            "origin": doc.origin_name,
            "destination": doc.destination_name,
            "status": doc.document_status,
            "risk_assessment": risk_evaluation,
            "events": ShipmentTrackingEventSerializer(events, many=True).data,
        })


class ColdChainReadingView(APIView):
    """
    Ingest IoT temperature telemetry.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        sensor_code = request.data.get("sensor_code")
        temp = float(request.data.get("temperature", 4.0))
        hum = float(request.data.get("humidity", 60.0))
        bat = float(request.data.get("battery", 90.0))

        sensor = get_object_or_404(ColdChainSensor, sensor_code=sensor_code)
        result = ColdChainTrackingService.record_reading(
            sensor=sensor,
            temperature=temp,
            humidity=hum,
            battery=bat,
            is_simulation=request.data.get("is_simulation", True),
        )
        return Response(result, status=status.HTTP_201_CREATED)


class ColdChainShipmentView(APIView):
    """
    Inspect cold chain sensor and telemetry history for a shipment.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk=None):
        doc = DigitalShipmentDocument.objects.filter(id=pk).first() or DigitalShipmentDocument.objects.filter(shipment_number__iexact=pk).first()
        if not doc:
            return Response({"error": "Shipment not found"}, status=status.HTTP_404_NOT_FOUND)

        sensors = doc.cold_chain_sensors.all()
        alerts = doc.cold_chain_alerts.order_by("-created_at")
        readings = doc.cold_chain_readings.order_by("-recorded_at")[:25]

        return Response({
            "shipment_number": doc.shipment_number,
            "sensors": ColdChainSensorSerializer(sensors, many=True).data,
            "active_alerts": ColdChainAlertSerializer(alerts.filter(is_resolved=False), many=True).data,
            "historical_alerts": ColdChainAlertSerializer(alerts, many=True).data,
            "recent_readings": ColdChainReadingSerializer(readings, many=True).data,
        })


class ColdChainAlertsListView(APIView):
    """
    List all active cold-chain alerts across fleet.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        alerts = ColdChainAlert.objects.filter(is_resolved=False).select_related("sensor", "document")
        return Response(ColdChainAlertSerializer(alerts, many=True).data)


class ColdChainSimulateView(APIView):
    """
    Trigger demonstration sensor scenarios (NORMAL, TEMPERATURE_RISE, CRITICAL_BREACH, SENSOR_OFFLINE, RECOVERY).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        sensor_code = request.data.get("sensor_code")
        scenario = request.data.get("scenario", "TEMPERATURE_RISE")

        sensor = None
        if sensor_code:
            sensor = ColdChainSensor.objects.filter(sensor_code=sensor_code).first()
        if not sensor:
            sensor = ColdChainSensor.objects.first()

        if not sensor:
            # Create a demo sensor
            sensor = ColdChainSensor.objects.create(
                sensor_code="CC-IOT-DEMO1",
                current_temperature=4.0,
                min_threshold=2.0,
                max_threshold=8.0,
                is_simulation=True,
            )

        res = ColdChainSimulator.run_scenario(sensor=sensor, scenario=scenario)
        return Response(res)
