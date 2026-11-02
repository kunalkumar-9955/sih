"""
SIH26002 — Marketplace Views & Endpoints.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404

from apps.marketplace.models import MarketplaceListing, FreightBid, ListingStatus, BidStatus
from apps.marketplace.serializers import (
    MarketplaceListingSerializer,
    FreightBidSerializer,
    SmsCommandSerializer,
    IvrSessionSerializer,
)
from apps.marketplace.services.bidding_engine import BiddingEngine
from apps.marketplace.services.fallback_service import SmsFallbackGateway, IvrFallbackGateway


class MarketplaceListingViewSet(viewsets.ModelViewSet):
    """
    CRUD and publishing for multimodal freight marketplace listings.
    """
    queryset = MarketplaceListing.objects.all().select_related("shipper", "load").prefetch_related("bids")
    serializer_class = MarketplaceListingSerializer
    permission_classes = [permissions.AllowAny]  # Or authenticated

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param.upper())
        cold_param = self.request.query_params.get("is_cold_chain")
        if cold_param is not None:
            qs = qs.filter(is_cold_chain=cold_param.lower() == "true")
        return qs

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        if not user:
            from apps.users.models import User
            user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        serializer.save(shipper=user)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        listing = self.get_object()
        listing.status = ListingStatus.PUBLISHED
        listing.published_at = timezone.now()
        listing.save(update_fields=["status", "published_at"])
        return Response(MarketplaceListingSerializer(listing).data)

    @action(detail=True, methods=["get", "post"])
    def bids(self, request, pk=None):
        listing = self.get_object()
        if request.method == "GET":
            bids = listing.bids.all().order_by("-ai_recommendation_score", "price_inr")
            return Response(FreightBidSerializer(bids, many=True).data)

        # POST new bid
        carrier = request.user if request.user.is_authenticated else None
        if not carrier:
            from apps.users.models import User
            carrier = User.objects.filter(is_superuser=True).first() or User.objects.first()

        price = float(request.data.get("price_inr", 15000.0))
        hours = float(request.data.get("estimated_transit_hours", 14.0))
        mode = request.data.get("proposed_mode", "ROAD")
        terms = request.data.get("terms", "")
        veh_id = request.data.get("proposed_vehicle_id")

        vehicle = None
        if veh_id:
            from apps.vehicles.models import Vehicle
            vehicle = Vehicle.objects.filter(id=veh_id).first()

        bid = BiddingEngine.submit_bid(
            listing=listing,
            carrier=carrier,
            price_inr=price,
            estimated_transit_hours=hours,
            proposed_mode=mode,
            proposed_vehicle=vehicle,
            terms=terms,
        )
        return Response(FreightBidSerializer(bid).data, status=status.HTTP_201_CREATED)


class FreightBidViewSet(viewsets.GenericViewSet):
    """
    Carrier bid management and acceptance.
    """
    queryset = FreightBid.objects.all().select_related("listing", "carrier", "proposed_vehicle")
    serializer_class = FreightBidSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        bid = self.get_object()
        user = request.user
        result = BiddingEngine.accept_bid(bid, user)
        return Response({
            "message": result["message"],
            "bid": FreightBidSerializer(result["bid"]).data,
            "document_shipment_number": result["document"].shipment_number,
            "document_id": str(result["document"].id),
        })


class MultimodalOptionsView(APIView):
    """
    Surfaces available multimodal transport corridors and estimated options.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        origin = request.query_params.get("origin", "Guwahati Hub")
        destination = request.query_params.get("destination", "Silchar Terminal")
        weight = float(request.query_params.get("weight_kg", 5000.0))

        options = [
            {
                "mode": "ROAD",
                "label": "Direct Road (NH-6 / NH-27)",
                "estimated_hours": 12.5,
                "estimated_cost_inr": round(weight * 3.8 + 4500, 2),
                "route_risk": "MEDIUM",
                "transfers": 0,
                "co2_kg": round(weight * 0.12, 1),
                "description": "Fastest door-to-door transit via Meghalaya Hills. Exposed to seasonal hill slips.",
            },
            {
                "mode": "ROAD_RAIL",
                "label": "Intermodal Road + NF Railway",
                "estimated_hours": 18.0,
                "estimated_cost_inr": round(weight * 2.6 + 3000, 2),
                "route_risk": "LOW",
                "transfers": 1,
                "co2_kg": round(weight * 0.05, 1),
                "description": "Road to Guwahati Goods Shed, Rail transshipment to Badarpur Siding. 35% cost savings.",
            },
            {
                "mode": "ROAD_WATERWAY",
                "label": "Intermodal Road + NW-2 Waterway Barge",
                "estimated_hours": 26.0,
                "estimated_cost_inr": round(weight * 1.9 + 2500, 2),
                "route_risk": "VERY_LOW",
                "transfers": 1,
                "co2_kg": round(weight * 0.03, 1),
                "description": "Pandu Port Ro-Ro barge across Brahmaputra. Immune to highway landslides.",
            },
            {
                "mode": "MULTIMODAL",
                "label": "Full Multimodal (Road + Rail + Waterway)",
                "estimated_hours": 22.0,
                "estimated_cost_inr": round(weight * 2.2 + 2800, 2),
                "route_risk": "LOW",
                "transfers": 2,
                "co2_kg": round(weight * 0.04, 1),
                "description": "Optimal disaster resilience combination bypassing all critical geohazard bottlenecks.",
            },
        ]
        return Response({
            "origin": origin,
            "destination": destination,
            "weight_kg": weight,
            "options": options,
        })


class SmsFallbackView(APIView):
    """
    Feature phone SMS webhook / simulation endpoint.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone = request.data.get("phone_number", "+919876543210")
        raw_cmd = request.data.get("command", "STATUS")
        res = SmsFallbackGateway.process_incoming_sms(phone_number=phone, raw_text=raw_cmd)
        return Response(res)


class IvrFallbackView(APIView):
    """
    Feature phone IVR DTMF voice menu simulation endpoint.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        session_id = request.data.get("session_id")
        phone = request.data.get("phone_number", "+919876543210")
        digit = request.data.get("digit")
        lang = request.data.get("language", "en")
        res = IvrFallbackGateway.interact(session_id=session_id, phone_number=phone, dtmf_digit=digit, language=lang)
        return Response(res)
