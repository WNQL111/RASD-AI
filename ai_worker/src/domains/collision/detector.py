import os
import json
import time
import uuid
import math
import logging
from typing import List, Dict, Any, Optional, Tuple

from .config import CollisionConfig
from .contracts import (
    CollisionType,
    CollisionState,
    CollisionCandidateDTO,
    CollisionEvidenceDTO,
    CollisionDecisionDTO
)
from .evidence import CollisionEvidenceEvaluator
from .temporal import CollisionTemporalTracker
from .decision import CollisionDecisionEngine

logger = logging.getLogger(__name__)

def euclidean_dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def compute_iou(b1: List[float], b2: List[float]) -> float:
    xA = max(b1[0], b2[0])
    yA = max(b1[1], b2[1])
    xB = min(b1[2], b2[2])
    yB = min(b1[3], b2[3])
    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    boxAArea = max(1.0, (b1[2] - b1[0]) * (b1[3] - b1[1]))
    boxBArea = max(1.0, (b2[2] - b2[0]) * (b2[3] - b2[1]))
    return interArea / float(boxAArea + boxBArea - interArea)

class CollisionDomainDetector:
    def __init__(self, rule_engine: Any = None, config: Optional[CollisionConfig] = None):
        self.rule_engine = rule_engine
        self.config = config or CollisionConfig()
        self.evidence_evaluator = CollisionEvidenceEvaluator(self.config)
        self.temporal_tracker = CollisionTemporalTracker(self.config)
        self.decision_engine = CollisionDecisionEngine(self.config)
        self.last_alert_frame: Dict[Tuple[int, int], int] = {}
        self.alert_cooldown_frames: int = 75  # Alert throttled to 1 event every 2.5 - 3.0s per track pair
        self.global_last_alert_frame: int = -999999
        self.global_alert_cooldown_frames: int = 50  # Global minimum 2.0s spacing between alerts
        self.pair_3d_cache: Dict[Tuple[int, int], Tuple[int, float]] = {}

    def _get_spatial_candidates(self, objects: Dict[int, Any]) -> List[CollisionCandidateDTO]:
        candidates: List[CollisionCandidateDTO] = []
        vehicles: Dict[int, Any] = {}
        pedestrians: Dict[int, Any] = {}

        for tid, obj in objects.items():
            if getattr(obj, 'lost_state', False):
                continue
            cid = getattr(obj, 'class_id', 0)
            if cid in self.config.VEHICLE_CLASS_IDS:
                vehicles[tid] = obj
            elif cid in self.config.PEDESTRIAN_CLASS_IDS:
                pedestrians[tid] = obj

        if not vehicles:
            return candidates

        # 1. Vehicle-Vehicle Interactions
        v_ids = list(vehicles.keys())
        for i in range(len(v_ids)):
            for j in range(i + 1, len(v_ids)):
                id1, id2 = v_ids[i], v_ids[j]
                v1, v2 = vehicles[id1], vehicles[id2]
                c1 = v1.get_center()
                c2 = v2.get_center()
                dist = euclidean_dist(c1, c2)
                iou = compute_iou(v1.bbox, v2.bbox)

                if dist < self.config.VEHICLE_VEHICLE_PROXIMITY_THRESH or iou > self.config.IOU_OVERLAP_THRESH:
                    approach_rate = 0.0
                    cosine_sim = 1.0
                    rel_speed = abs(getattr(v1, 'velocity', 0.0) - getattr(v2, 'velocity', 0.0))

                    if len(getattr(v1, 'history', [])) >= 2 and len(getattr(v2, 'history', [])) >= 2:
                        p1_prev = ((v1.history[-2][1][0] + v1.history[-2][1][2])/2.0, (v1.history[-2][1][1] + v1.history[-2][1][3])/2.0)
                        p2_prev = ((v2.history[-2][1][0] + v2.history[-2][1][2])/2.0, (v2.history[-2][1][1] + v2.history[-2][1][3])/2.0)
                        prev_dist = euclidean_dist(p1_prev, p2_prev)
                        approach_rate = prev_dist - dist  # Positive when converging

                    candidates.append(CollisionCandidateDTO(
                        pair_key=(min(id1, id2), max(id1, id2)),
                        collision_type=CollisionType.VEHICLE_VEHICLE,
                        track_id_1=id1,
                        track_id_2=id2,
                        class_id_1=getattr(v1, 'class_id', 2),
                        class_id_2=getattr(v2, 'class_id', 2),
                        relative_speed=rel_speed,
                        approach_rate=approach_rate,
                        cosine_similarity=cosine_sim,
                        iou_overlap=iou,
                        ground_distance=dist,
                        spatial_distance=dist,
                        timestamp=0.0
                    ))

        # 2. Vehicle-Pedestrian Interactions
        for vid, v in vehicles.items():
            for pid, p in pedestrians.items():
                c_v = v.get_center()
                c_p = p.get_center()
                dist = euclidean_dist(c_v, c_p)
                iou = compute_iou(v.bbox, p.bbox)
                g_v = ((v.bbox[0] + v.bbox[2])/2.0, v.bbox[3])
                g_p = ((p.bbox[0] + p.bbox[2])/2.0, p.bbox[3])
                ground_d = euclidean_dist(g_v, g_p)

                if dist < self.config.VEHICLE_PEDESTRIAN_PROXIMITY_THRESH or ground_d < self.config.GROUND_DISTANCE_THRESH or iou > self.config.IOU_OVERLAP_THRESH:
                    approach_rate = 0.0
                    if len(getattr(v, 'history', [])) >= 2 and len(getattr(p, 'history', [])) >= 2:
                        pv = ((v.history[-2][1][0] + v.history[-2][1][2])/2.0, (v.history[-2][1][1] + v.history[-2][1][3])/2.0)
                        pp = ((p.history[-2][1][0] + p.history[-2][1][2])/2.0, (p.history[-2][1][1] + p.history[-2][1][3])/2.0)
                        prev_dist = euclidean_dist(pv, pp)
                        approach_rate = prev_dist - dist  # Positive when converging

                    candidates.append(CollisionCandidateDTO(
                        pair_key=(min(vid, pid), max(vid, pid)),
                        collision_type=CollisionType.VEHICLE_PEDESTRIAN,
                        track_id_1=vid,
                        track_id_2=pid,
                        class_id_1=getattr(v, 'class_id', 2),
                        class_id_2=getattr(p, 'class_id', 0),
                        relative_speed=abs(getattr(v, 'velocity', 0.0) - getattr(p, 'velocity', 0.0)),
                        approach_rate=approach_rate,
                        cosine_similarity=1.0,
                        iou_overlap=iou,
                        ground_distance=ground_d,
                        spatial_distance=dist,
                        timestamp=0.0
                    ))

        return candidates

    def analyze(self, *args, **kwargs):
        return self.process_frame(*args, **kwargs)

    def process_frame(
        self,
        memory: Any,
        frame_idx: int,
        video_id: str,
        crowd_features: Optional[Dict[str, Any]] = None,
        camera_context: Optional[Dict[str, Any]] = None,
        verifier_3d: Any = None
    ) -> List[Dict[str, Any]]:
        candidates = self._get_spatial_candidates(memory.objects)
        events = []

        for candidate in candidates:
            id1, id2 = candidate.pair_key
            if id1 not in memory.objects or id2 not in memory.objects:
                continue

            obj1 = memory.objects[id1]
            obj2 = memory.objects[id2]

            # Fast preliminary 2D evidence evaluation
            evidence_dto = self.evidence_evaluator.evaluate_evidence(
                candidate=candidate,
                obj1=obj1,
                obj2=obj2,
                crowd_features=crowd_features,
                camera_context=camera_context,
                score_3d=0.0
            )

            # Candidate-Gated 3D Verification with 6-frame temporal stride cache
            score_3d = 0.0
            meta_3d = {}
            last_f, last_s = self.pair_3d_cache.get(candidate.pair_key, (-999, 0.0))
            if verifier_3d is not None and (getattr(evidence_dto, "evidence_score", 0.0) >= 0.35 or candidate.iou_overlap > 0.05):
                if (frame_idx - last_f) >= 6:
                    score_3d, meta_3d = verifier_3d.verify_candidate_action(
                        stream_id=video_id,
                        domain="collision",
                        bboxes=[obj1.bbox, obj2.bbox],
                        current_frame_idx=frame_idx
                    )
                    self.pair_3d_cache[candidate.pair_key] = (frame_idx, score_3d)
                else:
                    score_3d = last_s

                # Re-evaluate evidence with 3D score fused
                evidence_dto = self.evidence_evaluator.evaluate_evidence(
                    candidate=candidate,
                    obj1=obj1,
                    obj2=obj2,
                    crowd_features=crowd_features,
                    camera_context=camera_context,
                    score_3d=score_3d
                )

            decision_dto = self.temporal_tracker.update(
                pair_key=candidate.pair_key,
                evidence=evidence_dto,
                frame_idx=frame_idx,
                timestamp=time.time()
            )

            if decision_dto.state == CollisionState.CONFIRMED and decision_dto.confidence >= 0.45:
                last_pair_frame = self.last_alert_frame.get(candidate.pair_key, -999999)
                is_pair_ready = (frame_idx - last_pair_frame) >= self.alert_cooldown_frames
                is_global_ready = (frame_idx - self.global_last_alert_frame) >= self.global_alert_cooldown_frames
                if is_pair_ready and is_global_ready:
                    self.last_alert_frame[candidate.pair_key] = frame_idx
                    self.global_last_alert_frame = frame_idx
                    episode_uuid = decision_dto.episode_id or decision_dto.event_id or str(uuid.uuid4())
                    ev_dict = {
                        'id': episode_uuid,
                        'type': 'accident',
                        'event_type': 'accident',
                        'event_category': 'COLLISION',
                        'confidence': decision_dto.confidence,
                        'risk_score': round(decision_dto.confidence * 100.0, 1),
                        'start_frame': max(0, frame_idx - decision_dto.persistence_count),
                        'end_frame': frame_idx,
                        'involved_tracks': list(candidate.pair_key),
                        'affected_persons': [id1, id2],
                        'bboxes': [obj1.bbox, obj2.bbox],
                        'details': f'{candidate.collision_type.value} incident detected between #{id1} and #{id2}',
                        'video_id': video_id,
                        'reasons': decision_dto.reason_codes,
                        'explainability': {
                            "evidence_2d": evidence_dto.approach_evidence + evidence_dto.overlap_evidence + evidence_dto.deceleration_evidence,
                            "evidence_3d": score_3d,
                            "persistence_frames": decision_dto.persistence_count,
                            "collision_type": candidate.collision_type.value,
                            "3d_meta": meta_3d
                        },
                        'snapshot_path': f'/videos/snapshots/{episode_uuid}.jpg',
                        'timestamp': time.time()
                    }
                    events.append(ev_dict)

        return events

CollisionDetector = CollisionDomainDetector
