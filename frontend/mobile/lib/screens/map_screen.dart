import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../models/route_option.dart';
import '../theme/app_theme.dart';

class MapScreen extends StatelessWidget {
  final RouteOption? selectedRoute;

  const MapScreen({super.key, this.selectedRoute});

  @override
  Widget build(BuildContext context) {
    // Default center around Guwahati-Shillong-Silchar
    final center = selectedRoute != null && selectedRoute!.coordinates.isNotEmpty
        ? selectedRoute!.coordinates.first
        : const LatLng(25.75, 92.15);

    final polylinePoints = selectedRoute?.coordinates ?? [
      const LatLng(26.115, 91.585),
      const LatLng(25.903, 91.879),
      const LatLng(25.5788, 91.883),
      const LatLng(24.8333, 92.7925),
    ];

    return Scaffold(
      backgroundColor: AppTheme.bgPrimary,
      appBar: AppBar(
        title: Text(selectedRoute != null ? "Route Navigation" : "Corridor Map"),
      ),
      body: Stack(
        children: [
          FlutterMap(
            options: MapOptions(
              initialCenter: center,
              initialZoom: 8.0,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'in.gov.mdoner.sih26002',
              ),
              PolylineLayer(
                polylines: [
                  Polyline(
                    points: polylinePoints,
                    strokeWidth: 5.0,
                    color: AppTheme.accentCyan,
                  ),
                ],
              ),
              MarkerLayer(
                markers: [
                  Marker(
                    point: polylinePoints.first,
                    width: 32,
                    height: 32,
                    child: const Icon(Icons.circle, color: AppTheme.accentCyan, size: 20),
                  ),
                  Marker(
                    point: polylinePoints.last,
                    width: 32,
                    height: 32,
                    child: const Icon(Icons.location_on, color: AppTheme.accentEmerald, size: 28),
                  ),
                ],
              ),
            ],
          ),

          // GPS Resilience & Accuracy Telemetry Badge
          Positioned(
            top: 16,
            left: 16,
            right: 16,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xDD0F172A),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0x3010B981)),
                boxShadow: const [
                  BoxShadow(color: Color(0x40000000), blurRadius: 8, offset: Offset(0, 2)),
                ],
              ),
              child: const Row(
                children: [
                  Icon(Icons.gps_fixed, color: AppTheme.accentEmerald, size: 16),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      "EKF Position Filtered • Mountain Canyon Resilient (±6m)",
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                    ),
                  ),
                  Text(
                    "LOCK",
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: AppTheme.accentEmerald),
                  ),
                ],
              ),
            ),
          ),

          // Route Details Floating Card
          if (selectedRoute != null)
            Positioned(
              bottom: 24,
              left: 16,
              right: 16,
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.bgSecondary.withOpacity(0.95),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0x30FFFFFF)),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x60000000),
                      blurRadius: 16,
                      offset: Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          selectedRoute!.routeTypeDisplay,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            color: AppTheme.accentCyan,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          "${(selectedRoute!.totalDistanceM / 1000).toStringAsFixed(1)} km • ${(selectedRoute!.totalTimeMin / 60).floor()}h ${(selectedRoute!.totalTimeMin % 60).round()}m",
                          style: const TextStyle(fontSize: 12, color: AppTheme.textSecondary),
                        ),
                      ],
                    ),
                    ElevatedButton(
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text("GPS Telemetry streaming to central MDoNER dispatch."),
                            backgroundColor: AppTheme.accentEmerald,
                          ),
                        );
                      },
                      child: const Text("Start Guidance"),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
