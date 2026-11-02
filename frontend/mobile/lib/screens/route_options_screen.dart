import 'package:flutter/material.dart';
import '../models/route_option.dart';
import '../models/transport_node.dart';
import '../theme/app_theme.dart';
import 'map_screen.dart';

class RouteOptionsScreen extends StatelessWidget {
  final TransportNode origin;
  final TransportNode destination;
  final List<RouteOption> routes;

  const RouteOptionsScreen({
    super.key,
    required this.origin,
    required this.destination,
    required this.routes,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgPrimary,
      appBar: AppBar(
        title: const Text("Route Alternatives"),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header summary
            Text(
              "${origin.name} → ${destination.name}",
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              "Found ${routes.length} risk-evaluated corridor options",
              style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
            ),
            const SizedBox(height: 20),

            Expanded(
              child: ListView.separated(
                itemCount: routes.length,
                separatorBuilder: (_, __) => const SizedBox(height: 14),
                itemBuilder: (context, index) {
                  final r = routes[index];
                  Color typeColor = AppTheme.accentCyan;
                  if (r.routeType == 'SAFEST') typeColor = AppTheme.accentEmerald;
                  if (r.routeType == 'CHEAPEST') typeColor = AppTheme.accentAmber;
                  if (r.routeType == 'MULTIMODAL') typeColor = AppTheme.accentPurple;

                  return Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppTheme.bgSurface,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: typeColor.withOpacity(0.4)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: typeColor.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(20),
                              ),
                              child: Text(
                                r.routeTypeDisplay,
                                style: TextStyle(
                                  color: typeColor,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                            Text(
                              "Risk Score: ${r.hazardPenaltyScore.toStringAsFixed(2)}",
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                                color: r.hazardPenaltyScore > 0.4 ? AppTheme.accentRose : AppTheme.accentEmerald,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        // Modes and Transfer Chips
                        Wrap(
                          spacing: 6,
                          runSpacing: 4,
                          children: [
                            for (var mode in r.modesUsed)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: AppTheme.bgPrimary,
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: AppTheme.borderSubtle),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      mode == 'ROAD'
                                          ? Icons.local_shipping
                                          : mode == 'RAIL'
                                              ? Icons.train
                                              : mode == 'WATER' || mode == 'WATERWAY'
                                                  ? Icons.directions_boat
                                                  : Icons.swap_horiz,
                                      size: 12,
                                      color: AppTheme.textMuted,
                                    ),
                                    const SizedBox(width: 4),
                                    Text(
                                      mode,
                                      style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                                    ),
                                  ],
                                ),
                              ),
                            if (r.transferCount > 0)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: AppTheme.accentPurple.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(color: AppTheme.accentPurple.withOpacity(0.3)),
                                ),
                                child: Text(
                                  "${r.transferCount} Transfer${r.transferCount > 1 ? 's' : ''}",
                                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.accentPurple),
                                ),
                              ),
                          ],
                        ),
                        if (r.explanation.isNotEmpty) ...[
                          const SizedBox(height: 10),
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: AppTheme.bgPrimary.withOpacity(0.6),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: AppTheme.borderSubtle.withOpacity(0.5)),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Icon(Icons.psychology_outlined, size: 16, color: AppTheme.accentCyan),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    r.explanation,
                                    style: const TextStyle(fontSize: 11, color: AppTheme.textMuted, height: 1.3),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                        const SizedBox(height: 16),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [
                            Column(
                              children: [
                                const Text("Distance", style: TextStyle(fontSize: 11, color: AppTheme.textMuted)),
                                const SizedBox(height: 2),
                                Text(
                                  "${(r.totalDistanceM / 1000).toStringAsFixed(1)} km",
                                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                                ),
                              ],
                            ),
                            Column(
                              children: [
                                const Text("Transit Time", style: TextStyle(fontSize: 11, color: AppTheme.textMuted)),
                                const SizedBox(height: 2),
                                Text(
                                  "${(r.totalTimeMin / 60).floor()}h ${(r.totalTimeMin % 60).round()}m",
                                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                                ),
                              ],
                            ),
                            Column(
                              children: [
                                const Text("Freight Est.", style: TextStyle(fontSize: 11, color: AppTheme.textMuted)),
                                const SizedBox(height: 2),
                                Text(
                                  "₹${r.totalCostInr.round()}",
                                  style: const TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.accentEmerald,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => MapScreen(selectedRoute: r),
                              ),
                            );
                          },
                          icon: const Icon(Icons.map, size: 16),
                          label: const Text("View Route on Map"),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: typeColor,
                            minimumSize: const Size.fromHeight(40),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
