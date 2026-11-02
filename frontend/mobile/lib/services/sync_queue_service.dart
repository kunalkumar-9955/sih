import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../models/sync_event.dart';
import 'api_service.dart';

class SyncBatchResult {
  final bool isSuccess;
  final int appliedCount;
  final int conflictCount;
  final int duplicateCount;
  final int rejectedCount;
  final String message;

  SyncBatchResult({
    required this.isSuccess,
    this.appliedCount = 0,
    this.conflictCount = 0,
    this.duplicateCount = 0,
    this.rejectedCount = 0,
    this.message = '',
  });
}

class SyncQueueService extends ChangeNotifier {
  static const String _queueKey = 'driver_offline_sync_queue_v1';
  final _uuid = const Uuid();

  List<SyncQueueItem> _queue = [];
  bool _isSyncing = false;
  DateTime? _lastSyncTime;

  List<SyncQueueItem> get queue => List.unmodifiable(_queue);
  int get pendingCount => _queue.length;
  bool get isSyncing => _isSyncing;
  DateTime? get lastSyncTime => _lastSyncTime;

  /// Loads stored queue from persistent storage on startup.
  Future<void> initialize() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(_queueKey);
      if (raw != null && raw.isNotEmpty) {
        final List list = jsonDecode(raw);
        _queue = list.map((item) => SyncQueueItem.fromJson(item)).toList();
        notifyListeners();
      }
    } catch (_) {
      _queue = [];
    }
  }

  Future<void> _persistQueue() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final str = jsonEncode(_queue.map((e) => e.toJson()).toList());
      await prefs.setString(_queueKey, str);
      notifyListeners();
    } catch (_) {}
  }

  /// Appends a new event with client-generated UUID idempotency key.
  Future<SyncQueueItem> enqueueEvent(String eventType, Map<String, dynamic> payload) async {
    final item = SyncQueueItem(
      idempotencyKey: _uuid.v4(),
      eventType: eventType,
      clientTimestamp: DateTime.now(),
      payload: payload,
    );

    _queue.add(item);
    await _persistQueue();
    return item;
  }

  // Convenience queue helpers
  Future<void> queueLocationUpdate({
    required double lat,
    required double lon,
    double? speedMps,
    double? headingDeg,
    double? accuracyM,
    String? tripId,
  }) async {
    await enqueueEvent(SyncEventType.locationUpdate, {
      'latitude': lat,
      'longitude': lon,
      'speed_mps': speedMps ?? 0.0,
      'heading_deg': headingDeg ?? 0.0,
      'accuracy_m': accuracyM ?? 10.0,
      if (tripId != null) 'trip_id': tripId,
    });
  }

  Future<void> queueTripStatus({
    required String tripId,
    required String status,
    int? routeVersion,
  }) async {
    await enqueueEvent(SyncEventType.tripStatus, {
      'trip_id': tripId,
      'status': status,
      if (routeVersion != null) 'route_version': routeVersion,
    });
  }

  /// Phase 7: Enqueues offline freight load status transitions (PICKED_UP, DELIVERED).
  Future<void> queueLoadStatusUpdate({
    required String loadId,
    required String status,
    String? locationNote,
  }) async {
    await enqueueEvent(SyncEventType.tripStatus, {
      'load_id': loadId,
      'status': status,
      'location_note': locationNote ?? 'Updated by driver via mobile app',
      'timestamp': DateTime.now().toIso8601String(),
    });
  }

  Future<void> queueHazardReport({
    required String incidentType,
    required double lat,
    required double lon,
    String? description,
    String severity = 'MODERATE',
    int? edgeId,
  }) async {
    await enqueueEvent(SyncEventType.hazardReport, {
      'incident_type': incidentType,
      'latitude': lat,
      'longitude': lon,
      'description': description ?? 'Driver reported offline hazard.',
      'severity': severity,
      if (edgeId != null) 'edge_id': edgeId,
    });
  }

  Future<void> queueEmergencySos({
    required double lat,
    required double lon,
    String? tripId,
    String? message,
  }) async {
    await enqueueEvent(SyncEventType.sosEmergency, {
      'latitude': lat,
      'longitude': lon,
      if (tripId != null) 'trip_id': tripId,
      'message': message ?? 'Emergency SOS triggered offline by driver.',
    });
  }

  Future<void> queueRouteAck({
    required String tripId,
    required int routeVersion,
    String? routeId,
  }) async {
    await enqueueEvent(SyncEventType.routeAck, {
      'trip_id': tripId,
      'route_version': routeVersion,
      if (routeId != null) 'route_id': routeId,
    });
  }

  /// Flushes pending queue to backend batch sync API.
  Future<SyncBatchResult> flushQueue(ApiService apiService) async {
    if (_isSyncing || _queue.isEmpty) {
      return SyncBatchResult(isSuccess: true, message: 'Queue is empty or already syncing.');
    }

    _isSyncing = true;
    notifyListeners();

    try {
      // Take up to 50 events for batch upload
      final batchToUpload = _queue.take(50).toList();
      final batchPayload = batchToUpload.map((e) => e.toApiBatchPayload()).toList();

      final res = await apiService.sendSyncBatch(batchPayload);

      if (res != null) {
        final results = res['results'] as List<dynamic>? ?? [];
        final completedKeys = <String>{};

        for (var r in results) {
          final key = r['idempotency_key'] as String? ?? '';
          final st = r['status'] as String? ?? '';
          if (st == SyncEventStatus.applied || st == SyncEventStatus.duplicate) {
            completedKeys.add(key);
          } else if (st == SyncEventStatus.conflict) {
            // Find item in queue and mark conflict details
            final item = _queue.firstWhere((q) => q.idempotencyKey == key, orElse: () => batchToUpload.first);
            item.status = SyncEventStatus.conflict;
            item.errorMessage = r['message'];
          }
        }

        // Remove applied & duplicate events
        _queue.removeWhere((item) => completedKeys.contains(item.idempotencyKey));
        _lastSyncTime = DateTime.now();
        await _persistQueue();

        _isSyncing = false;
        notifyListeners();

        return SyncBatchResult(
          isSuccess: true,
          appliedCount: res['applied_count'] ?? 0,
          conflictCount: res['conflict_count'] ?? 0,
          duplicateCount: res['duplicate_count'] ?? 0,
          rejectedCount: res['rejected_count'] ?? 0,
          message: 'Synchronized ${completedKeys.length} offline events.',
        );
      } else {
        // Increment retry on items
        for (var item in batchToUpload) {
          item.retryCount += 1;
          item.lastAttempt = DateTime.now();
        }
        await _persistQueue();
        _isSyncing = false;
        notifyListeners();
        return SyncBatchResult(isSuccess: false, message: 'Server did not return a valid sync response.');
      }
    } catch (e) {
      _isSyncing = false;
      notifyListeners();
      return SyncBatchResult(isSuccess: false, message: 'Network sync failed: $e');
    }
  }
}
