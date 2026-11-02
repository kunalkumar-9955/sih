import 'package:flutter/material.dart';
import '../models/route_option.dart';
import '../models/transport_node.dart';
import '../services/api_service.dart';
import '../services/offline_graph_service.dart';
import '../services/offline_routing_service.dart';
import '../theme/app_theme.dart';
import 'route_options_screen.dart';

class TripPlanningScreen extends StatefulWidget {
  const TripPlanningScreen({super.key});

  @override
  State<TripPlanningScreen> createState() => _TripPlanningScreenState();
}

class _TripPlanningScreenState extends State<TripPlanningScreen> {
  final _api = ApiService();
  final _graphService = OfflineGraphService();
  List<TransportNode> _nodes = [];
  TransportNode? _origin;
  TransportNode? _destination;
  bool _loading = true;
  bool _computing = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadNodes();
  }

  Future<void> _loadNodes() async {
    try {
      final nodes = await _api.getNodes();
      setState(() {
        _nodes = nodes;
        if (nodes.length >= 2) {
          _origin = nodes.first;
          _destination = nodes.last;
        }
      });
    } catch (e) {
      // Check cached graph bundle first
      final bundle = await _graphService.loadCachedGraph();
      if (bundle != null && bundle.nodes.isNotEmpty) {
        final cachedNodes = _graphService.getCachedTransportNodes();
        setState(() {
          _nodes = cachedNodes;
          _origin = cachedNodes.first;
          _destination = cachedNodes.last;
        });
      } else {
        // Fallback local nodes for offline simulation
        final mockNodes = [
          TransportNode(
            id: '1',
            name: 'Guwahati Multimodal Logistics Park',
            nodeType: 'MULTIMODAL_HUB',
            nodeTypeDisplay: 'Multimodal Logistics Park',
            longitude: 91.585,
            latitude: 26.115,
            state: 'Assam',
            district: 'Kamrup Metro',
          ),
          TransportNode(
            id: '2',
            name: 'Shillong Central Hub',
            nodeType: 'LOCAL_HUB',
            nodeTypeDisplay: 'Local Hub',
            longitude: 91.883,
            latitude: 25.5788,
            state: 'Meghalaya',
            district: 'East Khasi Hills',
          ),
          TransportNode(
            id: '3',
            name: 'Silchar Goods Yard',
            nodeType: 'MULTIMODAL_HUB',
            nodeTypeDisplay: 'Multimodal Hub',
            longitude: 92.7925,
            latitude: 24.8333,
            state: 'Assam',
            district: 'Cachar',
          ),
        ];
        setState(() {
          _nodes = mockNodes;
          _origin = mockNodes[0];
          _destination = mockNodes[2];
        });
      }
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _handleCompute() async {
    if (_origin == null || _destination == null) return;
    if (_origin!.id == _destination!.id) {
      setState(() => _error = "Origin and destination cannot be the same.");
      return;
    }

    setState(() {
      _computing = true;
      _error = null;
    });

    try {
      final routes = await _api.computeRoutes(_origin!.id, _destination!.id);
      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => RouteOptionsScreen(
              origin: _origin!,
              destination: _destination!,
              routes: routes,
            ),
          ),
        );
      }
    } catch (e) {
      // Offline fallback: Use local offline graph bundle and A* pathfinder!
      final bundle = await _graphService.loadCachedGraph();
      if (bundle != null && bundle.nodes.isNotEmpty) {
        final offlineRouter = OfflineRoutingService(bundle);
        final origInt = int.tryParse(_origin!.id) ?? 1;
        final destInt = int.tryParse(_destination!.id) ?? (bundle.nodes.last.id);

        final safestRoute = offlineRouter.findRoute(originId: origInt, destinationId: destInt, policy: 'SAFEST');
        final fastestRoute = offlineRouter.findRoute(originId: origInt, destinationId: destInt, policy: 'FASTEST');
        final multimodalRoute = offlineRouter.findRoute(originId: origInt, destinationId: destInt, policy: 'MULTIMODAL');

        final offlineRoutes = [safestRoute, fastestRoute, multimodalRoute].whereType<RouteOption>().toList();
        if (offlineRoutes.isNotEmpty && mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text("Offline Mode: Route computed on-device using local A* search!"),
              backgroundColor: AppTheme.accentEmerald,
              duration: Duration(seconds: 3),
            ),
          );
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => RouteOptionsScreen(
                origin: _origin!,
                destination: _destination!,
                routes: offlineRoutes,
              ),
            ),
          );
          return;
        }
      }
      setState(() => _error = "Network offline and no local graph bundle cached. Please connect to download network cache.");
    } finally {
      if (mounted) setState(() => _computing = false);
    }
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.bgPrimary,
      appBar: AppBar(title: const Text("Plan Trip & Route")),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_error != null)
                    Container(
                      padding: const EdgeInsets.all(12),
                      margin: const EdgeInsets.bottom(16),
                      decoration: BoxDecoration(
                        color: const Color(0x20F43F5E),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppTheme.accentRose),
                      ),
                      child: Text(_error!, style: const TextStyle(color: AppTheme.accentRose)),
                    ),

                  const Text(
                    "Select Corridor Origin & Destination",
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),

                  // Origin Picker
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.bgSurface,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0x20FFFFFF)),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<TransportNode>(
                        value: _origin,
                        isExpanded: true,
                        dropdownColor: AppTheme.bgSurface,
                        items: _nodes.map((n) {
                          return DropdownMenuItem(
                            value: n,
                            child: Text(n.name, style: const TextStyle(fontSize: 14)),
                          );
                        }).toList(),
                        onChanged: (val) => setState(() => _origin = val),
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Destination Picker
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.bgSurface,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0x20FFFFFF)),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<TransportNode>(
                        value: _destination,
                        isExpanded: true,
                        dropdownColor: AppTheme.bgSurface,
                        items: _nodes.map((n) {
                          return DropdownMenuItem(
                            value: n,
                            child: Text(n.name, style: const TextStyle(fontSize: 14)),
                          );
                        }).toList(),
                        onChanged: (val) => setState(() => _destination = val),
                      ),
                    ),
                  ),

                  const Spacer(),

                  ElevatedButton.icon(
                    onPressed: _computing ? null : _handleCompute,
                    icon: const Icon(Icons.alt_route),
                    label: Text(_computing ? "Calculating Optimal Routes..." : "Compute Risk-Aware Routes"),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
