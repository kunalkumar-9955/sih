"""
SIH26002 — Explainable Multimodal Freight Bidding Engine.

Provides:
- Transparent multi-factor bid scoring (Cost, Transit Time, Route Safety, Vehicle Suitability, Carrier Rating)
- Explainable recommendation breakdowns
- Atomic bid acceptance with automated digital document generation
"""
import logging
from typing import Dict, Any, List, Optional
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.marketplace.models import MarketplaceListing, FreightBid, ListingStatus, BidStatus
from apps.fleet.models import CargoStatus, LoadAssignment

logger = logging.getLogger(__name__)


class BiddingEngine:
    """
    Transparent, explainable freight bidding evaluation and management engine.
    """

    # Multi-factor recommendation weights
    WEIGHT_COST = 0.30
    WEIGHT_TIME = 0.25
    WEIGHT_SAFETY = 0.20
    WEIGHT_SUITABILITY = 0.15
    WEIGHT_RATING = 0.10

    @classmethod
    def evaluate_bid_factors(
        cls,
        listing: MarketplaceListing,
        price_inr: float,
        transit_hours: float,
        proposed_mode: str,
        vehicle: Optional[Any] = None,
        operator_rating: float = 4.5,
    ) -> Dict[str, Any]:
        """
        Computes transparent, explainable 0-100 subscores and composite rank score.
        """
        # 1. Cost Score (0 - 100)
        # Higher score for lower price relative to max budget or benchmark
        max_budget = float(listing.max_budget_inr) if listing.max_budget_inr else None
        if max_budget and max_budget > 0:
            if price_inr <= max_budget:
                # Up to 100 if at or below 80% of budget
                cost_ratio = price_inr / max_budget
                cost_score = max(0.0, min(100.0, (1.2 - cost_ratio) * 100.0))
            else:
                over_ratio = (price_inr - max_budget) / max_budget
                cost_score = max(0.0, 100.0 - (over_ratio * 150.0))
        else:
            # Baseline estimation if no budget set
            cost_score = 75.0

        # 2. Transit Time & Deadline Score (0 - 100)
        if listing.delivery_deadline:
            now = timezone.now()
            hours_available = max(0.1, (listing.delivery_deadline - now).total_seconds() / 3600.0)
            if transit_hours <= hours_available:
                slack_ratio = (hours_available - transit_hours) / hours_available
                time_score = min(100.0, 60.0 + (slack_ratio * 40.0))
            else:
                # Late penalty
                over_hrs = transit_hours - hours_available
                time_score = max(0.0, 50.0 - (over_hrs * 10.0))
        else:
            time_score = 80.0

        # 3. Route Safety Score (0 - 100)
        # Multimodal waterway/rail avoids NH-6 landslides; road has terrain exposure
        if "WATERWAY" in proposed_mode:
            safety_score = 92.0  # NW-2 Brahmaputra immune to road landslides
        elif "RAIL" in proposed_mode:
            safety_score = 88.0  # NF Railway heavy transport
        elif proposed_mode == "MULTIMODAL":
            safety_score = 90.0
        else:
            safety_score = 74.0  # Mountain highway exposure

        # 4. Vehicle & Equipment Suitability Score (0 - 100)
        suitability_score = 70.0
        if vehicle:
            # Check capacity
            payload_fit = True
            if vehicle.capacity_kg and listing.weight_kg:
                if vehicle.capacity_kg >= float(listing.weight_kg):
                    suitability_score += 15.0
                else:
                    payload_fit = False
                    suitability_score -= 40.0
            # Check cold-chain
            if listing.is_cold_chain:
                # Bolero / Reefer check
                if "REEFER" in str(vehicle.vehicle_type).upper() or "COLD" in str(vehicle.operating_region).upper():
                    suitability_score += 15.0
                else:
                    suitability_score -= 20.0
            else:
                suitability_score += 10.0
        else:
            if listing.is_cold_chain:
                suitability_score = 60.0
            else:
                suitability_score = 75.0
        suitability_score = max(0.0, min(100.0, suitability_score))

        # 5. Operator Reliability Rating Score (0 - 100)
        rating_score = max(0.0, min(100.0, (operator_rating / 5.0) * 100.0))

        # Composite Score
        composite_score = (
            (cls.WEIGHT_COST * cost_score)
            + (cls.WEIGHT_TIME * time_score)
            + (cls.WEIGHT_SAFETY * safety_score)
            + (cls.WEIGHT_SUITABILITY * suitability_score)
            + (cls.WEIGHT_RATING * rating_score)
        )
        composite_score = round(max(0.0, min(100.0, composite_score)), 1)

        # Synthesize explainability text
        reasons = []
        if cost_score >= 80:
            reasons.append("Highly competitive commercial rate")
        elif cost_score < 50:
            reasons.append("Premium quote exceeding target budget")

        if time_score >= 85:
            reasons.append(f"Fast delivery buffer (ETA: {transit_hours:.1f}h)")
        elif time_score < 60:
            reasons.append("Tight delivery deadline margin")

        if safety_score >= 85:
            reasons.append(f"High-resilience {proposed_mode} corridor bypasses hill hazards")
        
        if listing.is_cold_chain and suitability_score >= 80:
            reasons.append("Verified active cold-chain temperature control")

        explanation = ". ".join(reasons) + "."

        return {
            "final_score": composite_score,
            "cost_score": round(cost_score, 1),
            "time_score": round(time_score, 1),
            "safety_score": round(safety_score, 1),
            "suitability_score": round(suitability_score, 1),
            "rating_score": round(rating_score, 1),
            "explanation": explanation,
        }

    @classmethod
    def submit_bid(
        cls,
        listing: MarketplaceListing,
        carrier: Any,
        price_inr: float,
        estimated_transit_hours: float,
        proposed_mode: str,
        proposed_vehicle: Optional[Any] = None,
        capacity_offered_kg: Optional[float] = None,
        terms: str = "",
        operator_rating: float = 4.5,
    ) -> FreightBid:
        """
        Creates a new carrier freight bid with automated AI factor evaluation.
        """
        if listing.status not in [ListingStatus.PUBLISHED, ListingStatus.BIDDING]:
            raise ValidationError(f"Cannot submit bid on listing with status '{listing.status}'.")

        factors = cls.evaluate_bid_factors(
            listing=listing,
            price_inr=price_inr,
            transit_hours=estimated_transit_hours,
            proposed_mode=proposed_mode,
            vehicle=proposed_vehicle,
            operator_rating=operator_rating,
        )

        eta = timezone.now() + timezone.timedelta(hours=estimated_transit_hours)
        validity = timezone.now() + timezone.timedelta(days=3)

        offered_cap = capacity_offered_kg or (float(proposed_vehicle.capacity_kg) if proposed_vehicle and proposed_vehicle.capacity_kg else 5000.0)

        bid = FreightBid.objects.create(
            listing=listing,
            carrier=carrier,
            proposed_vehicle=proposed_vehicle,
            proposed_mode=proposed_mode,
            price_inr=price_inr,
            estimated_transit_hours=estimated_transit_hours,
            eta=eta,
            validity_period=validity,
            capacity_offered_kg=offered_cap,
            terms=terms,
            operator_rating=operator_rating,
            status=BidStatus.ACTIVE,
            ai_recommendation_score=factors["final_score"],
            ai_recommendation_factors=factors,
            recommendation_explanation=factors["explanation"],
        )

        # Transition listing to BIDDING if it was only PUBLISHED
        if listing.status == ListingStatus.PUBLISHED:
            listing.status = ListingStatus.BIDDING
            listing.save(update_fields=["status"])

        return bid

    @classmethod
    @transaction.atomic
    def accept_bid(cls, bid: FreightBid, user: Any) -> Dict[str, Any]:
        """
        Shipper accepts a winning carrier bid.
        Marks other bids rejected, listing matched, binds FreightLoad,
        and generates the digital shipment document.
        """
        listing = bid.listing
        if bid.status not in [BidStatus.SUBMITTED, BidStatus.ACTIVE]:
            raise ValidationError(f"Bid cannot be accepted from status '{bid.status}'.")

        # 1. Accept winning bid
        bid.status = BidStatus.ACCEPTED
        bid.save(update_fields=["status"])

        # 2. Reject all other bids on this listing
        FreightBid.objects.filter(listing=listing).exclude(id=bid.id).update(status=BidStatus.REJECTED)

        # 3. Update listing status
        listing.status = ListingStatus.MATCHED
        listing.save(update_fields=["status"])

        # 4. If linked to FreightLoad, update load and create LoadAssignment
        load = listing.load
        load_assignment = None
        if load:
            load.status = CargoStatus.MATCHED
            if bid.proposed_vehicle:
                load.assigned_vehicle = bid.proposed_vehicle
            load.save(update_fields=["status", "assigned_vehicle"])

            if bid.proposed_vehicle:
                load_assignment = LoadAssignment.objects.create(
                    load=load,
                    vehicle=bid.proposed_vehicle,
                    driver=getattr(bid.proposed_vehicle, "assigned_driver", None),
                    matched_score=bid.ai_recommendation_score,
                    matching_factors=bid.ai_recommendation_factors,
                    assigned_by=user if hasattr(user, "is_authenticated") and user.is_authenticated else None,
                    is_active=True,
                )

        # 5. Generate digital shipment document
        from apps.shipments.services.document_service import DigitalShipmentDocumentService
        document = DigitalShipmentDocumentService.generate_document_for_bid(bid, user)

        return {
            "bid": bid,
            "listing": listing,
            "load_assignment": load_assignment,
            "document": document,
            "message": f"Bid #{str(bid.id)[:8]} accepted. Digital freight document {document.shipment_number} issued.",
        }
