import math
import logging
from core.scene_types import TrackContext
from core.interaction_types import InteractionPair

logger = logging.getLogger(__name__)

class DirectionAnalysisEngine:
    """
    Direction & Heading Analysis Engine for ASIS-V2.
    Evaluates vector direction similarity/opposition (Cosine Similarity) between track pairs.
    Distinguishes parallel walking (low risk) from head-on converging trajectories (high interaction candidate).
    """
    def analyze_directions(
        self,
        pair: InteractionPair,
        track_a: TrackContext,
        track_b: TrackContext
    ) -> InteractionPair:
        """
        Updates pair with direction_score and relative_velocity.
        """
        dir_a = track_a.motion_features.direction_rad
        dir_b = track_b.motion_features.direction_rad

        vel_a = track_a.motion_features.normalized_velocity
        vel_b = track_b.motion_features.normalized_velocity

        # Relative velocity magnitude
        vx_a, vy_a = vel_a * math.cos(dir_a), vel_a * math.sin(dir_a)
        vx_b, vy_b = vel_b * math.cos(dir_b), vel_b * math.sin(dir_b)

        rel_vx = vx_a - vx_b
        rel_vy = vy_a - vy_b
        rel_vel = math.hypot(rel_vx, rel_vy)
        pair.relative_velocity = round(rel_vel, 2)

        # Cosine Similarity between heading vectors
        if vel_a > 0.1 and vel_b > 0.1:
            cos_sim = (vx_a * vx_b + vy_a * vy_b) / (vel_a * vel_b)
            # Head-on converging: cos_sim close to -1.0
            # Parallel walking together: cos_sim close to +1.0
            if cos_sim < -0.5:
                # Opposing directions (converging candidate)
                pair.direction_score = round(min(1.0, abs(cos_sim)), 3)
            elif cos_sim > 0.5:
                # Parallel walking together (suppresses false violence alarms!)
                pair.direction_score = 0.0
            else:
                # Crossing trajectory
                pair.direction_score = 0.2
        else:
            pair.direction_score = 0.0

        return pair
