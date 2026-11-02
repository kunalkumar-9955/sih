"""
SIH26002 — Hardened Routing Views.

Provides:
- POST /api/v1/routes/plan/      (Full multi-objective route planning with vehicle constraints)
- POST /api/v1/routes/compute/   (Backward-compatible endpoint)
- GET  /api/v1/routes/{id}/      (Retrieve computed route details)
- GET  /api/v1/routes/           (List active/current routes)
"""
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.decorators import audit_action, audit_log
from .constraints import VehicleContext
from .engine import RoutingEngine
from .models import Route
from .serializers import RoutePlanRequestSerializer, RouteSerializer


class RoutePlanView(APIView):
    """
    POST /api/v1/routes/plan/

    Orchestrates GIS multimodal route computation with:
    - Multi-policy alternatives (FASTEST, SAFEST, CHEAPEST, MULTIMODAL)
    - Vehicle payload & mode compatibility checks
    - Geohazard risk weighting
    - PostGIS spatial geometry synthesis
    - Contextual human-readable route explanations
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RoutePlanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        origin = data["resolved_origin"]
        destination = data["resolved_destination"]
        requested_types = data["requested_types"]
        alpha = data.get("alpha")
        persist = data.get("persist", True)

        vehicle_ctx = VehicleContext.from_dict({
            "vehicle_id": data.get("vehicle_id"),
            "vehicle_type": data.get("vehicle_type"),
            "cargo_weight": data.get("cargo_weight"),
            "departure_time": data.get("departure_time"),
            "allow_multimodal": data.get("allow_multimodal", True),
            "avoid_modes": data.get("avoid_modes", []),
            "preferred_modes": data.get("preferred_modes", []),
        })

        engine = RoutingEngine(alpha=alpha)
        routes = engine.compute_all_routes(
            origin=origin,
            destination=destination,
            requested_types=requested_types,
            vehicle_context=vehicle_ctx,
            alpha=alpha,
            persist=persist,
        )

        if not routes:
            return Response(
                {
                    "success": False,
                    "detail": (
                        f"No traversable multimodal route found from '{origin.name}' to '{destination.name}' "
                        f"under requested constraints (cargo weight, available modes, or active closures)."
                    ),
                    "routes": [],
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        audit_log(
            actor=request.user,
            action="PLAN_MULTIMODAL_ROUTE",
            resource_type="Route",
            resource_id=routes[0].id if persist else None,
            payload={
                "origin": origin.name,
                "destination": destination.name,
                "routes_generated": len(routes),
                "policies": [r.route_type for r in routes],
            },
        )

        serialized_routes = RouteSerializer(routes, many=True).data

        return Response(
            {
                "success": True,
                "origin": origin.name,
                "destination": destination.name,
                "routes_count": len(routes),
                "routes": serialized_routes,
                # Also include direct list for legacy clients expecting array directly
                "data": serialized_routes,
            },
            status=status.HTTP_200_OK,
        )


class RouteComputeView(APIView):
    """
    POST /api/v1/routes/compute/
    Backward-compatible endpoint returning a direct JSON array of route options.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RoutePlanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        origin = data["resolved_origin"]
        destination = data["resolved_destination"]
        requested_types = data["requested_types"]
        alpha = data.get("alpha")
        persist = data.get("persist", True)

        vehicle_ctx = VehicleContext.from_dict({
            "vehicle_id": data.get("vehicle_id"),
            "cargo_weight": data.get("cargo_weight"),
            "allow_multimodal": data.get("allow_multimodal", True),
        })

        engine = RoutingEngine(alpha=alpha)
        routes = engine.compute_all_routes(
            origin=origin,
            destination=destination,
            requested_types=requested_types,
            vehicle_context=vehicle_ctx,
            alpha=alpha,
            persist=persist,
        )

        if not routes:
            return Response(
                {"detail": "No traversable route found between specified nodes under current network conditions."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(RouteSerializer(routes, many=True).data, status=status.HTTP_200_OK)


class RouteDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/routes/{id}/
    Retrieve details of a specific computed route.
    """

    queryset = Route.objects.select_related("origin_node", "destination_node").all()
    serializer_class = RouteSerializer
    permission_classes = [permissions.IsAuthenticated]


class RouteListView(generics.ListAPIView):
    """
    GET /api/v1/routes/
    List previously computed routes.
    """

    serializer_class = RouteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Route.objects.select_related("origin_node", "destination_node").filter(is_current=True)
        origin_id = self.request.query_params.get("origin_node")
        dest_id = self.request.query_params.get("destination_node")
        route_type = self.request.query_params.get("route_type")

        if origin_id:
            qs = qs.filter(origin_node_id=origin_id)
        if dest_id:
            qs = qs.filter(destination_node_id=dest_id)
        if route_type:
            qs = qs.filter(route_type=route_type)
        return qs


class MultimodalRouteOptimizationView(APIView):
    """
    POST /api/v1/routes/multimodal-optimize/
    Pareto multi-objective route generation with multimodal transfer optimization,
    capacity, deadline feasibility, and contextual explainability.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        origin_id = data.get("origin_node_id") or data.get("origin_id")
        destination_id = data.get("destination_node_id") or data.get("destination_id")

        if not origin_id or not destination_id:
            return Response(
                {"success": False, "error": "origin_node_id and destination_node_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.routing.services.multimodal_service import MultimodalRouteOptimizationService

        result = MultimodalRouteOptimizationService.optimize(
            origin_id=origin_id,
            destination_id=destination_id,
            cargo_weight_kg=data.get("cargo_weight_kg"),
            cargo_type=data.get("cargo_type"),
            water_draft_m=data.get("water_draft_m"),
            avoid_modes=data.get("avoid_modes"),
            preferred_modes=data.get("preferred_modes"),
            allow_multimodal=data.get("allow_multimodal", True),
            max_hazard_threshold=data.get("max_hazard_threshold"),
            priority=data.get("priority", "NORMAL"),
            is_disaster_mode=data.get("is_disaster_mode", False),
        )
        http_status = status.HTTP_200_OK if result.get("success") else status.HTTP_400_BAD_REQUEST
        return Response(result, status=http_status)

