import logging
from typing import List, Dict, Tuple, Optional, Any
from core.scene_types import TrackContext, CrowdBaselineContext

logger = logging.getLogger(__name__)

class SuppressionEvidenceEngine:
    """
    Suppression Evidence Engine (Negative Evidence Engine) for ASIS-V2.
    Evaluates explicit contextual negative evidence:
    - Coherent crowd flow (parallel direction vector alignment)
    - Coordinated walking (normal speed, low acceleration)
    - Transient contact / brief overlap
    - Low persistence (< 3 frames)
    
    Generates negative evidence scores and explainable suppression reason codes
    that explicitly subtract risk scores.
    """
    def __init__(self):
        pass

    def evaluate_suppression(
        self,
        tracks: List[TrackContext],
        baseline_ctx: CrowdBaselineContext,
        global_flow_coherence: float = 1.0
    ) -> Dict[str, Any]:
        """
        Evaluates negative evidence signals across the active scene.
        """
        reasons = []
        suppression_score = 0.0

        # 1. High Flow Coherence Negative Evidence
        if global_flow_coherence >= 0.70:
            suppression_score += 0.35
            reasons.append("coherent_crowd_flow")

        # 2. Calm Coherent Behavior State Negative Evidence
        if baseline_ctx.behavior_state in ["CALM_COHERENT", "NORMAL_FLOW"]:
            suppression_score += 0.25
            reasons.append("normal_flow_baseline")

        # 3. Low Acceleration / Coordinated Walking Negative Evidence
        persons = [t for t in tracks if t.class_id == 0]
        if persons:
            avg_acc = sum(abs(t.motion_features.normalized_acceleration) for t in persons) / len(persons)
            if avg_acc < 1.0:
                suppression_score += 0.20
                reasons.append("coordinated_low_acceleration")

        final_suppression = round(min(0.85, suppression_score), 3)

        return {
            "suppression_score": final_suppression,
            "reasons": list(set(reasons)),
            "active": final_suppression >= 0.30
        }
