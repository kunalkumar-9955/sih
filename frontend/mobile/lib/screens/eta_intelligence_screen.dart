import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class ETAIntelligenceScreen extends StatelessWidget {
  final Map<String, dynamic> etaData;
  final bool isOfflineFallback;

  const ETAIntelligenceScreen({
    super.key,
    required this.etaData,
    this.isOfflineFallback = false,
  });

  @override
  Widget build(BuildContext context) {
    final predictedEta = etaData['predicted_eta'] as String? ?? '16:45 IST';
    final expectedDelayMin = (etaData['expected_delay_min'] as num? ?? 45).toInt();
    final delayProb = ((etaData['delay_probability'] as num? ?? 0.75) * 100).toInt();
    final confidence = ((etaData['confidence_score'] as num? ?? 0.88) * 100).toInt();
    final factors = etaData['contributing_factors'] as Map<String, dynamic>? ?? {
      'weather_rainfall_delay_min': 25,
      'geohazard_risk_delay_min': 15,
      'corridor_incident_delay_min': 0,
      'mountain_terrain_delay_min': 5,
    };
    final routeExplanation = etaData['explanation'] as String? ??
        'Route diverted via Lumding rail-waterway bypass to avoid active NH-6 Sonapur mudslide. 85% lower hazard exposure.';

    return Scaffold(
      backgroundColor: AppTheme.bgPrimary,
      appBar: AppBar(
        title: const Text('Intelligent ETA & Delay Factors'),
        backgroundColor: AppTheme.bgSecondary,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Offline Fallback Banner
            if (isOfflineFallback)
              Container(
                margin: const EdgeInsets.only(bottom: 16),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.amber.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.amber),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.cloud_off, color: Colors.amber, size: 20),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'OFFLINE FALLBACK — ETA calculated using locally cached corridor weights & A* heuristic.',
                        style: TextStyle(color: Colors.amber, fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ),

            // High Contrast ETA Card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppTheme.bgSecondary,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.accentPrimary.withOpacity(0.5)),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.accentPrimary.withOpacity(0.1),
                    blurRadius: 16,
                  ),
                ],
              ),
              child: Column(
                children: [
                  const Text(
                    'PREDICTED ARRIVAL TIME',
                    style: TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.1),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    predictedEta,
                    style: const TextStyle(color: Colors.white, fontSize: 36, fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: expectedDelayMin > 30 ? Colors.red.withOpacity(0.2) : Colors.amber.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: expectedDelayMin > 30 ? Colors.red : Colors.amber),
                        ),
                        child: Text(
                          '+$expectedDelayMin Min Expected Delay',
                          style: TextStyle(
                            color: expectedDelayMin > 30 ? Colors.redAccent : Colors.amber,
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '($delayProb% Delay Probability • $confidence% Confidence)',
                        style: const TextStyle(color: Colors.white60, fontSize: 11),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Contributing Delay Factors Breakdown
            const Text(
              'CONTRIBUTING DELAY FACTORS',
              style: TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            _buildFactorItem(
              icon: Icons.cloudy_snowing,
              title: 'Heavy Monsoon Rainfall & Surface Runoff',
              delayMin: (factors['weather_rainfall_delay_min'] as num? ?? 0).toInt(),
              color: Colors.lightBlueAccent,
            ),
            _buildFactorItem(
              icon: Icons.terrain,
              title: 'Mountain Slope Landslide Caution (NH-6)',
              delayMin: (factors['geohazard_risk_delay_min'] as num? ?? 0).toInt(),
              color: Colors.amberAccent,
            ),
            _buildFactorItem(
              icon: Icons.alt_route,
              title: 'Intermodal Transfer & Yard Siding Delay',
              delayMin: (factors['multimodal_transfer_delay_min'] as num? ?? 0).toInt(),
              color: Colors.purpleAccent,
            ),
            _buildFactorItem(
              icon: Icons.traffic,
              title: 'Ghat Section Crawl & Steep Incline',
              delayMin: (factors['mountain_terrain_delay_min'] as num? ?? 0).toInt(),
              color: Colors.orangeAccent,
            ),
            const SizedBox(height: 20),

            // Explainable Route Choice Box
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.bgSecondary,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.white12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.psychology, color: Colors.cyanAccent, size: 20),
                      SizedBox(width: 8),
                      Text(
                        'WHY THIS ROUTE WAS CHOSEN',
                        style: TextStyle(color: Colors.cyanAccent, fontSize: 12, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    routeExplanation,
                    style: const TextStyle(color: Colors.white, fontSize: 13, height: 1.4),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFactorItem({
    required IconData icon,
    required String title,
    required int delayMin,
    required Color color,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.bgSecondary,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white10),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              title,
              style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500),
            ),
          ),
          Text(
            '+$delayMin m',
            style: TextStyle(color: color, fontSize: 14, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
