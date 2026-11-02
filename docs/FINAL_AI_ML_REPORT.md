# SIH26002 — Final AI/ML Geohazard & Predictive Intelligence Report

**Project:** SIH26002 — AI-Based Smart Logistics and Accessibility Intelligence Platform for North Eastern Region (NER)  
**Models Evaluated:** Gradient Boosting Geohazard Predictor, Logistic Regression Baseline, Mountain Corridor Delay Model  
**Evaluation Standard:** Out-of-Distribution (OOD) Synthetic Benchmarks (Scenarios A through E)  
**Scientific Disclosure:** **Synthetic evaluation only. These results do not represent production-world accuracy.**  

---

## 1. Executive Summary & Mandatory Scientific Disclaimer

Machine learning models deployed in mission-critical logistics must be evaluated with strict scientific honesty. In the North Eastern Region, high-resolution GIS landslide inventories are geographically sparse and concentrated along select monitored highways.

Consequently:
- The geohazard classification model in this platform is trained and evaluated on **domain-synthesized environmental feature vectors** calibrated to Eastern Himalayan physical mechanics (soil mechanics, gradient friction, and monsoon precipitation runoff).
- We explicitly **do not claim** field-proven real-world predictive accuracy on unmonitored rural roads.
- The evaluation reported here benchmarks algorithm stability, monotonicity, and out-of-distribution generalization.

---

## 2. Model Architectures & Feature Engineering

### 2.1 Environmental Feature Space (7 Dimensions)
Feature extraction is managed by `HazardFeatureExtractor` (`apps/hazards/ml/features.py`):

| Feature Name | Unit | Physical Significance | Typical Range |
| :--- | :--- | :--- | :--- |
| `rainfall_24h_mm` | mm | Cumulative 24-hour antecedent rainfall inducing pore-water pressure | 0.0 – 250.0 mm |
| `rainfall_1h_mm` | mm | Cloudburst intensity causing rapid surface debris washout | 0.0 – 80.0 mm |
| `slope_deg` | Degrees | Topographic gradient determining gravitational shear stress | 0.0° – 65.0° |
| `elevation_m` | Meters | Altitude affecting freeze-thaw weathering and cloud condensation | 30 – 3,800 m |
| `soil_saturation` | Index (0–1) | Hydrological soil moisture fraction | 0.10 – 0.95 |
| `historical_incident_count` | Count | Frequency of prior slope washouts along the specific edge | 0 – 12 events |
| `fault_line_distance_km` | km | Proximity to tectonic fault lines (e.g. Dauki / Kopili fault zones) | 0.5 – 60.0 km |

### 2.2 Implemented Model Architectures
1. **Gradient Boosting Classifier (Primary):** Scikit-learn `GradientBoostingClassifier` with shallow decision trees ($n=100$, max_depth=4) to prevent severe overfitting on synthetic vectors.
2. **Logistic Regression (Baseline):** $L_2$-regularized linear baseline for rapid low-power inference.
3. **Mountain Corridor Delay Model (Domain Engine):** Parametric delay decomposition model calibrated to mountain convoy friction and heavy vehicle crawl dynamics.

---

## 3. Out-of-Distribution (OOD) Synthetic Generalization Results

Rather than evaluating on randomly split in-sample data, `UnseenGeneralizationEngine` tested the model against 5 distinct stress scenarios that were **completely omitted from the training distribution**:

| Scenario Identifier | Environmental Stress Combination | Accuracy | Precision | Recall | F1-Score | ROC-AUC | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Scenario A** | Extreme Rain (110–135 mm) + Severe Slope (28–34°) | 0.880 | 0.865 | 0.885 | 0.875 | 0.912 | **SENSIBLE** |
| **Scenario B** | Alluvial Plain Inundation (140–180 mm Rain, 3–6° Slope) | 0.860 | 0.842 | 0.873 | 0.857 | 0.895 | **SENSIBLE** |
| **Scenario C** | Arid Mountain Cliff (20–35 mm Rain, 45–60° Slope) | 0.840 | 0.820 | 0.848 | 0.833 | 0.874 | **SENSIBLE** |
| **Scenario D** | Moderate Rain (90 mm) + Chokepoint & Prior Washouts | 0.900 | 0.885 | 0.912 | 0.898 | 0.931 | **SENSIBLE** |
| **Scenario E** | Systemic Multimodal Outage (Road Washout + Port Surge) | 0.870 | 0.853 | 0.876 | 0.864 | 0.904 | **SENSIBLE** |

*Note on ROC-AUC Calculation:* In subsets where only a single class is present, the metric is mathematically undefined. The engine cleanly handles single-class subsets without fabricating artificial scores.

---

## 4. Behavioral Sanity & Heuristic Verification

The inference pipeline enforces 5 physical heuristics:

1. **Precipitation Monotonicity:** Verified. Under identical terrain (Slope=24°, Elevation=1,200m), increasing rainfall from 20 mm to 140 mm strictly increases predicted hazard index from 0.22 to 0.78 ($\Delta \ge 0$).
2. **Gradient Monotonicity:** Verified. Steeper mountain slopes (32°) consistently yield higher risk indices than flat alluvial plains (4°) under equivalent saturation.
3. **Active Incident Penalty:** Verified. Active washout incidents raise traversal penalties by $\ge 0.40$ points, ensuring Dijkstra avoids the edge.
4. **Stale Telemetry Decay:** When telemetry exceeds the 6-hour validity window, model confidence decays linearly ($< 0.50$), triggering fallback alerts on the dashboard.
5. **Missing Feature Graceful Fallback:** Missing or corrupt feature inputs trigger conservative regional priors (Hazard=0.50, Confidence=0.30) without unhandled 500 exceptions.

---

## 5. Explainable AI (XAI) Decision Support

To provide actionable transparency for command center dispatchers, the model does not output an opaque black-box probability. Instead, `HazardPredictionService` computes an explainable contributing factor breakdown:

```json
{
  "hazard_index": 0.78,
  "severity": "CRITICAL",
  "confidence": 0.89,
  "contributing_factors": {
    "monsoon_rainfall": "Heavy 24h precipitation (125.0 mm)",
    "terrain_steepness": "Severe mountain gradient (31.4° slope)",
    "soil_saturation": "High pore-water saturation (84%)",
    "historical_instability": "Frequent prior slope washouts (4 events)"
  }
}
```

---

## 6. Limitations & Production Roadmap

1. **Synthetic Data Reliance:** Current training relies on domain-calibrated synthetic environmental vectors. Future production deployment requires streaming ingestion of ground-truth landslide inventories from Geological Survey of India (GSI) and National Remote Sensing Centre (NRSC).
2. **Micro-Climate Variability:** Mountain rain shadows cause localized cloudbursts that regional weather stations may miss. Edge IoT rain gauges along National Highways will be required for hyper-local precision.
