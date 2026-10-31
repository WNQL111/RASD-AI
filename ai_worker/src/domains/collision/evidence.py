import math
from typing import List, Tuple, Dict, Any, Optional
from .contracts import CollisionCandidateDTO, CollisionEvidenceDTO, CollisionType
from .config import CollisionConfig

class CollisionEvidenceEvaluator:
    def __init__(self, config: CollisionConfig):
        self.config = config

    def evaluate_evidence(
        self,
        candidate: CollisionCandidateDTO,
        track_1: Any = None,
        track_2: Any = None,
        obj1: Any = None,
        obj2: Any = None,
        crowd_features: Optional[Dict[str, Any]] = None,
        camera_context: Optional[Dict[str, Any]] = None,
        score_3d: float = 0.0,
        **kwargs
    ) -> CollisionEvidenceDTO:
        t1 = track_1 or obj1
        t2 = track_2 or obj2
        reason_codes: List[str] = []
        approach_evidence = 0.0
        overlap_evidence = 0.0
        deceleration_evidence = 0.0
        deviation_evidence = 0.0
        post_impact_evidence = 0.0
        suppression_discount = 0.0

        v1 = getattr(t1, 'velocity', 0.0) or 0.0
        v2 = getattr(t2, 'velocity', 0.0) or 0.0
        a1 = getattr(t1, 'acceleration', 0.0) or 0.0
        a2 = getattr(t2, 'acceleration', 0.0) or 0.0

        # Max velocity in recent history
        h1_vels = [math.sqrt((t1.history[k][1][0]-t1.history[k-1][1][0])**2 + (t1.history[k][1][1]-t1.history[k-1][1][1])**2) for k in range(1, len(t1.history))] if hasattr(t1, 'history') and len(t1.history) >= 2 else [v1]
        h2_vels = [math.sqrt((t2.history[k][1][0]-t2.history[k-1][1][0])**2 + (t2.history[k][1][1]-t2.history[k-1][1][1])**2) for k in range(1, len(t2.history))] if hasattr(t2, 'history') and len(t2.history) >= 2 else [v2]
        max_v1 = max(h1_vels[-15:]) if h1_vels else v1
        max_v2 = max(h2_vels[-15:]) if h2_vels else v2

        dist = candidate.spatial_distance
        ground_dist = candidate.ground_distance
        iou = candidate.iou_overlap
        approach_rate = candidate.approach_rate  # Positive = converging
        cosine_sim = candidate.cosine_similarity
        is_ped = (candidate.collision_type == CollisionType.VEHICLE_PEDESTRIAN or candidate.collision_type == CollisionType.PEDESTRIAN_VEHICLE)

        # 1. Contact Zone Check
        in_contact_zone = False
        if not is_ped and (dist < self.config.VEHICLE_VEHICLE_PROXIMITY_THRESH or iou > self.config.IOU_OVERLAP_THRESH):
            in_contact_zone = True
        elif is_ped and (ground_dist < self.config.GROUND_DISTANCE_THRESH or dist < self.config.VEHICLE_PEDESTRIAN_PROXIMITY_THRESH or iou > self.config.IOU_OVERLAP_THRESH):
            in_contact_zone = True

        if not in_contact_zone:
            return CollisionEvidenceDTO(
                pair_key=candidate.pair_key,
                collision_type=candidate.collision_type,
                base_score=0.0,
                approach_evidence=0.0,
                overlap_evidence=0.0,
                deceleration_evidence=0.0,
                deviation_evidence=0.0,
                post_impact_evidence=0.0,
                track_reliability_score=1.0,
                suppression_discount=0.0,
                final_confidence=0.0,
                evidence_score=0.0,
                score_3d=round(score_3d, 3),
                reason_codes=[],
                explainability={}
            )

        # 2. Suppression Rules
        if not is_ped and max_v1 < 0.5 and max_v2 < 0.5 and len(getattr(t1, 'history', [])) > 15 and len(getattr(t2, 'history', [])) > 15:
            reason_codes.append('STATIONARY_PARKED_VEHICLE_SUPPRESSION')
            suppression_discount += 0.40

        if is_ped and max_v1 < 0.5 and len(getattr(t1, 'history', [])) > 15:
            reason_codes.append('PEDESTRIAN_NEAR_PARKED_VEHICLE_SUPPRESSION')
            suppression_discount += 0.40

        if not is_ped and cosine_sim > self.config.PARALLEL_COSINE_SIMILARITY and candidate.relative_speed < 1.0 and approach_rate <= 0.1:
            reason_codes.append('PARALLEL_TRAFFIC_FLOW_SUPPRESSION')
            suppression_discount += 0.35

        if camera_context:
            cam_motion = camera_context.get('camera_motion_type')
            cam_mag = camera_context.get('camera_motion_magnitude', 0.0)
            if cam_motion == 'SHAKE' or cam_mag > 5.0:
                suppression_discount += 0.35
                reason_codes.append('CAMERA_MOTION_COMPENSATION_DISCOUNT')

        # 3. Approach & Convergence Signals
        if approach_rate >= self.config.RAPID_APPROACH_RATE_THRESH:
            approach_evidence = min(0.35, 0.20 + (approach_rate / 15.0) * 0.15)
            reason_codes.append('RAPID_CONVERGING_APPROACH')
        elif approach_rate >= 0.5:
            approach_evidence = 0.18
            reason_codes.append('MODERATE_APPROACH')
        elif approach_rate >= 0.1:
            approach_evidence = 0.10

        # 4. Overlap & Proximity Signals
        if iou >= 0.03:
            overlap_evidence = min(0.40, 0.28 + (iou / 0.15) * 0.12)
            reason_codes.append('SPATIAL_BBOX_IOU_OVERLAP')
        elif iou > self.config.IOU_OVERLAP_THRESH:
            overlap_evidence = 0.26
            reason_codes.append('BBOX_TOUCH_CONTACT')
        elif dist < 85.0:
            prox_factor = max(0.0, (85.0 - dist) / 85.0)
            overlap_evidence = 0.18 + prox_factor * 0.10
            reason_codes.append('CLOSE_PROXIMITY_CONTACT')
        else:
            overlap_evidence = 0.12

        # 5. Deceleration & Kinetic Signals
        min_a = min(a1, a2)
        if min_a < -self.config.DECELERATION_SPIKE_THRESH:
            deceleration_evidence = min(0.35, 0.20 + (abs(min_a) / 8.0) * 0.15)
            reason_codes.append('ABRUPT_IMPACT_DECELERATION_SPIKE')
        elif (max_v1 > self.config.MIN_PRE_IMPACT_SPEED or max_v2 > self.config.MIN_PRE_IMPACT_SPEED) and (v1 < 0.8 or v2 < 0.8):
            deceleration_evidence = 0.20
            reason_codes.append('POST_IMPACT_VELOCITY_HALT')
        elif min_a < -0.8:
            deceleration_evidence = 0.12
            reason_codes.append('MODERATE_BRAKING_DECELERATION')

        # 6. Vehicle-Pedestrian Interaction Bonus
        if is_ped and max_v1 > self.config.MIN_PRE_IMPACT_SPEED:
            reason_codes.append('VEHICLE_PEDESTRIAN_IMPACT_ZONE')
            overlap_evidence = max(overlap_evidence, 0.30)

        # 7. 3D Spatio-Temporal Action Activation
        score_3d_component = 0.0
        if score_3d >= 0.60:
            score_3d_component = 0.25 * score_3d
            reason_codes.append('3D_SPATIOTEMPORAL_COLLISION_PATTERN')
        elif score_3d >= 0.40:
            score_3d_component = 0.12 * score_3d
        else:
            score_3d_component = 0.08

        base_score = approach_evidence + overlap_evidence + deceleration_evidence + score_3d_component
        final_conf = max(0.0, min(0.99, base_score - suppression_discount))

        return CollisionEvidenceDTO(
            pair_key=candidate.pair_key,
            collision_type=candidate.collision_type,
            base_score=round(base_score, 3),
            approach_evidence=round(approach_evidence, 3),
            overlap_evidence=round(overlap_evidence, 3),
            deceleration_evidence=round(deceleration_evidence, 3),
            deviation_evidence=round(deviation_evidence, 3),
            post_impact_evidence=round(post_impact_evidence, 3),
            track_reliability_score=1.0,
            suppression_discount=round(suppression_discount, 3),
            final_confidence=round(final_conf, 3),
            evidence_score=round(final_conf, 3),
            score_3d=round(score_3d, 3),
            quality='HIGH',
            reason_codes=reason_codes,
            explainability={
                "approach_evidence": round(approach_evidence, 3),
                "overlap_evidence": round(overlap_evidence, 3),
                "deceleration_evidence": round(deceleration_evidence, 3),
                "evidence_3d": round(score_3d, 3),
                "suppression_discount": round(suppression_discount, 3),
                "total_evidence": round(final_conf, 3)
            }
        )
