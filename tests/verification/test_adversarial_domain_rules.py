import unittest, sys, os, time
sys.path.insert(0, os.path.abspath('ai_worker/src'))
from domains.violence.temporal import ViolenceTemporalTracker
from domains.violence.evidence import ViolenceEvidenceEvaluator
from domains.violence.decision import ViolenceDecisionEngine

class DummyTrack:
    def __init__(self, track_id: int, center=(100, 100), velocity=0.0, acceleration=0.0, bbox=(80, 50, 120, 150)):
        self.track_id = track_id
        self.center = center
        self.velocity = velocity
        self.acceleration = acceleration
        self.bbox = bbox
        
    def get_center(self):
        return self.center

class TestAdversarialDomainRules(unittest.TestCase):
    def test_proximity_alone_never_confirms_violence(self):
        # High proximity (dist=10px), but zero velocity and zero acceleration
        p1 = DummyTrack(1, (100, 100), velocity=0.0, acceleration=0.0)
        p2 = DummyTrack(2, (105, 100), velocity=0.0, acceleration=0.0)
        
        conf, supp, reasons = ViolenceEvidenceEvaluator.evaluate_pair_evidence(p1, p2)
        # Proximity alone adds 0.20 confidence
        self.assertLess(conf, 0.50, 'Proximity alone confidence MUST be less than 0.50 candidate threshold.')
        
        decision = ViolenceDecisionEngine.make_decision((1, 2), conf, persistence=50, duration_thresh=15, reasons=reasons)
        self.assertNotEqual(decision.state, 'CONFIRMED', 'Proximity alone MUST NEVER confirm violence.')
        self.assertIn(decision.state, ['REJECTED', 'CANDIDATE'])

    def test_episode_deduplication_preserves_single_uuid(self):
        tracker = ViolenceTemporalTracker(duration_thresh=15)
        pair = (10, 20)
        
        id_frame_1 = tracker.get_episode_id(pair)
        for frame in range(1, 101):
            tracker.update_pair(pair, active=True)
            current_id = tracker.get_episode_id(pair)
            self.assertEqual(id_frame_1, current_id, f'Frame {frame}: Episode UUID MUST remain constant during ongoing incident.')

    def test_temporal_ttl_memory_cleanup(self):
        tracker = ViolenceTemporalTracker(duration_thresh=15, max_ttl_seconds=0.1)
        # Populate 1,000 inactive track pairs
        for i in range(1000):
            pair = (i, i + 1000)
            tracker.update_pair(pair, active=False)
            
        self.assertEqual(len(tracker.state_acc), 0, 'Inactive pairs MUST be pruned to prevent unbounded memory leak.')

if __name__ == '__main__':
    unittest.main()
