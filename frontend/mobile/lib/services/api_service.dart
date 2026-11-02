import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/transport_node.dart';
import '../models/route_option.dart';
import '../models/trip.dart';

class ApiService {
  static const String baseUrl = "http://10.0.2.2:8000/api/v1"; // Standard Android emulator localhost alias
  final _storage = const FlutterSecureStorage();

  Future<String?> getToken() async {
    return await _storage.read(key: 'jwt_access_token');
  }

  Future<Map<String, String>> _getHeaders() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<Map<String, dynamic>> login(String email, String password) async {
    final res = await http.post(
      Uri.parse('$baseUrl/auth/login/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );

    if (res.statusCode == 200) {
      final body = jsonDecode(res.body);
      final tokens = body['data']['tokens'];
      await _storage.write(key: 'jwt_access_token', value: tokens['access']);
      await _storage.write(key: 'jwt_refresh_token', value: tokens['refresh']);
      return body['data'];
    } else {
      final err = jsonDecode(res.body);
      throw Exception(err['error']?['message'] ?? 'Login failed');
    }
  }

  Future<List<TransportNode>> getNodes() async {
    final headers = await _getHeaders();
    final res = await http.get(Uri.parse('$baseUrl/transport/nodes/'), headers: headers);
    if (res.statusCode == 200) {
      final body = jsonDecode(res.body);
      final results = body['results'] as List;
      return results.map((n) => TransportNode.fromJson(n)).toList();
    }
    return [];
  }

  Future<List<RouteOption>> planRoute({
    required String originId,
    required String destinationId,
    String routingPolicy = 'SAFEST',
    double? cargoWeightTons,
    bool allowMultimodal = true,
  }) async {
    final headers = await _getHeaders();
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/routes/plan/'),
        headers: headers,
        body: jsonEncode({
          'origin_node_id': originId,
          'destination_node_id': destinationId,
          'routing_policy': routingPolicy,
          'cargo_weight_tons': cargoWeightTons,
          'allow_multimodal': allowMultimodal,
        }),
      );

      if (res.statusCode == 200) {
        final body = jsonDecode(res.body);
        final List routesData = body['routes'] ?? [body];
        return routesData.map((r) => RouteOption.fromJson(r)).toList();
      }
    } catch (_) {
      // Fallback to legacy endpoint if plan fails
    }
    return computeRoutes(originId, destinationId);
  }

  Future<List<RouteOption>> computeRoutes(String originId, String destinationId) async {
    final headers = await _getHeaders();
    final res = await http.post(
      Uri.parse('$baseUrl/routes/compute/'),
      headers: headers,
      body: jsonEncode({
        'origin_node_id': originId,
        'destination_node_id': destinationId,
        'route_types': ['SAFEST', 'FASTEST', 'CHEAPEST', 'MULTIMODAL'],
      }),
    );

    if (res.statusCode == 200) {
      final List data = jsonDecode(res.body);
      return data.map((r) => RouteOption.fromJson(r)).toList();
    } else {
      throw Exception('Failed to compute route options');
    }
  }

  Future<List<Trip>> getTrips() async {
    final headers = await _getHeaders();
    final res = await http.get(Uri.parse('$baseUrl/trips/'), headers: headers);
    if (res.statusCode == 200) {
      final body = jsonDecode(res.body);
      final results = body['results'] as List;
      return results.map((t) => Trip.fromJson(t)).toList();
    }
    return [];
  }

  Future<void> updateTripStatus(String tripId, String status) async {
    final headers = await _getHeaders();
    await http.post(
      Uri.parse('$baseUrl/trips/$tripId/status/'),
      headers: headers,
      body: jsonEncode({'status': status}),
    );
  }

  Future<List<Map<String, dynamic>>> getRerouteEvents(String tripId) async {
    final headers = await _getHeaders();
    final res = await http.get(Uri.parse('$baseUrl/trips/$tripId/reroute-events/'), headers: headers);
    if (res.statusCode == 200) {
      final body = jsonDecode(res.body);
      final List results = body is Map ? (body['results'] ?? []) : body;
      return results.cast<Map<String, dynamic>>();
    }
    return [];
  }

  Future<Map<String, dynamic>> acknowledgeReroute({
    required String tripId,
    required String eventId,
    required String action,
    String notes = '',
  }) async {
    final headers = await _getHeaders();
    final res = await http.post(
      Uri.parse('$baseUrl/trips/$tripId/reroute-events/$eventId/acknowledge/'),
      headers: headers,
      body: jsonEncode({'action': action, 'notes': notes}),
    );
    if (res.statusCode == 200) {
      return jsonDecode(res.body);
    } else {
      final err = jsonDecode(res.body);
      throw Exception(err['detail'] ?? 'Failed to acknowledge reroute');
    }
  }

  Future<Map<String, dynamic>?> getRouteRisk(String tripId) async {
    final headers = await _getHeaders();
    final res = await http.get(Uri.parse('$baseUrl/trips/$tripId/route-risk/'), headers: headers);
    if (res.statusCode == 200) {
      return jsonDecode(res.body);
    }
    return null;
  }

  // ── Phase 5: Offline Sync & Graph APIs ─────────────────────────────────────

  Future<Map<String, dynamic>?> getOfflineGraphVersion({String region = 'NER_CORRIDOR'}) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/sync/graph/version/?region=$region'));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> downloadOfflineGraphBundle({String region = 'NER_CORRIDOR'}) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/sync/graph/download/?region=$region'));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> sendSyncBatch(List<Map<String, dynamic>> events) async {
    try {
      final headers = await _getHeaders();
      final res = await http.post(
        Uri.parse('$baseUrl/sync/events/batch/'),
        headers: headers,
        body: jsonEncode({'events': events}),
      );
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> getSyncDiagnostics() async {
    try {
      final headers = await _getHeaders();
      final res = await http.get(Uri.parse('$baseUrl/sync/status/'), headers: headers);
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>?> sendEmergencySOS({
    double? lat,
    double? lon,
    String? tripId,
    String? message,
  }) async {
    try {
      final headers = await _getHeaders();
      final res = await http.post(
        Uri.parse('$baseUrl/sync/sos/'),
        headers: headers,
        body: jsonEncode({
          if (lat != null) 'latitude': lat,
          if (lon != null) 'longitude': lon,
          if (tripId != null) 'trip': tripId,
          if (message != null) 'message': message,
        }),
      );
      if (res.statusCode == 201 || res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (_) {}
    return null;
  }
}

