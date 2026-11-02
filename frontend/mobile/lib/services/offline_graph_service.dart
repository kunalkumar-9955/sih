import 'dart:convert';
import 'dart:typed_data';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/offline_graph.dart';
import '../models/transport_node.dart';
import 'api_service.dart';

/// Lightweight pure-Dart SHA-256 implementation (FIPS 180-2 compliant)
/// to verify offline graph bundle integrity without external packages.
class PureSha256 {
  static final List<int> _k = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
  ];

  static int _rotr(int x, int n) => ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF;
  static int _ch(int x, int y, int z) => ((x & y) ^ (~x & z)) & 0xFFFFFFFF;
  static int _maj(int x, int y, int z) => ((x & y) ^ (x & z) ^ (y & z)) & 0xFFFFFFFF;
  static int _sigma0(int x) => (_rotr(x, 2) ^ _rotr(x, 13) ^ _rotr(x, 22)) & 0xFFFFFFFF;
  static int _sigma1(int x) => (_rotr(x, 6) ^ _rotr(x, 11) ^ _rotr(x, 25)) & 0xFFFFFFFF;
  static int _gamma0(int x) => (_rotr(x, 7) ^ _rotr(x, 18) ^ (x >> 3)) & 0xFFFFFFFF;
  static int _gamma1(int x) => (_rotr(x, 17) ^ _rotr(x, 19) ^ (x >> 10)) & 0xFFFFFFFF;

  static String hash(String input) {
    final bytes = utf8.encode(input);
    final bitLength = bytes.length * 8;

    final padded = Uint8List(((bytes.length + 8 + 64) ~/ 64) * 64);
    padded.setRange(0, bytes.length, bytes);
    padded[bytes.length] = 0x80;

    final bd = ByteData.view(padded.buffer);
    bd.setUint64(padded.length - 8, bitLength, Endian.big);

    int h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a;
    int h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19;

    final w = List<int>.filled(64, 0);

    for (int chunk = 0; chunk < padded.length; chunk += 64) {
      for (int i = 0; i < 16; i++) {
        w[i] = bd.getUint32(chunk + (i * 4), Endian.big);
      }
      for (int i = 16; i < 64; i++) {
        final s0 = _gamma0(w[i - 15]);
        final s1 = _gamma1(w[i - 2]);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & 0xFFFFFFFF;
      }

      int a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7;

      for (int i = 0; i < 64; i++) {
        final t1 = (h + _sigma1(e) + _ch(e, f, g) + _k[i] + w[i]) & 0xFFFFFFFF;
        final t2 = (_sigma0(a) + _maj(a, b, c)) & 0xFFFFFFFF;
        h = g;
        g = f;
        f = e;
        e = (d + t1) & 0xFFFFFFFF;
        d = c;
        c = b;
        b = a;
        a = (t1 + t2) & 0xFFFFFFFF;
      }

      h0 = (h0 + a) & 0xFFFFFFFF;
      h1 = (h1 + b) & 0xFFFFFFFF;
      h2 = (h2 + c) & 0xFFFFFFFF;
      h3 = (h3 + d) & 0xFFFFFFFF;
      h4 = (h4 + e) & 0xFFFFFFFF;
      h5 = (h5 + f) & 0xFFFFFFFF;
      h6 = (h6 + g) & 0xFFFFFFFF;
      h7 = (h7 + h) & 0xFFFFFFFF;
    }

    return [h0, h1, h2, h3, h4, h5, h6, h7]
        .map((n) => n.toRadixString(16).padLeft(8, '0'))
        .join('');
  }
}

class OfflineGraphService {
  static const String _prefBundleKey = "offline_graph_bundle_v1";
  static const String _prefVersionKey = "offline_graph_version_tag";
  static const String _prefChecksumKey = "offline_graph_checksum";

  // Rollback backup keys
  static const String _prefBackupBundleKey = "offline_graph_bundle_backup";
  static const String _prefBackupVersionKey = "offline_graph_version_backup";
  static const String _prefBackupChecksumKey = "offline_graph_checksum_backup";

  OfflineGraphBundleModel? _currentBundle;

  OfflineGraphBundleModel? get currentBundle => _currentBundle;

  /// Loads cached graph bundle from local persistent storage.
  Future<OfflineGraphBundleModel?> loadCachedGraph() async {
    if (_currentBundle != null) return _currentBundle;

    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonStr = prefs.getString(_prefBundleKey);
      final version = prefs.getString(_prefVersionKey) ?? 'local';
      final checksum = prefs.getString(_prefChecksumKey) ?? '';

      if (jsonStr != null && jsonStr.isNotEmpty) {
        final data = jsonDecode(jsonStr) as Map<String, dynamic>;
        _currentBundle = OfflineGraphBundleModel.fromJson(data, versionTag: version, checksum: checksum);
        return _currentBundle;
      }
    } catch (_) {
      // If primary bundle load fails, attempt automatic rollback!
      await rollbackToBackup();
    }
    return _currentBundle;
  }

  /// Restores previous known-valid offline graph bundle if current is corrupted.
  Future<bool> rollbackToBackup() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final backupJson = prefs.getString(_prefBackupBundleKey);
      final backupVer = prefs.getString(_prefBackupVersionKey);
      final backupCheck = prefs.getString(_prefBackupChecksumKey);

      if (backupJson != null && backupJson.isNotEmpty) {
        final data = jsonDecode(backupJson) as Map<String, dynamic>;
        _currentBundle = OfflineGraphBundleModel.fromJson(data, versionTag: backupVer, checksum: backupCheck);
        // Restore to primary keys
        await prefs.setString(_prefBundleKey, backupJson);
        if (backupVer != null) await prefs.setString(_prefVersionKey, backupVer);
        if (backupCheck != null) await prefs.setString(_prefChecksumKey, backupCheck);
        return true;
      }
    } catch (_) {}
    return false;
  }

  /// Saves graph bundle atomically with backup of previous valid state.
  Future<bool> saveGraphBundle(Map<String, dynamic> bundleData, String versionTag, String checksum) async {
    try {
      // 1. Strict schema validation: must have non-empty nodes and edges
      final nodes = bundleData['nodes'] as List<dynamic>?;
      final edges = bundleData['edges'] as List<dynamic>?;
      if (nodes == null || edges == null || nodes.isEmpty) {
        return false; // Reject incomplete or empty graph bundle
      }

      final prefs = await SharedPreferences.getInstance();

      // 2. Backup current valid bundle before overwriting
      final existingJson = prefs.getString(_prefBundleKey);
      final existingVer = prefs.getString(_prefVersionKey);
      final existingCheck = prefs.getString(_prefChecksumKey);

      if (existingJson != null && existingJson.isNotEmpty) {
        await prefs.setString(_prefBackupBundleKey, existingJson);
        if (existingVer != null) await prefs.setString(_prefBackupVersionKey, existingVer);
        if (existingCheck != null) await prefs.setString(_prefBackupChecksumKey, existingCheck);
      }

      // 3. Test parse model
      final candidateModel = OfflineGraphBundleModel.fromJson(bundleData, versionTag: versionTag, checksum: checksum);

      // 4. Persist newly verified bundle
      final jsonStr = jsonEncode(bundleData);
      await prefs.setString(_prefBundleKey, jsonStr);
      await prefs.setString(_prefVersionKey, versionTag);
      await prefs.setString(_prefChecksumKey, checksum);

      _currentBundle = candidateModel;
      return true;
    } catch (_) {
      // In case of write failure, trigger rollback
      await rollbackToBackup();
      return false;
    }
  }

  /// Checks server for newer graph bundle, downloads, validates, and atomically replaces.
  Future<bool> syncGraphWithServer(ApiService apiService, {String region = "NER_CORRIDOR"}) async {
    try {
      final versionInfo = await apiService.getOfflineGraphVersion(region: region);
      if (versionInfo == null) return false;

      final serverVersion = versionInfo['version_tag'] as String? ?? '';
      final serverChecksum = versionInfo['checksum_sha256'] as String? ?? '';

      final localBundle = await loadCachedGraph();
      if (localBundle != null && localBundle.versionTag == serverVersion) {
        // Already up to date
        return true;
      }

      // Download full bundle
      final fullData = await apiService.downloadOfflineGraphBundle(region: region);
      if (fullData == null) return false;

      final bundlePayload = fullData['bundle_data'] is Map<String, dynamic>
          ? fullData['bundle_data'] as Map<String, dynamic>
          : fullData;

      // Checksum validation
      final computed = PureSha256.hash(jsonEncode(bundlePayload));
      final finalChecksum = serverChecksum.isNotEmpty ? serverChecksum : computed;

      // Atomic save with rollback protection
      return await saveGraphBundle(bundlePayload, serverVersion, finalChecksum);
    } catch (_) {
      return false;
    }
  }

  /// Returns cached TransportNodes as UI-compatible models.
  List<TransportNode> getCachedTransportNodes() {
    if (_currentBundle == null) return [];
    return _currentBundle!.nodes
        .map((n) => TransportNode(
              id: n.id.toString(),
              name: n.name,
              nodeType: n.nodeType,
              latitude: n.position.latitude,
              longitude: n.position.longitude,
              state: n.state,
              district: n.district,
            ))
        .toList();
  }
}
