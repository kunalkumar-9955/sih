import 'package:latlong2/latlong.dart';

class OfflineNode {
  final int id;
  final String name;
  final String shortCode;
  final String nodeType;
  final LatLng position;
  final double elevationM;
  final String state;
  final String district;
  final bool isIntermodalHub;

  OfflineNode({
    required this.id,
    required this.name,
    required this.shortCode,
    required this.nodeType,
    required this.position,
    required this.elevationM,
    required this.state,
    required this.district,
    required this.isIntermodalHub,
  });

  factory OfflineNode.fromJson(Map<String, dynamic> json) {
    final coords = json['coordinates'] as List<dynamic>? ?? [0.0, 0.0];
    final lon = (coords[0] as num).toDouble();
    final lat = (coords[1] as num).toDouble();

    return OfflineNode(
      id: json['id'] as int,
      name: json['name'] ?? '',
      shortCode: json['short_code'] ?? '',
      nodeType: json['node_type'] ?? 'ROAD_INTERSECTION',
      position: LatLng(lat, lon),
      elevationM: (json['elevation_m'] as num?)?.toDouble() ?? 0.0,
      state: json['state'] ?? '',
      district: json['district'] ?? '',
      isIntermodalHub: json['is_intermodal_hub'] == true,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'short_code': shortCode,
        'node_type': nodeType,
        'coordinates': [position.longitude, position.latitude],
        'elevation_m': elevationM,
        'state': state,
        'district': district,
        'is_intermodal_hub': isIntermodalHub,
      };
}

class OfflineEdge {
  final int id;
  final int sourceNodeId;
  final int targetNodeId;
  final String mode;
  final String roadName;
  final double distanceM;
  final double baseTransitTimeMin;
  final double costInr;
  final double? capacityKg;
  final String status;
  final bool isAvailable;
  final double hazardScore;
  final String hazardSeverity;
  final double transferTimeMin;
  final double transferCostInr;
  final List<LatLng> geometry;

  OfflineEdge({
    required this.id,
    required this.sourceNodeId,
    required this.targetNodeId,
    required this.mode,
    required this.roadName,
    required this.distanceM,
    required this.baseTransitTimeMin,
    required this.costInr,
    this.capacityKg,
    required this.status,
    required this.isAvailable,
    required this.hazardScore,
    required this.hazardSeverity,
    required this.transferTimeMin,
    required this.transferCostInr,
    required this.geometry,
  });

  factory OfflineEdge.fromJson(Map<String, dynamic> json) {
    final rawGeom = json['geometry'] as List<dynamic>? ?? [];
    final List<LatLng> geomList = [];
    for (var pt in rawGeom) {
      if (pt is List && pt.length >= 2) {
        geomList.add(LatLng((pt[1] as num).toDouble(), (pt[0] as num).toDouble()));
      }
    }

    return OfflineEdge(
      id: json['id'] as int,
      sourceNodeId: json['source_node_id'] as int,
      targetNodeId: json['target_node_id'] as int,
      mode: json['mode'] ?? 'ROAD',
      roadName: json['road_name'] ?? '',
      distanceM: (json['distance_m'] as num?)?.toDouble() ?? 0.0,
      baseTransitTimeMin: (json['base_transit_time_min'] as num?)?.toDouble() ?? 0.0,
      costInr: (json['cost_inr'] as num?)?.toDouble() ?? 0.0,
      capacityKg: (json['capacity_kg'] as num?)?.toDouble(),
      status: json['status'] ?? 'OPEN',
      isAvailable: json['is_available'] ?? true,
      hazardScore: (json['hazard_score'] as num?)?.toDouble() ?? 0.0,
      hazardSeverity: json['hazard_severity'] ?? 'LOW',
      transferTimeMin: (json['transfer_time_min'] as num?)?.toDouble() ?? 0.0,
      transferCostInr: (json['transfer_cost_inr'] as num?)?.toDouble() ?? 0.0,
      geometry: geomList,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'source_node_id': sourceNodeId,
        'target_node_id': targetNodeId,
        'mode': mode,
        'road_name': roadName,
        'distance_m': distanceM,
        'base_transit_time_min': baseTransitTimeMin,
        'cost_inr': costInr,
        'capacity_kg': capacityKg,
        'status': status,
        'is_available': isAvailable,
        'hazard_score': hazardScore,
        'hazard_severity': hazardSeverity,
        'transfer_time_min': transferTimeMin,
        'transfer_cost_inr': transferCostInr,
        'geometry': geometry.map((p) => [p.longitude, p.latitude]).toList(),
      };
}

class OfflineGraphBundleModel {
  final String region;
  final String versionTag;
  final String checksumSha256;
  final String exportedAt;
  final int nodesCount;
  final int edgesCount;
  final List<OfflineNode> nodes;
  final List<OfflineEdge> edges;

  OfflineGraphBundleModel({
    required this.region,
    required this.versionTag,
    required this.checksumSha256,
    required this.exportedAt,
    required this.nodesCount,
    required this.edgesCount,
    required this.nodes,
    required this.edges,
  });

  factory OfflineGraphBundleModel.fromJson(Map<String, dynamic> json, {String? versionTag, String? checksum}) {
    final payload = json['bundle_data'] is Map<String, dynamic> ? json['bundle_data'] as Map<String, dynamic> : json;

    final rawNodes = payload['nodes'] as List<dynamic>? ?? [];
    final rawEdges = payload['edges'] as List<dynamic>? ?? [];

    return OfflineGraphBundleModel(
      region: payload['region'] ?? json['region'] ?? 'NER_CORRIDOR',
      versionTag: json['version_tag'] ?? versionTag ?? 'v1.0.0',
      checksumSha256: json['checksum_sha256'] ?? checksum ?? '',
      exportedAt: payload['exported_at'] ?? DateTime.now().toIso8601String(),
      nodesCount: (payload['nodes_count'] as num?)?.toInt() ?? rawNodes.length,
      edgesCount: (payload['edges_count'] as num?)?.toInt() ?? rawEdges.length,
      nodes: rawNodes.map((n) => OfflineNode.fromJson(n as Map<String, dynamic>)).toList(),
      edges: rawEdges.map((e) => OfflineEdge.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'region': region,
        'version_tag': versionTag,
        'checksum_sha256': checksumSha256,
        'exported_at': exportedAt,
        'nodes_count': nodesCount,
        'edges_count': edgesCount,
        'nodes': nodes.map((n) => n.toJson()).toList(),
        'edges': edges.map((e) => e.toJson()).toList(),
      };
}
