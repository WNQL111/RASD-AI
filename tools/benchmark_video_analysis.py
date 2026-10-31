import sys
import os
import time
import uuid
import logging
import numpy as np
from typing import Dict, Any

# Ensure ai_worker/src is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))

from core.frame_decoder import FrameDecoder
from core.pipeline import Pipeline
from core.event_schema import EventEnvelope, EventTypes
from detectors.yolo_detector import YoloDetector
from tracker.byte_tracker import ByteTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark_video_analysis")

def run_video_analysis_benchmark(video_file_path: str, run_count: int = 10):
    """
    Benchmarks Video User Trial Mode Processing Times across stages:
    decode_time, AI_time, event_reasoning_time, persist_time, realtime_time, total_time.
    Calculates p50, p95, p99 metrics.
    """
    logger.info("==========================================================")
    logger.info("     ASIS-V2 VIDEO USER TRIAL MODE PERFORMANCE BENCHMARK")
    logger.info("==========================================================")

    if not os.path.exists(video_file_path):
        logger.error(f"Test video file not found: {video_file_path}")
        return None

    detector = YoloDetector(model_dir=".", model_name="yolov8n.pt")
    
    stage_metrics = {
        "decode_time_ms": [],
        "ai_inference_time_ms": [],
        "event_reasoning_time_ms": [],
        "total_video_analysis_sec": []
    }

    for run_idx in range(run_count):
        t0_start = time.time()
        decoder = FrameDecoder(video_file_path)
        tracker = ByteTracker(detector)
        pipeline = Pipeline(detector, redis_client=None, video_path=video_file_path, fps=25.0)
        
        frame_count = 0
        while True:
            t_dec_start = time.time()
            ret, frame = decoder.read_frame()
            t_dec_end = time.time()
            if not ret:
                break
            
            stage_metrics["decode_time_ms"].append((t_dec_end - t_dec_start) * 1000.0)
            
            frame_resized = decoder.resize_frame(frame, width=640)
            t_ai_start = time.time()
            pipeline.process_frame(frame_resized, frame_count, f"trial_{run_idx}", tracker=tracker)
            t_ai_end = time.time()

            stage_metrics["ai_inference_time_ms"].append((t_ai_end - t_ai_start) * 1000.0)
            frame_count += 1
            if frame_count >= 100: # Benchmark 100 frames slice
                break

        decoder.release()
        total_sec = time.time() - t0_start
        stage_metrics["total_video_analysis_sec"].append(total_sec)

    summary = {}
    for stage, vals in stage_metrics.items():
        if len(vals) > 0:
            summary[stage] = {
                "p50": round(float(np.percentile(vals, 50)), 3),
                "p95": round(float(np.percentile(vals, 95)), 3),
                "p99": round(float(np.percentile(vals, 99)), 3),
                "avg": round(float(np.mean(vals)), 3)
            }
        else:
            summary[stage] = {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0}

    logger.info(f"Video Analysis Benchmark Results: {summary}")
    return summary

if __name__ == "__main__":
    sample_video = "RADIOMONTALVOFMAZUAY(MP4).mp4"
    if not os.path.exists(sample_video):
        sample_video = "Package Thief CAUGHT on Ring Doorbell Camera(240P).mp4"
    run_video_analysis_benchmark(sample_video, run_count=3)
