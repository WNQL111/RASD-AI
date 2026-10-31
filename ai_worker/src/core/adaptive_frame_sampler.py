import logging
from core.resource_types import GpuHealthState, ResourceState

logger = logging.getLogger(__name__)

class AdaptiveFrameSampler:
    """
    Adaptive Frame Sampling Controller for ASIS-V2.
    Determines analytical FPS cadence (frame skip factor) dynamically.
    Adjusts cadence based on scene risk level and GPU health pressure.
    """
    def should_process_frame(
        self,
        frame_idx: int,
        net_evidence_score: float,
        resource_state: ResourceState
    ) -> bool:
        """
        Determines whether the current frame should undergo full AI analysis.
        """
        health = resource_state.gpu_health

        # 1. High Risk & Critical Evidence -> ALWAYS process (25 FPS)
        if net_evidence_score >= 0.50:
            return True

        # 2. Under Severe GPU Pressure -> Throttle non-critical frames
        if health == GpuHealthState.GPU_CRITICAL:
            # Process only 1 out of every 5 frames under CRITICAL GPU pressure
            return (frame_idx % 5 == 0)
        elif health == GpuHealthState.GPU_PRESSURED:
            # Process 1 out of every 3 frames under GPU pressure
            return (frame_idx % 3 == 0)

        # 3. Normal / Low Risk Adaptive Cadence
        if net_evidence_score < 0.20:
            # Low Risk -> 8 FPS (1 out of every 3 frames)
            return (frame_idx % 3 == 0)
        elif net_evidence_score < 0.40:
            # Standard -> 12.5 FPS (1 out of every 2 frames)
            return (frame_idx % 2 == 0)
        else:
            # Focused -> 25 FPS
            return True
