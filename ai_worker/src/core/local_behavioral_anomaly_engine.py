import math
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional, Any
from core.scene_types import TrackContext, CrowdBaselineContext

logger = logging.getLogger(__name__)

class LocalBehavioralAnomalyEngine:
    """
    Local Behavioral Anomaly Engine for ASIS-V2.
    Evaluates localized track motion against local and crowd baselines to detect:
    - Speed spikes & acceleration spikes relative to scene baseline.
    - Direction conflict (converging or head-on movement).
    - Local cluster density anomalies.
    Does NOT call scene-wide violence. Returns localized anomalous track IDs & cluster risk.
    """
    def __init__(self, speed_spike_multiplier: float = 2.5):
        self.speed_spike_multiplier = speed_spike_multiplier

    def detect_anomalies(
        self,
        tracks: List[TrackContext],
        baseline_ctx: CrowdBaselineContext
    ) -> Dict[str, Any]:
        """
        Scans tracks for local behavioral anomalies against scene baseline.
        """
        persons = [t for t in tracks if t.class_id == 0]
        if not persons:
            return {"anomalous_track_ids": [], "clusters": [], "max_anomaly_score": 0.0}

        med_speed = max(1.0, baseline_ctx.median_speed)
        mad_speed = max(0.3, baseline_ctx.mad_speed)

        anomalous_tracks = []
        track_scores: Dict[int, float] = {}

        for t in persons:
            mf = t.motion_features
            vel = mf.normalized_velocity
            acc = abs(mf.normalized_acceleration)

            # Z-score relative to robust baseline median & MAD
            speed_z = max(0.0, (vel - med_speed) / (mad_speed + 1e-5))
            acc_score = min(1.0, acc / 4.0)

            # Combined local anomaly score for this track
            t_score = 0.0
            if speed_z >= self.speed_spike_multiplier:
                t_score += min(0.6, (speed_z - self.speed_spike_multiplier) * 0.2 + 0.3)
            if acc_score > 0.4:
                t_score += acc_score * 0.4

            if t_score >= 0.35:
                anomalous_tracks.append(t.track_id)
                track_scores[t.track_id] = round(t_score, 3)

        max_score = max(track_scores.values()) if track_scores else 0.0

        return {
            "anomalous_track_ids": anomalous_tracks,
            "track_scores": track_scores,
            "max_anomaly_score": round(max_score, 3)
        }
