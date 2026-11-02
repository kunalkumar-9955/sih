import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class RerouteAlertScreen extends StatefulWidget {
  final String tripId;
  final Map<String, dynamic> event;

  const RerouteAlertScreen({
    super.key,
    required this.tripId,
    required this.event,
  });

  @override
  State<RerouteAlertScreen> createState() => _RerouteAlertScreenState();
}

class _RerouteAlertScreenState extends State<RerouteAlertScreen> {
  final ApiService _api = ApiService();
  bool _submitting = false;

  Future<void> _handleAction(String action) async {
    setState(() => _submitting = true);
    try {
      final eventId = widget.event['id'] as String;
      await _api.acknowledgeReroute(
        tripId: widget.tripId,
        eventId: eventId,
        action: action,
      );
      if (mounted) {
        Navigator.pop(context, action == 'ACCEPT');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.toString()}')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final payload = widget.event['notification_payload'] as Map<String, dynamic>? ?? {};
    final metrics = payload['metrics'] as Map<String, dynamic>? ?? {};
    final isMandatory = payload['is_mandatory'] == true;
    final title = payload['title'] as String? ?? '⚠️ Dynamic Reroute Alert';
    final message = payload['message'] as String? ?? widget.event['trigger_reason'] as String? ?? '';
    final improvementPct = (widget.event['improvement_pct'] as num? ?? 0.0) * 100.0;
    final timeDelta = metrics['time_delta_min'] ?? 0;
    final distDelta = metrics['distance_delta_km'] ?? 0;

    return Scaffold(
      backgroundColor: AppTheme.bgPrimary,
      appBar: AppBar(
        title: const Text('Corridor Hazard Warning'),
        automaticallyImplyLeading: !isMandatory,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Urgency Alert Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isMandatory
                      ? Colors.red.withOpacity(0.15)
                      : Colors.amber.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isMandatory ? Colors.redAccent : Colors.amber,
                    width: 1.5,
                  ),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      isMandatory ? Icons.block : Icons.warning_amber_rounded,
                      color: isMandatory ? Colors.redAccent : Colors.amber,
                      size: 28,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            title,
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: isMandatory ? Colors.redAccent : Colors.amber,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            message,
                            style: const TextStyle(fontSize: 13, height: 1.4),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              // Metrics Comparison
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.bgCard,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.borderSubtle),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Safety Improvement:', style: TextStyle(fontSize: 13, color: AppTheme.textMuted)),
                        Text(
                          '+${improvementPct.toStringAsFixed(0)}% Safer',
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            color: Colors.greenAccent,
                          ),
                        ),
                      ],
                    ),
                    const Divider(height: 20),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Time Impact:', style: TextStyle(fontSize: 13, color: AppTheme.textMuted)),
                        Text(
                          '$timeDelta min',
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Distance Impact:', style: TextStyle(fontSize: 13, color: AppTheme.textMuted)),
                        Text(
                          '$distDelta km',
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              const Spacer(),

              // Action Buttons
              if (_submitting)
                const Center(child: CircularProgressIndicator())
              else ...[
                ElevatedButton.icon(
                  onPressed: () => _handleAction('ACCEPT'),
                  icon: const Icon(Icons.navigation_rounded),
                  label: const Text('Accept Safe Bypass Route'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green.shade700,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
                if (!isMandatory) ...[
                  const SizedBox(height: 10),
                  OutlinedButton(
                    onPressed: () => _handleAction('DECLINE'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    child: const Text('Decline & Keep Current Path'),
                  ),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }
}
