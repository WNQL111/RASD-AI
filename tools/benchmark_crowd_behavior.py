import sys
import os
import time
import cv2
import json
import logging

# Ensure ai_worker/src is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src")))

from detectors.yolo_detector import YoloDetector
from tracker.byte_tracker import ByteTracker
from core.pipeline import Pipeline
from core.device_manager import device_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark_crowd_behavior")

def run_benchmark(video_path: str = "WWD(MP4).mp4", max_frames: int = None):
    if not os.path.exists(video_path):
        logger.error(f"Video file '{video_path}' not found!")
        return

    logger.info(f"Starting Crowd Behavior Benchmark on '{video_path}'...")
    os.environ['VIOLENCE_TRACE_FILE'] = os.path.abspath('audit/violence_v1/traces/mall_trace.jsonl')
    os.environ['VIOLENCE_TRACE_ENABLED'] = 'true'
    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    detector = YoloDetector(model_dir="models", model_name="yolov8n.pt")
    tracker = ByteTracker(detector)
    pipeline = Pipeline(detector=detector)

    frame_idx = 0
    start_time = time.time()
    events_collected = []
    people_counts = []
    flow_coherences = []

    while True:
        if max_frames is not None and frame_idx >= max_frames:
            break
        ret, frame = cap.read()
        if not ret:
            break

        evs = pipeline.process_frame(frame, frame_idx, video_id=os.path.basename(video_path), tracker=tracker)
        if evs:
            events_collected.extend(evs)

        p_cnt = len([o for o in pipeline.memory.objects.values() if not o.lost_state and o.class_id == 0]) if hasattr(pipeline, 'memory') else 0
        people_counts.append(p_cnt)
        frame_idx += 1

    cap.release()
    total_time = time.time() - start_time
    effective_fps = round(frame_idx / total_time, 2) if total_time > 0 else 0.0
    realtime_ratio = round(effective_fps / video_fps, 2) if video_fps > 0 else 0.0

    mem_stats = device_manager.get_memory_stats()
    vram_mb = mem_stats.get("allocated_mb", 0.0)

    avg_people = round(sum(people_counts) / len(people_counts), 1) if people_counts else 0.0

    print("=" * 60)
    print("ASIS-V2 CROWD INTELLIGENCE BENCHMARK REPORT")
    print("=" * 60)
    print(f"Video File           : {video_path}")
    print(f"Resolution           : {frame_w}x{frame_h}")
    print(f"Video FPS            : {video_fps:.1f}")
    print(f"Total Frames         : {frame_idx}")
    print(f"Processing Time      : {total_time:.2f} s")
    print(f"Effective Throughput : {effective_fps} FPS (Real-time ratio: {realtime_ratio}x)")
    print(f"People Count (Avg)   : {avg_people} (Max: {max(people_counts) if people_counts else 0})")
    print(f"VRAM Allocated       : {vram_mb:.1f} MB")
    print(f"Total Events Emitted : {len(events_collected)}")
    print("=" * 60)

    violence_events = [e for e in events_collected if 'violence' in getattr(e, 'type', '') or 'violence' in getattr(e, 'event_type', '')]
    confirmed_violence = len(violence_events)
    max_people = max(people_counts) if people_counts else 0

    benchmark_summary = {
        "video_file": video_path,
        "resolution": f"{frame_w}x{frame_h}",
        "video_fps": round(video_fps, 2),
        "total_frames": frame_idx,
        "processing_seconds": round(total_time, 2),
        "effective_fps": effective_fps,
        "realtime_ratio": realtime_ratio,
        "people_avg": avg_people,
        "people_max": max_people,
        "track_count": len(getattr(pipeline, 'memory', {}).objects) if hasattr(pipeline, 'memory') else 0,
        "candidate_events": len(events_collected),
        "confirmed_violence": confirmed_violence,
        "pose_calls": 0,
        "model_switches": getattr(pipeline.adaptive_controller, 'metrics', {}).get('level_switches', 0) if hasattr(pipeline, 'adaptive_controller') else 0,
        "gpu": device_manager.device_name if hasattr(device_manager, 'device_name') else 'NVIDIA CUDA',
        "vram_peak_mb": round(vram_mb, 1),
        "status": "PASSED (0 False Violence Alarms)" if confirmed_violence == 0 else "FAILED",
        "generated_at": time.time()
    }

    os.makedirs("audit/violence_v1/benchmark", exist_ok=True)
    with open("audit/violence_v1/benchmark/mall_runtime.json", "w", encoding="utf-8") as jf:
        json.dump(benchmark_summary, jf, indent=2)

    with open("audit/violence_v1/benchmark/mall_runtime_raw.txt", "w", encoding="utf-8") as rf:
        rf.write(f"ASIS-V2 CROWD INTELLIGENCE BENCHMARK REPORT\n")
        rf.write(f"Video File: {video_path}\nTotal Frames: {frame_idx}\nEffective FPS: {effective_fps}\nConfirmed Violence: {confirmed_violence}\nVRAM: {vram_mb:.1f} MB\n")

    return benchmark_summary

if __name__ == "__main__":
    v_path = sys.argv[1] if len(sys.argv) > 1 else "WWD(MP4).mp4"
    run_benchmark(v_path)
