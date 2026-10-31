import logging
from typing import Dict, Tuple
from core.interaction_types import InteractionPair, InteractionState

logger = logging.getLogger(__name__)

class ApproachSeparationEngine:
    """
    Approach & Separation Engine for ASIS-V2.
    Tracks distance rate of change between track pairs across frames.
    Distinguishes rapid approach (closing distance) from separation (opening distance).
    """
    def __init__(self):
        self.prev_distances: Dict[Tuple[int, int], float] = {}

    def analyze_approach_separation(
        self,
        pair: InteractionPair,
        dt_frames: int = 1
    ) -> InteractionPair:
        """
        Updates pair with approach_velocity and approach_score.
        """
        dt = max(1, dt_frames)
        pair_key = (pair.track_id_a, pair.track_id_b)
        prev_dist = self.prev_distances.get(pair_key)

        if prev_dist is not None:
            # Velocity = delta_distance / dt (px per frame)
            # Negative -> distance decreasing (approaching)
            # Positive -> distance increasing (separating)
            raw_app_vel = (pair.center_distance_px - prev_dist) / float(dt)
            pair.approach_velocity = round(raw_app_vel, 2)

            if raw_app_vel < -2.0:
                # Approaching fast
                pair.approach_score = round(min(1.0, abs(raw_app_vel) / 12.0), 3)
                if pair.interaction_state not in [InteractionState.HIGH_RISK_INTERACTION, InteractionState.EVENT_CANDIDATE]:
                    pair.interaction_state = InteractionState.APPROACHING
            elif raw_app_vel > 2.0:
                # Separating
                pair.approach_score = 0.0
                pair.interaction_state = InteractionState.SEPARATING
            else:
                pair.approach_score = round(max(0.0, pair.approach_score - 0.1), 3)

        self.prev_distances[pair_key] = pair.center_distance_px
        return pair

    def prune_stale_pairs(self, active_pair_keys: set):
        stale = [k for k in self.prev_distances if k not in active_pair_keys]
        for k in stale:
            self.prev_distances.pop(k, None)
