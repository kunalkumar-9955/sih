class Trip {
  final String id;
  final String? driverName;
  final String? vehicleRegistration;
  final String originName;
  final String destinationName;
  final String status;
  final String statusDisplay;
  final String? plannedDeparture;
  final String? actualDeparture;
  final String cargoDescription;
  final double? cargoWeightKg;

  Trip({
    required this.id,
    this.driverName,
    this.vehicleRegistration,
    required this.originName,
    required this.destinationName,
    required this.status,
    required this.statusDisplay,
    this.plannedDeparture,
    this.actualDeparture,
    required this.cargoDescription,
    this.cargoWeightKg,
  });

  factory Trip.fromJson(Map<String, dynamic> json) {
    return Trip(
      id: json['id'] ?? '',
      driverName: json['driver_name'],
      vehicleRegistration: json['vehicle_registration'],
      originName: json['origin_name'] ?? '',
      destinationName: json['destination_name'] ?? '',
      status: json['status'] ?? 'PLANNED',
      statusDisplay: json['status_display'] ?? 'Planned',
      plannedDeparture: json['planned_departure'],
      actualDeparture: json['actual_departure'],
      cargoDescription: json['cargo_description'] ?? '',
      cargoWeightKg: (json['cargo_weight_kg'] as num?)?.toDouble(),
    );
  }
}
