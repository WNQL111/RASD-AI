import os
import sys
import time
import logging
import numpy as np
import torch

# Ensure ai_worker/src is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))

from core.device_manager import device_manager
from core.model_registry import model_registry
from engines.model_manager import ModelManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark_models")

def benchmark_model(model_id: str, sample_shape=(640, 640, 3), warmup_count: int = 10, run_count: int = 50):
    """
    Benchmarks model load time, warmup latency, steady-state latency (p50, p95, avg), FPS, and VRAM memory.
    """
    logger.info(f"--- Benchmarking Model: {model_id} ---")
    spec = model_registry.get_spec(model_id)
    if not spec:
        logger.error(f"Model {model_id} not registered.")
        return None

    model_manager = ModelManager(model_dir="./models", default_model=model_id)

    # 1. Load Time
    t_start_load = time.time()
    instance = model_manager.get_or_load_model_instance(model_id)
    load_time_ms = (time.time() - t_start_load) * 1000.0

    if not instance:
        logger.error(f"Failed to load model {model_id}")
        return None

    # Dummy BGR uint8 image frame
    dummy_frame = np.zeros(sample_shape, dtype=np.uint8)

    # 2. Warmup Runs (Discarded from steady-state statistics)
    for _ in range(warmup_count):
        model_manager.detect(dummy_frame, model_name=model_id)

    if device_manager.get_device().type == "cuda":
        torch.cuda.synchronize()

    # 3. Steady-State Measurement Runs
    latencies = []
    for _ in range(run_count):
        t0 = time.time()
        model_manager.detect(dummy_frame, model_name=model_id)
        if device_manager.get_device().type == "cuda":
            torch.cuda.synchronize()
        latencies.append((time.time() - t0) * 1000.0)

    avg_latency = float(np.mean(latencies))
    p50_latency = float(np.percentile(latencies, 50))
    p95_latency = float(np.percentile(latencies, 95))
    fps = round(1000.0 / avg_latency, 1) if avg_latency > 0 else 0.0

    # 4. Memory Stats
    mem_stats = device_manager.get_memory_stats()

    # 5. Update Registry with Measured Stats
    model_registry.update_measured_latency(model_id, avg_latency)

    results = {
        "model_id": model_id,
        "task": spec.task,
        "tier": spec.tier,
        "load_time_ms": round(load_time_ms, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "p50_latency_ms": round(p50_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "steady_state_fps": fps,
        "allocated_vram_mb": mem_stats.get("allocated_mb", 0.0),
        "device": mem_stats.get("device", "CPU")
    }

    logger.info(f"Benchmark Results for {model_id}: {results}")
    return results

def benchmark_scene_profiler(run_count: int = 100):
    """
    Benchmarks SceneProfiler latency, CPU processing time, and mode breakdown.
    """
    from core.scene_profiler import SceneProfiler
    logger.info("--- Benchmarking SceneProfiler Overhead ---")
    profiler = SceneProfiler(fps=25.0)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    latencies = []
    modes = []

    class DummyObj:
        def __init__(self, tid, cx, cy):
            self.track_id = tid
            self.class_id = 0
            self.bbox = [cx-20, cy-20, cx+20, cy+20]
            self.dx = 2.0
            self.dy = 1.0

    dummy_objs = [DummyObj(1, 100, 100), DummyObj(2, 110, 110)]

    for i in range(run_count):
        t0 = time.time()
        sp, ap = profiler.profile_scene(dummy_frame, dummy_objs, frame_idx=i)
        latencies.append((time.time() - t0) * 1000.0)
        modes.append(ap.mode)

    avg_lat = float(np.mean(latencies))
    p50_lat = float(np.percentile(latencies, 50))
    p95_lat = float(np.percentile(latencies, 95))

    mode_counts = {m: modes.count(m) for m in set(modes)}
    results = {
        "component": "SceneProfiler",
        "avg_latency_ms": round(avg_lat, 3),
        "p50_latency_ms": round(p50_lat, 3),
        "p95_latency_ms": round(p95_lat, 3),
        "mode_breakdown": mode_counts
    }
    logger.info(f"SceneProfiler Benchmark Results: {results}")
    return results

def benchmark_interaction_engine(run_count: int = 100):
    """
    Benchmarks AdaptiveInteractionEngine latency, pair generation time, and pose trigger frequency.
    """
    from core.adaptive_interaction_engine import AdaptiveInteractionEngine
    from core.scene_types import TrackContext, MotionFeatures

    logger.info("--- Benchmarking AdaptiveInteractionEngine Overhead ---")
    engine = AdaptiveInteractionEngine(proximity_radius_px=180.0, max_pairs=30)

    mf_a = MotionFeatures(normalized_velocity=3.0, direction_rad=0.0)
    mf_b = MotionFeatures(normalized_velocity=3.0, direction_rad=3.14)

    dummy_tracks = [
        TrackContext(track_id=1, class_id=0, bbox=[100,100,140,140], center=[120,120], motion_features=mf_a),
        TrackContext(track_id=2, class_id=0, bbox=[130,100,170,140], center=[150,120], motion_features=mf_b),
        TrackContext(track_id=3, class_id=0, bbox=[200,200,240,240], center=[220,220], motion_features=mf_a)
    ]

    latencies = []
    pose_triggers = 0

    for i in range(run_count):
        t0 = time.time()
        res = engine.process_interactions(dummy_tracks, frame_idx=i)
        latencies.append((time.time() - t0) * 1000.0)
        if res.pose_trigger_needed:
            pose_triggers += 1

    avg_lat = float(np.mean(latencies))
    p50_lat = float(np.percentile(latencies, 50))
    p95_lat = float(np.percentile(latencies, 95))

    results = {
        "component": "AdaptiveInteractionEngine",
        "avg_latency_ms": round(avg_lat, 3),
        "p50_latency_ms": round(p50_lat, 3),
        "p95_latency_ms": round(p95_lat, 3),
        "pose_trigger_percentage": round((pose_triggers / float(run_count)) * 100.0, 1)
    }
    logger.info(f"AdaptiveInteractionEngine Benchmark Results: {results}")
    return results

def benchmark_event_reasoner(run_count: int = 100):
    """
    Benchmarks EventReasoningOrchestrator latency, firewall suppression speed, and multi-signal fusion overhead.
    """
    from core.adaptive_interaction_engine import AdaptiveInteractionEngine
    from core.event_reasoning_orchestrator import EventReasoningOrchestrator
    from core.scene_types import TrackContext, MotionFeatures, SceneProfile

    logger.info("--- Benchmarking EventReasoningOrchestrator Overhead ---")
    inter_engine = AdaptiveInteractionEngine(proximity_radius_px=180.0, max_pairs=30)
    reasoner = EventReasoningOrchestrator(max_events=20)
    sp = SceneProfile(people_count=3)

    mf_a = MotionFeatures(normalized_velocity=3.0, direction_rad=0.0)
    mf_b = MotionFeatures(normalized_velocity=3.0, direction_rad=3.14)

    dummy_tracks = [
        TrackContext(track_id=1, class_id=0, bbox=[100,100,140,140], center=[120,120], motion_features=mf_a),
        TrackContext(track_id=2, class_id=0, bbox=[130,100,170,140], center=[150,120], motion_features=mf_b),
        TrackContext(track_id=3, class_id=0, bbox=[200,200,240,240], center=[220,220], motion_features=mf_a)
    ]

    latencies = []

    for i in range(run_count):
        res = inter_engine.process_interactions(dummy_tracks, frame_idx=i)
        t0 = time.time()
        evs, max_ev, reasons = reasoner.evaluate_events(res, sp, frame_idx=i)
        latencies.append((time.time() - t0) * 1000.0)

    avg_lat = float(np.mean(latencies))
    p50_lat = float(np.percentile(latencies, 50))
    p95_lat = float(np.percentile(latencies, 95))

    results = {
        "component": "EventReasoningOrchestrator",
        "avg_latency_ms": round(avg_lat, 3),
        "p50_latency_ms": round(p50_lat, 3),
        "p95_latency_ms": round(p95_lat, 3)
    }
    logger.info(f"EventReasoningOrchestrator Benchmark Results: {results}")
    return results

def benchmark_compute_orchestrator(run_count: int = 100):
    """
    Benchmarks AdaptiveComputeOrchestrator latency, GPU health sampling speed, and quality scheduling overhead.
    """
    from core.adaptive_compute_orchestrator import AdaptiveComputeOrchestrator

    logger.info("--- Benchmarking AdaptiveComputeOrchestrator Overhead ---")
    orchestrator = AdaptiveComputeOrchestrator(max_queue_size=30)

    latencies = []

    for i in range(run_count):
        t0 = time.time()
        should_proc, res_state, q_level, rec_model = orchestrator.evaluate_compute_budget(
            frame_idx=i, net_evidence_score=0.45
        )
        latencies.append((time.time() - t0) * 1000.0)

    avg_lat = float(np.mean(latencies))
    p50_lat = float(np.percentile(latencies, 50))
    p95_lat = float(np.percentile(latencies, 95))

    results = {
        "component": "AdaptiveComputeOrchestrator",
        "avg_latency_ms": round(avg_lat, 3),
        "p50_latency_ms": round(p50_lat, 3),
        "p95_latency_ms": round(p95_lat, 3)
    }
    logger.info(f"AdaptiveComputeOrchestrator Benchmark Results: {results}")
    return results

def run_all_benchmarks():
    print("==========================================================")
    print(" ASIS-V2 MODEL, SCENE, INTERACTION, EVENT & SCHEDULER BENCHMARK")
    print("==========================================================")
    benchmark_scene_profiler()
    benchmark_interaction_engine()
    benchmark_event_reasoner()
    benchmark_compute_orchestrator()
    for spec in model_registry.list_all():
        benchmark_model(spec.model_id)

if __name__ == "__main__":
    run_all_benchmarks()
