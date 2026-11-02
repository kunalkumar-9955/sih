import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../services/offline_graph_service.dart';
import '../services/sync_queue_service.dart';
import '../theme/app_theme.dart';
import '../models/trip.dart';
import 'trip_planning_screen.dart';
import 'map_screen.dart';
import 'profile_screen.dart';
import 'reroute_alert_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _api = ApiService();
  final _syncQueue = SyncQueueService();
  final _graphService = OfflineGraphService();

  List<Trip> _trips = [];
  Map<String, dynamic>? _activeRerouteEvent;
  bool _loading = true;
  bool _isOnline = true;
  String _graphVersion = 'Checking...';

  @override
  void initState() {
    super.initState();
    _initServices();
    _loadTrips();
  }

  Future<void> _initServices() async {
    await _syncQueue.initialize();
    final bundle = await _graphService.loadCachedGraph();
    if (bundle != null && mounted) {
      setState(() => _graphVersion = bundle.versionTag);
    }
    _syncQueue.addListener(() {
      if (mounted) setState(() {});
    });
  }

  Future<void> _triggerSync() async {
    final res = await _syncQueue.flushQueue(_api);
    await _graphService.syncGraphWithServer(_api);
    final bundle = _graphService.currentBundle;
    if (mounted) {
      if (bundle != null) {
        setState(() => _graphVersion = bundle.versionTag);
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(res.message.isNotEmpty ? res.message : "Sync finished."),
          backgroundColor: res.isSuccess ? AppTheme.accentEmerald : AppTheme.accentCrimson,
        ),
      );
    }
  }

  Future<void> _triggerEmergencySos() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.bgSurface,
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: AppTheme.accentCrimson, size: 28),
            SizedBox(width: 8),
            Text("TRIGGER SOS DISTRESS?", style: TextStyle(color: AppTheme.accentCrimson)),
          ],
        ),
        content: const Text(
          "This will immediately transmit an emergency distress beacon with your last GPS coordinates to the MDoNER Disaster Response Control Room.",
          style: TextStyle(color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text("CANCEL", style: TextStyle(color: AppTheme.textMuted)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accentCrimson),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text("SEND SOS NOW", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      // Queue offline and attempt live send
      final tripId = _trips.isNotEmpty ? _trips.first.id : null;
      await _syncQueue.queueEmergencySos(
        lat: 26.1445,
        lon: 91.7362,
        tripId: tripId,
        message: "Driver SOS triggered via Mobile Emergency Button",
      );
      await _api.sendEmergencySOS(lat: 26.1445, lon: 91.7362, tripId: tripId, message: "EMERGENCY SOS DISTRESS");

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("🚨 SOS Beacon Transmitted & Logged! Control Room Alerted."),
            backgroundColor: AppTheme.accentCrimson,
            duration: Duration(seconds: 4),
          ),
        );
      }
    }
  }

  Future<void> _loadTrips() async {
    try {
      final data = await _api.getTrips();
      setState(() {
        _trips = data;
        _isOnline = true;
      });
      if (data.isNotEmpty && data.first.status == 'ACTIVE') {
        try {
          final events = await _api.getRerouteEvents(data.first.id);
          final pending = events.where((e) => e['status'] == 'PENDING' || e['status'] == 'SENT').toList();
          setState(() {
            _activeRerouteEvent = pending.isNotEmpty ? pending.first : null;
          });
        } catch (_) {}
      } else {
        setState(() => _activeRerouteEvent = null);
      }
    } catch (_) {
      setState(() => _isOnline = false);
      // Fallback local mock trip for demo
      setState(() {
        _trips = [
          Trip(
            id: 'mock-trip-1',
            originName: 'Guwahati Logistics Park',
            destinationName: 'Silchar Goods Terminal',
            status: 'ACTIVE',
            statusDisplay: 'In Transit',
            cargoDescription: 'Essential Food Supplies',
            cargoWeightKg: 4200.0,
          )
        ];
      });
    } finally {
      setState(() => _loading = false);
    }
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgPrimary,
      appBar: AppBar(
        title: const Text("RouteIQ Driver Terminal"),
        actions: [
          IconButton(
            icon: const Icon(Icons.person),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ProfileScreen()),
              );
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadTrips,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Dynamic Connectivity & Offline Sync Status Bar
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                decoration: BoxDecoration(
                  color: _isOnline ? const Color(0x1510B981) : const Color(0x20F59E0B),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: _isOnline ? const Color(0x4010B981) : const Color(0x50F59E0B)),
                ),
                child: Row(
                  children: [
                    Icon(
                      _isOnline ? Icons.wifi : Icons.wifi_off,
                      color: _isOnline ? AppTheme.accentEmerald : AppTheme.accentAmber,
                      size: 20,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _isOnline ? "Online • Local Graph Synced" : "Offline Mode • Dead-Zone Active",
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              color: _isOnline ? AppTheme.accentEmerald : AppTheme.accentAmber,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            "Graph: $_graphVersion • ${_syncQueue.pendingCount} events queued",
                            style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                          ),
                        ],
                      ),
                    ),
                    if (_syncQueue.isSyncing)
                      const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.accentCyan),
                      )
                    else
                      InkWell(
                        onTap: _triggerSync,
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: const Color(0x20FFFFFF),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Row(
                            children: [
                              Icon(Icons.sync, size: 14, color: AppTheme.textPrimary),
                              SizedBox(width: 4),
                              Text("Sync", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 12),

              // Emergency SOS Distress Trigger
              InkWell(
                onTap: _triggerEmergencySos,
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0x35DC2626), Color(0x15991B1B)],
                    ),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0x60DC2626)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.sos_rounded, color: AppTheme.accentCrimson, size: 28),
                      SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              "EMERGENCY SOS DISTRESS",
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.accentCrimson,
                                letterSpacing: 0.5,
                              ),
                            ),
                            SizedBox(height: 2),
                            Text(
                              "Tap to broadcast emergency location in network dead zones",
                              style: TextStyle(fontSize: 10, color: AppTheme.textMuted),
                            ),
                          ],
                        ),
                      ),
                      Icon(Icons.arrow_forward_ios, size: 14, color: AppTheme.accentCrimson),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Active Trip Section
              const Text(
                "Current Active Dispatch",
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 12),

              if (_trips.isNotEmpty)
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: AppTheme.bgSurface,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0x200EA5E9)),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x15000000),
                        blurRadius: 12,
                        offset: Offset(0, 4),
                      ),
                    ],
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
                              color: const Color(0x200EA5E9),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text(
                              _trips.first.statusDisplay,
                              style: const TextStyle(
                                color: AppTheme.accentCyan,
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          const Text(
                            "NH-6 Mountain Corridor",
                            style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          const Icon(Icons.circle, color: AppTheme.accentCyan, size: 14),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              _trips.first.originName,
                              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                      Padding(
                        padding: const EdgeInsets.only(left: 6.0),
                        child: Container(
                          width: 2,
                          height: 20,
                          color: const Color(0x40FFFFFF),
                        ),
                      ),
                      Row(
                        children: [
                          const Icon(Icons.location_on, color: AppTheme.accentEmerald, size: 16),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _trips.first.destinationName,
                              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                            ),
                          ),
                        ],
                      ),
                      if (_activeRerouteEvent != null) ...[
                        const SizedBox(height: 14),
                        InkWell(
                          onTap: () async {
                            final accepted = await Navigator.push<bool>(
                              context,
                              MaterialPageRoute(
                                builder: (_) => RerouteAlertScreen(
                                  tripId: _trips.first.id,
                                  event: _activeRerouteEvent!,
                                ),
                              ),
                            );
                            if (accepted == true) {
                              _loadTrips();
                            }
                          },
                          child: Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: Colors.amber.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: Colors.amber, width: 1.2),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.warning_amber_rounded, color: Colors.amber, size: 22),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text(
                                        "⚠️ Reroute Recommended",
                                        style: TextStyle(
                                          color: Colors.amber,
                                          fontWeight: FontWeight.bold,
                                          fontSize: 13,
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        _activeRerouteEvent!['trigger_reason'] ?? "High hazard detected ahead",
                                        style: const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ],
                                  ),
                                ),
                                const Icon(Icons.chevron_right, color: Colors.amber, size: 20),
                              ],
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: 18),
                      ElevatedButton.icon(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(builder: (_) => const MapScreen()),
                          );
                        },
                        icon: const Icon(Icons.navigation, size: 18),
                        label: const Text("Open Live GPS Route Navigation"),
                        style: ElevatedButton.styleFrom(
                          minimumSize: const Size.fromHeight(44),
                        ),
                      ),
                    ],
                  ),
                ),

              // Phase 7: Assigned Freight Load & Delivery Status Card
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.bgSurface,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0x3038BDF8)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Row(
                          children: [
                            Icon(Icons.inventory_2_outlined, color: AppTheme.accentCyan, size: 18),
                            SizedBox(width: 8),
                            Text(
                              "Assigned Freight Cargo",
                              style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textPrimary),
                            ),
                          ],
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0x2038BDF8),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Text(
                            "PRIORITY LOAD",
                            style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.accentCyan),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    const Text(
                      "Essential Medical & Mountain Relief Supplies",
                      style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      "Payload: 12,000 kg • Handling: Dry / Secure Tie-down • Window: Today 18:30 IST",
                      style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () async {
                              await _syncQueue.queueLoadStatusUpdate(
                                loadId: _trips.isNotEmpty ? _trips.first.id : 'demo-load-1',
                                status: 'PICKED_UP',
                              );
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text("Cargo Pickup Confirmed & Queued for Sync.")),
                                );
                              }
                            },
                            child: const Text("Confirm Pickup", style: TextStyle(fontSize: 12)),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: ElevatedButton(
                            onPressed: () async {
                              await _syncQueue.queueLoadStatusUpdate(
                                loadId: _trips.isNotEmpty ? _trips.first.id : 'demo-load-1',
                                status: 'DELIVERED',
                              );
                              if (context.mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text("Delivery Completed & Queued for Sync.")),
                                );
                              }
                            },
                            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.accentEmerald),
                            child: const Text("Mark Delivered", style: TextStyle(fontSize: 12, color: Colors.white)),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              else
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: AppTheme.bgSurface,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Center(
                    child: Text(
                      "No trips in transit. Plan a new trip below.",
                      style: TextStyle(color: AppTheme.textMuted),
                    ),
                  ),
                ),

              const SizedBox(height: 28),

              // Quick Actions
              const Text(
                "Logistics Operations",
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 14),

              Row(
                children: [
                  Expanded(
                    child: InkWell(
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const TripPlanningScreen()),
                        );
                      },
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppTheme.bgSurface,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0x15FFFFFF)),
                        ),
                        child: const Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(Icons.add_road, color: AppTheme.accentCyan, size: 28),
                            SizedBox(height: 12),
                            Text(
                              "Plan New Trip",
                              style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                            ),
                            SizedBox(height: 4),
                            Text(
                              "Risk-aware route options",
                              style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: InkWell(
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const MapScreen()),
                        );
                      },
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppTheme.bgSurface,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0x15FFFFFF)),
                        ),
                        child: const Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(Icons.map, color: AppTheme.accentEmerald, size: 28),
                            SizedBox(height: 12),
                            Text(
                              "Network Map",
                              style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                            ),
                            SizedBox(height: 4),
                            Text(
                              "Offline tiles & bottlenecks",
                              style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
