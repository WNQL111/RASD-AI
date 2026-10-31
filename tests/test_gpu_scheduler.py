import sys
import os
import time
import unittest
import numpy as np

# Ensure ai_worker/src is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_worker", "src"))

from core.resource_types import (
    GpuHealthState, TaskPriority, QualityLevel, ResourceState, FrameIngressItem
)
from core.gpu_health_monitor import GpuHealthMonitor
from core.adaptive_frame_sampler import AdaptiveFrameSampler
from core.backpressure_controller import BackpressureController
from core.resource_aware_gpu_scheduler import ResourceAwareGpuScheduler
from core.adaptive_compute_orchestrator import AdaptiveComputeOrchestrator

class TestGpuSchedulerAndBackpressure(unittest.TestCase):
    def setUp(self):
        self.health_monitor = GpuHealthMonitor()
        self.sampler = AdaptiveFrameSampler()
        self.backpressure = BackpressureController(max_queue_size=10, max_age_ms=100.0)
        self.scheduler = ResourceAwareGpuScheduler(switch_cooldown_frames=15)
        self.orchestrator = AdaptiveComputeOrchestrator(max_queue_size=10)

    # Scenario 1: Low Risk -> Low Compute (8 FPS cadence, 1 out of 3 frames)
    def test_01_low_risk_low_compute_sampling(self):
        res_healthy = ResourceState(gpu_health=GpuHealthState.GPU_HEALTHY)
        p0 = self.sampler.should_process_frame(frame_idx=0, net_evidence_score=0.10, resource_state=res_healthy)
        p1 = self.sampler.should_process_frame(frame_idx=1, net_evidence_score=0.10, resource_state=res_healthy)
        p2 = self.sampler.should_process_frame(frame_idx=2, net_evidence_score=0.10, resource_state=res_healthy)

        self.assertTrue(p0)
        self.assertFalse(p1)
        self.assertFalse(p2)

    # Scenario 3: High-Risk Escalation -> Full 25 FPS Cadence & Critical Quality
    def test_02_high_risk_escalation(self):
        res_healthy = ResourceState(gpu_health=GpuHealthState.GPU_HEALTHY)
        p_all = [
            self.sampler.should_process_frame(frame_idx=i, net_evidence_score=0.80, resource_state=res_healthy)
            for i in range(5)
        ]
        self.assertTrue(all(p_all))

        quality, priority, model = self.scheduler.schedule_task_quality(0.80, res_healthy, frame_idx=1)
        self.assertEqual(quality, QualityLevel.L5_CRITICAL_EVIDENCE)
        self.assertEqual(priority, TaskPriority.CRITICAL_EVENT)

    # Scenario 5: GPU Pressure Rises -> Non-Critical Tasks Downgrade
    def test_03_gpu_pressure_downgrades_non_critical_tasks(self):
        res_pressured = ResourceState(gpu_health=GpuHealthState.GPU_PRESSURED)
        quality, priority, model = self.scheduler.schedule_task_quality(0.40, res_pressured, frame_idx=1)

        self.assertEqual(quality, QualityLevel.L1_FAST_DETECTOR)
        self.assertEqual(model, "yolov8n.pt")

    # Scenario 6: Critical Event Under GPU Pressure -> Critical Path Preserved
    def test_04_critical_event_preserved_under_gpu_pressure(self):
        res_critical = ResourceState(gpu_health=GpuHealthState.GPU_CRITICAL)
        quality, priority, model = self.scheduler.schedule_task_quality(0.85, res_critical, frame_idx=1)

        self.assertEqual(quality, QualityLevel.L5_CRITICAL_EVIDENCE)
        self.assertEqual(priority, TaskPriority.CRITICAL_EVENT)

    # Scenario 7: Surge & Backpressure -> Stale Non-Critical Frames Dropped
    def test_05_backpressure_stale_frame_dropping(self):
        # Enqueue stale non-critical frame
        self.backpressure.enqueue_frame(frame_id=1, camera_id="cam1", frame_data=None, is_critical=False)
        time.sleep(0.15) # Age > 100ms

        item = self.backpressure.dequeue_frame()
        self.assertIsNone(item) # Stale frame dropped!
        self.assertGreater(self.backpressure.total_dropped_count, 0)

    # Scenario 7b: Critical Event Evidence NEVER Dropped Even If Stale
    def test_06_critical_evidence_never_dropped(self):
        self.backpressure.enqueue_frame(frame_id=1, camera_id="cam1", frame_data=None, is_critical=True)
        time.sleep(0.15) # Age > 100ms

        item = self.backpressure.dequeue_frame()
        self.assertIsNotNone(item) # Critical frame preserved!
        self.assertEqual(item.frame_id, 1)

    # Model Switch Cooldown Hysteresis Test
    def test_07_model_switch_cooldown_hysteresis(self):
        res_healthy = ResourceState(gpu_health=GpuHealthState.GPU_HEALTHY)

        # Switch to BALANCED on frame 20 (>= 15 cooldown threshold)
        q1, p1, m1 = self.scheduler.schedule_task_quality(0.35, res_healthy, frame_idx=20)
        self.assertEqual(q1, QualityLevel.L2_BALANCED_DETECTOR)

        # Immediate drop to LOW on frame 21 (1 frame later: Cooldown prevents rapid flapping)
        q2, p2, m2 = self.scheduler.schedule_task_quality(0.10, res_healthy, frame_idx=21)
        self.assertEqual(q2, QualityLevel.L2_BALANCED_DETECTOR) # Held by 15-frame dwell cooldown

if __name__ == "__main__":
    unittest.main()
