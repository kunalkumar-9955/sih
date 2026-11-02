class SyncEventType {
  static const String locationUpdate = 'LOCATION_UPDATE';
  static const String tripStatus = 'TRIP_STATUS';
  static const String hazardReport = 'HAZARD_REPORT';
  static const String routeAck = 'ROUTE_ACK';
  static const String sosEmergency = 'SOS_EMERGENCY';
}

class SyncEventStatus {
  static const String queued = 'QUEUED';
  static const String applied = 'APPLIED';
  static const String conflict = 'CONFLICT';
  static const String rejected = 'REJECTED';
  static const String duplicate = 'DUPLICATE';
}

class SyncQueueItem {
  final String idempotencyKey;
  final String eventType;
  final DateTime clientTimestamp;
  final Map<String, dynamic> payload;
  int retryCount;
  String status;
  DateTime? lastAttempt;
  String? errorMessage;

  SyncQueueItem({
    required this.idempotencyKey,
    required this.eventType,
    required this.clientTimestamp,
    required this.payload,
    this.retryCount = 0,
    this.status = SyncEventStatus.queued,
    this.lastAttempt,
    this.errorMessage,
  });

  factory SyncQueueItem.fromJson(Map<String, dynamic> json) {
    return SyncQueueItem(
      idempotencyKey: json['idempotency_key'] ?? '',
      eventType: json['event_type'] ?? SyncEventType.locationUpdate,
      clientTimestamp: DateTime.tryParse(json['client_timestamp'] ?? '') ?? DateTime.now(),
      payload: json['payload'] is Map<String, dynamic> ? json['payload'] as Map<String, dynamic> : {},
      retryCount: (json['retry_count'] as num?)?.toInt() ?? 0,
      status: json['status'] ?? SyncEventStatus.queued,
      lastAttempt: json['last_attempt'] != null ? DateTime.tryParse(json['last_attempt']) : null,
      errorMessage: json['error_message'],
    );
  }

  Map<String, dynamic> toJson() => {
        'idempotency_key': idempotencyKey,
        'event_type': eventType,
        'client_timestamp': clientTimestamp.toIso8601String(),
        'payload': payload,
        'retry_count': retryCount,
        'status': status,
        'last_attempt': lastAttempt?.toIso8601String(),
        'error_message': errorMessage,
      };

  Map<String, dynamic> toApiBatchPayload() => {
        'idempotency_key': idempotencyKey,
        'event_type': eventType,
        'client_timestamp': clientTimestamp.toIso8601String(),
        'payload': payload,
      };
}
