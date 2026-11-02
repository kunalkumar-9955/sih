"""
SIH26002 — Route Cache Invalidator.

Invalidates cached route queries when transport edge hazard scores or
operational statuses change.
"""
import logging
from typing import List, Optional
from django.core.cache import cache

logger = logging.getLogger("sih.routing.cache")


class RouteCacheInvalidator:
    """
    Handles targeted and bulk cache invalidation for routing calculations.
    """

    CACHE_PREFIX = "sih_route"

    @classmethod
    def get_cache_key(cls, origin_id: str, dest_id: str, policy: str) -> str:
        return f"{cls.CACHE_PREFIX}:{origin_id}:{dest_id}:{policy}"

    @classmethod
    def invalidate_pair(cls, origin_id: str, dest_id: str):
        """Invalidate all policy routes for a specific origin-destination pair."""
        policies = ["FASTEST", "SAFEST", "CHEAPEST", "MULTIMODAL"]
        for p in policies:
            key = cls.get_cache_key(origin_id, dest_id, p)
            cache.delete(key)
        logger.info(f"Invalidated route cache for OD pair {origin_id} → {dest_id}")

    @classmethod
    def invalidate_for_edges(cls, edge_ids: List[str]):
        """
        Invalidate routes that pass through the affected edges.
        If cache backend supports pattern deletion (e.g. redis), uses that,
        or clears prefix namespace.
        """
        try:
            if hasattr(cache, "delete_pattern"):
                cache.delete_pattern(f"{cls.CACHE_PREFIX}:*")
            else:
                # locmem or dummy fallback
                cache.clear()
            logger.info(f"Invalidated route cache for {len(edge_ids)} affected edges.")
        except Exception as e:
            logger.warning(f"Cache invalidation error (non-fatal): {e}")

    @classmethod
    def invalidate_all_routes(cls):
        """Flush all route caches."""
        try:
            if hasattr(cache, "delete_pattern"):
                cache.delete_pattern(f"{cls.CACHE_PREFIX}:*")
            else:
                cache.clear()
            logger.info("Cleared all route caches.")
        except Exception as e:
            logger.warning(f"Cache flush error (non-fatal): {e}")
