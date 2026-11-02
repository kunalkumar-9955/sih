import 'package:latlong2/latlong.dart';

class RouteSegment {
  final int sequence;
  final String edgeId;
  final String sourceName;
  final String targetName;
  final String mode;
  final double distanceM;
  final double transitTimeMin;
  final double costInr;
  final double hazardScore;
  final String roadName;
  final double? transferTimeMin;
  final double? transferCostInr;

  RouteSegment({
    required this.sequence,
    required this.edgeId,
    required this.sourceName,
    required this.targetName,
    required this.mode,
    required this.distanceM,
    required this.transitTimeMin,
    required this.costInr,
    required this.hazardScore,
    required this.roadName,
    this.transferTimeMin,
    this.transferCostInr,
  });

  factory RouteSegment.fromJson(Map<String, dynamic> json) {
    return RouteSegment(
      sequence: json['sequence'] ?? 1,
      edgeId: json['edge_id'] ?? '',
      sourceName: json['source_node'] ?? json['source_name'] ?? '',
      targetName: json['target_node'] ?? json['target_name'] ?? '',
      mode: json['mode'] ?? '',
      distanceM: (json['distance_m'] as num?)?.toDouble() ?? 0.0,
      transitTimeMin: (json['transit_time_min'] as num?)?.toDouble() ?? 0.0,
      costInr: (json['cost_inr'] as num?)?.toDouble() ?? 0.0,
      hazardScore: (json['hazard_score'] as num?)?.toDouble() ?? 0.0,
      roadName: json['road_name'] ?? '',
      transferTimeMin: (json['transfer_time_min'] as num?)?.toDouble(),
      transferCostInr: (json['transfer_cost_inr'] as num?)?.toDouble(),
    );
  }
}

class RouteOption {
  final String id;
  final String originNodeName;
  final String destinationNodeName;
  final String routeType;
  final String routeTypeDisplay;
  final double totalDistanceM;
  final double totalTimeMin;
  final double totalCostInr;
  final double hazardPenaltyScore;
  final List<String> modesUsed;
  final int transferCount;
  final String explanation;
  final List<LatLng> coordinates;
  final List<RouteSegment> segments;

  RouteOption({
    required this.id,
    required this.originNodeName,
    required this.destinationNodeName,
    required this.routeType,
    required this.routeTypeDisplay,
    required this.totalDistanceM,
    required this.totalTimeMin,
    required this.totalCostInr,
    required this.hazardPenaltyScore,
    required this.modesUsed,
    required this.transferCount,
    required this.explanation,
    required this.coordinates,
    required this.segments,
  });

  factory RouteOption.fromJson(Map<String, dynamic> json) {
    final rawCoords = json['geometry_coordinates'] as List<dynamic>? ?? [];
    final List<LatLng> coordsList = [];
    for (var item in rawCoords) {
      if (item is List && item.length >= 2) {
        coordsList.add(LatLng((item[1] as num).toDouble(), (item[0] as num).toDouble()));
      }
    }

    final rawSegments = json['segments'] as List<dynamic>? ?? [];
    final segmentsList = rawSegments.map((s) => RouteSegment.fromJson(s as Map<String, dynamic>)).toList();

    final rawModes = json['modes_used'] as List<dynamic>? ?? [];
    final List<String> modesList = rawModes.map((m) => m.toString()).toList();

    return RouteOption(
      id: json['route_id'] ?? json['id'] ?? '',
      originNodeName: json['origin'] ?? json['origin_node_name'] ?? '',
      destinationNodeName: json['destination'] ?? json['destination_node_name'] ?? '',
      routeType: json['routing_policy'] ?? json['route_type'] ?? 'SAFEST',
      routeTypeDisplay: json['route_type_display'] ?? 'Safest',
      totalDistanceM: (json['total_distance'] ?? json['total_distance_m'] as num?)?.toDouble() ?? 0.0,
      totalTimeMin: (json['total_time'] ?? json['total_time_min'] as num?)?.toDouble() ?? 0.0,
      totalCostInr: (json['total_cost'] ?? json['total_cost_inr'] as num?)?.toDouble() ?? 0.0,
      hazardPenaltyScore: (json['risk_score'] ?? json['hazard_penalty_score'] as num?)?.toDouble() ?? 0.0,
      modesUsed: modesList,
      transferCount: json['transfer_count'] ?? 0,
      explanation: json['explanation'] ?? '',
      coordinates: coordsList,
      segments: segmentsList,
    );
  }
}
