"""
SIH26002 — Phase 10 Performance Benchmarking Suite.
Measures empirical latencies (Mean, Median, P95, Min, Max) across 9 critical demo workloads:
1. Route Calculation (Multi-modal Dijkstra)
2. Hazard Inference / Prediction Engine
3. Fleet Optimization (Multi-Depot Optimizer)
4. Dynamic Freight Load Consolidation
5. Predictive ETA Calculation
6. Disruption Scenario Simulation
7. Corridor Network Accessibility Calculation
8. Command-Center Intelligence Summary API
9. Demo Readiness Healthcheck (15 Subsystems)

Hardware & Environment recorded automatically.
Zero metric fabrication: results reflect real empirical timings on the active database & host environment.
"""

import os
import sys
import time
import json
import statistics
import platform
from pathlib import Path

# Setup Django Environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.transport_graph.models import TransportNode, TransportEdge
from apps.vehicles.models import Vehicle
from apps.fleet.models import FreightLoad
from apps.routing.engine import RoutingEngine
from apps.hazards.services.prediction_service import HazardPredictionService
from apps.fleet.services.fleet_optimizer import MultiDepotFleetOptimizer
from apps.fleet.services.dynamic_consolidation_service import DynamicLoadConsolidationService
from apps.routing.services.eta_intelligence import PredictiveETAService
from apps.incidents.services.simulation_engine import DisruptionSimulationEngine
from apps.transport_graph.services.accessibility import AccessibilityIntelligenceService
from apps.analytics.intelligence_views import NetworkOperationalSummaryView
from apps.core.demo_views import DemoReadinessView

User = get_user_model()


def time_callable(func, *args, **kwargs):
    """Executes func and returns (result, elapsed_ms)."""
    start = time.perf_counter()
    res = func(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return res, elapsed_ms


def compute_stats(latencies):
    """Computes mean, median, p95, min, max."""
    sorted_lats = sorted(latencies)
    p95_idx = int(len(sorted_lats) * 0.95)
    return {
        "mean_ms": round(statistics.mean(latencies), 2),
        "median_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(sorted_lats[p95_idx] if p95_idx < len(sorted_lats) else sorted_lats[-1], 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "samples": len(latencies),
    }


def run_benchmarks(iterations=5):
    print("=" * 70)
    print("SIH26002 PHASE 10 PERFORMANCE BENCHMARK SUITE")
    print(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {platform.python_version()} | Host: Windows Host Environment")
    print(f"Iterations per benchmark: {iterations}")
    print("=" * 70)

    user = User.objects.filter(is_active=True).first()
    if not user:
        user = User.objects.create(email="bench_op@sih26002.in", phone="+919111199999", role="DISPATCHER")
    factory = RequestFactory()
    results = {}

    # 1. Demo Readiness Check
    print("\n[1/9] Benchmarking Demo Readiness Check (15 Subsystems)...")
    readiness_lats = []
    readiness_view = DemoReadinessView.as_view()
    for _ in range(iterations):
        req = factory.get("/api/v1/demo/readiness/")
        req.user = user
        _, elapsed = time_callable(readiness_view, req)
        readiness_lats.append(elapsed)
    results["demo_readiness"] = {
        "workload": "Demo Readiness Check (15 Subsystems)",
        "dataset_size": "15 Subsystem Health Probes",
        **compute_stats(readiness_lats)
    }
    print(f"  -> Mean: {results['demo_readiness']['mean_ms']} ms | Median: {results['demo_readiness']['median_ms']} ms | P95: {results['demo_readiness']['p95_ms']} ms")

    # 2. Hazard Prediction
    print("\n[2/9] Benchmarking Hazard Prediction Engine...")
    edge = TransportEdge.objects.first()
    hazard_service = HazardPredictionService()
    hazard_lats = []
    if edge:
        for _ in range(iterations):
            _, elapsed = time_callable(hazard_service.predict_single_edge, edge=edge)
            hazard_lats.append(elapsed)
        results["hazard_inference"] = {
            "workload": "Multi-Modal Hazard Inference",
            "dataset_size": f"1 Edge Query (DB Edges: {TransportEdge.objects.count()})",
            **compute_stats(hazard_lats)
        }
        print(f"  -> Mean: {results['hazard_inference']['mean_ms']} ms | Median: {results['hazard_inference']['median_ms']} ms | P95: {results['hazard_inference']['p95_ms']} ms")
    else:
        print("  -> SKIPPED (No edges in DB)")

    # 3. Route Calculation
    print("\n[3/9] Benchmarking Multi-Modal Routing Engine...")
    nodes = list(TransportNode.objects.filter(is_active=True)[:2])
    routing_lats = []
    if len(nodes) >= 2:
        origin, destination = nodes[0], nodes[1]
        router = RoutingEngine()
        for _ in range(iterations):
            _, elapsed = time_callable(router.compute_single_route, origin=origin, destination=destination)
            routing_lats.append(elapsed)
        results["route_calculation"] = {
            "workload": "Multi-Modal Dijkstra / A* Routing",
            "dataset_size": f"Nodes: {TransportNode.objects.count()}, Edges: {TransportEdge.objects.count()}",
            **compute_stats(routing_lats)
        }
        print(f"  -> Mean: {results['route_calculation']['mean_ms']} ms | Median: {results['route_calculation']['median_ms']} ms | P95: {results['route_calculation']['p95_ms']} ms")
    else:
        print("  -> SKIPPED (Insufficient nodes)")

    # 4. Predictive ETA Calculation
    print("\n[4/9] Benchmarking Predictive ETA Intelligence...")
    from apps.routing.services.eta_intelligence import MountainCorridorDelayModel
    delay_model = MountainCorridorDelayModel()
    eta_lats = []
    for _ in range(iterations):
        _, elapsed = time_callable(
            delay_model.predict,
            base_transit_time_min=240.0,
            route_distance_km=145.0,
            hazard_score=0.45,
            weather_rainfall_mm=65.0,
            transfer_count=1,
            is_hill_corridor=True,
        )
        eta_lats.append(elapsed)
    results["eta_prediction"] = {
        "workload": "Domain & Gradient-Calibrated Predictive ETA Inference",
        "dataset_size": "145.0 km Inter-State Corridor Vector",
        **compute_stats(eta_lats)
    }
    print(f"  -> Mean: {results['eta_prediction']['mean_ms']} ms | Median: {results['eta_prediction']['median_ms']} ms | P95: {results['eta_prediction']['p95_ms']} ms")

    # 5. Dynamic Load Consolidation
    print("\n[5/9] Benchmarking Dynamic Load Consolidation...")
    consolidation_lats = []
    for _ in range(iterations):
        _, elapsed = time_callable(
            DynamicLoadConsolidationService.generate_recommendations,
            persist=False,
            is_simulation=True,
        )
        consolidation_lats.append(elapsed)
    results["load_consolidation"] = {
        "workload": "Dynamic Freight Load Consolidation",
        "dataset_size": f"Freight Loads: {FreightLoad.objects.count()}",
        **compute_stats(consolidation_lats)
    }
    print(f"  -> Mean: {results['load_consolidation']['mean_ms']} ms | Median: {results['load_consolidation']['median_ms']} ms | P95: {results['load_consolidation']['p95_ms']} ms")

    # 6. Fleet Optimization
    print("\n[6/9] Benchmarking Multi-Depot Fleet Optimization...")
    fleet_lats = []
    for _ in range(iterations):
        _, elapsed = time_callable(
            MultiDepotFleetOptimizer.optimize,
            is_simulation=True,
            operator_user=user,
        )
        fleet_lats.append(elapsed)
    results["fleet_optimization"] = {
        "workload": "Multi-Depot Fleet Routing & Dispatch",
        "dataset_size": f"Vehicles: {Vehicle.objects.count()}, Loads: {FreightLoad.objects.count()}",
        **compute_stats(fleet_lats)
    }
    print(f"  -> Mean: {results['fleet_optimization']['mean_ms']} ms | Median: {results['fleet_optimization']['median_ms']} ms | P95: {results['fleet_optimization']['p95_ms']} ms")

    # 7. Disruption Scenario Simulation
    print("\n[7/9] Benchmarking Disruption Scenario Simulator...")
    sim_lats = []
    for _ in range(iterations):
        _, elapsed = time_callable(
            DisruptionSimulationEngine.run_scenario,
            scenario_type="HEAVY_RAINFALL",
            target_corridor="NH-27 / Guwahati Corridor",
            target_state="AS",
            persist=False,
            operator_user=user,
        )
        sim_lats.append(elapsed)
    results["disruption_simulation"] = {
        "workload": "Disruption Scenario Simulation & Cascade Impact",
        "dataset_size": "Target: NH-27 Corridor, HEAVY_RAINFALL Scenario",
        **compute_stats(sim_lats)
    }
    print(f"  -> Mean: {results['disruption_simulation']['mean_ms']} ms | Median: {results['disruption_simulation']['median_ms']} ms | P95: {results['disruption_simulation']['p95_ms']} ms")

    # 8. Corridor Network Accessibility Calculation
    print("\n[8/9] Benchmarking Accessibility Intelligence...")
    access_lats = []
    for _ in range(iterations):
        _, elapsed = time_callable(
            AccessibilityIntelligenceService.evaluate_corridor_accessibility,
        )
        access_lats.append(elapsed)
    results["accessibility_calculation"] = {
        "workload": "Corridor-level Accessibility Index & Scoring",
        "dataset_size": f"All {TransportEdge.objects.count()} Edges in NER Topology",
        **compute_stats(access_lats)
    }
    print(f"  -> Mean: {results['accessibility_calculation']['mean_ms']} ms | Median: {results['accessibility_calculation']['median_ms']} ms | P95: {results['accessibility_calculation']['p95_ms']} ms")

    # 9. Command-Center Intelligence Summary API
    print("\n[9/9] Benchmarking Command-Center Intelligence API...")
    cc_lats = []
    cc_view = NetworkOperationalSummaryView.as_view()
    for _ in range(iterations):
        req = factory.get("/api/v1/intelligence/network/")
        req.user = user
        _, elapsed = time_callable(cc_view, req)
        cc_lats.append(elapsed)
    results["command_center_api"] = {
        "workload": "Command-Center Unified Network Operational Summary",
        "dataset_size": "Full System Operational Snapshot",
        **compute_stats(cc_lats)
    }
    print(f"  -> Mean: {results['command_center_api']['mean_ms']} ms | Median: {results['command_center_api']['median_ms']} ms | P95: {results['command_center_api']['p95_ms']} ms")

    # Summary table
    print("\n" + "=" * 76)
    print(f"{'Workload':<32} | {'Mean (ms)':<9} | {'Median (ms)':<11} | {'P95 (ms)':<9}")
    print("-" * 76)
    for k, v in results.items():
        print(f"{v['workload'][:32]:<32} | {v['mean_ms']:<9.2f} | {v['median_ms']:<11.2f} | {v['p95_ms']:<9.2f}")
    print("=" * 76)

    # Save to JSON
    output_path = BASE_DIR / "benchmark_results_phase10.json"
    benchmark_payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "benchmarks": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_payload, f, indent=2)
    print(f"\n[OK] Benchmark metrics saved to {output_path}")
    return results


if __name__ == "__main__":
    run_benchmarks(iterations=5)
