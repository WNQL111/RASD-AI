# Violence Domain Primary Detector Engine
import math
import uuid
import time
import os
import json
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional
from .config import ViolenceDomainConfig
from .evidence import ViolenceEvidenceEvaluator
from .temporal import ViolenceTemporalTracker
from .decision import ViolenceDecisionEngine

class ViolenceDomainDetector:
    def __init__(self, rule_engine: Any = None, trace_file: Optional[str] = None):
        self.config = ViolenceDomainConfig()
        self.temporal_tracker = ViolenceTemporalTracker(self.config.violence_duration_thresh)
        self.rule_engine = rule_engine
        self.trace_file = trace_file or os.environ.get('VIOLENCE_TRACE_FILE')
        self.trace_enabled = os.environ.get('VIOLENCE_TRACE_ENABLED', 'false').lower() == 'true' or self.trace_file is not None
        self.stats = {
            'pairs_materialized': 0,
            'candidates_generated': 0,
            'pairs_rejected_spatially': 0
        }
        self.last_alert_frame: Dict[Tuple[int, int], int] = {}
        self.alert_cooldown_frames: int = 75  # Alert throttled to 1 event every 2.5 - 3.0s per track pair
        self.global_last_alert_frame: int = -999999
        self.global_alert_cooldown_frames: int = 50  # Global minimum 2.0s spacing between alerts
        self.pair_3d_cache: Dict[Tuple[int, int], Tuple[int, float]] = {}

    def _get_spatial_candidates(self, persons: List[Any], proximity_thresh: float) -> List[Tuple[Any, Any]]:
        n = len(persons)
        if n < 2:
            return []
        
        if n <= 15:
            candidates = []
            for i in range(n):
                c1 = persons[i].get_center()
                for j in range(i + 1, n):
                    self.stats['pairs_materialized'] += 1
                    c2 = persons[j].get_center()
                    if math.hypot(c1[0] - c2[0], c1[1] - c2[1]) <= proximity_thresh:
                        candidates.append((persons[i], persons[j]))
                    else:
                        self.stats['pairs_rejected_spatially'] += 1
            return candidates

        cell_size = max(50.0, proximity_thresh * 1.2)
        grid = defaultdict(list)
        for p in persons:
            cx, cy = p.get_center()
            grid[(int(cx // cell_size), int(cy // cell_size))].append(p)

        candidates = []
        seen_pairs = set()
        for (gx, gy), cell_persons in grid.items():
            neighbor_cells = [(gx + dx, gy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
            for n_cell in neighbor_cells:
                if n_cell not in grid:
                    continue
                for p1 in cell_persons:
                    for p2 in grid[n_cell]:
                        if p1.track_id >= p2.track_id:
                            continue
                        pair_id = (p1.track_id, p2.track_id)
                        if pair_id in seen_pairs:
                            continue
                        seen_pairs.add(pair_id)
                        self.stats['pairs_materialized'] += 1
                        c1 = p1.get_center()
                        c2 = p2.get_center()
                        if math.hypot(c1[0] - c2[0], c1[1] - c2[1]) <= proximity_thresh:
                            candidates.append((p1, p2))
                        else:
                            self.stats['pairs_rejected_spatially'] += 1

        self.stats['candidates_generated'] += len(candidates)
        return candidates

    def process_frame(
        self, 
        memory: Any, 
        frame_idx: int, 
        video_id: str, 
        crowd_features: Any = None, 
        pose_data: Any = None,
        verifier_3d: Any = None
    ) -> List[Dict[str, Any]]:
        active_persons = [state for state in memory.objects.values() if state.class_id == 0]
        n = len(active_persons)
        if n < 2:
            return []

        candidates = self._get_spatial_candidates(active_persons, self.config.violence_proximity_thresh)
        events = []

        for p1, p2 in candidates:
            pair_key = (min(p1.track_id, p2.track_id), max(p1.track_id, p2.track_id))
            
            # Step 1: Rapid 2D Kinematics Evidence Evaluation
            ev_res = ViolenceEvidenceEvaluator.evaluate_pair_evidence(
                p1, p2, crowd_features=crowd_features, score_3d=0.0, pose_data=pose_data
            )
            conf_2d = ev_res.final_confidence
            current_pers = self.temporal_tracker.state_acc.get(pair_key, 0)

            # Step 2: Candidate-Gated 3D Verification with 6-frame temporal stride cache
            # Only trigger heavy 3D spatio-temporal CNN when 2D kinematics detect suspicious interaction (conf_2d >= 0.40 or current_pers >= 2)
            score_3d = 0.0
            meta_3d = {}
            last_f, last_s = self.pair_3d_cache.get(pair_key, (-999, 0.0))
            if verifier_3d is not None and (conf_2d >= 0.40 or current_pers >= 2):
                if (frame_idx - last_f) >= 6:
                    score_3d, meta_3d = verifier_3d.verify_candidate_action(
                        stream_id=video_id,
                        domain="violence",
                        bboxes=[p1.bbox, p2.bbox],
                        current_frame_idx=frame_idx
                    )
                    self.pair_3d_cache[pair_key] = (frame_idx, score_3d)
                else:
                    score_3d = last_s
                
                ev_res = ViolenceEvidenceEvaluator.evaluate_pair_evidence(
                    p1, p2, crowd_features=crowd_features, score_3d=score_3d, pose_data=pose_data
                )

            conf, supp, reasons = ev_res[0], ev_res[1], ev_res[2]
            breakdown = getattr(ev_res, 'explainability', ev_res[3] if len(ev_res) > 3 else {})

            is_active = conf >= 0.50
            persistence = self.temporal_tracker.update_pair(pair_key, is_active)
            decision = ViolenceDecisionEngine.make_decision(pair_key, conf, persistence, self.config.violence_duration_thresh, reasons)

            if decision.state == 'CONFIRMED' and decision.confidence >= 0.45:
                last_pair_frame = self.last_alert_frame.get(pair_key, -999999)
                is_pair_ready = (frame_idx - last_pair_frame) >= self.alert_cooldown_frames
                is_global_ready = (frame_idx - self.global_last_alert_frame) >= self.global_alert_cooldown_frames
                if is_pair_ready and is_global_ready:
                    self.last_alert_frame[pair_key] = frame_idx
                    self.global_last_alert_frame = frame_idx
                    event_id = self.temporal_tracker.get_episode_id(pair_key)
                    ev_dict = {
                        'id': event_id,
                        'type': 'violence',
                        'event_type': 'violence',
                        'event_category': 'VIOLENCE',
                        'confidence': decision.confidence,
                        'risk_score': round(decision.confidence * 100.0, 1),
                        'start_frame': max(0, frame_idx - persistence),
                        'end_frame': frame_idx,
                        'involved_tracks': list(pair_key),
                        'affected_persons': [p1.track_id, p2.track_id],
                        'bboxes': [p1.bbox, p2.bbox],
                        'details': f'Physical violence detected between Person #{p1.track_id} and Person #{p2.track_id}',
                        'video_id': video_id,
                        'reasons': decision.reason_codes,
                        'explainability': {
                            "evidence_2d": breakdown.get("evidence_2d", 0.0) if isinstance(breakdown, dict) else 0.0,
                            "evidence_pose": breakdown.get("evidence_pose", 0.0) if isinstance(breakdown, dict) else 0.0,
                            "evidence_3d": breakdown.get("evidence_3d", 0.0) if isinstance(breakdown, dict) else 0.0,
                            "crowd_suppression": breakdown.get("crowd_suppression", 0.0) if isinstance(breakdown, dict) else 0.0,
                            "persistence_frames": persistence,
                            "3d_meta": meta_3d
                        },
                        'snapshot_path': f'/videos/snapshots/{event_id}.jpg',
                        'timestamp': time.time()
                    }
                    events.append(ev_dict)

        return events

ViolenceDetector = ViolenceDomainDetector
