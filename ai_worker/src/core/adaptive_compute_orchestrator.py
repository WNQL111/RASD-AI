import logging
from typing import Tuple, Optional
from core.resource_types import ResourceState, QualityLevel
from core.gpu_health_monitor import GpuHealthMonitor
from core.adaptive_frame_sampler import AdaptiveFrameSampler
from core.backpressure_controller import BackpressureController
from core.resource_aware_gpu_scheduler import ResourceAwareGpuScheduler

logger = logging.getLogger(__name__)

class AdaptiveComputeOrchestrator:
    """
    Master Adaptive Compute Orchestrator for ASIS-V2.
    Integrates GPU Health Monitor, Adaptive Frame Sampler, Backpressure Controller, and GPU Scheduler.
    Executes Minimum Compute for Maximum Necessary Evidence policy.
    """
    def __init__(self, max_queue_size: int = 30):
        self.health_monitor = GpuHealthMonitor()
        self.frame_sampler = AdaptiveFrameSampler()
        self.backpressure = BackpressureController(max_queue_size=max_queue_size)
        self.scheduler = ResourceAwareGpuScheduler()

    def evaluate_compute_budget(
        self,
        frame_idx: int,
        net_evidence_score: float
    ) -> Tuple[bool, ResourceState, str, str]:
        """
        Evaluates current resource state and returns (should_process, resource_state, quality_level, recommended_model).
        """
        # 1. Sample GPU Health State
        res_state = self.health_monitor.sample_resource_state(
            current_queue_depth=self.backpressure.get_queue_depth(),
            dropped_count=self.backpressure.total_dropped_count
        )

        # 2. Evaluate Adaptive Frame Sampling
        should_process = self.frame_sampler.should_process_frame(frame_idx, net_evidence_score, res_state)

        if not should_process:
            return False, res_state, QualityLevel.L0_CHEAP_SCENE, "yolov8n.pt"

        # 3. Schedule Quality Ladder and Model Tier
        quality_level, priority, rec_model = self.scheduler.schedule_task_quality(
            net_evidence_score, res_state, frame_idx
        )

        return True, res_state, quality_level, rec_model
