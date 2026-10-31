import os
import sys
import unittest
import time
from typing import List

# Ensure ai_worker/src is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai_worker', 'src'))

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

class MockObjectState:
    def __init__(self, track_id: int, class_id: int, bbox: List[float], velocity: float = 0.0, acceleration: float = 0.0, confidence: float = 0.90):
        self.track_id = track_id
        self.class_id = class_id
        self.bbox = bbox
        self.velocity = velocity
        self.acceleration = acceleration
        self.confidence = confidence
        self.lost_state = False
        c = ((bbox[0]+bbox[2])/2.0, (bbox[1]+bbox[3])/2.0)
        self.history = [(0, bbox), (1, bbox), (2, bbox), (3, bbox)]

    def get_center(self):
        return ((self.bbox[0]+self.bbox[2])/2.0, (self.bbox[1]+self.bbox[3])/2.0)

class MockMemory:
    def __init__(self, objects):
        self.objects = objects

class TestCollisionDomain(unittest.TestCase):
    def setUp(self):
        self.config = CollisionConfig()
        self.evaluator = CollisionEvidenceEvaluator(self.config)
        self.tracker = CollisionTemporalTracker(self.config)
        self.detector = CollisionDomainDetector(config=self.config)

    def test_01_parked_vehicles_no_collision(self):
        v1 = MockObjectState(1, 2, [100, 100, 200, 200], velocity=0.2, acceleration=0.0)
        v2 = MockObjectState(2, 2, [150, 100, 250, 200], velocity=0.1, acceleration=0.0)
        cand = CollisionCandidateDTO(
            pair_key=(1, 2),
            collision_type=CollisionType.VEHICLE_VEHICLE,
            track_id_1=1,
            track_id_2=2,
            class_id_1=2,
            class_id_2=2,
            spatial_distance=50.0,
            ground_distance=50.0,
            iou_overlap=0.33,
            relative_speed=0.1,
            approach_rate=0.0,
            cosine_similarity=1.0,
            timestamp=time.time()
        )
        evidence = self.evaluator.evaluate_evidence(cand, v1, v2)
        self.assertIn('STATIONARY_PARKED_VEHICLE_SUPPRESSION', evidence.reason_codes)
        self.assertLess(evidence.final_confidence, 0.40)

    def test_02_parallel_traffic_flow_suppression(self):
        v1 = MockObjectState(1, 2, [100, 100, 200, 200], velocity=8.0, acceleration=0.0)
        v2 = MockObjectState(2, 2, [100, 250, 200, 350], velocity=8.2, acceleration=0.0)
        cand = CollisionCandidateDTO(
            pair_key=(1, 2),
            collision_type=CollisionType.VEHICLE_VEHICLE,
            track_id_1=1,
            track_id_2=2,
            class_id_1=2,
            class_id_2=2,
            spatial_distance=150.0,
            ground_distance=150.0,
            iou_overlap=0.0,
            relative_speed=0.2,
            approach_rate=0.0,
            cosine_similarity=0.98,
            timestamp=time.time()
        )
        evidence = self.evaluator.evaluate_evidence(cand, v1, v2)
        self.assertIn('PARALLEL_TRAFFIC_FLOW_SUPPRESSION', evidence.reason_codes)
        self.assertLess(evidence.final_confidence, 0.30)

    def test_03_pedestrian_near_parked_car_suppression(self):
        v1 = MockObjectState(1, 2, [100, 100, 200, 200], velocity=0.1, acceleration=0.0)
        p1 = MockObjectState(2, 0, [150, 120, 190, 200], velocity=1.2, acceleration=0.0)
        cand = CollisionCandidateDTO(
            pair_key=(1, 2),
            collision_type=CollisionType.VEHICLE_PEDESTRIAN,
            track_id_1=1,
            track_id_2=2,
            class_id_1=2,
            class_id_2=0,
            spatial_distance=40.0,
            ground_distance=40.0,
            iou_overlap=0.10,
            relative_speed=1.1,
            approach_rate=0.0,
            cosine_similarity=1.0,
            timestamp=time.time()
        )
        evidence = self.evaluator.evaluate_evidence(cand, v1, p1)
        self.assertIn('PEDESTRIAN_NEAR_PARKED_VEHICLE_SUPPRESSION', evidence.reason_codes)
        self.assertLess(evidence.final_confidence, 0.35)

    def test_04_vehicle_vehicle_head_on_impact_positive(self):
        v1 = MockObjectState(1, 2, [100, 100, 200, 200], velocity=12.0, acceleration=-8.0)
        v2 = MockObjectState(2, 2, [180, 100, 280, 200], velocity=10.0, acceleration=-7.5)
        cand = CollisionCandidateDTO(
            pair_key=(1, 2),
            collision_type=CollisionType.VEHICLE_VEHICLE,
            track_id_1=1,
            track_id_2=2,
            class_id_1=2,
            class_id_2=2,
            spatial_distance=30.0,
            ground_distance=30.0,
            iou_overlap=0.18,
            relative_speed=22.0,
            approach_rate=-12.0,
            cosine_similarity=-0.95,
            timestamp=time.time()
        )
        evidence = self.evaluator.evaluate_evidence(cand, v1, v2)
        self.assertIn('HEAD_ON_CONVERGING_TRAJECTORIES', evidence.reason_codes)
        self.assertIn('ABRUPT_IMPACT_DECELERATION_SPIKE', evidence.reason_codes)
        self.assertGreaterEqual(evidence.final_confidence, 0.65)

        for f in range(10):
            decision = self.tracker.update((1, 2), evidence, frame_idx=f)
        self.assertEqual(decision.state, CollisionState.CONFIRMED)
        self.assertIsNotNone(decision.event_id)

    def test_05_vehicle_pedestrian_direct_impact_positive(self):
        v1 = MockObjectState(1, 2, [100, 100, 200, 200], velocity=15.0, acceleration=-6.0)
        p1 = MockObjectState(2, 0, [140, 120, 180, 200], velocity=2.0, acceleration=-2.0)
        cand = CollisionCandidateDTO(
            pair_key=(1, 2),
            collision_type=CollisionType.VEHICLE_PEDESTRIAN,
            track_id_1=1,
            track_id_2=2,
            class_id_1=2,
            class_id_2=0,
            spatial_distance=25.0,
            ground_distance=25.0,
            iou_overlap=0.15,
            relative_speed=13.0,
            approach_rate=-8.0,
            cosine_similarity=-0.30,
            timestamp=time.time()
        )
        evidence = self.evaluator.evaluate_evidence(cand, v1, p1)
        self.assertIn('VEHICLE_PEDESTRIAN_DIRECT_IMPACT_OVERRIDE', evidence.reason_codes)
        self.assertGreaterEqual(evidence.final_confidence, 0.70)

    def test_06_episode_deduplication_stable_uuid(self):
        tracker = CollisionTemporalTracker(self.config)
        v1 = MockObjectState(10, 2, [100, 100, 200, 200], velocity=10.0, acceleration=-6.0)
        v2 = MockObjectState(20, 2, [160, 100, 260, 200], velocity=10.0, acceleration=-6.0)
        cand = CollisionCandidateDTO(
            pair_key=(10, 20),
            collision_type=CollisionType.VEHICLE_VEHICLE,
            track_id_1=10,
            track_id_2=20,
            class_id_1=2,
            class_id_2=2,
            spatial_distance=40.0,
            ground_distance=40.0,
            iou_overlap=0.20,
            relative_speed=20.0,
            approach_rate=-6.0,
            cosine_similarity=-0.80,
            timestamp=time.time()
        )
        evidence = self.evaluator.evaluate_evidence(cand, v1, v2)
        
        event_ids = []
        for f in range(50):
            dec = tracker.update((10, 20), evidence, frame_idx=f)
            if dec.state == CollisionState.CONFIRMED:
                event_ids.append(dec.event_id)

        self.assertGreater(len(event_ids), 30)
        self.assertEqual(len(set(event_ids)), 1, 'Multiple frames in 1 physical collision must produce exactly 1 unique stable event UUID')

    def test_07_temporal_ttl_memory_cleanup(self):
        tracker = CollisionTemporalTracker(self.config)
        v1 = MockObjectState(1, 2, [100, 100, 200, 200])
        v2 = MockObjectState(2, 2, [150, 100, 250, 200])
        cand = CollisionCandidateDTO(
            pair_key=(1, 2),
            collision_type=CollisionType.VEHICLE_VEHICLE,
            track_id_1=1,
            track_id_2=2,
            class_id_1=2,
            class_id_2=2,
            spatial_distance=50.0,
            ground_distance=50.0,
            iou_overlap=0.1,
            relative_speed=0.0,
            approach_rate=0.0,
            cosine_similarity=1.0,
            timestamp=100.0
        )
        evidence = self.evaluator.evaluate_evidence(cand, v1, v2)
        tracker.update((1, 2), evidence, frame_idx=0, timestamp=100.0)
        self.assertEqual(len(tracker.state_acc), 1)

        evicted = tracker.cleanup_expired_keys(current_time=150.0)
        self.assertEqual(evicted, 1)
        self.assertEqual(len(tracker.state_acc), 0)

if __name__ == '__main__':
    unittest.main()
