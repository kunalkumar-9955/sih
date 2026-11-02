class TransportNode {
  final String id;
  final String name;
  final String? shortCode;
  final String nodeType;
  final String nodeTypeDisplay;
  final double longitude;
  final double latitude;
  final double? elevationM;
  final String state;
  final String district;

  TransportNode({
    required this.id,
    required this.name,
    this.shortCode,
    required this.nodeType,
    required this.nodeTypeDisplay,
    required this.longitude,
    required this.latitude,
    this.elevationM,
    required this.state,
    required this.district,
  });

  factory TransportNode.fromJson(Map<String, dynamic> json) {
    final coords = json['coordinates'] as Map<String, dynamic>?;
    return TransportNode(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      shortCode: json['short_code'],
      nodeType: json['node_type'] ?? '',
      nodeTypeDisplay: json['node_type_display'] ?? '',
      longitude: (coords?['longitude'] as num?)?.toDouble() ?? 0.0,
      latitude: (coords?['latitude'] as num?)?.toDouble() ?? 0.0,
      elevationM: (json['elevation_m'] as num?)?.toDouble(),
      state: json['state'] ?? '',
      district: json['district'] ?? '',
    );
  }
}
