import 'dart:math';
import 'package:latlong2/latlong.dart';
import '../models/offline_graph.dart';
import '../models/route_option.dart';

class _AStarNode {
  final int nodeId;
  final double fScore;
  final double gScore;

  _AStarNode({required this.nodeId, required this.fScore, required this.gScore});
}

class OfflineRoutingService {
  final OfflineGraphBundleModel bundle;
  late final Map<int, OfflineNode> _nodesById;
  late final Map<int, List<OfflineEdge>> _adjacency;
  late final Map<int, OfflineEdge> _edgesById;

  static const double _maxSpeedMps = 25.0; // ~90 km/h denominator for heuristic

  OfflineRoutingService(this.bundle) {
    _nodesById = {for (var n in bundle.nodes) n.id: n};
    _edgesById = {for (var e in bundle.edges) e.id: e};
    _adjacency = {for (var n in bundle.nodes) n.id: []};

    for (var edge in bundle.edges) {
      if (_adjacency.containsKey(edge.sourceNodeId)) {
        _adjacency[edge.sourceNodeId]!.add(edge);
      }
    }
  }

  /// Great-circle Haversine distance between two points in metres.
  static double haversineM(double lat1, double lon1, double lat2, double lon2) {
    const r = 6371000.0;
    final phi1 = lat1 * pi / 180.0;
    final phi2 = lat2 * pi / 180.0;
    final dPhi = (lat2 - lat1) * pi / 180.0;
    final dLam = (lon2 - lon1) * pi / 180.0;

    final a = sin(dPhi / 2.0) * sin(dPhi / 2.0) +
        cos(phi1) * cos(phi2) * sin(dLam / 2.0) * sin(dLam / 2.0);
    final c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a));
    return r * c;
  }

  double _heuristic(int currId, int targetId, String policy) {
    final curr = _nodesById[currId];
    final target = _nodesById[targetId];
    if (curr == null || target == null) return 0.0;

    final distM = haversineM(
      curr.position.latitude,
      curr.position.longitude,
      target.position.latitude,
      target.position.longitude,
    );

    final minTransitMin = (distM / _maxSpeedMps) / 60.0;
    if (policy == 'CHEAPEST') {
      return minTransitMin * 20.0;
    }
    return minTransitMin;
  }

  double _evaluateEdgeWeight(OfflineEdge edge, String policy, double? vehicleWeightKg) {
    if (!edge.isAvailable) return double.infinity;
    if (['BLOCKED', 'SEASONAL', 'UNDER_REPAIR'].contains(edge.status)) {
      return double.infinity;
    }

    if (edge.capacityKg != null && vehicleWeightKg != null) {
      if (vehicleWeightKg > edge.capacityKg!) return double.infinity;
    }

    double statusMult = 1.0;
    if (edge.status == 'RESTRICTED') {
      statusMult = 1.35;
    } else if (edge.status == 'CRITICAL') {
      statusMult = policy == 'SAFEST' ? 8.0 : 3.5;
    }

    final transitTime = edge.baseTransitTimeMin * statusMult;
    final transferTime = edge.transferTimeMin;
    final costInr = edge.costInr > 0 ? edge.costInr : (transitTime * 25.0);
    final transferCost = edge.transferCostInr;
    final hazard = edge.hazardScore;

    switch (policy) {
      case 'FASTEST':
        return transitTime + (transferTime * 1.5) + (hazard * 5.0);
      case 'SAFEST':
        final hazardFactor = 1.0 + (1.5 * hazard * hazard * 6.0);
        return (transitTime * hazardFactor) + transferTime + (hazard * 250.0);
      case 'CHEAPEST':
        return (costInr * statusMult) + transferCost + (transitTime * 0.05);
      case 'MULTIMODAL':
        double modeFactor = 1.0;
        if (edge.mode == 'RAIL') modeFactor = 0.80;
        if (edge.mode == 'WATER' || edge.mode == 'WATERWAY') modeFactor = 0.70;
        final hazardFactor = 1.0 + (1.5 * hazard);
        return (transitTime * hazardFactor * modeFactor) + (transferTime * 0.9);
      default:
        return transitTime + (hazard * 10.0);
    }
  }

  /// Executes A* path search and packages the result into a UI-ready RouteOption.
  RouteOption? findRoute({
    required int originId,
    required int destinationId,
    String policy = 'SAFEST',
    double? vehicleWeightKg,
  }) {
    if (!_nodesById.containsKey(originId) || !_nodesById.containsKey(destinationId)) {
      return null;
    }

    final originNode = _nodesById[originId]!;
    final destNode = _nodesById[destinationId]!;

    if (originId == destinationId) {
      return RouteOption(
        id: 'offline_direct',
        originNodeName: originNode.name,
        destinationNodeName: destNode.name,
        routeType: policy,
        routeTypeDisplay: '$policy (Offline Local)',
        totalDistanceM: 0.0,
        totalTimeMin: 0.0,
        totalCostInr: 0.0,
        hazardPenaltyScore: 0.0,
        modesUsed: ['ROAD'],
        transferCount: 0,
        explanation: 'Direct local route: Origin and destination are identical.',
        coordinates: [originNode.position],
        segments: [],
      );
    }

    final frontier = <_AStarNode>[
      _AStarNode(
        nodeId: originId,
        fScore: _heuristic(originId, destinationId, policy),
        gScore: 0.0,
      )
    ];

    final gScores = <int, double>{originId: 0.0};
    final cameFrom = <int, MapEntry<int, int>>{}; // targetNode -> MapEntry(prevNode, edgeId)
    final visited = <int>{};

    while (frontier.isNotEmpty) {
      // Extract lowest fScore
      frontier.sort((a, b) => a.fScore.compareTo(b.fScore));
      final current = frontier.removeAt(0);

      if (visited.contains(current.nodeId)) continue;
      visited.add(current.nodeId);

      if (current.nodeId == destinationId) break;

      final outgoing = _adjacency[current.nodeId] ?? [];
      for (var edge in outgoing) {
        final neighbor = edge.targetNodeId;
        if (visited.contains(neighbor)) continue;

        final weight = _evaluateEdgeWeight(edge, policy, vehicleWeightKg);
        if (weight.isInfinite) continue;

        final tentativeG = current.gScore + weight;
        if (!gScores.containsKey(neighbor) || tentativeG < gScores[neighbor]!) {
          gScores[neighbor] = tentativeG;
          cameFrom[neighbor] = MapEntry(current.nodeId, edge.id);
          final h = _heuristic(neighbor, destinationId, policy);
          frontier.add(_AStarNode(nodeId: neighbor, fScore: tentativeG + h, gScore: tentativeG));
        }
      }
    }

    if (!cameFrom.containsKey(destinationId)) {
      return null; // Path blocked or unreachable
    }

    // Reconstruct path
    final List<int> pathEdges = [];
    int curr = destinationId;
    while (cameFrom.containsKey(curr)) {
      final entry = cameFrom[curr]!;
      pathEdges.add(entry.value);
      curr = entry.key;
    }
    pathEdges.reversed.toList();
    final orderedEdges = pathEdges.reversed.map((eid) => _edgesById[eid]!).toList();

    // Construct route metrics & geometry
    double totalDistM = 0.0;
    double totalTransitMin = 0.0;
    double totalCostInr = 0.0;
    final List<double> hazards = [];
    final Set<String> modes = {};
    int transferCount = 0;
    final List<LatLng> fullCoords = [];
    final List<RouteSegment> segments = [];

    for (int i = 0; i < orderedEdges.length; i++) {
      final edge = orderedEdges[i];
      totalDistM += edge.distanceM;
      totalTransitMin += edge.baseTransitTimeMin + edge.transferTimeMin;
      totalCostInr += edge.costInr + edge.transferCostInr;
      hazards.add(edge.hazardScore);
      modes.add(edge.mode);
      if (edge.mode == 'TRANSFER') transferCount++;

      if (edge.geometry.isNotEmpty) {
        fullCoords.addAll(edge.geometry);
      } else {
        final sNode = _nodesById[edge.sourceNodeId];
        final tNode = _nodesById[edge.targetNodeId];
        if (sNode != null) fullCoords.add(sNode.position);
        if (tNode != null) fullCoords.add(tNode.position);
      }

      segments.add(RouteSegment(
        sequence: i + 1,
        edgeId: edge.id.toString(),
        sourceName: _nodesById[edge.sourceNodeId]?.name ?? 'Node ${edge.sourceNodeId}',
        targetName: _nodesById[edge.targetNodeId]?.name ?? 'Node ${edge.targetNodeId}',
        mode: edge.mode,
        distanceM: edge.distanceM,
        transitTimeMin: edge.baseTransitTimeMin,
        costInr: edge.costInr,
        hazardScore: edge.hazardScore,
        roadName: edge.roadName,
        transferTimeMin: edge.transferTimeMin,
        transferCostInr: edge.transferCostInr,
      ));
    }

    final avgHazard = hazards.isNotEmpty ? hazards.reduce((a, b) => a + b) / hazards.length : 0.0;

    return RouteOption(
      id: 'offline_${DateTime.now().millisecondsSinceEpoch}',
      originNodeName: originNode.name,
      destinationNodeName: destNode.name,
      routeType: policy,
      routeTypeDisplay: '$policy (Offline Local Cache)',
      totalDistanceM: totalDistM,
      totalTimeMin: totalTransitMin,
      totalCostInr: totalCostInr,
      hazardPenaltyScore: avgHazard,
      modesUsed: modes.toList(),
      transferCount: transferCount,
      explanation: 'Computed on-device via A* heuristic search over cached graph bundle (${bundle.versionTag}).',
      coordinates: fullCoords,
      segments: segments,
    );
  }
}
