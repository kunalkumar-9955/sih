"""
SIH26002 — Sync Conflict Resolution Service.

Implements conflict detection and resolution rules for asynchronous offline sync:
1. Trip State Monotonicity (preventing regressions from terminal states).
2. Route Version Validation (detecting stale route acknowledgments).
3. Last-Write-Wins (LWW) with temporal sanity window verification.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from django.utils import timezone

from apps.trips.models import Trip, TripStatus


class SyncConflictResolver:
    """
    Validates offline queued events against current server state.
    """

    # Monotonic order rank for trip lifecycle
    STATE_RANKS = {
        TripStatus.PLANNED: 1,
        TripStatus.ACTIVE: 2,
        TripStatus.PAUSED: 2,  # Paused can alternate with Active
        TripStatus.COMPLETED: 3,
        TripStatus.CANCELLED: 3,
    }

    TERMINAL_STATES = {TripStatus.COMPLETED, TripStatus.CANCELLED}

    # Max allowed age for offline events: 24 hours
    MAX_EVENT_AGE_HOURS = 24.0
    # Max allowed future skew: 10 minutes
    MAX_FUTURE_SKEW_MINUTES = 10.0

    @classmethod
    def validate_timestamp_sanity(
        cls, client_timestamp: datetime, now: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        Ensures client event timestamp falls within a realistic operational window.
        """
        if now is None:
            now = timezone.now()

        # Check if timestamp is naive; make aware if needed
        if timezone.is_naive(client_timestamp):
            client_timestamp = timezone.make_aware(client_timestamp)

        # Check future skew
        if client_timestamp > now + timedelta(minutes=cls.MAX_FUTURE_SKEW_MINUTES):
            return False, f"Event timestamp is {client_timestamp} which is too far in future."

        # Check age drift (> 24 hours)
        if now - client_timestamp > timedelta(hours=cls.MAX_EVENT_AGE_HOURS):
            return False, f"Event is older than {cls.MAX_EVENT_AGE_HOURS} hours (stale event)."

        return True, ""

    @classmethod
    def resolve_trip_state_transition(
        cls, current_status: str, requested_status: str
    ) -> Tuple[bool, str]:
        """
        Validates monotonic trip state transitions.
        Returns: (is_allowed, error_or_warning_message)
        """
        # If identical, no-op
        if current_status == requested_status:
            return True, "No-op identical state."

        # If current state is terminal, no transition allowed
        if current_status in cls.TERMINAL_STATES:
            return False, f"Trip is already in terminal state '{current_status}'. Cannot transition to '{requested_status}'."

        curr_rank = cls.STATE_RANKS.get(current_status, 0)
        req_rank = cls.STATE_RANKS.get(requested_status, 0)

        # Regression check: cannot move from ACTIVE/PAUSED back to PLANNED
        if req_rank < curr_rank:
            return False, f"Illegal state regression from '{current_status}' to '{requested_status}'."

        return True, ""

    @classmethod
    def validate_route_version(
        cls, trip: Trip, client_route_version: Optional[int]
    ) -> Tuple[bool, str]:
        """
        Validates route versioning between client and server.
        """
        if client_route_version is None:
            return True, ""

        if client_route_version < trip.route_version:
            return (
                False,
                f"Stale route version: Client is on v{client_route_version}, but server has updated to v{trip.route_version}.",
            )

        return True, ""

    @classmethod
    def apply_last_write_wins(
        cls,
        server_updated_at: datetime,
        client_timestamp: datetime,
    ) -> bool:
        """
        Returns True if client write is newer than server record.
        """
        if timezone.is_naive(client_timestamp):
            client_timestamp = timezone.make_aware(client_timestamp)
        if timezone.is_naive(server_updated_at):
            server_updated_at = timezone.make_aware(server_updated_at)

        return client_timestamp >= server_updated_at
