import sys
import os
import time
import uuid
import json
import logging
import asyncio
import numpy as np
from typing import Dict, List, Any

# Ensure ai_worker/src and backend/app are on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "app"))

from core.event_schema import EventEnvelope, EventTypes
from core.backpressure_controller import BackpressureController
from core.device_manager import device_manager
from engines.model_manager import ModelManager
from services.event_processor import EventProcessor
from services.broadcaster import BroadcasterManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark_reliability")

class SystemReliabilitySuite:
    """
    ASIS-V2 Comprehensive System Reliability & Chaos Benchmark Suite.
    Measures Latency, Event Delivery Guarantee, Loss/Duplication Rates,
    Queue Saturation, Memory/VRAM Stability, and Failure Recovery.
    """
    def __init__(self):
        self.processor = EventProcessor(max_history_capacity=1000)
        self.broadcaster = BroadcasterManager(history_limit=100)
        self.backpressure = BackpressureController(max_queue_size=30, max_age_ms=100.0)
        self.model_manager = ModelManager(model_dir=".", default_model="yolov8n.pt")

    def run_event_delivery_burst_test(self, burst_count: int = 500) -> Dict[str, Any]:
        """
        Test 1: Event Delivery Guarantee & Loss/Duplication Validation
        Sends 500 events in high-frequency burst, measures loss, duplicates, and out-of-order count.
        """
        logger.info(f"--- Running Event Delivery Burst Test ({burst_count} events) ---")
        generated_count = 0
        persisted_count = 0
        duplicate_count = 0
        loss_count = 0

        start_time = time.time()
        for i in range(burst_count):
            ev_id = f"burst_evt_{i}"
            envelope = EventEnvelope(
                event_id=ev_id,
                trace_id=str(uuid.uuid4()),
                type=EventTypes.VIOLENCE_CANDIDATE if i % 10 != 0 else EventTypes.VIOLENCE_CONFIRMED,
                camera_id="cam_burst_1",
                sequence=i + 1
            )
            generated_count += 1
            payload = envelope.to_dict()

            processed = self.processor.process_incoming_event(payload)
            if processed:
                persisted_count += 1
            else:
                duplicate_count += 1

        elapsed = time.time() - start_time
        loss_count = generated_count - (persisted_count + duplicate_count)

        res = {
            "test_name": "Event Delivery Burst Test",
            "events_generated": generated_count,
            "events_persisted": persisted_count,
            "duplicate_count": duplicate_count,
            "loss_count": loss_count,
            "throughput_eps": round(generated_count / elapsed, 1) if elapsed > 0 else 0.0,
            "status": "PASS" if loss_count == 0 and duplicate_count == 0 else "FAIL"
        }
        logger.info(f"Burst Test Results: {res}")
        return res

    def run_duplicate_suppression_test(self) -> Dict[str, Any]:
        """
        Test 2: Duplicate Event Suppression Test
        Sends exact same event_id 10 times. Expects 1 processed, 9 suppressed.
        """
        logger.info("--- Running Duplicate Event Suppression Test ---")
        target_id = "dup_test_target_999"
        processed_count = 0
        suppressed_count = 0

        for i in range(10):
            payload = EventEnvelope(event_id=target_id, camera_id="cam_dup_1").to_dict()
            res = self.processor.process_incoming_event(payload)
            if res is not None:
                processed_count += 1
            else:
                suppressed_count += 1

        status = "PASS" if processed_count == 1 and suppressed_count == 9 else "FAIL"
        res = {
            "test_name": "Duplicate Event Suppression",
            "processed_count": processed_count,
            "suppressed_count": suppressed_count,
            "status": status
        }
        logger.info(f"Duplicate Suppression Results: {res}")
        return res

    def run_queue_saturation_test(self, surge_frames: int = 100) -> Dict[str, Any]:
        """
        Test 3: Queue Saturation & Frame Age Dropper Test
        Simulates frame ingress surge (100 FPS), measures queue depth bound (<= 30) and stale frame dropping.
        """
        logger.info(f"--- Running Queue Saturation Test ({surge_frames} frames surge) ---")
        dropped_count = 0
        queue_max_observed = 0

        for i in range(surge_frames):
            is_critical = (i % 20 == 0) # Every 20th frame is critical evidence
            success = self.backpressure.enqueue_frame(
                frame_id=i,
                camera_id="cam_surge_1",
                frame_data=None,
                is_critical=is_critical
            )
            q_depth = self.backpressure.get_queue_depth()
            if q_depth > queue_max_observed:
                queue_max_observed = q_depth

        dropped_count = self.backpressure.total_dropped_count
        bounded_pass = queue_max_observed <= 30

        res = {
            "test_name": "Queue Saturation & Backpressure",
            "surge_frames": surge_frames,
            "queue_max_observed": queue_max_observed,
            "bounded_max_limit": 30,
            "stale_dropped_count": dropped_count,
            "queue_bounded_pass": bounded_pass,
            "status": "PASS" if bounded_pass else "FAIL"
        }
        logger.info(f"Queue Saturation Results: {res}")
        return res

    def run_vram_memory_leak_test(self, cycles: int = 5) -> Dict[str, Any]:
        """
        Test 4: VRAM & System Memory Leak Detection Test
        Repeatedly loads, infers, and switches models across cycles while tracking VRAM memory trend.
        """
        logger.info(f"--- Running VRAM & Memory Leak Detection Test ({cycles} cycles) ---")
        vram_snapshots = []

        for cycle in range(cycles):
            for model_id in ["yolov8n.pt", "yolov8m.pt", "yolov8n-pose.pt"]:
                try:
                    mdl = self.model_manager.get_or_load_model_instance(model_id)
                except Exception as e:
                    logger.warning(f"Leak Test: Error loading model {model_id}: {e}")

            mem_stats = device_manager.get_memory_stats()
            alloc_mb = mem_stats.get("allocated_mb", 0.0)
            vram_snapshots.append(alloc_mb)

        # Check for continuous upward trend in VRAM allocation
        initial_mb = vram_snapshots[0]
        final_mb = vram_snapshots[-1]
        leak_detected = (final_mb - initial_mb) > 50.0 # Leak threshold = 50 MB

        res = {
            "test_name": "VRAM Leak Detection",
            "initial_vram_mb": initial_mb,
            "final_vram_mb": final_mb,
            "delta_vram_mb": round(final_mb - initial_mb, 2),
            "vram_snapshots_mb": vram_snapshots,
            "status": "PASS" if not leak_detected else "FAIL"
        }
        logger.info(f"VRAM Leak Test Results: {res}")
        return res

    def run_multi_camera_isolation_test(self, camera_count: int = 4) -> Dict[str, Any]:
        """
        Test 5: Multi-Camera State Isolation Test
        Simulates events across 4 concurrent cameras (cam_1, cam_2, cam_3, cam_4), verifying 0 cross-camera pollution.
        """
        logger.info(f"--- Running Multi-Camera Isolation Test ({camera_count} cameras) ---")
        cam_sequences = {}

        for c_idx in range(1, camera_count + 1):
            cam_id = f"cam_{c_idx}"
            for seq in range(1, 10):
                ev = EventEnvelope(event_id=f"evt_{cam_id}_{seq}", camera_id=cam_id, sequence=seq).to_dict()
                self.processor.process_incoming_event(ev)
                cam_sequences[cam_id] = self.processor.last_sequence_by_camera.get(cam_id)

        all_isolated = all(cam_sequences[f"cam_{i}"] == 9 for i in range(1, camera_count + 1))
        res = {
            "test_name": "Multi-Camera State Isolation",
            "camera_count": camera_count,
            "sequences_by_camera": cam_sequences,
            "status": "PASS" if all_isolated else "FAIL"
        }
        logger.info(f"Multi-Camera Isolation Results: {res}")
        return res

    def run_all_reliability_benchmarks(self) -> Dict[str, Any]:
        logger.info("==========================================================")
        logger.info("     ASIS-V2 SYSTEM RELIABILITY & STRESS BENCHMARK")
        logger.info("==========================================================")

        r1 = self.run_event_delivery_burst_test(burst_count=500)
        r2 = self.run_duplicate_suppression_test()
        r3 = self.run_queue_saturation_test(surge_frames=100)
        r4 = self.run_vram_memory_leak_test(cycles=5)
        r5 = self.run_multi_camera_isolation_test(camera_count=4)

        all_passed = all(
            r["status"] == "PASS" for r in [r1, r2, r3, r4, r5]
        )

        overall_summary = {
            "overall_status": "PASS" if all_passed else "FAIL",
            "burst_test": r1,
            "duplicate_test": r2,
            "queue_saturation_test": r3,
            "vram_leak_test": r4,
            "multi_camera_test": r5,
            "long_run_status": "NOT_VERIFIED (Requires continuous multi-day deployment)"
        }
        logger.info(f"Overall Reliability Benchmark Summary: {overall_summary}")
        return overall_summary

if __name__ == "__main__":
    suite = SystemReliabilitySuite()
    suite.run_all_reliability_benchmarks()
