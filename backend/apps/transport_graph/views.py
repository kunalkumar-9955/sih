"""
SIH26002 — Transport graph views.
"""
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.decorators import audit_action  # noqa: F401  — available for view decorators
from apps.users.permissions import CanManageTransportGraph, IsAuthenticatedAndVerified
from .models import EdgeStatus, TransportEdge, TransportNode
from .serializers import (
    TransportEdgeSerializer,
    TransportGraphDumpSerializer,
    TransportNodeSerializer,
)


class TransportNodeListView(generics.ListCreateAPIView):
    """
    List transport nodes or create a new node.
    Read: Authenticated users.
    Create: Graph Admins / Ministry Admins only.
    """

    serializer_class = TransportNodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = TransportNode.objects.all()
        node_type = self.request.query_params.get("node_type")
        state = self.request.query_params.get("state")
        is_active = self.request.query_params.get("is_active")

        if node_type:
            qs = qs.filter(node_type=node_type)
        if state:
            qs = qs.filter(state__iexact=state)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), CanManageTransportGraph()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        node = serializer.save()
        audit_log(
            actor=self.request.user,
            action="CREATE_NODE",
            resource_type="TransportNode",
            resource_id=node.id,
            payload={"name": node.name, "node_type": node.node_type},
        )


class TransportNodeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a transport node."""

    queryset = TransportNode.objects.all()
    serializer_class = TransportNodeSerializer

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [permissions.IsAuthenticated(), CanManageTransportGraph()]
        return [permissions.IsAuthenticated()]


class TransportEdgeListView(generics.ListCreateAPIView):
    """
    List transport edges or create a new edge.
    Read: Authenticated users.
    Create: Graph Admins / Ministry Admins only.
    """

    serializer_class = TransportEdgeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = TransportEdge.objects.select_related("source_node", "target_node").all()
        mode = self.request.query_params.get("mode")
        edge_status = self.request.query_params.get("status")
        traversable_only = self.request.query_params.get("traversable_only")

        if mode:
            qs = qs.filter(mode=mode)
        if edge_status:
            qs = qs.filter(status=edge_status)
        if traversable_only and traversable_only.lower() == "true":
            qs = qs.filter(
                is_available=True
            ).exclude(status__in=[EdgeStatus.BLOCKED, EdgeStatus.CRITICAL])
        return qs

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), CanManageTransportGraph()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        edge = serializer.save()
        audit_log(
            actor=self.request.user,
            action="CREATE_EDGE",
            resource_type="TransportEdge",
            resource_id=edge.id,
            payload={
                "source": str(edge.source_node_id),
                "target": str(edge.target_node_id),
                "mode": edge.mode,
            },
        )


class TransportEdgeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a transport edge."""

    queryset = TransportEdge.objects.select_related("source_node", "target_node").all()
    serializer_class = TransportEdgeSerializer

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [permissions.IsAuthenticated(), CanManageTransportGraph()]
        return [permissions.IsAuthenticated()]


class TransportGraphDumpView(APIView):
    """
    Returns full active transport graph (nodes and traversable edges).
    Optimized for offline cache sync on mobile devices and local client routing.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        nodes = TransportNode.objects.filter(is_active=True)
        edges = TransportEdge.objects.filter(is_available=True).select_related(
            "source_node", "target_node"
        )

        data = {
            "timestamp": timezone.now(),
            "nodes": TransportNodeSerializer(nodes, many=True).data,
            "edges": TransportEdgeSerializer(edges, many=True).data,
        }
        return Response(data, status=status.HTTP_200_OK)


class TransportEdgeStatusUpdateView(APIView):
    """
    Update the operational or hazard status of an edge (e.g. block due to landslide).
    """

    permission_classes = [permissions.IsAuthenticated, CanManageTransportGraph]

    def patch(self, request, pk):
        try:
            edge = TransportEdge.objects.get(pk=pk)
        except TransportEdge.DoesNotExist:
            return Response({"detail": "Edge not found."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        hazard_score = request.data.get("hazard_score")
        is_available = request.data.get("is_available")

        if new_status:
            if new_status not in EdgeStatus.values:
                return Response(
                    {"detail": f"Invalid status. Must be one of {EdgeStatus.values}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            edge.status = new_status

        if hazard_score is not None:
            try:
                score = float(hazard_score)
                if not (0.0 <= score <= 1.0):
                    raise ValueError()
                edge.hazard_score = score
            except (ValueError, TypeError):
                return Response(
                    {"detail": "hazard_score must be a float between 0.0 and 1.0"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if is_available is not None:
            edge.is_available = bool(is_available)

        edge.save()

        audit_log(
            actor=request.user,
            action="UPDATE_EDGE_STATUS",
            resource_type="TransportEdge",
            resource_id=edge.id,
            payload={
                "status": edge.status,
                "hazard_score": edge.hazard_score,
                "is_available": edge.is_available,
            },
        )

        return Response(TransportEdgeSerializer(edge).data, status=status.HTTP_200_OK)


class AccessibilityIntelligenceView(APIView):
    """
    GET /api/v1/transport/accessibility/
    Returns multi-criteria corridor accessibility score (0-100) and contributing factors.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        region = request.query_params.get("region", "NER_CORRIDOR")
        from apps.transport_graph.services.accessibility import AccessibilityIntelligenceService

        result = AccessibilityIntelligenceService.evaluate_corridor_accessibility(region=region)
        return Response(result, status=status.HTTP_200_OK)

