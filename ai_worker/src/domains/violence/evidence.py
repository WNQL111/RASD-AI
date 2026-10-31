import math
from typing import List, Tuple, Dict, Any, Optional

class ViolenceEvidenceResult(tuple):
    def __new__(cls, final_confidence, suppression_discount, reasons, explainability=None):
        return super().__new__(cls, (final_confidence, suppression_discount, reasons))

    def __init__(self, final_confidence, suppression_discount, reasons, explainability=None):
        self.final_confidence = final_confidence
        self.suppression_discount = suppression_discount
        self.reasons = reasons
        self.explainability = explainability or {}
        self.breakdown = self.explainability

class ViolenceEvidenceEvaluator:
    def __init__(self, rule_engine: Any = None):
        self.rule_engine = rule_engine

    def evaluate(self, p1: Any, p2: Any, crowd_features: Any = None, pose1: Any = None, pose2: Any = None, verifier_3d: Any = None, frame_idx: int = 0, video_id: str = "video"):
        score_3d = 0.0
        meta_3d = {}
        if verifier_3d is not None:
            score_3d, meta_3d = verifier_3d.verify_candidate_action(
                stream_id=video_id,
                domain="violence",
                bboxes=[p1.bbox, p2.bbox],
                current_frame_idx=frame_idx
            )
        pose_data = None
        if pose1 or pose2:
            pose_data = {"raised_arms": True}
        res = self.evaluate_pair_evidence(p1, p2, crowd_features=crowd_features, pose_data=pose_data, score_3d=score_3d)
        explain = {
            "E_2d": res.explainability.get("evidence_2d", 0.0),
            "E_pose": res.explainability.get("evidence_pose", 0.0),
            "E_3d": res.explainability.get("evidence_3d", 0.0),
            "E_crowd_discount": res.explainability.get("crowd_suppression", 0.0),
            "final_confidence": res.final_confidence
        }
        return res.final_confidence, res.suppression_discount > 0.3, res.reasons, explain

    @staticmethod
    def evaluate_pair_evidence(
        p1: Any,
        p2: Any,
        crowd_coherence: float = 0.0,
        crowd_features: Any = None,
        pose_data: Optional[Dict[str, Any]] = None,
        score_3d: float = 0.0
    ) -> ViolenceEvidenceResult:
        reasons = []
        
        if crowd_features is not None:
            if isinstance(crowd_features, dict):
                crowd_coherence = crowd_features.get('coherence', crowd_coherence)
            elif hasattr(crowd_features, 'coherence'):
                crowd_coherence = getattr(crowd_features, 'coherence', crowd_coherence) or crowd_coherence
        
        c1 = p1.get_center() if hasattr(p1, 'get_center') else ((p1.bbox[0]+p1.bbox[2])/2, (p1.bbox[1]+p1.bbox[3])/2)
        c2 = p2.get_center() if hasattr(p2, 'get_center') else ((p2.bbox[0]+p2.bbox[2])/2, (p2.bbox[1]+p2.bbox[3])/2)
        dist = math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)
        
        v1 = getattr(p1, 'velocity', 0.0) or 0.0
        v2 = getattr(p2, 'velocity', 0.0) or 0.0
        a1 = getattr(p1, 'acceleration', 0.0) or 0.0
        a2 = getattr(p2, 'acceleration', 0.0) or 0.0
        
        # 1. 2D Kinematics Evidence (E_2D)
        score_2d = 0.0
        if dist < 150.0:
            score_2d += 0.20
            reasons.append("CLOSE_SPATIAL_PROXIMITY")
            
        if (v1 > 6.0 or v2 > 6.0):
            score_2d += 0.35
            reasons.append("HIGH_VELOCITY_CHARGE")
        elif (v1 > 3.0 or v2 > 3.0):
            score_2d += 0.15
            reasons.append("MODERATE_APPROACH_SPEED")
            
        if (a1 > 12.0 or a2 > 12.0):
            score_2d += 0.25
            reasons.append("ABRUPT_ACCELERATION_SPIKE")
            
        # 2. Pose Kinematics Evidence (E_pose)
        score_pose = 0.0
        if pose_data and pose_data.get("strike_motion_detected"):
            score_pose = 0.30
            reasons.append("BODY_POSE_STRIKE_MOTION")
        elif pose_data and pose_data.get("raised_arms"):
            score_pose = 0.15
            reasons.append("AGGRESSIVE_ARM_POSTURE")
            
        # 3. 3D Spatio-Temporal Action Evidence (E_3D)
        score_3d_component = 0.0
        if score_3d >= 0.65:
            score_3d_component = 0.30 * score_3d
            reasons.append("SPATIOTEMPORAL_3D_ACTION_ACTIVATION")
        elif score_3d >= 0.45:
            score_3d_component = 0.15 * score_3d
            
        # 4. Crowd Coherence Suppression Discount (E_crowd_suppression)
        suppression_discount = 0.0
        if crowd_coherence > 0.70:
            suppression_discount = 0.40 * crowd_coherence
            reasons.append("CROWD_COHERENCE_FLOW_DISCOUNT")
            
        # Anti-false-positive: Proximity alone without movement
        if v1 < 1.0 and v2 < 1.0 and a1 < 2.0 and a2 < 2.0 and score_pose == 0.0 and score_3d < 0.40:
            score_2d = min(score_2d, 0.20)
            
        total_raw = score_2d + score_pose + score_3d_component
        final_confidence = min(0.99, max(0.0, total_raw - suppression_discount))
        
        breakdown = {
            "evidence_2d": round(score_2d, 3),
            "evidence_pose": round(score_pose, 3),
            "evidence_3d": round(score_3d, 3),
            "crowd_suppression": round(suppression_discount, 3),
            "final_confidence": round(final_confidence, 3)
        }
        
        return ViolenceEvidenceResult(
            final_confidence=round(final_confidence, 3),
            suppression_discount=round(suppression_discount, 3),
            reasons=reasons,
            explainability=breakdown
        )
