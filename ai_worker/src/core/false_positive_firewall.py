import logging
from typing import List, Tuple, Dict, Any
from core.scene_types import SceneProfile, CameraMotionClass
from core.interaction_types import InteractionPair, InteractionState
from core.event_reasoning_types import FirewallDecision

logger = logging.getLogger(__name__)

class FalsePositiveFirewall:
    """
    Independent False Positive Firewall Engine for ASIS-V2.
    Analyzes contradictory patterns (parallel walking, separating tracks, camera shake, short contact)
    and applies deterministic suppression rules to prevent false alarm storms.
    """
    def evaluate_hypothesis(
        self,
        pair: InteractionPair,
        scene_profile: SceneProfile,
        persistence_frames: int
    ) -> Tuple[str, float, List[str]]:
        """
        Evaluates an interaction hypothesis against contradictory patterns.
        Returns (FirewallDecision, contradictory_score, reason_codes).
        """
        reasons = []
        contradiction_score = 0.0

        # Rule 1: Parallel Walking Together Suppression
        if pair.direction_score == 0.0 and pair.relative_velocity < 3.0:
            contradiction_score += 0.60
            reasons.append("SUPPRESS_PARALLEL_WALKING_TOGETHER")

        # Rule 2: Separating Tracks Suppression
        if pair.approach_velocity > 2.0:
            contradiction_score += 0.60
            reasons.append("SUPPRESS_SEPARATING_TRACKS")

        # Rule 3: Camera Motion / Shake / Pan Compensation Suppression
        if scene_profile.global_motion_class in [CameraMotionClass.SHAKE, CameraMotionClass.PAN]:
            contradiction_score += 0.40
            reasons.append("SUPPRESS_CAMERA_GLOBAL_MOTION")

        # Rule 4: Short Accidental Contact (Low Persistence)
        if persistence_frames < 5:
            contradiction_score += 0.30
            reasons.append("HOLD_SHORT_ACCIDENTAL_CONTACT")

        # Rule 5: Normal Crowd Motion (High Density without Converging Trajectory)
        if scene_profile.crowd_density > 0.40 and pair.approach_score < 0.20:
            contradiction_score += 0.40
            reasons.append("SUPPRESS_CROWD_NORMAL_WALKING")

        contradiction_score = round(min(1.0, contradiction_score), 3)

        # Decision Mapping
        if contradiction_score >= 0.60:
            return FirewallDecision.SUPPRESS, contradiction_score, reasons
        elif contradiction_score >= 0.30 or persistence_frames < 5:
            return FirewallDecision.REQUIRE_MORE_EVIDENCE, contradiction_score, reasons
        else:
            return FirewallDecision.PASS, contradiction_score, reasons
