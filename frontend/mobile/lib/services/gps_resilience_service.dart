import 'dart:math';
import 'package:latlong2/latlong.dart';

enum GpsSignalQuality {
  excellent,
  good,
  poor,
  deadReckoning,
  noSignal,
}

class GpsStateEstimate {
  final LatLng position;
  final double speedMps;
  final double headingDeg;
  final double accuracyM;
  final GpsSignalQuality quality;
  final DateTime timestamp;
  final bool isDeadReckoning;

  GpsStateEstimate({
    required this.position,
    required this.speedMps,
    required this.headingDeg,
    required this.accuracyM,
    required this.quality,
    required this.timestamp,
    this.isDeadReckoning = false,
  });
}

/// Extended Kalman Filter & Dead Reckoning filter for robust driver telemetry in NER mountain canyons.
class GpsResilienceService {
  // State vector: [lat, lon, v_lat_deg_s, v_lon_deg_s]
  double _lat = 0.0;
  double _lon = 0.0;
  double _vLat = 0.0;
  double _vLon = 0.0;

  // Covariance matrix diagonal approximations
  double _pPos = 100.0;
  double _pVel = 10.0;

  // Noise parameters
  static const double _qPos = 0.000001; // Process noise for position
  static const double _qVel = 0.00001;  // Process noise for velocity

  DateTime? _lastUpdateTime;
  double _lastSpeedMps = 0.0;
  double _lastHeadingDeg = 0.0;
  bool _initialized = false;

  static const double _metresPerDegreeLat = 111132.0;

  GpsStateEstimate? _latestEstimate;
  GpsStateEstimate? get latestEstimate => _latestEstimate;

  /// Updates filter state with a raw GPS measurement from Geolocator.
  GpsStateEstimate processMeasurement({
    required double rawLat,
    required double rawLon,
    required double rawAccuracyM,
    required double rawSpeedMps,
    required double rawHeadingDeg,
    DateTime? timestamp,
  }) {
    final now = timestamp ?? DateTime.now();

    if (!_initialized) {
      _lat = rawLat;
      _lon = rawLon;
      _vLat = 0.0;
      _vLon = 0.0;
      _lastSpeedMps = max(0.0, rawSpeedMps);
      _lastHeadingDeg = rawHeadingDeg;
      _lastUpdateTime = now;
      _initialized = true;

      _latestEstimate = GpsStateEstimate(
        position: LatLng(_lat, _lon),
        speedMps: _lastSpeedMps,
        headingDeg: _lastHeadingDeg,
        accuracyM: rawAccuracyM,
        quality: _classifyQuality(rawAccuracyM, false),
        timestamp: now,
        isDeadReckoning: false,
      );
      return _latestEstimate!;
    }

    final dt = max(0.05, now.difference(_lastUpdateTime!).inMilliseconds / 1000.0);
    _lastUpdateTime = now;

    // 1. Prediction Step (Kinematic Extrapolation)
    _lat += _vLat * dt;
    _lon += _vLon * dt;
    _pPos += _pVel * dt * dt + _qPos;
    _pVel += _qVel;

    // 2. Outlier / Gross Jump Rejection
    // Compute distance from predicted position to raw measurement
    final jumpDistM = OfflineRoutingService.haversineM(_lat, _lon, rawLat, rawLon);
    final isGrossJump = jumpDistM > max(150.0, rawAccuracyM * 4.0);

    if (!isGrossJump && rawAccuracyM < 80.0) {
      // 3. Measurement Update Step (Kalman Gain)
      // Measurement noise R scales with reported accuracy in metres converted to deg
      final rDeg = (rawAccuracyM / _metresPerDegreeLat);
      final rVariance = rDeg * rDeg;

      final kPos = _pPos / (_pPos + rVariance);
      _lat += kPos * (rawLat - _lat);
      _lon += kPos * (rawLon - _lon);
      _pPos = (1.0 - kPos) * _pPos;

      // Update velocity estimate from smoothed displacement
      if (dt > 0.1) {
        final measuredVLat = (rawLat - _lat) / dt;
        final measuredVLon = (rawLon - _lon) / dt;
        final kVel = _pVel / (_pVel + (rVariance / dt));
        _vLat += kVel * (measuredVLat - _vLat);
        _vLon += kVel * (measuredVLon - _vLon);
        _pVel = (1.0 - kVel) * _pVel;
      }

      if (rawSpeedMps >= 0) _lastSpeedMps = rawSpeedMps;
      if (rawHeadingDeg >= 0) _lastHeadingDeg = rawHeadingDeg;
    }

    _latestEstimate = GpsStateEstimate(
      position: LatLng(_lat, _lon),
      speedMps: _lastSpeedMps,
      headingDeg: _lastHeadingDeg,
      accuracyM: rawAccuracyM,
      quality: _classifyQuality(rawAccuracyM, false),
      timestamp: now,
      isDeadReckoning: false,
    );

    return _latestEstimate!;
  }

  /// Extrapolates position during tunnel or canyon GPS blackout (Dead Reckoning).
  GpsStateEstimate predictDeadReckoning({DateTime? currentTime}) {
    final now = currentTime ?? DateTime.now();
    if (!_initialized || _lastUpdateTime == null) {
      return GpsStateEstimate(
        position: const LatLng(26.1445, 91.7362), // Guwahati fallback
        speedMps: 0.0,
        headingDeg: 0.0,
        accuracyM: 100.0,
        quality: GpsSignalQuality.noSignal,
        timestamp: now,
        isDeadReckoning: true,
      );
    }

    final dt = max(0.1, min(60.0, now.difference(_lastUpdateTime!).inMilliseconds / 1000.0));
    _lastUpdateTime = now;

    // Extrapolate based on velocity and heading
    final speedMps = _lastSpeedMps;
    final headingRad = _lastHeadingDeg * pi / 180.0;

    final distanceM = speedMps * dt;
    final deltaLat = (distanceM * cos(headingRad)) / _metresPerDegreeLat;
    final metresPerLon = _metresPerDegreeLat * max(0.1, cos(_lat * pi / 180.0));
    final deltaLon = (distanceM * sin(headingRad)) / metresPerLon;

    _lat += deltaLat;
    _lon += deltaLon;

    // Uncertainty grows during dead reckoning
    _pPos += distanceM * 0.1;

    _latestEstimate = GpsStateEstimate(
      position: LatLng(_lat, _lon),
      speedMps: speedMps,
      headingDeg: _lastHeadingDeg,
      accuracyM: min(200.0, 25.0 + (_pPos * 0.5)),
      quality: GpsSignalQuality.deadReckoning,
      timestamp: now,
      isDeadReckoning: true,
    );

    return _latestEstimate!;
  }

  GpsSignalQuality _classifyQuality(double accuracyM, bool isDeadReckoning) {
    if (isDeadReckoning) return GpsSignalQuality.deadReckoning;
    if (accuracyM <= 10.0) return GpsSignalQuality.excellent;
    if (accuracyM <= 25.0) return GpsSignalQuality.good;
    if (accuracyM <= 60.0) return GpsSignalQuality.poor;
    return GpsSignalQuality.noSignal;
  }
}
