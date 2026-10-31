import unittest
import sys
import os
import time

sys.path.insert(0, os.path.abspath('ai_worker/src'))

from domains.collision.config import CollisionConfig
from domains.collision.contracts import (
    CollisionType,
    CollisionState,
    CollisionCandidateDTO
)
from domains.collision.evidence import CollisionEvidenceEvaluator
from domains.collision.temporal import CollisionTemporalTracker
from domains.collision.decision import CollisionDecisionEngine
from domains.collision.detector import CollisionDomainDetector
from domains.violence.detector import ViolenceDomainDetector

class DummyTrack:
    def __init__(self, track_id: int, class_id: int, bbox, velocity=0.0, acceleration=0.0, confidence=0.90):
        self.track_id = track_id
        self.class_id = class_id
        self.bbox = bbox
        self.velocity = velocity
        self.acceleration = acceleration
        self.confidence = confidence
        self.history = [(0, bbox), (1, bbox), (2, bbox), (3, bbox)]
        self.lost_state = False

    def get_center(self):
        return ((self.bbox[0]+self.bbox[2])/2.0, (self.bbox[1]+self.bbox[3])/2.0)

class TestAdversarialCollisionRules(unittest.TestCase):
    def setUp(self):
        self.config = CollisionConfig()
        self.evaluator = CollisionEvidenceEvaluator(self.config)
        self.tracker = CollisionTemporalTracker(self.config)

    def test_01_cross_domain_isolation(self):
        v_det = ViolenceDomainDetector()
        c_det = CollisionDomainDetector()
        self.assertNotEqual(id(v_det), id(c_det))
        self.assertFalse(hasattr(v_det, 'collision_detector'))
        self.assertFalse(hasattr(c_det, 'violence_detector'))

    def test_02_proximity_alone_never_confirms_collision(self):
        v1 = DummyTrack(1, 2, [100, 100, 200, 200], velocity=0.0, acceleration=0.0)
        v2 = DummyTrack(2, 2, [105, 100, 205, 200], velocity=0.0, acceleration=0.0)
        cand = CollisionCandidateDTO(
            pair_key=(1, 2),
            collision_type=CollisionType.VEHICLE_VEHICLE,
            track_id_1=1,
            track_id_2=2,
            class_id_1=2,
            class_id_2=2,
            spatial_distance=5.0,
            ground_distance=5.0,
            iou_overlap=0.85,
            relative_speed=0.0,
            approach_rate=0.0,
            cosine_similarity=1.0,
            timestamp=time.time()
        )
        evidence = self.evaluator.evaluate_evidence(cand, v1, v2)
        self.assertLess(evidence.final_confidence, 0.40)
        dec = self.tracker.update((1, 2), evidence, frame_idx=0)
        self.assertNotEqual(dec.state, CollisionState.CONFIRMED)

    def test_03_camera_shake_suppression(self):
        v1 = DummyTrack(1, 2, [100, 100, 200, 200], velocity=4.0, acceleration=-1.0)
        v2 = DummyTrack(2, 2, [150, 100, 250, 200], velocity=4.0, acceleration=-1.0)
        cand = CollisionCandidateDTO(
            pair_key=(1, 2),
            collision_type=CollisionType.VEHICLE_VEHICLE,
            track_id_1=1,
            track_id_2=2,
            class_id_1=2,
            class_id_2=2,
            spatial_distance=50.0,
            ground_distance=50.0,
            iou_overlap=0.05,
            relative_speed=0.0,
            approach_rate=0.0,
            cosine_similarity=1.0,
            timestamp=time.time()
        )
        camera_ctx = {'camera_motion_type': 'SHAKE', 'camera_motion_magnitude': 6.5}
        evidence = self.evaluator.evaluate_evidence(cand, v1, v2, camera_context=camera_ctx)
        self.assertIn('CAMERA_MOTION_COMPENSATION_DISCOUNT', evidence.reason_codes)
        self.assertLess(evidence.final_confidence, 0.35)

if __name__ == '__main__':
    unittest.main()
