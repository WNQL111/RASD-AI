import logging
from typing import Tuple, Dict, Any
from core.resource_types import GpuHealthState, TaskPriority, QualityLevel, ResourceState

logger = logging.getLogger(__name__)

class ResourceAwareGpuScheduler:
    """
    Resource-Aware GPU Scheduler for ASIS-V2.
    Determines Task Priority, Adaptive Quality Level (L0 -> L5), and Model Selection.
    Enforces VRAM Protection and Model Switch Cooldown Hysteresis (minimum dwell time = 15 frames).
    """
    def __init__(self, switch_cooldown_frames: int = 15):
        self.switch_cooldown_frames = switch_cooldown_frames
        self.last_model_switch_frame = 0
        self.current_quality_level = QualityLevel.L1_FAST_DETECTOR

    def schedule_task_quality(
        self,
        net_evidence_score: float,
        resource_state: ResourceState,
        frame_idx: int
    ) -> Tuple[str, int, str]:
        """
        Schedules quality level, task priority, and recommended model tier.
        Returns (quality_level, priority_score, recommended_model_id).
        """
        health = resource_state.gpu_health

        # 1. Determine Target Quality Level & Priority
        if net_evidence_score >= 0.70:
            target_quality = QualityLevel.L5_CRITICAL_EVIDENCE
            priority = TaskPriority.CRITICAL_EVENT
            rec_model = "yolov8m.pt"
        elif net_evidence_score >= 0.50:
            target_quality = QualityLevel.L3_SELECTIVE_POSE
            priority = TaskPriority.HIGH_RISK_INTERACTION
            rec_model = "yolov8n-pose.pt"
        elif net_evidence_score >= 0.30:
            target_quality = QualityLevel.L2_BALANCED_DETECTOR
            priority = TaskPriority.BALANCED_DETECTION
            rec_model = "yolov8m.pt"
        else:
            target_quality = QualityLevel.L1_FAST_DETECTOR
            priority = TaskPriority.FAST_DETECTION
            rec_model = "yolov8n.pt"

        # 2. Resource-Aware Downgrade under GPU Pressure
        if health in [GpuHealthState.GPU_PRESSURED, GpuHealthState.GPU_CRITICAL]:
            if priority < TaskPriority.CRITICAL_EVENT:
                # Downgrade non-critical tasks to FAST tier under GPU pressure
                target_quality = QualityLevel.L1_FAST_DETECTOR
                rec_model = "yolov8n.pt"
                priority = TaskPriority.FAST_DETECTION

        # 3. Model Switch Cooldown Hysteresis (Minimum 15 frames dwell time)
        if target_quality != self.current_quality_level:
            if (frame_idx - self.last_model_switch_frame) >= self.switch_cooldown_frames or priority >= TaskPriority.CRITICAL_EVENT:
                self.current_quality_level = target_quality
                self.last_model_switch_frame = frame_idx

        return self.current_quality_level, priority, rec_model
