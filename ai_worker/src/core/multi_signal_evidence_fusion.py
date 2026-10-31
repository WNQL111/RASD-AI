import logging
from typing import List, Tuple, Dict
from core.scene_types import SceneProfile
from core.interaction_types import InteractionPair
from core.event_reasoning_types import EventEvidenceVector

logger = logging.getLogger(__name__)

class MultiSignalEvidenceFusionEngine:
    """
    Multi-Signal Evidence Fusion Engine for ASIS-V2.
    Fuses Spatial, Motion, Relative Motion, Interaction, Pose, Joint, Temporal Persistence, and Contradiction signals.
    Calculates net evidence score and produces explainable decision codes.
    """
    def fuse_signals(
        self,
        pair: InteractionPair,
        scene_profile: SceneProfile,
        persistence_frames: int,
        contradiction_score: float,
        contradiction_reasons: List[str]
    ) -> Tuple[EventEvidenceVector, List[str]]:
        """
        Fuses multi-modal signals into an EventEvidenceVector and explainability codes.
        """
        explainability = []

        # 1. Component Signal Scores
        spatial_score = pair.overlap_score
        if spatial_score > 0.3:
            explainability.append(f"SPATIAL_OVERLAP_{spatial_score}")

        motion_score = min(1.0, scene_profile.motion_level / 5.0)
        relative_motion_score = min(1.0, pair.relative_velocity / 8.0)
        if relative_motion_score > 0.4:
            explainability.append(f"HIGH_RELATIVE_VELOCITY_{relative_motion_score}")

        interaction_score = pair.approach_score
        if pair.approach_score > 0.3:
            explainability.append(f"RAPID_APPROACH_{pair.approach_score}")

        pose_score = pair.pose_anomaly_score
        if pose_score > 0.4:
            explainability.append(f"POSE_ANOMALY_SUPPORT_{pose_score}")

        persistence_score = min(1.0, persistence_frames / 15.0)
        if persistence_score > 0.5:
            explainability.append(f"PERSISTENT_INTERACTION_FRAMES_{persistence_frames}")

        # Add contradiction reasons if any
        explainability.extend(contradiction_reasons)

        # 2. Positive Weighted Sum
        positive_sum = (
            (0.20 * spatial_score) +
            (0.15 * motion_score) +
            (0.25 * relative_motion_score) +
            (0.20 * interaction_score) +
            (0.10 * pose_score) +
            (0.10 * persistence_score)
        )

        # 3. Net Evidence Score (Suppressed by contradictory evidence)
        net_score = round(positive_sum * (1.0 - contradiction_score), 3)

        vector = EventEvidenceVector(
            spatial_score=round(spatial_score, 3),
            motion_score=round(motion_score, 3),
            relative_motion_score=round(relative_motion_score, 3),
            interaction_score=round(interaction_score, 3),
            pose_score=round(pose_score, 3),
            joint_score=round(pose_score, 3),
            persistence_score=round(persistence_score, 3),
            contradictory_score=round(contradiction_score, 3),
            net_evidence_score=net_score
        )

        return vector, explainability
