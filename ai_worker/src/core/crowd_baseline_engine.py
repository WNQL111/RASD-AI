import math
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional
from core.scene_types import (
    TrackContext, CrowdBaselineContext, WarmupState, CrowdMode, CrowdBehaviorState
)

logger = logging.getLogger(__name__)

class CrowdBaselineEngine:
    """
    Scene-Adaptive Online Crowd Baseline Engine for ASIS-V2.
    Learns normal scene speed (median & MAD), direction dispersion, track persistence,
    and manages warm-up phase (WARMUP -> BASELINE_ESTABLISHED -> NORMAL_MONITORING).
    Uses robust non-parametric statistics to reject outliers and prevent violent anomalies
    from corrupting the baseline.
    """
    def __init__(self, warmup_frames: int = 15, max_history_frames: int = 150):
        self.warmup_frames = warmup_frames
        self.max_history_frames = max_history_frames
        self.frame_count = 0
        self.speed_history: List[float] = []
        self.direction_history: List[float] = []
        
        # Current robust baseline statistics
        self.median_speed: float = 1.5
        self.mad_speed: float = 0.5
        self.dominant_direction_rad: float = 0.0
        self.warmup_state: str = WarmupState.WARMUP

    def update_baseline(
        self,
        tracks: List[TrackContext],
        frame_idx: int,
        critical_evidence: bool = False
    ) -> CrowdBaselineContext:
        """
        Updates baseline statistics using active person tracks.
        """
        self.frame_count += 1
        persons = [t for t in tracks if t.class_id == 0]
        
        # 1. Warmup Lifecycle
        if self.frame_count < self.warmup_frames and not critical_evidence:
            self.warmup_state = WarmupState.WARMUP
        elif self.frame_count < self.warmup_frames + 30:
            self.warmup_state = WarmupState.BASELINE_ESTABLISHED
        else:
            self.warmup_state = WarmupState.NORMAL_MONITORING

        if not persons:
            return CrowdBaselineContext(
                warmup_state=self.warmup_state,
                median_speed=self.median_speed,
                mad_speed=self.mad_speed,
                dominant_flow_vector=[0.0, 0.0],
                flow_coherence=1.0,
                direction_dispersion=0.0
            )

        # 2. Extract Person Speeds & Directions
        current_speeds = [t.motion_features.normalized_velocity for t in persons]
        current_dirs = [t.motion_features.direction_rad for t in persons if t.motion_features.normalized_velocity > 0.3]

        # 3. Robust Statistics (Median & MAD) with Outlier Rejection
        if current_speeds:
            med_sp = float(np.median(current_speeds))
            # Outlier rejection: filter out extreme speed spikes (> 4.0 * median) before updating baseline
            normal_speeds = [s for s in current_speeds if s <= max(3.0, med_sp * 3.0)]
            if normal_speeds:
                self.speed_history.extend(normal_speeds)

        if current_dirs:
            self.direction_history.extend(current_dirs)

        # Maintain bounded history window
        if len(self.speed_history) > self.max_history_frames * 10:
            self.speed_history = self.speed_history[-self.max_history_frames * 5:]
        if len(self.direction_history) > self.max_history_frames * 10:
            self.direction_history = self.direction_history[-self.max_history_frames * 5:]

        # 4. Compute Scene Baseline Statistics
        if self.speed_history:
            self.median_speed = float(np.median(self.speed_history))
            abs_devs = np.abs(np.array(self.speed_history) - self.median_speed)
            self.mad_speed = float(np.median(abs_devs)) if len(abs_devs) > 0 else 0.5
            self.mad_speed = max(0.2, self.mad_speed) # Safety floor

        # 5. Dominant Direction & Dispersion
        flow_vector = [0.0, 0.0]
        dir_dispersion = 0.0
        if current_dirs:
            sin_sum = sum(math.sin(d) for d in current_dirs)
            cos_sum = sum(math.cos(d) for d in current_dirs)
            count = float(len(current_dirs))
            mean_sin = sin_sum / count
            mean_cos = cos_sum / count
            flow_vector = [round(mean_cos, 3), round(mean_sin, 3)]
            mean_len = math.hypot(mean_sin, mean_cos)
            dir_dispersion = round(1.0 - mean_len, 3) # 0 = all parallel, 1 = uniform circular dispersion

        # 6. Crowd Mode & Behavior State Classification
        p_count = len(persons)
        if p_count >= 15:
            crowd_mode = CrowdMode.EXTREME_CROWD if p_count >= 40 else CrowdMode.CROWD_MODE
        else:
            crowd_mode = CrowdMode.NORMAL

        behavior_state = CrowdBehaviorState.NORMAL_FLOW
        if dir_dispersion < 0.25:
            behavior_state = CrowdBehaviorState.CALM_COHERENT
        elif dir_dispersion > 0.65:
            behavior_state = CrowdBehaviorState.MIXED_FLOW
        elif crowd_mode != CrowdMode.NORMAL:
            behavior_state = CrowdBehaviorState.DENSE_STABLE

        return CrowdBaselineContext(
            warmup_state=self.warmup_state,
            crowd_mode=crowd_mode,
            behavior_state=behavior_state,
            median_speed=round(self.median_speed, 2),
            mad_speed=round(self.mad_speed, 2),
            dominant_flow_vector=flow_vector,
            flow_coherence=round(1.0 - dir_dispersion, 3),
            direction_dispersion=dir_dispersion
        )
